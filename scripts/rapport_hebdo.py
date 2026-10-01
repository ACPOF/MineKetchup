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
    return create_client(
        settings.get("SUPABASE_URL"), settings.get("SUPABASE_SERVICE_ROLE_KEY")
    )


def rassembler(client, debut: date, fin: date) -> list[dict]:
    """Commandes de la période, regroupées par commerce."""
    depuis, jusqua = bornes_utc(debut, fin)
    commandes = (
        client.table("orders")
        .select("*, retailers(business_name, contact_name, phone, email)")
        .gte("created_at", depuis)
        .lt("created_at", jusqua)
        .order("created_at")
        .execute()
    ).data or []
    commandes = [c for c in commandes if c.get("status") not in EXCLUS]
    if not commandes:
        return []

    ids = {c["id"] for c in commandes}
    articles = (client.table("order_items").select("*").execute()).data or []
    par_commande: dict[str, list[dict]] = {}
    for article in articles:
        if article["order_id"] in ids:
            par_commande.setdefault(article["order_id"], []).append(article)

    groupes: OrderedDict[str, dict] = OrderedDict()
    for commande in commandes:
        lie = commande.get("retailers") or {}
        nom = lie.get("business_name") or commande.get("retailer_name") or "Commerce inconnu"
        groupe = groupes.setdefault(
            nom,
            {
                "nom": nom,
                "contact": lie.get("contact_name") or commande.get("contact_name"),
                "phone": lie.get("phone") or commande.get("phone"),
                "email": lie.get("email") or commande.get("email"),
                "commandes": [],   # une entrée par commande, avec son statut
                "lignes": [],      # toutes les lignes à plat, pour le CSV
                "total": 0.0,
            },
        )
        ref = str(commande["id"]).split("-")[0].upper()
        jour = str(commande["created_at"])[:10]
        statut = commande.get("status", "")

        lignes_commande = []
        total_commande = 0.0
        for article in par_commande.get(commande["id"], []):
            ligne = {**article, "date": jour, "ref": ref, "status": statut}
            lignes_commande.append(ligne)
            groupe["lignes"].append(ligne)
            if article.get("price") is not None:
                montant = float(article["quantity"]) * float(article["price"])
                total_commande += montant
                groupe["total"] += montant

        groupe["commandes"].append(
            {
                "ref": ref,
                "date": jour,
                "status": statut,
                "lignes": lignes_commande,
                "total": total_commande,
            }
        )

    return sorted(groupes.values(), key=lambda g: g["nom"].lower())


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
    par_commerce = rassembler(client_admin(), debut, fin)
    logger.info(
        "%d commerce(s), %d ligne(s)",
        len(par_commerce),
        sum(len(c["lignes"]) for c in par_commerce),
    )

    if not par_commerce and args.taire_si_vide and not args.essai:
        logger.info("Aucune commande, et --taire-si-vide demandé : rien n'est envoyé.")
        return 0

    sujet, html, texte = emails.rapport_hebdomadaire(debut, fin, par_commerce)
    pieces = (
        [(f"commandes-{debut}-au-{fin}.csv", emails.rapport_csv(par_commerce), "text/csv")]
        if par_commerce
        else None
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
