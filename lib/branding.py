"""
Identité visuelle partagée par la page de commande et le tableau de bord.

Un seul endroit pour la palette, les polices et les composants d'habillage,
pour que la page publique (détaillants) et la page admin (producteur) aient
exactement le même look « Mine de Ketchup » : sombre, chaleureux, artisanal.
"""

from __future__ import annotations

import streamlit as st

BRAND = {
    "name": "Mine de Ketchup",
    "tagline": "Ketchups & salsas artisanaux — Padoue, Bas-Saint-Laurent",
    "site": "https://mine-de-ketchup.square.site",
    # Palette : fond terreux très sombre, rouge tomate en accent, or et crème.
    "bg": "#14100E",
    "surface": "#1D1815",
    "surface_2": "#241D18",
    "border": "#3A2F26",
    "text": "#F4ECE2",
    "muted": "#A5917E",
    "red": "#D8452F",
    "red_light": "#EE5B42",
    "gold": "#E3A63F",
    "green": "#7FB185",
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

:root {
  __MK_VARS__
  --mk-serif: 'Fraunces', Georgia, 'Times New Roman', serif;
  --mk-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --mk-radius: 14px;
}

/* ---------- Fond & typographie générale ---------- */
.stApp {
  background:
    radial-gradient(1100px 480px at 50% -220px, rgba(216, 69, 47, .16), transparent 70%),
    var(--mk-bg);
  color: var(--mk-text);
  font-family: var(--mk-sans);
}
[data-testid="stHeader"] { background: transparent; height: 2.8rem; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu { display: none !important; }
.block-container { padding-top: 3rem; padding-bottom: 4rem; max-width: __MK_MAXW__; }
/* Resserre l'espacement vertical : plus de produits visibles d'un coup sur mobile. */
.block-container [data-testid="stVerticalBlock"] { gap: .7rem; }
h1, h2, h3, h4 { font-family: var(--mk-serif); color: var(--mk-text); letter-spacing: -.01em; }
p, li, label, span, div { color: var(--mk-text); }
a { color: var(--mk-gold); }
hr { border-color: var(--mk-border); }

/* ---------- En-tête de marque ---------- */
.mk-header { display: flex; align-items: center; gap: .9rem; padding: .2rem 0 .8rem 0; }
.mk-logo {
  width: 54px; height: 54px; flex: 0 0 54px; border-radius: 16px;
  display: flex; align-items: center; justify-content: center; font-size: 1.7rem;
  background: linear-gradient(150deg, var(--mk-red), #8E2517);
  box-shadow: 0 6px 18px rgba(216, 69, 47, .3);
}
.mk-brand {
  font-family: var(--mk-serif); font-weight: 700; font-size: 1.45rem;
  line-height: 1.15; letter-spacing: .01em;
}
.mk-tag { color: var(--mk-muted); font-size: .83rem; margin-top: .12rem; }
.mk-rule {
  height: 3px; border: 0; border-radius: 3px; margin: 0 0 .5rem 0;
  background: linear-gradient(90deg, var(--mk-red), var(--mk-gold) 55%, transparent);
}

/* ---------- Titres d'étape ---------- */
.mk-step { display: flex; align-items: center; gap: .6rem; margin: 1.25rem 0 .2rem 0; }
.mk-step-num {
  width: 26px; height: 26px; flex: 0 0 26px; border-radius: 50%;
  background: var(--mk-red); color: #fff; font-size: .82rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.mk-step-txt { font-family: var(--mk-serif); font-weight: 600; font-size: 1.12rem; }
.mk-step-hint { color: var(--mk-muted); font-size: .82rem; margin: -.1rem 0 .4rem 2.2rem; }

/* ---------- Cartes produits ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--mk-surface);
  border: 1px solid var(--mk-border) !important;
  border-radius: var(--mk-radius) !important;
}
.mk-card-head { display: flex; align-items: baseline; gap: .6rem; }
.mk-card-title { font-family: var(--mk-serif); font-weight: 600; font-size: 1.06rem; flex: 1 1 auto; }
.mk-card-price { color: var(--mk-gold); font-weight: 700; font-size: .98rem; white-space: nowrap; }
.mk-card-desc { color: var(--mk-muted); font-size: .85rem; line-height: 1.4; margin-top: .25rem; }
.mk-card-unit {
  display: inline-block; margin-top: .5rem; padding: .12rem .55rem;
  border: 1px solid var(--mk-border); border-radius: 999px;
  color: var(--mk-muted); font-size: .74rem; letter-spacing: .02em;
}
.mk-incart { color: var(--mk-green); font-size: .8rem; font-weight: 600; margin-top: .55rem; }

/* Bandeau « Commande pour <commerce> » : le lien personnel a déjà identifié
   le détaillant, il n'a donc plus rien à choisir ni à saisir. */
.mk-who {
  display: flex; align-items: baseline; gap: .6rem; flex-wrap: wrap;
  background: var(--mk-surface); border: 1px solid var(--mk-border);
  border-left: 3px solid var(--mk-green);
  border-radius: var(--mk-radius); padding: .75rem 1rem;
}
.mk-who-label { color: var(--mk-muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
.mk-who-name { font-family: var(--mk-serif); font-weight: 600; font-size: 1.12rem; }
.mk-thumb {
  width: 100%; max-height: 130px; object-fit: cover;
  border-radius: 10px; margin-bottom: .6rem; border: 1px solid var(--mk-border);
}
.mk-cat {
  font-family: var(--mk-serif); font-size: 1.02rem; font-weight: 600;
  color: var(--mk-gold); margin: 1rem 0 .1rem 0;
  text-transform: uppercase; letter-spacing: .09em;
}

/* ---------- Rangée quantité : reste horizontale même sur mobile ---------- */
[data-testid="stHorizontalBlock"]:has(.mk-qtyrow) {
  flex-wrap: nowrap !important;
  gap: .45rem !important;
  align-items: center;
}
[data-testid="stHorizontalBlock"]:has(.mk-qtyrow) > div {
  min-width: 0 !important;
  flex: 1 1 0 !important;
}
[data-testid="stHorizontalBlock"]:has(.mk-qtyrow) .stButton > button {
  height: 48px; padding: 0; border-radius: 12px;
}
/* Le libellé du bouton est un <p> : c'est lui qu'il faut grossir. */
[data-testid="stHorizontalBlock"]:has(.mk-qtyrow) .stButton > button p {
  font-size: 1.6rem; font-weight: 700; line-height: 1;
}
/* Les steppers natifs du number_input font doublon avec nos gros boutons. */
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] { display: none !important; }
[data-testid="stNumberInput"] input {
  text-align: center; font-weight: 700; font-size: 1.12rem;
  background: var(--mk-surface-2); color: var(--mk-text);
}

/* ---------- Champs ---------- */
/* Streamlit a changé de librairie de widgets au fil des versions (BaseWeb ->
   React Aria) : on cible les deux pour que l'habillage tienne dans les deux cas. */
[data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input,
[data-testid="stDateInputField"],
[data-testid="stSelectbox"] [role="group"] {
  background: var(--mk-surface-2) !important;
  border-color: var(--mk-border) !important;
  color: var(--mk-text) !important;
  border-radius: 11px !important;
}
[data-baseweb="select"] svg { fill: var(--mk-muted); }

/* ---------- Boutons ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; font-weight: 600; border: 1px solid var(--mk-border);
  background: var(--mk-surface-2); color: var(--mk-text); transition: all .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
  border-color: var(--mk-red); color: #fff;
}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: var(--mk-red); border-color: var(--mk-red); color: #fff;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
  background: var(--mk-red-light); border-color: var(--mk-red-light);
}
.stButton > button:disabled { opacity: .38; }

/* ---------- Récapitulatif / envoi ---------- */
.mk-total {
  display: flex; justify-content: space-between; align-items: baseline;
  border-top: 1px dashed var(--mk-border); margin-top: .6rem; padding-top: .6rem;
  font-weight: 700;
}
.mk-line { display: flex; justify-content: space-between; gap: 1rem; padding: .18rem 0; font-size: .92rem; }
.mk-line span:last-child { color: var(--mk-muted); white-space: nowrap; }
.mk-done {
  text-align: center; padding: 2.2rem 1.2rem; border-radius: var(--mk-radius);
  background: var(--mk-surface); border: 1px solid var(--mk-border);
}
.mk-done-emoji { font-size: 2.6rem; }
.mk-ref {
  display: inline-block; margin-top: .7rem; padding: .3rem .8rem; border-radius: 999px;
  background: var(--mk-surface-2); border: 1px solid var(--mk-border);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--mk-gold);
}

/* ---------- Divers Streamlit ---------- */
[data-testid="stExpander"] details {
  background: var(--mk-surface); border: 1px solid var(--mk-border); border-radius: var(--mk-radius);
}
[data-testid="stMetric"] {
  background: var(--mk-surface); border: 1px solid var(--mk-border);
  border-radius: var(--mk-radius); padding: .8rem 1rem;
}
[data-testid="stMetricValue"] { font-family: var(--mk-serif); color: var(--mk-gold); }
.stTabs [data-baseweb="tab-list"] { gap: .3rem; border-bottom: 1px solid var(--mk-border); }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: .5rem .9rem; }
.stTabs [aria-selected="true"] { background: var(--mk-surface); color: var(--mk-gold) !important; }
[data-testid="stSidebarNav"] { font-family: var(--mk-sans); }
.mk-foot {
  text-align: center; color: var(--mk-muted); font-size: .78rem;
  margin-top: 2.6rem; padding-top: 1.1rem; border-top: 1px solid var(--mk-border);
}

/* Messages (info / succès / avertissement / erreur) aux couleurs de la marque */
[data-testid="stAlert"] {
  background: var(--mk-surface) !important;
  border: 1px solid var(--mk-border) !important;
  border-left: 3px solid var(--mk-gold) !important;
  border-radius: var(--mk-radius) !important;
  color: var(--mk-text) !important;
}
[data-testid="stAlertContentSuccess"] { border-left-color: var(--mk-green) !important; }
[data-testid="stAlertContentError"] { border-left-color: var(--mk-red) !important; }

@media (max-width: 640px) {
  .block-container { padding-left: .9rem; padding-right: .9rem; }
  .mk-brand { font-size: 1.2rem; }
  .mk-logo { width: 46px; height: 46px; flex-basis: 46px; font-size: 1.4rem; }
}
</style>
"""


_VAR_KEYS = (
    "bg", "surface", "surface_2", "border", "text", "muted",
    "red", "red_light", "gold", "green",
)


def inject_theme(wide: bool = False) -> None:
    """Injecte la feuille de style Mine de Ketchup (à appeler une fois par page).

    `wide=True` pour le tableau de bord (layout large), False pour la page de
    commande, volontairement étroite et lisible au pouce sur un téléphone.
    """
    variables = "\n  ".join(
        f"--mk-{key.replace('_', '-')}: {BRAND[key]};" for key in _VAR_KEYS
    )
    css = _CSS.replace("__MK_VARS__", variables)
    css = css.replace("__MK_MAXW__", "1400px" if wide else "940px")
    st.markdown(css, unsafe_allow_html=True)


def brand_header(subtitle: str | None = None) -> None:
    """En-tête avec logo, nom de la marque et sous-titre."""
    st.markdown(
        f"""
        <div class="mk-header">
          <div class="mk-logo">🍅</div>
          <div>
            <div class="mk-brand">{BRAND['name']}</div>
            <div class="mk-tag">{subtitle or BRAND['tagline']}</div>
          </div>
        </div>
        <hr class="mk-rule"/>
        """,
        unsafe_allow_html=True,
    )


def step(number: int | str, title: str, hint: str | None = None) -> None:
    """Titre d'étape numéroté (1, 2, 3...) pour guider le détaillant."""
    st.markdown(
        f'<div class="mk-step"><div class="mk-step-num">{number}</div>'
        f'<div class="mk-step-txt">{title}</div></div>',
        unsafe_allow_html=True,
    )
    if hint:
        st.markdown(f'<div class="mk-step-hint">{hint}</div>', unsafe_allow_html=True)


def money(value) -> str:
    """Formate un prix à la québécoise : 7,25 $. Retourne '' si pas de prix."""
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",") + " $"
    except (TypeError, ValueError):
        return ""


def footer() -> None:
    st.markdown(
        f'<div class="mk-foot">{BRAND["name"]} — aucun paiement n\'est traité ici. '
        f'Vous serez contacté(e) pour la confirmation.</div>',
        unsafe_allow_html=True,
    )
