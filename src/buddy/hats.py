"""Hat/accessory definitions."""

from __future__ import annotations

from .models import Hat

HATS: tuple[Hat, ...] = (
    Hat(id="none", name="无帽子", ascii_art=""),
    Hat(
        id="crown",
        name="皇冠",
        ascii_art=r"""
      ___
     /   \
    |_____|
""",
    ),
    Hat(
        id="tophat",
        name="礼帽",
        ascii_art=r"""
      ___
     |___|
     |   |
""",
    ),
    Hat(
        id="propeller",
        name="螺旋桨帽",
        ascii_art=r"""
     /-o-\
      ___
""",
    ),
    Hat(
        id="halo",
        name="光环",
        ascii_art=r"""
      (O)
""",
    ),
    Hat(
        id="wizard",
        name="巫师帽",
        ascii_art=r"""
       ^
      /_\
     /___\
""",
    ),
    Hat(
        id="beanie",
        name="毛线帽",
        ascii_art=r"""
      ___
     (___)
""",
    ),
    Hat(
        id="tinyduck",
        name="小鸭子",
        ascii_art=r"""
      (o)
     <(__)
""",
    ),
)


def get_hat(id: str) -> Hat | None:
    """Get hat by ID."""
    for hat in HATS:
        if hat.id == id:
            return hat
    return None
