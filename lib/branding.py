"""
Identité visuelle partagée par la page de commande et le tableau de bord.

Un seul endroit pour la palette, les polices et les composants d'habillage,
pour que la page publique (détaillants) et la page admin (gestion) aient
exactement le même look « Mine de Ketchup » : sombre, chaleureux, artisanal.
"""

from __future__ import annotations

import base64
from pathlib import Path

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
.mk-header { padding: .2rem 0 .8rem 0; }

/* Lettrage « MINE / pics croisés / DE KETCHUP », repris du logo de la marque.
   Reconstruit en texte plutôt qu'en image : net à toutes les tailles, et il
   prend la couleur crème du thème sombre au lieu du noir du fichier d'origine.
   Un fichier déposé dans assets/ (voir logo_markup) le remplace. */
.mk-wordmark { display: inline-block; text-align: center; line-height: 1; }
.mk-wm-top {
  font-family: var(--mk-serif); font-weight: 600; font-size: 1.6rem;
  letter-spacing: .34em; text-indent: .34em; color: var(--mk-text);
}
.mk-wm-mid { display: flex; align-items: center; gap: .45rem; margin: .28rem 0; }
.mk-wm-rule { flex: 1 1 auto; height: 1.5px; background: var(--mk-text); opacity: .9; }
.mk-wm-picks { flex: 0 0 auto; width: 38px; height: 31px; }
.mk-wm-bot {
  font-family: var(--mk-serif); font-weight: 600; font-size: .92rem;
  letter-spacing: .3em; text-indent: .3em; color: var(--mk-text);
}
.mk-logo-img { display: block; height: 66px; width: auto; max-width: 100%; }
/* Le logo fourni est noir sur blanc : inversé, il devient blanc et se fond
   dans le thème sombre sans rectangle blanc autour. */
.mk-logo-img.mk-invert { filter: invert(1); }
.mk-tag { color: var(--mk-muted); font-size: .83rem; margin-top: .5rem; }
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
  .mk-wm-top { font-size: 1.3rem; }
  .mk-wm-bot { font-size: .78rem; }
  .mk-logo-img { height: 54px; }
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


# Pics croisés du logo. Dessinés en SVG pour rester nets et suivre la couleur
# du texte (currentColor) quel que soit le thème.
_PICKS_SVG = """
<svg class="mk-wm-picks" viewBox="0 0 68 56" fill="none"
     stroke="currentColor" stroke-width="3"
     stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <g transform="translate(34 26)">
    <g transform="rotate(-45)"><path d="M0 -21 L0 20"/></g>
    <g transform="translate(-14.85 -14.85) rotate(-40)">
      <path d="M-8 3 Q0 -6 8 3 Q3.6 -0.9 0 -0.9 Q-3.6 -0.9 -8 3 Z" fill="currentColor" stroke-width="1.2"/>
    </g>
    <g transform="rotate(45)"><path d="M0 -21 L0 20"/></g>
    <g transform="translate(14.85 -14.85) rotate(40)">
      <path d="M-8 3 Q0 -6 8 3 Q3.6 -0.9 0 -0.9 Q-3.6 -0.9 -8 3 Z" fill="currentColor" stroke-width="1.2"/>
    </g>
  </g>
</svg>
"""

_LOGO_DIR = Path(__file__).resolve().parent.parent / "assets"
_LOGO_EXTS = (".svg", ".png", ".webp", ".jpg", ".jpeg")
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@st.cache_data(show_spinner=False)
def _logo_data_uri() -> tuple[str, bool] | None:
    """Logo déposé dans assets/, encodé en data URI, + faut-il l'inverser.

    Convention : un fichier dont le nom contient « blanc » ou « white » est
    déjà clair, on l'affiche tel quel. Tout autre fichier est supposé sombre
    sur fond clair (comme le logo officiel) et est inversé pour le thème.
    """
    if not _LOGO_DIR.is_dir():
        return None
    candidates = sorted(
        f for f in _LOGO_DIR.iterdir()
        if f.is_file() and f.name.lower().startswith("logo")
        and f.suffix.lower() in _LOGO_EXTS
    )
    if not candidates:
        return None
    logo = candidates[0]
    encoded = base64.b64encode(logo.read_bytes()).decode("ascii")
    light = any(w in logo.stem.lower() for w in ("blanc", "white"))
    return f"data:{_MIME[logo.suffix.lower()]};base64,{encoded}", not light


def logo_markup() -> str:
    """Le logo de la marque : le fichier d'assets/ s'il existe, sinon le lettrage."""
    found = _logo_data_uri()
    if found:
        uri, invert = found
        classes = "mk-logo-img mk-invert" if invert else "mk-logo-img"
        return f'<img class="{classes}" src="{uri}" alt="{BRAND["name"]}">'
    return (
        '<div class="mk-wordmark">'
        '<div class="mk-wm-top">MINE</div>'
        f'<div class="mk-wm-mid"><span class="mk-wm-rule"></span>{_PICKS_SVG}'
        '<span class="mk-wm-rule"></span></div>'
        '<div class="mk-wm-bot">DE KETCHUP</div>'
        "</div>"
    )


def brand_header(subtitle: str | None = None) -> None:
    """En-tête : logo de la marque puis sous-titre."""
    st.markdown(
        f"""
        <div class="mk-header">
          {logo_markup()}
          <div class="mk-tag">{subtitle or BRAND['tagline']}</div>
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
