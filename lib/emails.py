"""
Gabarits des courriels envoyés par l'app.

Trois courriels :
  1. nouvelle commande  -> Mine de Ketchup, à chaque commande reçue ;
  2. confirmation       -> le détaillant, s'il a une adresse courriel connue ;
  3. rapport hebdomadaire -> la comptable, pour la facturation.

Choix d'écriture : HTML clair (pas le thème sombre de l'app) avec styles en
ligne et mise en page par tableaux. C'est ce que les clients de messagerie —
Outlook en tête — savent rendre de façon fiable. Chaque courriel a aussi sa
version texte, pour les lecteurs qui n'affichent pas le HTML.
"""

from __future__ import annotations

import csv
import html
import io
from datetime import date

from lib.format import money

ROUGE = "#C43A24"
ENCRE = "#1F1A17"
GRIS = "#6B6158"
BORDURE = "#E3DCD3"
PAPIER = "#FBF8F4"


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _shell(titre: str, corps: str, pied: str = "") -> str:
    """Enveloppe commune : en-tête de marque, corps, pied de page."""
    return f"""\
<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:{PAPIER};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{PAPIER};padding:24px 12px;">
<tr><td align="center">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="max-width:640px;background:#FFFFFF;border:1px solid {BORDURE};
                border-radius:14px;overflow:hidden;
                font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
                color:{ENCRE};">
    <tr><td style="padding:22px 28px 14px 28px;border-bottom:3px solid {ROUGE};">
      <div style="font-size:19px;font-weight:700;letter-spacing:.22em;">MINE</div>
      <div style="font-size:11px;letter-spacing:.2em;color:{GRIS};margin-top:2px;">DE KETCHUP</div>
      <div style="font-size:17px;font-weight:600;margin-top:12px;">{_esc(titre)}</div>
    </td></tr>
    <tr><td style="padding:22px 28px;font-size:15px;line-height:1.55;">{corps}</td></tr>
    <tr><td style="padding:16px 28px 22px 28px;border-top:1px solid {BORDURE};
                   font-size:12px;color:{GRIS};line-height:1.5;">
      {pied or "Courriel automatique — Mine de Ketchup, Padoue, Bas-Saint-Laurent."}
    </td></tr>
  </table>
</td></tr></table></body></html>"""


def _table_lignes(items: list[dict], avec_prix: bool = True) -> str:
    """Tableau des articles d'une commande."""
    entetes = ["Produit", "Qté", "Format"] + (["Prix", "Total"] if avec_prix else [])
    th = "".join(
        f'<th align="{"right" if h in ("Qté", "Prix", "Total") else "left"}" '
        f'style="padding:7px 8px;border-bottom:2px solid {BORDURE};font-size:12px;'
        f'text-transform:uppercase;letter-spacing:.05em;color:{GRIS};">{h}</th>'
        for h in entetes
    )
    lignes = []
    for item in items:
        quantite = float(item["quantity"])
        prix = item.get("price")
        cellules = [
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};">{_esc(item["product_name"])}</td>',
            f'<td align="right" style="padding:8px;border-bottom:1px solid {BORDURE};'
            f'font-weight:600;">{quantite:g}</td>',
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};color:{GRIS};">'
            f'{_esc(item.get("unit") or "")}</td>',
        ]
        if avec_prix:
            total = quantite * float(prix) if prix is not None else None
            cellules += [
                f'<td align="right" style="padding:8px;border-bottom:1px solid {BORDURE};'
                f'color:{GRIS};">{money(prix) or "—"}</td>',
                f'<td align="right" style="padding:8px;border-bottom:1px solid {BORDURE};'
                f'font-weight:600;">{money(total) or "—"}</td>',
            ]
        lignes.append("<tr>" + "".join(cellules) + "</tr>")
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;font-size:14px;margin:10px 0;">'
        f"<tr>{th}</tr>{''.join(lignes)}</table>"
    )


def _lignes_texte(items: list[dict]) -> str:
    return "\n".join(
        f"  - {float(i['quantity']):g} × {i['product_name']} ({i.get('unit') or ''})"
        for i in items
    )


# ------------------------------------------------------------------
# 1. Nouvelle commande -> Mine de Ketchup
# ------------------------------------------------------------------
def nouvelle_commande(commande: dict, items: list[dict], acheteur: dict) -> tuple[str, str, str]:
    """(sujet, html, texte) du courriel d'alerte envoyé à Mine de Ketchup."""
    nom = acheteur.get("business_name") or "Commerce inconnu"
    ref = str(commande["id"]).split("-")[0].upper()
    sujet = f"Nouvelle commande — {nom}"

    avertissement = ""
    if not acheteur.get("registered"):
        avertissement = (
            f'<div style="background:#FFF4E5;border-left:3px solid #D08700;'
            f'padding:10px 12px;border-radius:6px;margin-bottom:14px;font-size:14px;">'
            f"⚠️ Commerce <strong>non enregistré</strong> — cette commande est arrivée "
            f"sans lien personnel. Un bouton du tableau de bord permet de l'enregistrer "
            f"en un clic.</div>"
        )

    details = [("Commerce", nom)]
    for libelle, cle in (("Contact", "contact_name"), ("Téléphone", "phone"), ("Courriel", "email")):
        if acheteur.get(cle):
            details.append((libelle, acheteur[cle]))
    if commande.get("requested_date"):
        details.append(("Date souhaitée", commande["requested_date"]))
    if commande.get("notes"):
        details.append(("Notes", commande["notes"]))

    bloc = "".join(
        f'<tr><td style="padding:3px 12px 3px 0;color:{GRIS};white-space:nowrap;">{_esc(k)}</td>'
        f'<td style="padding:3px 0;font-weight:600;">{_esc(v)}</td></tr>'
        for k, v in details
    )

    corps = (
        f"{avertissement}"
        f'<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="font-size:14px;margin-bottom:6px;">{bloc}</table>'
        f"{_table_lignes(items)}"
        f'<p style="font-size:12px;color:{GRIS};margin-top:16px;">Commande n° {ref}</p>'
    )
    texte = (
        f"Nouvelle commande — {nom}\n\n"
        + "\n".join(f"{k} : {v}" for k, v in details)
        + "\n\nArticles :\n"
        + _lignes_texte(items)
        + f"\n\nCommande n° {ref}\n"
    )
    return sujet, _shell("Nouvelle commande reçue", corps), texte


# ------------------------------------------------------------------
# 2. Confirmation -> le détaillant
# ------------------------------------------------------------------
def confirmation_detaillant(commande: dict, items: list[dict], nom_commerce: str) -> tuple[str, str, str]:
    ref = str(commande["id"]).split("-")[0].upper()
    sujet = f"Votre commande Mine de Ketchup — n° {ref}"

    extras = ""
    if commande.get("requested_date"):
        extras += (
            f'<p style="margin:4px 0;color:{GRIS};font-size:14px;">'
            f"Date de livraison souhaitée : <strong>{_esc(commande['requested_date'])}</strong></p>"
        )
    if commande.get("notes"):
        extras += (
            f'<p style="margin:4px 0;color:{GRIS};font-size:14px;">'
            f"Vos notes : {_esc(commande['notes'])}</p>"
        )

    corps = (
        f"<p style=\"margin-top:0;\">Bonjour,</p>"
        f"<p>Nous avons bien reçu la commande de <strong>{_esc(nom_commerce)}</strong>. "
        f"Merci ! Nous vous contacterons pour la confirmation et la livraison.</p>"
        f"{_table_lignes(items, avec_prix=False)}"
        f"{extras}"
        f'<p style="font-size:12px;color:{GRIS};margin-top:16px;">'
        f"Référence : <strong>{ref}</strong> — à rappeler si vous nous écrivez.</p>"
    )
    texte = (
        f"Bonjour,\n\nNous avons bien reçu la commande de {nom_commerce}. Merci !\n"
        f"Nous vous contacterons pour la confirmation et la livraison.\n\n"
        f"Articles :\n{_lignes_texte(items)}\n\nRéférence : {ref}\n\n"
        f"Mine de Ketchup\n"
    )
    pied = (
        "Aucun paiement n'est traité par ce courriel. Pour toute question, "
        "répondez simplement à ce message."
    )
    return sujet, _shell("Commande bien reçue", corps, pied), texte


# ------------------------------------------------------------------
# 3. Rapport hebdomadaire -> la comptable
# ------------------------------------------------------------------
# Couleurs des pastilles de statut. La comptable doit voir d'un coup d'œil ce
# qui est livré (donc facturable) et ce qui est encore en atelier.
STATUT_COULEUR = {
    "nouvelle": ("#B3261E", "#FDECEA"),
    "en préparation": ("#9A6700", "#FFF4E5"),
    "prête": ("#1B6E3C", "#E8F5EC"),
    "complétée": ("#44524A", "#EDF1EE"),
    "annulée": ("#8A8178", "#F1EEEA"),
}


def _pastille(statut: str) -> str:
    texte, fond = STATUT_COULEUR.get(statut, (GRIS, "#F0ECE7"))
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
        f"background:{fond};color:{texte};font-size:11px;font-weight:700;"
        f'text-transform:uppercase;letter-spacing:.04em;">{_esc(statut)}</span>'
    )


def _bandeau_total(montant: float, nb_commandes: int, nb_commerces: int) -> str:
    """Le chiffre que la comptable cherche en premier, en haut et en gros."""
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{ENCRE};border-radius:12px;margin:4px 0 18px 0;">'
        f'<tr><td style="padding:18px 22px;">'
        f'<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;'
        f'color:#C9BFB4;">À facturer cette semaine</div>'
        f'<div style="font-size:30px;font-weight:700;color:#FFFFFF;margin-top:4px;">'
        f'{money(montant) or "—"}</div>'
        f'<div style="font-size:13px;color:#C9BFB4;margin-top:2px;">'
        f'{nb_commandes} commande(s) complétée(s) · {nb_commerces} commerce(s)</div>'
        f"</td></tr></table>"
    )


def _titre_section(numero: str, titre: str, sous_titre: str) -> str:
    return (
        f'<div style="margin:26px 0 2px 0;padding-bottom:8px;'
        f'border-bottom:2px solid {ENCRE};">'
        f'<span style="display:inline-block;width:22px;height:22px;border-radius:50%;'
        f'background:{ROUGE};color:#fff;font-size:12px;font-weight:700;text-align:center;'
        f'line-height:22px;margin-right:8px;">{numero}</span>'
        f'<span style="font-size:16px;font-weight:700;">{_esc(titre)}</span>'
        f'<div style="font-size:13px;color:{GRIS};margin-top:4px;">{_esc(sous_titre)}</div>'
        f"</div>"
    )


def _tableau_mouvements(mouvements: list[dict]) -> str:
    """Résumé : une ligne par commande qui a changé de statut, sans le détail."""
    entetes = ["Changée le", "Commerce", "N°", "Commandée le", "Statut", "Montant"]
    th = "".join(
        f'<th align="{"right" if h == "Montant" else "left"}" '
        f'style="padding:7px 8px;border-bottom:2px solid {BORDURE};font-size:11px;'
        f'text-transform:uppercase;letter-spacing:.05em;color:{GRIS};">{h}</th>'
        for h in entetes
    )
    lignes = []
    for m in mouvements:
        lignes.append(
            "<tr>"
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};white-space:nowrap;">'
            f'{_esc(m["change_le"])}</td>'
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};font-weight:600;">'
            f'{_esc(m["nom"])}</td>'
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};'
            f'font-family:ui-monospace,Menlo,monospace;font-size:13px;">{_esc(m["ref"])}</td>'
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};color:{GRIS};'
            f'white-space:nowrap;">{_esc(m["date"])}</td>'
            f'<td style="padding:8px;border-bottom:1px solid {BORDURE};">'
            f'{_pastille(m["status"])}</td>'
            f'<td align="right" style="padding:8px;border-bottom:1px solid {BORDURE};'
            f'color:{GRIS};">{money(m["total"]) or "—"}</td>'
            "</tr>"
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;font-size:14px;margin:12px 0;">'
        f"<tr>{th}</tr>{''.join(lignes)}</table>"
    )


def rapport_hebdomadaire(debut: date, fin: date, rapport: dict) -> tuple[str, str, str]:
    """Rapport en deux sections : le détail à facturer, puis ce qui a bougé.

    `rapport` : {"facturables": [...], "mouvements": [...], "suivi_statuts": bool}.
    La période se lit sur la DATE DE CHANGEMENT DE STATUT, pas sur la date de
    commande : une commande d'il y a trois semaines livrée lundi se facture
    cette semaine-ci.
    """
    facturables = rapport.get("facturables") or []
    mouvements = rapport.get("mouvements") or []
    periode = f"{debut.isoformat()} au {fin.isoformat()}"

    if not facturables and not mouvements:
        sujet = f"Aucun mouvement — {periode}"
        corps = (
            f'<p style="margin-top:0;">Aucune commande n\'a été reçue ni modifiée '
            f"entre le <strong>{debut.isoformat()}</strong> et le "
            f"<strong>{fin.isoformat()}</strong>.</p>"
            f'<p style="color:{GRIS};font-size:14px;">Ce courriel est envoyé même '
            f"quand la semaine est vide : s'il arrive, c'est que la prise de "
            f"commande et l'envoi du rapport fonctionnent.</p>"
        )
        texte = (
            f"Aucune commande reçue ni modifiée entre le {debut} et le {fin}.\n\n"
            "Ce courriel est envoyé même quand la semaine est vide : s'il arrive, "
            "c'est que la prise de commande et l'envoi du rapport fonctionnent.\n"
        )
        return sujet, _shell("Rapport hebdomadaire", corps), texte

    total_facturable = sum(c["total"] for c in facturables)
    nb_completees = sum(len(c["commandes"]) for c in facturables)
    sujet = (
        f"À facturer {money(total_facturable) or '—'} — Mine de Ketchup, {periode}"
        if facturables
        else f"Aucune commande à facturer — Mine de Ketchup, {periode}"
    )

    prix_manquants = any(
        ligne.get("price") is None
        for c in facturables
        for ligne in c["lignes"]
    )

    # --- Section 1 : le détail, commerce par commerce
    if facturables:
        blocs = []
        for commerce in facturables:
            coordonnees = " · ".join(
                v for v in (commerce.get("contact"), commerce.get("phone"), commerce.get("email")) if v
            )
            commandes_html = []
            for commande in commerce["commandes"]:
                commandes_html.append(
                    f'<div style="margin-top:12px;">'
                    f'<div style="font-size:13px;color:{GRIS};">'
                    f'<strong style="color:{ENCRE};">n° {_esc(commande["ref"])}</strong> · '
                    f'commandée le {_esc(commande["date"])} · '
                    f'complétée le <strong style="color:{ENCRE};">{_esc(commande["change_le"])}</strong></div>'
                    + _table_lignes(commande["lignes"])
                    + (
                        f'<div align="right" style="font-size:13px;color:{GRIS};">'
                        f'Total de la commande : {money(commande["total"]) or "—"}</div>'
                        if len(commerce["commandes"]) > 1
                        else ""
                    )
                    + "</div>"
                )
            blocs.append(
                f'<div style="margin:22px 0 0 0;padding-top:14px;border-top:1px solid {BORDURE};">'
                f'<div style="font-size:16px;font-weight:700;">{_esc(commerce["nom"])}</div>'
                + (
                    f'<div style="font-size:13px;color:{GRIS};margin-top:2px;">{_esc(coordonnees)}</div>'
                    if coordonnees
                    else ""
                )
                + "".join(commandes_html)
                + f'<div align="right" style="font-weight:700;font-size:15px;margin-top:10px;'
                f'padding-top:8px;border-top:1px solid {BORDURE};">'
                f'À facturer à {_esc(commerce["nom"])} : {money(commerce["total"]) or "—"}</div></div>'
            )
        section1 = (
            _titre_section(
                "1", "Commandes complétées — à facturer",
                "Livrées pendant la période, détaillées par commerce. "
                "La date de commande peut être antérieure.",
            )
            + "".join(blocs)
            + f'<div align="right" style="margin-top:18px;padding-top:10px;'
            f'border-top:2px solid {ENCRE};font-size:17px;font-weight:700;">'
            f'Total à facturer : {money(total_facturable) or "—"}</div>'
        )
    else:
        section1 = _titre_section(
            "1", "Commandes complétées — à facturer",
            "Aucune commande n'est passée à « complétée » pendant la période.",
        )

    # --- Section 2 : le reste, en résumé
    if mouvements:
        section2 = (
            _titre_section(
                "2", "Autres commandes ayant évolué",
                "Reçues ou passées à un autre statut pendant la période. "
                "Pour information : rien à facturer ici.",
            )
            + _tableau_mouvements(mouvements)
        )
    else:
        section2 = _titre_section(
            "2", "Autres commandes ayant évolué",
            "Aucune autre commande n'a changé de statut pendant la période.",
        )

    notes = ""
    if prix_manquants:
        notes += (
            f'<div style="background:#FFF4E5;border-left:3px solid #D08700;padding:10px 12px;'
            f'border-radius:6px;margin-top:18px;font-size:13px;">'
            f"Certains produits n'ont pas de prix dans le catalogue : leurs lignes "
            f"apparaissent sans montant et ne sont pas comptées dans les totaux.</div>"
        )
    if not rapport.get("suivi_statuts", True):
        notes += (
            f'<div style="background:#FFF4E5;border-left:3px solid #D08700;padding:10px 12px;'
            f'border-radius:6px;margin-top:10px;font-size:13px;">'
            f"Le suivi des changements de statut n'est pas encore activé dans la "
            f"base : la période se lit ici sur la date de commande. Réexécutez "
            f"<code>supabase_schema.sql</code> dans Supabase.</div>"
        )

    corps = (
        f'<p style="margin-top:0;color:{GRIS};font-size:14px;">Semaine du '
        f"<strong style=\"color:{ENCRE};\">{debut.isoformat()}</strong> au "
        f"<strong style=\"color:{ENCRE};\">{fin.isoformat()}</strong></p>"
        + _bandeau_total(total_facturable, nb_completees, len(facturables))
        + section1
        + section2
        + notes
        + f'<p style="font-size:13px;color:{GRIS};margin-top:20px;">'
        f"Le détail ligne par ligne des deux sections est joint en CSV.</p>"
    )

    # --- Version texte
    lignes_txt = [f"RAPPORT MINE DE KETCHUP — {periode}", ""]
    lignes_txt.append(
        f"À FACTURER : {money(total_facturable) or '—'} "
        f"({nb_completees} commande(s) complétée(s), {len(facturables)} commerce(s))"
    )
    lignes_txt.append("")
    lignes_txt.append("1. COMMANDES COMPLÉTÉES — À FACTURER")
    if facturables:
        for commerce in facturables:
            lignes_txt.append(f"\n  {commerce['nom']}")
            for commande in commerce["commandes"]:
                lignes_txt.append(
                    f"    n° {commande['ref']} — commandée le {commande['date']}, "
                    f"complétée le {commande['change_le']}"
                )
                lignes_txt.append(_lignes_texte(commande["lignes"]))
            lignes_txt.append(f"    À facturer : {money(commerce['total']) or '—'}")
    else:
        lignes_txt.append("  Aucune.")
    lignes_txt.append("")
    lignes_txt.append("2. AUTRES COMMANDES AYANT ÉVOLUÉ")
    if mouvements:
        for m in mouvements:
            lignes_txt.append(
                f"  {m['change_le']} — {m['nom']} — n° {m['ref']} — "
                f"{m['status']} — {money(m['total']) or '—'}"
            )
    else:
        lignes_txt.append("  Aucune.")
    texte = "\n".join(lignes_txt) + "\n"

    return sujet, _shell("Rapport hebdomadaire", corps), texte


def rapport_csv(rapport: dict) -> bytes:
    """Une ligne par article, les deux sections réunies et distinguées."""
    tampon = io.StringIO()
    writer = csv.writer(tampon, delimiter=";")
    writer.writerow(
        ["Section", "Changée le", "Commandée le", "Commerce", "Contact", "Courriel",
         "Téléphone", "Commande", "Statut", "Produit", "Format", "Quantité",
         "Prix unitaire", "Total ligne"]
    )

    def ecrire(section, ligne, commerce_nom, contact="", courriel="", tel=""):
        prix = ligne.get("price")
        quantite = float(ligne["quantity"])
        writer.writerow([
            section,
            ligne.get("change_le", ""),
            ligne.get("date", ""),
            commerce_nom,
            contact or "",
            courriel or "",
            tel or "",
            ligne.get("ref", ""),
            ligne.get("status", ""),
            ligne["product_name"],
            ligne.get("unit") or "",
            f"{quantite:g}",
            f"{float(prix):.2f}".replace(".", ",") if prix is not None else "",
            f"{quantite * float(prix):.2f}".replace(".", ",") if prix is not None else "",
        ])

    for commerce in rapport.get("facturables") or []:
        for ligne in commerce["lignes"]:
            ecrire("À facturer", ligne, commerce["nom"], commerce.get("contact"),
                   commerce.get("email"), commerce.get("phone"))
    for mouvement in rapport.get("mouvements") or []:
        for ligne in mouvement["lignes"]:
            ecrire("Autre mouvement", ligne, mouvement["nom"])

    # BOM UTF-8 : sans lui, Excel en français massacre les accents.
    return tampon.getvalue().encode("utf-8-sig")
