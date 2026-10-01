"""
Calcul des indicateurs du tableau de bord.

Volontairement sans Streamlit ni pandas : ce sont des fonctions pures, qui
prennent les lignes telles que Supabase les renvoie et rendent des nombres.
C'est ce qui les rend testables, et c'est là que vit la logique métier.

Deux notions de date coexistent, et les confondre fausserait tout :
  - une commande est REÇUE à sa date de création ;
  - une vente est RÉALISÉE quand la commande passe à « complétée ».
Les libellés de l'interface disent toujours laquelle des deux est utilisée.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("America/Toronto")
ANNULEE = "annulée"
COMPLETEE = "complétée"
EN_COURS = ("nouvelle", "en préparation", "prête")


def _moment(valeur) -> datetime | None:
    """Horodatage Supabase -> datetime local, tolérant aux formats."""
    if not valeur:
        return None
    texte = str(valeur).replace("Z", "+00:00")
    try:
        instant = datetime.fromisoformat(texte)
    except ValueError:
        return None
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=FUSEAU)
    return instant.astimezone(FUSEAU)


def _jour(valeur) -> date | None:
    instant = _moment(valeur)
    return instant.date() if instant else None


def _dans(valeur, debut: date, fin: date) -> bool:
    jour = _jour(valeur)
    return jour is not None and debut <= jour <= fin


def periode_precedente(debut: date, fin: date) -> tuple[date, date]:
    """Même durée, juste avant — pour comparer sans biais de longueur."""
    duree = (fin - debut).days + 1
    return debut - timedelta(days=duree), debut - timedelta(days=1)


def _total_commande(lignes: list[dict]) -> float:
    return sum(
        float(l["quantity"]) * float(l["price"])
        for l in lignes
        if l.get("price") is not None
    )


def _lignes_par_commande(items: list[dict]) -> dict[str, list[dict]]:
    groupes: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groupes[item["order_id"]].append(item)
    return groupes


def _nom(commande: dict) -> str:
    lie = commande.get("retailers") or {}
    return lie.get("business_name") or commande.get("retailer_name") or "Commerce inconnu"


def calculer(orders: list[dict], items: list[dict], debut: date, fin: date) -> dict:
    """Indicateurs d'une période. Les montants ignorent les commandes annulées."""
    lignes = _lignes_par_commande(items)

    recues = [
        o for o in orders
        if o.get("status") != ANNULEE and _dans(o.get("created_at"), debut, fin)
    ]
    completees = [
        o for o in orders
        if o.get("status") == COMPLETEE
        and _dans(o.get("status_changed_at") or o.get("created_at"), debut, fin)
    ]

    ventes = sum(_total_commande(lignes.get(o["id"], [])) for o in completees)
    articles = sum(
        float(l["quantity"]) for o in recues for l in lignes.get(o["id"], [])
    )

    # Délai de traitement : seulement là où il a vraiment été mesuré. Les
    # commandes antérieures au suivi des statuts ont status_changed_at =
    # created_at ; les compter à zéro jour embellirait faussement la moyenne.
    delais = []
    for commande in completees:
        depart = _moment(commande.get("created_at"))
        arrivee = _moment(commande.get("status_changed_at"))
        if depart and arrivee and arrivee > depart:
            delais.append((arrivee - depart).total_seconds() / 86400)

    return {
        "ventes": ventes,
        "nb_completees": len(completees),
        "nb_recues": len(recues),
        "panier_moyen": ventes / len(completees) if completees else 0.0,
        "detaillants_actifs": len({_nom(o) for o in recues}),
        "articles": articles,
        "delai_moyen": sum(delais) / len(delais) if delais else None,
        "nb_delais_mesures": len(delais),
        "annulees": sum(
            1 for o in orders
            if o.get("status") == ANNULEE
            and _dans(o.get("status_changed_at") or o.get("created_at"), debut, fin)
        ),
    }


def par_mois(orders: list[dict], items: list[dict], nb_mois: int = 12) -> list[dict]:
    """Série mensuelle : ventes complétées et commandes reçues."""
    lignes = _lignes_par_commande(items)
    aujourdhui = datetime.now(FUSEAU).date()

    mois: list[str] = []
    curseur = aujourdhui.replace(day=1)
    for _ in range(nb_mois):
        mois.append(curseur.strftime("%Y-%m"))
        curseur = (curseur - timedelta(days=1)).replace(day=1)
    mois.reverse()
    connus = set(mois)

    ventes: Counter = Counter()
    recues: Counter = Counter()
    for commande in orders:
        if commande.get("status") == ANNULEE:
            continue
        jour_recu = _jour(commande.get("created_at"))
        if jour_recu and jour_recu.strftime("%Y-%m") in connus:
            recues[jour_recu.strftime("%Y-%m")] += 1
        if commande.get("status") == COMPLETEE:
            jour_fini = _jour(commande.get("status_changed_at") or commande.get("created_at"))
            if jour_fini and jour_fini.strftime("%Y-%m") in connus:
                ventes[jour_fini.strftime("%Y-%m")] += _total_commande(
                    lignes.get(commande["id"], [])
                )

    return [{"mois": m, "ventes": ventes.get(m, 0.0), "commandes": recues.get(m, 0)} for m in mois]


def top_produits(orders: list[dict], items: list[dict], debut: date, fin: date,
                 limite: int = 8) -> list[dict]:
    """Produits les plus commandés sur la période, en quantité."""
    retenues = {
        o["id"] for o in orders
        if o.get("status") != ANNULEE and _dans(o.get("created_at"), debut, fin)
    }
    quantites: Counter = Counter()
    montants: Counter = Counter()
    for item in items:
        if item["order_id"] in retenues:
            quantites[item["product_name"]] += float(item["quantity"])
            if item.get("price") is not None:
                montants[item["product_name"]] += float(item["quantity"]) * float(item["price"])
    return [
        {"produit": nom, "quantite": qte, "montant": montants.get(nom, 0.0)}
        for nom, qte in quantites.most_common(limite)
    ]


def top_detaillants(orders: list[dict], items: list[dict], debut: date, fin: date,
                    limite: int = 8) -> list[dict]:
    """Détaillants les plus actifs sur la période."""
    lignes = _lignes_par_commande(items)
    commandes: Counter = Counter()
    montants: Counter = Counter()
    for commande in orders:
        if commande.get("status") == ANNULEE or not _dans(commande.get("created_at"), debut, fin):
            continue
        nom = _nom(commande)
        commandes[nom] += 1
        montants[nom] += _total_commande(lignes.get(commande["id"], []))
    classe = sorted(
        commandes, key=lambda n: (montants.get(n, 0.0), commandes[n]), reverse=True
    )[:limite]
    return [
        {"detaillant": n, "commandes": commandes[n], "montant": montants.get(n, 0.0)}
        for n in classe
    ]


def pipeline(orders: list[dict], items: list[dict]) -> list[dict]:
    """Commandes en cours — ce qu'il reste à préparer, maintenant."""
    lignes = _lignes_par_commande(items)
    nombres: Counter = Counter()
    montants: Counter = Counter()
    for commande in orders:
        statut = commande.get("status")
        if statut in EN_COURS:
            nombres[statut] += 1
            montants[statut] += _total_commande(lignes.get(commande["id"], []))
    return [
        {"statut": s, "commandes": nombres.get(s, 0), "montant": montants.get(s, 0.0)}
        for s in EN_COURS
    ]


def detaillants_inactifs(orders: list[dict], retailers: list[dict],
                         jours: int = 60) -> list[dict]:
    """Détaillants actifs n'ayant rien commandé depuis `jours` — à relancer."""
    aujourdhui = datetime.now(FUSEAU).date()
    derniere: dict[str, date] = {}
    for commande in orders:
        jour = _jour(commande.get("created_at"))
        if not jour:
            continue
        nom = _nom(commande)
        if nom not in derniere or jour > derniere[nom]:
            derniere[nom] = jour

    dormants = []
    for detaillant in retailers:
        if not detaillant.get("is_active"):
            continue
        nom = detaillant["business_name"]
        vue = derniere.get(nom)
        ecart = (aujourdhui - vue).days if vue else None
        if ecart is None or ecart >= jours:
            dormants.append({
                "detaillant": nom,
                "derniere_commande": vue.isoformat() if vue else "Jamais",
                "jours": ecart,
                "courriel": detaillant.get("email") or "",
            })
    return sorted(dormants, key=lambda d: (d["jours"] is not None, -(d["jours"] or 0)))
