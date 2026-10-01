"""
Lecture de la configuration, quel que soit l'endroit où le code tourne.

Trois contextes, trois sources :
- GitHub Actions (rapport hebdomadaire) : variables d'environnement ;
- Streamlit Cloud : st.secrets ;
- poste local : .streamlit/secrets.toml.

Les modules d'envoi de courriel ne doivent PAS dépendre de Streamlit : le
script du rapport hebdomadaire tourne sans lui.
"""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

_SECRETS_FILE = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"


@lru_cache(maxsize=1)
def _file_secrets() -> dict:
    try:
        with _SECRETS_FILE.open("rb") as handle:
            return tomllib.load(handle)
    except Exception:  # noqa: BLE001 — absent en production, c'est normal
        return {}


def get(name: str, default: str = "") -> str:
    """Valeur de configuration, cherchée dans l'ordre env → st.secrets → fichier."""
    value = os.environ.get(name)
    if value:
        return value.strip()

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:  # noqa: BLE001 — hors Streamlit, ou secrets absents
        pass

    value = _file_secrets().get(name)
    return str(value).strip() if value else default


def get_list(name: str) -> list[str]:
    """Configuration multi-valeurs : « a@b.ca, c@d.ca » -> ['a@b.ca', 'c@d.ca']."""
    raw = get(name)
    return [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
