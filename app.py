"""
Mine de Ketchup — page publique de commande pour les détaillants.

Objectif : commander en 2 clics. Les détaillants sont DÉJÀ connus du
Mine de Ketchup, donc aucune coordonnée n'est redemandée :

1. le détaillant ouvre SON lien personnel (.../?c=XXXXXXXX) — la page sait
   déjà quel commerce commande,
2. il ajuste les quantités avec les boutons + / −,
3. il envoie.

Le lien personnel remplace la liste déroulante : aucune liste de détaillants
n'est affichée ni même envoyée au navigateur, donc la liste de clients du
Mine de Ketchup reste confidentielle.

Date de livraison et notes sont optionnelles et repliées par défaut.
Aucun compte, aucun mot de passe, aucun paiement.
"""

from __future__ import annotations

import uuid

import streamlit as st

from lib.branding import BRAND, brand_header, footer, inject_theme, money, step
from lib.supabase_client import get_public_client

st.set_page_config(
    page_title="Mine de Ketchup — Commande détaillants",
    page_icon="🍅",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inject_theme()


# ------------------------------------------------------------------
# Chargement des données (mises en cache : le catalogue bouge peu)
# ------------------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def load_products() -> list[dict]:
    res = (
        get_public_client()
        .table("products")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .order("name")
        .execute()
    )
    return res.data or []


# TTL court volontairement : il évite un appel réseau à chaque clic sur + / −,
# mais garde une désactivation ou une régénération de lien effective en moins
# d'une minute. Ne pas rallonger sans revoir le texte du tableau de bord.
@st.cache_data(ttl=30, show_spinner=False)
def resolve_retailer(code: str) -> dict | None:
    """Traduit un code de lien personnel en commerce, via la fonction Supabase.

    La clé anon ne peut PAS lire la table `retailers` : elle peut seulement
    appeler cette fonction, qui répond pour un code à la fois et ne renvoie
    que l'id et le nom du commerce. Impossible d'énumérer la clientèle.
    """
    res = get_public_client().rpc("retailer_by_code", {"p_code": code}).execute()
    rows = res.data or []
    return rows[0] if rows else None


def qty_key(product_id: str) -> str:
    return f"qty_{product_id}"


def bump(product_id: str, delta: int) -> None:
    key = qty_key(product_id)
    st.session_state[key] = max(0, int(st.session_state.get(key, 0)) + delta)


def clear_cart() -> None:
    for key in [k for k in st.session_state if k.startswith("qty_")]:
        st.session_state[key] = 0


# ------------------------------------------------------------------
# Écran de confirmation (après envoi)
# ------------------------------------------------------------------
if st.session_state.get("mk_receipt"):
    receipt = st.session_state["mk_receipt"]
    brand_header("Commande envoyée")
    lines = "".join(
        f'<div class="mk-line"><span>{it["quantity"]} × {it["product_name"]}</span>'
        f'<span>{it["unit"]}</span></div>'
        for it in receipt["items"]
    )
    st.markdown(
        f"""
        <div class="mk-done">
          <div class="mk-done-emoji">✅</div>
          <h3 style="margin:.5rem 0 .2rem 0;">Merci, c'est envoyé !</h3>
          <div style="color:var(--mk-muted);font-size:.9rem;">
            Commande de <strong>{receipt['retailer']}</strong> bien reçue.<br/>
            Mine de Ketchup vous contactera pour la confirmation.
          </div>
          <div class="mk-ref">N<sup>o</sup> {receipt['ref']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("**Récapitulatif**")
        st.markdown(lines, unsafe_allow_html=True)
        if receipt.get("requested_date"):
            st.caption(f"Livraison souhaitée : {receipt['requested_date']}")
        if receipt.get("notes"):
            st.caption(f"Notes : {receipt['notes']}")

    if st.button("Passer une nouvelle commande", type="primary", width="stretch"):
        clear_cart()
        st.session_state.pop("mk_receipt", None)
        st.rerun()
    footer()
    st.stop()


# ------------------------------------------------------------------
# Page de commande
# ------------------------------------------------------------------
brand_header("Commande détaillants — 2 clics, c'est envoyé")

try:
    products = load_products()
except Exception as exc:  # noqa: BLE001
    st.error(
        "Impossible de joindre la base de données. Vérifiez la configuration "
        f"Supabase de l'app (secrets `SUPABASE_URL` / `SUPABASE_ANON_KEY`).\n\n`{exc}`"
    )
    st.stop()

if not products:
    st.warning(
        "Le catalogue n'est pas encore configuré. Mine de Ketchup doit ajouter "
        "des produits dans le tableau de bord."
    )
    st.stop()

# --- Qui commande ? Le lien personnel répond déjà ------------------
# Le code arrive dans l'URL (.../?c=XXXXXXXX). Aucune liste n'est chargée :
# on ne résout qu'un code à la fois, côté serveur.
access_code = (st.query_params.get("c") or "").strip().upper()

selected: dict | None = None
lookup_error: str | None = None
if access_code:
    try:
        selected = resolve_retailer(access_code)
    except Exception as exc:  # noqa: BLE001
        lookup_error = str(exc)

if selected:
    st.markdown(
        f'<div class="mk-who"><span class="mk-who-label">Commande pour</span>'
        f'<span class="mk-who-name">{selected["business_name"]}</span></div>',
        unsafe_allow_html=True,
    )
else:
    if lookup_error:
        st.warning(
            "Impossible de vérifier votre lien pour le moment. Vous pouvez "
            "quand même commander en indiquant votre commerce ci-dessous."
        )
    elif access_code:
        st.warning(
            "Ce lien de commande n'est plus valide. Demandez votre lien "
            "personnel à Mine de Ketchup — ou commandez quand même en indiquant "
            "votre commerce ci-dessous."
        )
    else:
        st.info(
            "Ouvrez **votre lien personnel** pour que votre commerce soit "
            "reconnu automatiquement. Vous ne l'avez pas sous la main ? "
            "Indiquez simplement votre commerce ci-dessous."
        )

fb_business = fb_contact = fb_phone = fb_email = ""
if not selected:
    with st.container(border=True):
        st.markdown("**Votre commerce**")
        fb_business = st.text_input("Nom de votre commerce", max_chars=200, key="mk_fb_business")
        fb_contact = st.text_input("Votre nom", max_chars=200, key="mk_fb_contact")
        fb_c1, fb_c2 = st.columns(2)
        fb_phone = fb_c1.text_input("Téléphone", key="mk_fb_phone")
        fb_email = fb_c2.text_input("Courriel", key="mk_fb_email")

fb_business = (fb_business or "").strip()
if selected:
    buyer_label = selected["business_name"]
elif fb_business:
    buyer_label = fb_business
else:
    buyer_label = None

# --- Étape 1 : les produits ---------------------------------------
step(1, "Vos produits", "Ajustez les quantités avec les boutons + et −.")

by_category: dict[str, list[dict]] = {}
for product in products:
    by_category.setdefault(product.get("category") or "Autres", []).append(product)

for category, items in by_category.items():
    st.markdown(f'<div class="mk-cat">{category}</div>', unsafe_allow_html=True)
    for product in items:
        pid = product["id"]
        current = int(st.session_state.get(qty_key(pid), 0))
        with st.container(border=True):
            if product.get("image_url"):
                st.markdown(
                    f'<img class="mk-thumb" src="{product["image_url"]}" alt="">',
                    unsafe_allow_html=True,
                )
            price_txt = money(product.get("price"))
            desc = product.get("description") or ""
            st.markdown(
                f"""
                <div class="mk-card-head">
                  <div class="mk-card-title">{product['name']}</div>
                  <div class="mk-card-price">{price_txt}</div>
                </div>
                {f'<div class="mk-card-desc">{desc}</div>' if desc else ''}
                <div class="mk-card-unit">{product.get('unit') or 'unité'}</div>
                """,
                unsafe_allow_html=True,
            )
            col_minus, col_qty, col_plus = st.columns([2, 3, 2], vertical_alignment="center")
            with col_minus:
                st.markdown('<span class="mk-qtyrow"></span>', unsafe_allow_html=True)
                st.button(
                    "−",
                    key=f"minus_{pid}",
                    on_click=bump,
                    args=(pid, -1),
                    disabled=current == 0,
                    width="stretch",
                    help="Retirer un",
                )
            with col_qty:
                st.number_input(
                    "Quantité",
                    min_value=0,
                    max_value=999,
                    step=1,
                    key=qty_key(pid),
                    label_visibility="collapsed",
                )
            with col_plus:
                st.button(
                    "+",
                    key=f"plus_{pid}",
                    on_click=bump,
                    args=(pid, 1),
                    width="stretch",
                    help="Ajouter un",
                )
            if current:
                st.markdown(
                    f'<div class="mk-incart">✓ {current} × {product.get("unit") or "unité"} au panier</div>',
                    unsafe_allow_html=True,
                )

cart = [
    {**p, "quantity": int(st.session_state.get(qty_key(p["id"]), 0))}
    for p in products
    if int(st.session_state.get(qty_key(p["id"]), 0)) > 0
]

# --- Étape 2 : envoi ----------------------------------------------
step(2, "Envoi")

with st.expander("Date de livraison souhaitée et notes (facultatif)"):
    requested_date = st.date_input(
        "Date de livraison / collecte souhaitée", value=None, format="YYYY-MM-DD"
    )
    notes = st.text_area(
        "Notes",
        placeholder="Ex : instructions de livraison, produit hors catalogue…",
        height=90,
    )

with st.container(border=True):
    if cart:
        total = sum(
            (c["quantity"] * float(c["price"])) for c in cart if c.get("price") is not None
        )
        priced = all(c.get("price") is not None for c in cart)
        st.markdown(
            "".join(
                f'<div class="mk-line"><span>{c["quantity"]} × {c["name"]}</span>'
                f'<span>{c.get("unit") or "unité"}</span></div>'
                for c in cart
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="mk-total"><span>'
            f'{sum(c["quantity"] for c in cart)} article(s)</span><span>'
            f'{money(total) + " (indicatif)" if priced and total else "—"}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color:var(--mk-muted);font-size:.9rem;">'
            "Votre panier est vide — ajoutez au moins un produit ci-dessus.</div>",
            unsafe_allow_html=True,
        )

    blockers = []
    if not buyer_label:
        blockers.append("indiquez votre commerce")
    if not cart:
        blockers.append("ajoutez au moins un produit")

    send = st.button(
        f"Envoyer la commande{f' — {buyer_label}' if buyer_label else ''}",
        type="primary",
        width="stretch",
        disabled=bool(blockers),
    )
    if blockers:
        st.caption("Pour envoyer : " + ", puis ".join(blockers) + ".")

if send:
    client = get_public_client()
    # L'identifiant est généré ici, pas par la base : la clé anon n'a aucune
    # policy SELECT sur `orders` (et c'est voulu — un détaillant ne doit pas
    # pouvoir relire les commandes). Sans cet id, il faudrait demander à
    # PostgREST de renvoyer la ligne insérée, ce qu'il refuse faute de droit
    # de lecture : « new row violates row-level security policy ».
    order_id = str(uuid.uuid4())
    order_payload = {
        "id": order_id,
        "retailer_id": selected["id"] if selected else None,
        "retailer_name": selected["business_name"] if selected else fb_business,
        "contact_name": None if selected else ((fb_contact or "").strip() or None),
        "phone": None if selected else ((fb_phone or "").strip() or None),
        "email": None if selected else ((fb_email or "").strip() or None),
        "requested_date": requested_date.isoformat() if requested_date else None,
        "notes": (notes or "").strip() or None,
    }
    try:
        # returning="minimal" : on n'exige aucune relecture après l'écriture.
        client.table("orders").insert(order_payload, returning="minimal").execute()

        items_payload = [
            {
                "order_id": order_id,
                "product_id": c["id"],
                "product_name": c["name"],
                "unit": c.get("unit") or "unité",
                "quantity": c["quantity"],
                "price": c.get("price"),
            }
            for c in cart
        ]
        client.table("order_items").insert(items_payload, returning="minimal").execute()

        st.session_state["mk_receipt"] = {
            "ref": str(order_id).split("-")[0].upper(),
            "retailer": buyer_label,
            "items": items_payload,
            "requested_date": order_payload["requested_date"],
            "notes": order_payload["notes"],
        }
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(
            "Une erreur est survenue lors de l'envoi. Réessayez, ou contactez "
            f"directement Mine de Ketchup.\n\n`{exc}`"
        )

st.markdown(
    f'<div class="mk-foot">{BRAND["name"]} — aucun paiement n\'est traité ici. '
    f'Vous serez contacté(e) pour la confirmation.<br/>'
    f'<a href="{BRAND["site"]}" target="_blank">{BRAND["site"].replace("https://", "")}</a></div>',
    unsafe_allow_html=True,
)
