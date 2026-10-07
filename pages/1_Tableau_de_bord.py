"""
Mine de Ketchup — tableau de bord de gestion.

Page volontairement absente du menu de navigation : on y accède par son
adresse directe (.../Tableau_de_bord), et elle reste protégée par mot de passe.

Quatre sections, protégées par le même mot de passe (secret ADMIN_PASSWORD) :
  1. Commandes  : consulter les commandes reçues et changer leur statut.
  2. Indicateurs: ventes, commandes, délais, produits et détaillants les plus
                  actifs, et qui relancer.
  3. Produits   : gérer le catalogue (ajouter / modifier / activer / réordonner).
  4. Détaillants: gérer les commerces autorisés à commander. C'est ici qu'on
                  ajoute un détaillant UNE SEULE FOIS et qu'on récupère son
                  lien de commande personnel ; ensuite il commande en 2 clics.

Utilise la clé service_role de Supabase (accès complet), d'où le mot de passe.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from lib import indicateurs as ind
from lib import photos
from lib.branding import BRAND, brand_header, inject_theme, money
from lib.supabase_client import get_admin_client

st.set_page_config(
    page_title="Mine de Ketchup — Tableau de bord",
    page_icon="🍅",
    layout="wide",
)
inject_theme(wide=True)

STATUS_OPTIONS = ["nouvelle", "en préparation", "prête", "complétée", "annulée"]
STATUS_ICON = {
    "nouvelle": "🔴",
    "en préparation": "🟠",
    "prête": "🟢",
    "complétée": "✅",
    "annulée": "⚪",
}
OPEN_STATUSES = ["nouvelle", "en préparation", "prête"]

PHOTO_HELP = (
    "Cliquez ou glissez une photo (JPG, PNG ou WebP). Elle est redressée et "
    "réduite automatiquement pour s'afficher vite sur téléphone."
)

# Même alphabet que la fonction gen_retailer_code() de supabase_schema.sql :
# sans caractères ambigus (ni O/0, ni I/1), donc dictable au téléphone.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def new_access_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def order_link(code: str | None) -> str:
    """Lien de commande personnel d'un détaillant.

    `APP_URL` (secret optionnel) est l'adresse publique de l'app. Sans lui, on
    n'affiche que la partie relative, qu'il suffit de coller après l'adresse.
    """
    if not code:
        return ""
    base = str(st.secrets.get("APP_URL", "")).strip().rstrip("/")
    return f"{base}/?c={code}" if base else f"?c={code}"


# ------------------------------------------------------------------
# Accès
# ------------------------------------------------------------------
def check_password() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    brand_header("Tableau de bord")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            st.markdown("### 🔒 Accès réservé")
            pwd = st.text_input("Mot de passe", type="password", label_visibility="collapsed")
            if st.button("Se connecter", type="primary", width="stretch"):
                if pwd and pwd == st.secrets.get("ADMIN_PASSWORD"):
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
    return False


if not check_password():
    st.stop()

client = get_admin_client()


# ------------------------------------------------------------------
# Accès aux données
# ------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def load_orders() -> tuple[list[dict], list[dict]]:
    try:
        orders_res = (
            client.table("orders")
            .select("*, retailers(business_name, contact_name, phone, email)")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:  # noqa: BLE001 — base pas encore migrée (table retailers absente)
        orders_res = client.table("orders").select("*").order("created_at", desc=True).execute()
    items_res = client.table("order_items").select("*").execute()
    return orders_res.data or [], items_res.data or []


def load_products() -> list[dict]:
    res = client.table("products").select("*").order("sort_order").order("name").execute()
    return res.data or []


def load_retailers() -> list[dict]:
    res = client.table("retailers").select("*").order("business_name").execute()
    return res.data or []


def order_buyer(order: dict) -> dict:
    """Coordonnées de l'auteur d'une commande : détaillant lié, sinon champs texte."""
    linked = order.get("retailers") or {}
    return {
        "business_name": linked.get("business_name") or order.get("retailer_name") or "—",
        "contact_name": linked.get("contact_name") or order.get("contact_name"),
        "phone": linked.get("phone") or order.get("phone"),
        "email": linked.get("email") or order.get("email"),
        "registered": bool(order.get("retailer_id")),
    }


def refresh() -> None:
    load_orders.clear()
    st.rerun()


def register_from_order(order: dict) -> tuple[bool, str]:
    """Crée un détaillant à partir d'une commande envoyée sans lien personnel.

    Rattache aussi les commandes déjà reçues de ce commerce, pour que
    l'historique soit complet et que l'avertissement disparaisse partout.
    Retourne (succès, message).
    """
    name = (order.get("retailer_name") or "").strip()
    if not name:
        return False, "Cette commande ne porte aucun nom de commerce."
    try:
        created = (
            client.table("retailers")
            .insert(
                {
                    "business_name": name,
                    "contact_name": (order.get("contact_name") or "").strip() or None,
                    "phone": (order.get("phone") or "").strip() or None,
                    "email": (order.get("email") or "").strip() or None,
                }
            )
            .execute()
        )
        retailer_id = created.data[0]["id"]
        client.table("orders").update({"retailer_id": retailer_id}).eq(
            "retailer_name", name
        ).is_("retailer_id", "null").execute()
        return True, (
            f"« {name} » est enregistré. Son lien de commande personnel "
            "est dans l'onglet « Détaillants » — envoyez-le-lui."
        )
    except Exception as exc:  # noqa: BLE001
        return False, (
            f"Impossible d'enregistrer « {name} » — un commerce du même nom "
            f"existe peut-être déjà.\n\n`{exc}`"
        )


# ------------------------------------------------------------------
# En-tête
# ------------------------------------------------------------------
head_left, head_right = st.columns([5, 1])
with head_left:
    brand_header("Tableau de bord")
with head_right:
    if st.button("Se déconnecter", width="stretch"):
        st.session_state.admin_authenticated = False
        st.rerun()
    # Le menu latéral est masqué (showSidebarNavigation dans config.toml) pour ne
    # pas annoncer ce tableau de bord aux détaillants : d'où ce retour explicite.
    # Lien HTML plutôt que st.page_link, qui exige que la page cible soit
    # enregistrée dans la navigation et lève StreamlitPageNotFoundError sinon.
    st.markdown(
        '<a class="mk-backlink" href="/" target="_self">↗ Page de commande</a>',
        unsafe_allow_html=True,
    )

# « Commandes » reste le premier onglet : c'est l'écran du quotidien, celui
# qu'on ouvre pour travailler. Les indicateurs se consultent, ils n'ont pas à
# s'interposer.
tab_orders, tab_kpi, tab_products, tab_retailers = st.tabs(
    ["📋 Commandes", "📊 Indicateurs", "🧂 Produits", "🏪 Détaillants"]
)


# ==================================================================
# 0. INDICATEURS
# ==================================================================
# Parti pris de lecture : chaque graphique ne porte QU'UNE série, et la
# grandeur se lit sur la longueur des barres. La couleur ne code donc rien —
# ce qui évite le piège des palettes à plusieurs teintes, illisibles pour un
# daltonien, et interdit l'axe double (deux échelles sur un même graphique).
# Deux mesures de nature différente = deux graphiques côte à côte.
TEINTE = BRAND["red"]

PERIODES = {
    "30 jours": 30,
    "90 jours": 90,
    "12 mois": 365,
}


def _barres(donnees: list[dict], champ_valeur: str, champ_categorie: str,
            titre_valeur: str, horizontal: bool = False, format_valeur: str = ",.0f"):
    """Graphique à barres, série unique, habillé pour le thème sombre."""
    source = pd.DataFrame(donnees)
    if source.empty:
        return None

    axe_categorie = alt.Axis(
        labelColor=BRAND["muted"], titleColor=BRAND["muted"],
        domainColor=BRAND["border"], tickColor=BRAND["border"], grid=False,
    )
    # Des comptages n'ont pas de demi-unité : sans pas minimal, l'axe place des
    # graduations fractionnaires que le format arrondit, et on lit « 1 1 2 2 ».
    entiers = all(float(d[champ_valeur]).is_integer() for d in donnees)
    axe_valeur = alt.Axis(
        labelColor=BRAND["muted"], titleColor=BRAND["muted"],
        gridColor=BRAND["border"], gridOpacity=0.5, domain=False, ticks=False,
        format=format_valeur, tickMinStep=1 if entiers else alt.Undefined,
    )
    infobulle = [
        alt.Tooltip(f"{champ_categorie}:N", title=""),
        alt.Tooltip(f"{champ_valeur}:Q", title=titre_valeur, format=format_valeur),
    ]

    if horizontal:
        base = alt.Chart(source).encode(
            x=alt.X(f"{champ_valeur}:Q", title=titre_valeur, axis=axe_valeur),
            y=alt.Y(f"{champ_categorie}:N", title=None, sort="-x", axis=axe_categorie),
            tooltip=infobulle,
        )
        # Peu de barres : la valeur au bout évite d'avoir à survoler.
        graphique = base.mark_bar(
            cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=TEINTE, height=18
        ) + base.mark_text(
            align="left", dx=6, color=BRAND["text"], fontSize=12
        ).encode(text=alt.Text(f"{champ_valeur}:Q", format=format_valeur))
    else:
        graphique = alt.Chart(source).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=TEINTE, size=18
        ).encode(
            x=alt.X(f"{champ_categorie}:N", title=None, sort=None, axis=axe_categorie),
            y=alt.Y(f"{champ_valeur}:Q", title=titre_valeur, axis=axe_valeur),
            tooltip=infobulle,
        )

    return graphique.properties(height=240).configure_view(
        strokeWidth=0
    ).configure(background="transparent", font="Inter, sans-serif")


def _variation(actuel: float, precedent: float) -> str | None:
    """Écart en pourcentage par rapport à la période précédente."""
    if not precedent:
        return None
    return f"{(actuel - precedent) / precedent * 100:+.0f} %"


with tab_kpi:
    orders, items = load_orders()
    try:
        retailers_kpi = load_retailers()
    except Exception:  # noqa: BLE001 — table absente : les autres mesures tiennent
        retailers_kpi = []

    if not orders:
        st.info(
            "Aucune commande reçue pour l'instant : les indicateurs apparaîtront "
            "dès la première commande."
        )
    else:
        choix = st.segmented_control(
            "Période", list(PERIODES), default="90 jours", key="kpi_periode"
        ) or "90 jours"
        fin = datetime.now(ind.FUSEAU).date()
        debut = fin - timedelta(days=PERIODES[choix] - 1)
        debut_prec, fin_prec = ind.periode_precedente(debut, fin)

        actuel = ind.calculer(orders, items, debut, fin)
        precedent = ind.calculer(orders, items, debut_prec, fin_prec)
        st.caption(
            f"Du {debut} au {fin} — les écarts comparent à la période "
            f"précédente de même durée ({debut_prec} au {fin_prec})."
        )

        l1 = st.columns(4)
        l1[0].metric(
            "Ventes complétées", money(actuel["ventes"]) or "—",
            _variation(actuel["ventes"], precedent["ventes"]),
            help="Somme des commandes passées à « complétée » pendant la période.",
        )
        l1[1].metric(
            "Commandes reçues", actuel["nb_recues"],
            _variation(actuel["nb_recues"], precedent["nb_recues"]),
            help="Par date de réception. Les commandes annulées sont exclues.",
        )
        l1[2].metric(
            "Panier moyen", money(actuel["panier_moyen"]) or "—",
            _variation(actuel["panier_moyen"], precedent["panier_moyen"]),
            help="Ventes complétées divisées par le nombre de commandes complétées.",
        )
        l1[3].metric(
            "Détaillants actifs", actuel["detaillants_actifs"],
            _variation(actuel["detaillants_actifs"], precedent["detaillants_actifs"]),
            help="Commerces ayant passé au moins une commande pendant la période.",
        )

        l2 = st.columns(3)
        l2[0].metric(
            "Articles commandés", f"{actuel['articles']:g}",
            _variation(actuel["articles"], precedent["articles"]),
            help="Total des quantités commandées — utile même sans prix au catalogue.",
        )
        delai = actuel["delai_moyen"]
        l2[1].metric(
            "Délai de traitement", f"{delai:.1f} j" if delai is not None else "—",
            _variation(delai or 0, precedent["delai_moyen"] or 0),
            delta_color="inverse",
            help="Moyenne entre la réception et le passage à « complétée », sur "
            f"{actuel['nb_delais_mesures']} commande(s) mesurée(s). Les commandes "
            "antérieures au suivi des statuts sont écartées.",
        )
        l2[2].metric(
            "Commandes annulées", actuel["annulees"],
            _variation(actuel["annulees"], precedent["annulees"]),
            delta_color="inverse",
        )

        if actuel["ventes"] == 0 and actuel["articles"] > 0:
            st.warning(
                "Les montants sont à zéro parce que le catalogue n'a pas encore de "
                "prix. Les indicateurs de volume (commandes, articles, détaillants) "
                "restent justes. Saisissez les prix dans l'onglet « Produits ».",
                icon="💲",
            )

        st.markdown("#### Évolution sur 12 mois")
        mensuel = ind.par_mois(orders, items, nb_mois=12)
        g1, g2 = st.columns(2)
        with g1:
            st.caption("Ventes complétées par mois")
            graphique = _barres(mensuel, "ventes", "mois", "Ventes ($)", format_valeur=",.0f")
            if graphique is not None:
                st.altair_chart(graphique, width="stretch")
        with g2:
            st.caption("Commandes reçues par mois")
            graphique = _barres(mensuel, "commandes", "mois", "Commandes")
            if graphique is not None:
                st.altair_chart(graphique, width="stretch")

        st.markdown(f"#### Sur la période ({choix})")
        g3, g4 = st.columns(2)
        with g3:
            st.caption("Produits les plus commandés (quantité)")
            produits = ind.top_produits(orders, items, debut, fin)
            graphique = _barres(produits, "quantite", "produit", "Quantité", horizontal=True)
            if graphique is not None:
                st.altair_chart(graphique, width="stretch")
            else:
                st.caption("Aucune commande sur la période.")
        with g4:
            st.caption("Détaillants les plus actifs (commandes)")
            clients = ind.top_detaillants(orders, items, debut, fin)
            graphique = _barres(clients, "commandes", "detaillant", "Commandes", horizontal=True)
            if graphique is not None:
                st.altair_chart(graphique, width="stretch")
            else:
                st.caption("Aucune commande sur la période.")

        st.markdown("#### À suivre maintenant")
        g5, g6 = st.columns(2)
        with g5:
            st.caption("Commandes en cours — à préparer")
            encours = ind.pipeline(orders, items)
            if sum(p["commandes"] for p in encours) == 0:
                st.success("Rien en attente : toutes les commandes sont traitées.")
            else:
                for etape in encours:
                    st.markdown(
                        f'{STATUS_ICON.get(etape["statut"], "•")} **{etape["commandes"]}** '
                        f'{etape["statut"]}'
                        + (f' — {money(etape["montant"])}' if etape["montant"] else "")
                    )
        with g6:
            st.caption("Détaillants à relancer (aucune commande depuis 60 jours)")
            dormants = ind.detaillants_inactifs(orders, retailers_kpi, jours=60)
            if not dormants:
                st.success("Tous vos détaillants ont commandé récemment.")
            else:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Détaillant": d["detaillant"],
                                "Dernière commande": d["derniere_commande"],
                                "Jours": d["jours"] if d["jours"] is not None else "—",
                                "Courriel": d["courriel"] or "—",
                            }
                            for d in dormants
                        ]
                    ),
                    hide_index=True, width="stretch",
                )


# ==================================================================
# 1. COMMANDES
# ==================================================================
with tab_orders:
    orders, items = load_orders()

    counts = {s: sum(1 for o in orders if o["status"] == s) for s in STATUS_OPTIONS}
    metric_cols = st.columns(4)
    metric_cols[0].metric("Nouvelles", counts["nouvelle"])
    metric_cols[1].metric("En préparation", counts["en préparation"])
    metric_cols[2].metric("Prêtes", counts["prête"])
    metric_cols[3].metric("Total reçues", len(orders))

    if not orders:
        st.info("Aucune commande reçue pour le moment.")
    else:
        items_by_order: dict[str, list[dict]] = {}
        for it in items:
            items_by_order.setdefault(it["order_id"], []).append(it)

        filter_col, refresh_col = st.columns([5, 1])
        with filter_col:
            status_filter = st.multiselect(
                "Filtrer par statut", STATUS_OPTIONS, default=OPEN_STATUSES
            )
        with refresh_col:
            st.write("")
            if st.button("🔄 Rafraîchir", width="stretch"):
                refresh()

        shown = [o for o in orders if o["status"] in status_filter] if status_filter else orders
        st.caption(f"{len(shown)} commande(s) affichée(s) sur {len(orders)} au total.")

        for order in shown:
            buyer = order_buyer(order)
            order_items = items_by_order.get(order["id"], [])
            created = pd.to_datetime(order["created_at"]).strftime("%Y-%m-%d %H:%M")
            nb = sum(float(it["quantity"]) for it in order_items)
            header = (
                f"{STATUS_ICON.get(order['status'], '•')}  {buyer['business_name']}"
                f"  —  {created}  —  {nb:g} article(s)"
            )
            with st.expander(header):
                info_col, items_col = st.columns([1, 2])
                with info_col:
                    if not buyer["registered"]:
                        st.warning(
                            "Commerce **non enregistré** : cette commande est "
                            "arrivée sans lien personnel.",
                            icon="⚠️",
                        )
                        if st.button(
                            "➕ Enregistrer ce commerce",
                            key=f"reg_{order['id']}",
                            width="stretch",
                            help="Crée le détaillant et lui rattache ses commandes "
                            "déjà reçues. Il aura ensuite son lien personnel.",
                        ):
                            ok, message = register_from_order(order)
                            if ok:
                                st.success(message)
                                refresh()
                            else:
                                st.error(message)
                    st.markdown(f"**Contact :** {buyer['contact_name'] or '—'}")
                    st.markdown(f"**Téléphone :** {buyer['phone'] or '—'}")
                    st.markdown(f"**Courriel :** {buyer['email'] or '—'}")
                    st.markdown(f"**Date souhaitée :** {order.get('requested_date') or '—'}")
                    st.markdown(f"**Notes :** {order.get('notes') or '—'}")
                    st.caption(f"N° {str(order['id']).split('-')[0].upper()}")
                with items_col:
                    if order_items:
                        st.dataframe(
                            pd.DataFrame(
                                [
                                    {
                                        "Produit": it["product_name"],
                                        "Quantité": float(it["quantity"]),
                                        "Format": it["unit"],
                                        "Prix": money(it.get("price")) or "—",
                                    }
                                    for it in order_items
                                ]
                            ),
                            hide_index=True,
                            width="stretch",
                        )
                    else:
                        st.write("Aucun article.")

                status_col, save_col = st.columns([3, 1])
                with status_col:
                    new_status = st.selectbox(
                        "Statut",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(order["status"]),
                        key=f"status_{order['id']}",
                    )
                with save_col:
                    st.write("")
                    if st.button(
                        "Enregistrer",
                        key=f"save_{order['id']}",
                        disabled=new_status == order["status"],
                        width="stretch",
                        type="primary",
                    ):
                        client.table("orders").update({"status": new_status}).eq(
                            "id", order["id"]
                        ).execute()
                        refresh()


# ==================================================================
# 2. PRODUITS
# ==================================================================
with tab_products:
    st.markdown("### Catalogue")
    st.caption(
        "Ce que les détaillants voient sur la page de commande. "
        "Désactivez un produit pour le retirer de la liste sans perdre l'historique."
    )

    try:
        products = load_products()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Lecture du catalogue impossible : `{exc}`")
        products = []

    def reorder(product_list: list[dict], index: int, delta: int) -> None:
        """Déplace un produit vers le haut/bas et renumérote proprement sort_order."""
        target = index + delta
        if not 0 <= target < len(product_list):
            return
        reordered = list(product_list)
        reordered[index], reordered[target] = reordered[target], reordered[index]
        for position, prod in enumerate(reordered, start=1):
            if prod["sort_order"] != position * 10:
                client.table("products").update({"sort_order": position * 10}).eq(
                    "id", prod["id"]
                ).execute()

    for index, product in enumerate(products):
        with st.container(border=True):
            title_col, up_col, down_col, active_col = st.columns([6, 1, 1, 2])
            with title_col:
                state = "" if product["is_active"] else "  ·  :gray[désactivé]"
                price_txt = money(product.get("price"))
                st.markdown(
                    f"**{product['name']}**{state}  \n"
                    f":gray[{product.get('category') or 'Sans catégorie'} — "
                    f"{product.get('unit') or 'unité'}"
                    f"{' — ' + price_txt if price_txt else ' — prix à saisir'}]"
                )
            with up_col:
                if st.button("⬆️", key=f"up_{product['id']}", disabled=index == 0,
                             width="stretch", help="Monter"):
                    reorder(products, index, -1)
                    st.rerun()
            with down_col:
                if st.button("⬇️", key=f"down_{product['id']}", disabled=index == len(products) - 1,
                             width="stretch", help="Descendre"):
                    reorder(products, index, 1)
                    st.rerun()
            with active_col:
                label = "Désactiver" if product["is_active"] else "Activer"
                if st.button(label, key=f"toggle_{product['id']}", width="stretch"):
                    client.table("products").update(
                        {"is_active": not product["is_active"]}
                    ).eq("id", product["id"]).execute()
                    st.rerun()

            with st.expander("Modifier"):
                with st.form(f"edit_product_{product['id']}"):
                    name = st.text_input("Nom", value=product["name"])
                    description = st.text_area(
                        "Description", value=product.get("description") or "", height=80
                    )
                    f1, f2, f3 = st.columns(3)
                    category = f1.text_input("Catégorie", value=product.get("category") or "")
                    unit = f2.text_input("Format / unité", value=product.get("unit") or "unité")
                    price = f3.number_input(
                        "Prix ($)",
                        min_value=0.0,
                        step=0.25,
                        format="%.2f",
                        value=float(product["price"]) if product.get("price") is not None else 0.0,
                        help="0 = aucun prix affiché aux détaillants.",
                    )
                    current_image = product.get("image_url") or ""
                    if current_image:
                        st.image(current_image, width=140, caption="Photo actuelle")
                    photo = st.file_uploader(
                        "Nouvelle photo" if current_image else "Photo du produit",
                        type=photos.TYPES,
                        key=f"photo_{product['id']}",
                        help=PHOTO_HELP,
                    )
                    remove_image = (
                        st.checkbox("Retirer la photo", key=f"rm_photo_{product['id']}")
                        if current_image
                        else False
                    )
                    if st.form_submit_button("Enregistrer", type="primary"):
                        try:
                            if photo is not None:
                                image_url = photos.televerser(client, photo)
                            elif remove_image:
                                image_url = ""
                            else:
                                image_url = current_image
                            client.table("products").update(
                                {
                                    "name": name.strip(),
                                    "description": description.strip() or None,
                                    "category": category.strip() or None,
                                    "unit": unit.strip() or "unité",
                                    "price": float(price) if price > 0 else None,
                                    "image_url": image_url.strip() or None,
                                }
                            ).eq("id", product["id"]).execute()
                            st.success("Produit mis à jour.")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Échec de l'enregistrement : `{exc}`")

                confirm = st.checkbox(
                    "Je veux supprimer définitivement ce produit", key=f"del_ok_{product['id']}"
                )
                if st.button("🗑️ Supprimer", key=f"del_{product['id']}", disabled=not confirm):
                    client.table("products").delete().eq("id", product["id"]).execute()
                    st.rerun()

    with st.expander("➕ Ajouter un produit"):
        with st.form("new_product", clear_on_submit=True):
            n_name = st.text_input("Nom *")
            n_desc = st.text_area("Description", height=80)
            n1, n2, n3 = st.columns(3)
            n_cat = n1.text_input("Catégorie", placeholder="Ketchups")
            n_unit = n2.text_input("Format / unité", value="bouteille 350 ml")
            n_price = n3.number_input("Prix ($)", min_value=0.0, step=0.25, format="%.2f")
            n_photo = st.file_uploader("Photo du produit", type=photos.TYPES, help=PHOTO_HELP)
            if st.form_submit_button("Ajouter au catalogue", type="primary"):
                if not n_name.strip():
                    st.error("Le nom est requis.")
                else:
                    try:
                        n_image = photos.televerser(client, n_photo) if n_photo is not None else ""
                        client.table("products").insert(
                            {
                                "name": n_name.strip(),
                                "description": n_desc.strip() or None,
                                "category": n_cat.strip() or None,
                                "unit": n_unit.strip() or "unité",
                                "price": float(n_price) if n_price > 0 else None,
                                "image_url": n_image.strip() or None,
                                "sort_order": (max((p["sort_order"] for p in products), default=0) + 10),
                            }
                        ).execute()
                        st.success("Produit ajouté.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Échec de l'ajout : `{exc}`")


# ==================================================================
# 3. DÉTAILLANTS
# ==================================================================
with tab_retailers:
    st.markdown("### Détaillants enregistrés")
    st.caption(
        "Chaque détaillant a un **lien de commande personnel** à lui envoyer une "
        "seule fois. Ce lien l'identifie automatiquement : il commande en 2 clics, "
        "sans jamais retaper ses coordonnées. Aucune liste de détaillants n'est "
        "affichée sur la page publique — votre clientèle reste confidentielle."
    )
    if not str(st.secrets.get("APP_URL", "")).strip():
        st.warning(
            "Ajoutez le secret **`APP_URL`** (l'adresse publique de l'app, par "
            "exemple `https://votre-app.streamlit.app`) pour que les liens "
            "ci-dessous soient complets et copiables tels quels.",
            icon="🔗",
        )

    try:
        retailers = load_retailers()
        retailers_ok = True
    except Exception as exc:  # noqa: BLE001
        retailers_ok = False
        retailers = []
        st.error(
            "La table `retailers` est introuvable. Exécutez `supabase_schema.sql` "
            f"dans Supabase (SQL Editor) pour la créer.\n\n`{exc}`"
        )

    if retailers_ok:
        c_search, c_count = st.columns([4, 1])
        with c_search:
            search = st.text_input(
                "Rechercher", placeholder="Nom du commerce…", label_visibility="collapsed"
            )
        with c_count:
            st.metric("Actifs", sum(1 for r in retailers if r["is_active"]))

        needle = (search or "").strip().lower()
        visible = [
            r
            for r in retailers
            if not needle
            or needle in (r["business_name"] or "").lower()
            or needle in (r.get("contact_name") or "").lower()
        ]

        for retailer in visible:
            with st.container(border=True):
                info_col, toggle_col = st.columns([6, 2])
                with info_col:
                    state = "" if retailer["is_active"] else "  ·  :gray[désactivé]"
                    details = " · ".join(
                        v for v in (
                            retailer.get("contact_name"),
                            retailer.get("phone"),
                            retailer.get("email"),
                        ) if v
                    )
                    st.markdown(
                        f"**{retailer['business_name']}**{state}  \n"
                        f":gray[{details or 'Aucune coordonnée enregistrée'}]"
                    )
                with toggle_col:
                    label = "Désactiver" if retailer["is_active"] else "Activer"
                    if st.button(label, key=f"rtoggle_{retailer['id']}", width="stretch"):
                        client.table("retailers").update(
                            {"is_active": not retailer["is_active"]}
                        ).eq("id", retailer["id"]).execute()
                        st.rerun()

                code = retailer.get("access_code")
                if code:
                    st.caption("Lien de commande personnel — à envoyer à ce détaillant :")
                    st.code(order_link(code), language=None)
                else:
                    st.warning(
                        "Pas de lien personnel : relancez `supabase_schema.sql` "
                        "dans Supabase pour en générer un.",
                        icon="⚠️",
                    )

                with st.expander("Modifier"):
                    with st.form(f"edit_retailer_{retailer['id']}"):
                        r_name = st.text_input("Nom du commerce *", value=retailer["business_name"])
                        r1, r2, r3 = st.columns(3)
                        r_contact = r1.text_input("Contact", value=retailer.get("contact_name") or "")
                        r_phone = r2.text_input("Téléphone", value=retailer.get("phone") or "")
                        r_email = r3.text_input("Courriel", value=retailer.get("email") or "")
                        r_notes = st.text_area(
                            "Notes internes", value=retailer.get("notes") or "", height=70,
                            help="Visible uniquement ici, jamais sur la page de commande.",
                        )
                        if st.form_submit_button("Enregistrer", type="primary"):
                            if not r_name.strip():
                                st.error("Le nom du commerce est requis.")
                            else:
                                try:
                                    client.table("retailers").update(
                                        {
                                            "business_name": r_name.strip(),
                                            "contact_name": r_contact.strip() or None,
                                            "phone": r_phone.strip() or None,
                                            "email": r_email.strip() or None,
                                            "notes": r_notes.strip() or None,
                                        }
                                    ).eq("id", retailer["id"]).execute()
                                    st.success("Détaillant mis à jour.")
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    st.error(f"Échec de l'enregistrement : `{exc}`")

                    st.divider()
                    st.caption(
                        "Régénérer le lien rend l'ancien inutilisable (en moins "
                        "d'une minute) : à faire si le lien a circulé par erreur."
                    )
                    if st.checkbox(
                        "Je veux régénérer le lien de ce détaillant",
                        key=f"regen_ok_{retailer['id']}",
                    ) and st.button("🔗 Régénérer le lien", key=f"regen_{retailer['id']}"):
                        try:
                            client.table("retailers").update(
                                {"access_code": new_access_code()}
                            ).eq("id", retailer["id"]).execute()
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Échec de la régénération : `{exc}`")

        if not visible:
            st.info("Aucun détaillant ne correspond à cette recherche.")

        with st.expander("➕ Ajouter un détaillant", expanded=not retailers):
            with st.form("new_retailer", clear_on_submit=True):
                a_name = st.text_input("Nom du commerce *", placeholder="Épicerie du Coin")
                a1, a2, a3 = st.columns(3)
                a_contact = a1.text_input("Contact", placeholder="Prénom Nom")
                a_phone = a2.text_input("Téléphone")
                a_email = a3.text_input("Courriel")
                a_notes = st.text_area("Notes internes", height=70)
                if st.form_submit_button("Ajouter à la liste", type="primary"):
                    if not a_name.strip():
                        st.error("Le nom du commerce est requis.")
                    else:
                        try:
                            client.table("retailers").insert(
                                {
                                    "business_name": a_name.strip(),
                                    "contact_name": a_contact.strip() or None,
                                    "phone": a_phone.strip() or None,
                                    "email": a_email.strip() or None,
                                    "notes": a_notes.strip() or None,
                                }
                            ).execute()
                            st.success(
                                f"« {a_name.strip()} » est ajouté. Son lien de "
                                "commande personnel apparaît sur sa carte "
                                "ci-dessus — envoyez-le-lui."
                            )
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(
                                "Échec de l'ajout (un commerce du même nom existe "
                                f"peut-être déjà).\n\n`{exc}`"
                            )
