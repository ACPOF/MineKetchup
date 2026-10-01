"""Formatage partagé, sans dépendance à Streamlit (les courriels s'en servent)."""

from __future__ import annotations


def money(value) -> str:
    """Formate un prix à la québécoise : 7,25 $. Retourne '' si pas de prix."""
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",") + " $"
    except (TypeError, ValueError):
        return ""
