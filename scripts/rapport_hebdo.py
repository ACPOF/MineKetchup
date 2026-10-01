#!/usr/bin/env python3
"""
Rapport des commandes pour la comptable.

Lancé chaque lundi par GitHub Actions (.github/workflows/rapport-hebdomadaire.yml),
et exécutable à la main pour rattraper une période :

    python scripts/rapport_hebdo.py                      # semaine précédente
    python scripts/rapport_hebdo.py --jours 30
    python scripts/rapport_hebdo.py --debut 2026-09-01 --fin 2026-09-30
    python scripts/rapport_hebdo.py --essai               # affiche sans envoyer

Ne dépend pas de Streamlit : il tourne dans GitHub Actions, où l'app n'existe
pas. Il utilise la clé service_role, qui doit rester dans les secrets.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import OrderedDict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase import create_client  # noqa: E402

from lib import emails, mailer, settings  # noqa: E402

FUSEAU = ZoneInfo("America/Toronto")
EXCLUS = {"annulée"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("rapport")


def semaine_precedente(aujourdhui: date) -> tuple[date, date]:
    """Lundi au dimanche de la semaine qui précède celle d'aujourd'hui."""
    lundi_courant = aujourdhui - timedelta(days=aujourdhui.weekday())
    debut = lundi_courant - timedelta(days=7)
    return debut, debut + timedelta(days=6)


def bornes_utc(debut: date, fin: date) -> tuple[str, str]:
    """Journées locales complètes -> bornes ISO exploitables par PostgREST."""
    depuis = datetime.combine(debut, time.min, tzinfo=FUSEAU)
    jusqua = datetime.combine(fin + timedelta(days=1), time.min, tzinfo=FUSEAU)
    return depuis.isoformat(), jusqua.isoformat()


def verifier_configuration(envoi_reel: bool, destinataire_fourni: bool) -> None:
    """Nomme d'un coup tout ce qui manque, plutôt qu'une panne à la fois.

    Une configuration se met en place en une fois : autant lister les huit
    secrets manquants ensemble que les découvrir un par un, à chaque relance.
    """
    requis = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    if envoi_reel:
        requis += ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]
        if not destinataire_fourni:
            requis.append("ACCOUNTANT_EMAIL")

    manquants = [nom for nom in requis if not settings.get(nom)]
    if manquants:
        raise SystemExit(
            "Configuration incomplète — ces valeurs sont vides : "
            + ", ".join(manquants)
            + ".\n\nDans GitHub Actions, ce sont des secrets de dépôt : "
            "Settings > Secrets and variables > Actions > New repository secret. "
            "Un nom, une valeur, sans guillemets. En local, elles peuvent aussi "
            "venir de .streamlit/secrets.toml."
        )


def client_admin():
    url = settings.get_compact("SUPABASE_URL").rstrip("/")
    cle = settings.get_compact("SUPABASE_SERVICE_ROLE_KEY")

    if not url.startswith("https://"):
        raise SystemExit(
            f"SUPABASE_URL ne ressemble pas à une adresse : « {url[:40]} ». "
            "Attendu : https://xxxxxxxx.supabase.co (Supabase > Project "
            "Settings > API > Project URL)."
        )
    # Une clé Supabase est un JWT : trois parties séparées par des points.
    if cle.count(".") != 2:
        raise SystemExit(
            f"SUPABASE_SERVICE_ROLE_KEY ne ressemble pas à une clé Supabase "
            f"({len(cle)} caractères, {cle.count('.') + 1} partie(s) au lieu de 3). "
            "Recopiez-la avec le bouton de copie de Supabase > Project Settings "
            "> API > service_role, plutôt qu'en sélectionnant le texte."
        )
    logger.info("Supabase : %s (clé de %d caractères)", url, len(cle))
    return create_client(url, cle)


def _commandes_de_la_periode(client, debut: date, fin: date) -> tuple[list[dict], bool]:
    """Commandes dont le STATUT a bougé pendant la période.

    C'est la bonne borne pour la comptabilité : une commande passée il y a
    trois semaines et livrée lundi se facture cette semaine-ci. Repli sur
    `created_at` si la colonne n'existe pas encore — le script reste
    utilisable tant que le schéma n'a pas été réexécuté.
    """
    depuis, jusqua = bornes_utc(debut, fin)
    select = "*, retailers(business_name, contact_name, phone, email)"
    try:
        res = (
            client.table("orders").select(select)
            .gte("status_changed_at", depuis).lt("status_changed_at", jusqua)
            .order("status_changed_at").execute()
        )
        return res.data or [], True
    except Exception as exc:  # noqa: BLE001 — colonne absente : schéma pas à jour
        logger.warning(
            "Colonne status_changed_at introuvable (%s). Repli sur la date de "
            "commande : réexécutez supabase_schema.sql pour le suivi des statuts.",
            type(exc).__name__,
        )
        res = (
            client.table("orders").select(select)
            .gte("created_at", depuis).lt("created_at", jusqua)
            .order("created_at").execute()
        )
        return res.data or [], False


def rassembler(client, debut: date, fin: date) -> dict:
    """Deux sections : le détail à facturer, puis le reste en résumé.

    - « facturables » : commandes passées à « complétée » pendant la période,
      détaillées par commerce et par commande ;
    - « mouvements » : toutes les autres commandes dont le statut a bougé,
      en une ligne chacune — de quoi savoir ce qui s'en vient.
    """
    commandes, suivi_statuts = _commandes_de_la_periode(client, debut, fin)
    if not commandes:
        return {"facturables": [], "mouvements": [], "suivi_statuts": suivi_statuts}

    ids = {c["id"] for c in commandes}
    articles = (client.table("order_items").select("*").execute()).data or []
    par_commande: dict[str, list[dict]] = {}
    for article in articles:
        if article["order_id"] in ids:
            par_commande.setdefault(article["order_id"], []).append(article)

    groupes: OrderedDict[str, dict] = OrderedDict()
    mouvements: list[dict] = []

    for commande in commandes:
        lie = commande.get("retailers") or {}
        nom = lie.get("business_name") or commande.get("retailer_name") or "Commerce inconnu"
        ref = str(commande["id"]).split("-")[0].upper()
        jour = str(commande["created_at"])[:10]
        bouge_le = str(commande.get("status_changed_at") or commande["created_at"])[:10]
        statut = commande.get("status", "")

        lignes = [
            {**article, "date": jour, "ref": ref, "status": statut, "change_le": bouge_le}
            for article in par_commande.get(commande["id"], [])
        ]
        total = sum(
            float(a["quantity"]) * float(a["price"])
            for a in lignes
            if a.get("price") is not None
        )

        if statut == "complétée":
            groupe = groupes.setdefault(
                nom,
                {
                    "nom": nom,
                    "contact": lie.get("contact_name") or commande.get("contact_name"),
                    "phone": lie.get("phone") or commande.get("phone"),
                    "email": lie.get("email") or commande.get("email"),
                    "commandes": [],
                    "lignes": [],
                    "total": 0.0,
                },
            )
            groupe["commandes"].append(
                {"ref": ref, "date": jour, "change_le": bouge_le,
                 "status": statut, "lignes": lignes, "total": total}
            )
            groupe["lignes"] += lignes
            groupe["total"] += total
        else:
            mouvements.append(
                {"nom": nom, "ref": ref, "date": jour, "change_le": bouge_le,
                 "status": statut, "total": total, "lignes": lignes}
            )

    return {
        "facturables": sorted(groupes.values(), key=lambda g: g["nom"].lower()),
        "mouvements": sorted(mouvements, key=lambda m: (m["change_le"], m["nom"].lower())),
        "suivi_statuts": suivi_statuts,
    }


def main() -> int:
    parseur = argparse.ArgumentParser(description="Rapport de commandes pour la comptable.")
    parseur.add_argument("--debut", help="Date de début (AAAA-MM-JJ).")
    parseur.add_argument("--fin", help="Date de fin incluse (AAAA-MM-JJ).")
    parseur.add_argument("--jours", type=int, help="Les N derniers jours, fin incluse aujourd'hui.")
    parseur.add_argument("--a", help="Destinataire(s), à la place de ACCOUNTANT_EMAIL.")
    parseur.add_argument("--essai", action="store_true", help="Affiche le rapport sans l'envoyer.")
    parseur.add_argument(
        "--taire-si-vide",
        action="store_true",
        help="N'envoie rien si aucune commande n'a été reçue. Par défaut, le "
        "rapport part quand même : sa seule arrivée confirme que la chaîne "
        "fonctionne, là où un silence ne distingue pas « pas de commande » "
        "de « le rapport est cassé ».",
    )
    args = parseur.parse_args()

    aujourdhui = datetime.now(FUSEAU).date()
    if args.debut or args.fin:
        debut = date.fromisoformat(args.debut) if args.debut else aujourdhui
        fin = date.fromisoformat(args.fin) if args.fin else aujourdhui
    elif args.jours:
        fin = aujourdhui
        debut = fin - timedelta(days=args.jours - 1)
    else:
        debut, fin = semaine_precedente(aujourdhui)
    if debut > fin:
        raise SystemExit(
            f"La date de début ({debut}) est postérieure à la date de fin ({fin}). "
            "Si vous n'avez rempli que « debut », la fin vaut aujourd'hui "
            f"({aujourdhui}) : une date de début dans le futur ne peut rien couvrir."
        )

    verifier_configuration(envoi_reel=not args.essai, destinataire_fourni=bool(args.a))

    logger.info("Période : %s → %s", debut, fin)
    try:
        rapport = rassembler(client_admin(), debut, fin)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — une trace httpx n'aide personne
        raise SystemExit(
            f"Lecture des commandes impossible : {type(exc).__name__} — {exc}\n\n"
            "Si le message parle de « StreamReset » ou de protocole, l'adresse "
            "ou la clé Supabase contient probablement un caractère parasite : "
            "recréez les secrets SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY en "
            "utilisant les boutons de copie de Supabase."
        ) from exc
    vide = not rapport["facturables"] and not rapport["mouvements"]
    logger.info(
        "À facturer : %d commerce(s) ; autres mouvements : %d commande(s)",
        len(rapport["facturables"]),
        len(rapport["mouvements"]),
    )

    if vide and args.taire_si_vide and not args.essai:
        logger.info("Aucune commande, et --taire-si-vide demandé : rien n'est envoyé.")
        return 0

    sujet, html, texte = emails.rapport_hebdomadaire(debut, fin, rapport)
    pieces = (
        None if vide
        else [(f"commandes-{debut}-au-{fin}.csv", emails.rapport_csv(rapport), "text/csv")]
    )

    if args.essai:
        print(f"\n--- SUJET ---\n{sujet}\n\n--- TEXTE ---\n{texte}")
        if pieces:
            print(f"--- PIÈCE JOINTE --- {pieces[0][0]} ({len(pieces[0][1])} octets)")
        return 0

    destinataires = (
        [a.strip() for a in args.a.split(",") if a.strip()]
        if args.a
        else settings.get_list("ACCOUNTANT_EMAIL")
    )
    if not destinataires:
        raise SystemExit("Aucun destinataire : renseignez ACCOUNTANT_EMAIL ou utilisez --a.")

    if mailer.send(destinataires, sujet, html, texte, attachments=pieces):
        logger.info("Rapport envoyé à %s", ", ".join(destinataires))
        return 0
    logger.error("Le rapport n'a pas pu être envoyé.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
