"""Rarity tier definitions."""

from __future__ import annotations

from .models import Rarity

# Color scheme from buddy design system
RARITIES: tuple[Rarity, ...] = (
    Rarity(id="common", name="Common", weight=60, color="#99a5b2"),
    Rarity(id="uncommon", name="Uncommon", weight=25, color="#a4bf8d"),
    Rarity(id="rare", name="Rare", weight=10, color="#86c0d0"),
    Rarity(id="epic", name="Epic", weight=4, color="#b78aaf"),
    Rarity(id="legendary", name="Legendary", weight=1, color="#ebca89"),
)

# Shiny is a separate flag, not a rarity tier
SHINY_CHANCE = 0.01  # 1%
SHINY_COLOR = "#f0c674"  # Rainbow gold


def get_rarity(id: str) -> Rarity | None:
    """Get rarity by ID."""
    for rarity in RARITIES:
        if rarity.id == id:
            return rarity
    return None


def total_weight() -> int:
    """Calculate total weight for random selection."""
    return sum(r.weight for r in RARITIES)