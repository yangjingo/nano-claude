"""Eye style definitions."""

from __future__ import annotations

from .models import EyeStyle

EYE_STYLES: tuple[EyeStyle, ...] = (
    EyeStyle(id="dot", symbol=".", name="Dot Eye"),
    EyeStyle(id="star", symbol="*", name="Star Eye"),
    EyeStyle(id="cross", symbol="x", name="Cross Eye"),
    EyeStyle(id="solid", symbol="@", name="Solid Eye"),
    EyeStyle(id="swirl", symbol="~", name="Swirl Eye"),
    EyeStyle(id="blank", symbol="o", name="Blank Eye"),
)


def get_eye_style(id: str) -> EyeStyle | None:
    """Get eye style by ID."""
    for eye in EYE_STYLES:
        if eye.id == id:
            return eye
    return None
