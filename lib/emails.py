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
def rapport_hebdomadaire(debut: date, fin: date, par_commerce: list[dict]) -> tuple[str, str, str]:
    """`par_commerce` : [{nom, contact, phone, email, commandes:[...], total, lignes:[...]}]."""
    sujet = f"Commandes Mine de Ketchup — {debut.isoformat()} au {fin.isoformat()}"

    if not par_commerce:
        corps = (
            f'<p style="margin-top:0;">Aucune commande reçue entre le '
            f"<strong>{debut.isoformat()}</strong> et le <strong>{fin.isoformat()}</strong>.</p>"
        )
        texte = f"Aucune commande entre le {debut} et le {fin}.\n"
        return sujet, _shell("Rapport hebdomadaire", corps), texte

    total_general = sum(c["total"] for c in par_commerce if c["total"] is not None)
    prix_manquants = any(
        ligne.get("price") is None for c in par_commerce for ligne in c["lignes"]
    )

    blocs = []
    for commerce in par_commerce:
        coordonnees = " · ".join(
            v for v in (commerce.get("contact"), commerce.get("phone"), commerce.get("email")) if v
        )
        blocs.append(
            f'<div style="margin:22px 0 0 0;">'
            f'<div style="font-size:16px;font-weight:700;">{_esc(commerce["nom"])}</div>'
            + (
                f'<div style="font-size:13px;color:{GRIS};margin-top:2px;">{_esc(coordonnees)}</div>'
                if coordonnees
                else ""
            )
            + f'<div style="font-size:13px;color:{GRIS};margin-top:2px;">'
            f'{len(commerce["commandes"])} commande(s) : {_esc(", ".join(commerce["commandes"]))}</div>'
            + _table_lignes(commerce["lignes"])
            + f'<div align="right" style="font-weight:700;font-size:15px;">'
            f'Sous-total : {money(commerce["total"]) or "—"}</div></div>'
        )

    note = ""
    if prix_manquants:
        note = (
            f'<div style="background:#FFF4E5;border-left:3px solid #D08700;padding:10px 12px;'
            f'border-radius:6px;margin-top:18px;font-size:13px;">'
            f"Certains produits n'ont pas de prix dans le catalogue : leurs lignes "
            f"apparaissent sans montant et ne sont pas comptées dans les totaux.</div>"
        )

    corps = (
        f'<p style="margin-top:0;">Commandes reçues du <strong>{debut.isoformat()}</strong> '
        f"au <strong>{fin.isoformat()}</strong> (commandes annulées exclues).</p>"
        + "".join(blocs)
        + f'<div align="right" style="margin-top:22px;padding-top:12px;'
        f'border-top:2px solid {ENCRE};font-size:17px;font-weight:700;">'
        f'Total de la période : {money(total_general) or "—"}</div>'
        + note
        + f'<p style="font-size:13px;color:{GRIS};margin-top:18px;">'
        f"Le détail ligne par ligne est joint en CSV, prêt à importer.</p>"
    )

    texte_blocs = []
    for commerce in par_commerce:
        texte_blocs.append(
            f"{commerce['nom']} — {len(commerce['commandes'])} commande(s)\n"
            + _lignes_texte(commerce["lignes"])
            + f"\n  Sous-total : {money(commerce['total']) or '—'}\n"
        )
    texte = (
        f"Commandes du {debut} au {fin}\n\n"
        + "\n".join(texte_blocs)
        + f"\nTotal de la période : {money(total_general) or '—'}\n"
    )
    return sujet, _shell("Rapport hebdomadaire", corps), texte


def rapport_csv(par_commerce: list[dict]) -> bytes:
    """Une ligne par article commandé — format d'import pour la comptabilité."""
    tampon = io.StringIO()
    writer = csv.writer(tampon, delimiter=";")
    writer.writerow(
        ["Date", "Commerce", "Contact", "Courriel", "Téléphone", "Commande",
         "Statut", "Produit", "Format", "Quantité", "Prix unitaire", "Total ligne"]
    )
    for commerce in par_commerce:
        for ligne in commerce["lignes"]:
            prix = ligne.get("price")
            quantite = float(ligne["quantity"])
            writer.writerow([
                ligne.get("date", ""),
                commerce["nom"],
                commerce.get("contact") or "",
                commerce.get("email") or "",
                commerce.get("phone") or "",
                ligne.get("ref", ""),
                ligne.get("status", ""),
                ligne["product_name"],
                ligne.get("unit") or "",
                f"{quantite:g}",
                f"{float(prix):.2f}".replace(".", ",") if prix is not None else "",
                f"{quantite * float(prix):.2f}".replace(".", ",") if prix is not None else "",
            ])
    # BOM UTF-8 : sans lui, Excel en français massacre les accents.
    return tampon.getvalue().encode("utf-8-sig")
