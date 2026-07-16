"""Warm terminal palette derived from Nano-Claude's clay-brown logo."""

# Brand ramp: the original logo brown, lifted for legibility on dark terminals.
BRAND_PRIMARY = "#c58b5d"  # clay
BRAND_ACCENT = "#dfb07f"  # sand
BRAND_DEEP = "#8c6239"  # original logo brown

# Warm neutrals keep secondary UI quieter than the conversation.
TEXT_PRIMARY = "#ddd5ca"
TEXT_MUTED = "#a0978d"
TEXT_SUBTLE = "#756e67"
SEPARATOR = "#5b544e"

# Low-saturation semantic colors sit comfortably beside the clay ramp.
SUCCESS = "#91ad7c"
WARNING = "#d2a35c"
ERROR = "#cf7468"


PT_STYLE_RULES = {
    "prompt": f"{BRAND_ACCENT} bold",
    "completion-menu": "noreverse bg:default",
    "completion-menu.completion": f"noreverse bg:default {TEXT_PRIMARY}",
    "completion-menu.completion.selected": (
        f"noreverse bg:default {BRAND_ACCENT} bold"
    ),
    "completion-menu.meta": f"noreverse bg:default {TEXT_SUBTLE}",
    "completion-menu.meta.selected": f"noreverse bg:default {BRAND_PRIMARY}",
    "scrollbar": f"noreverse bg:default {SEPARATOR}",
    "scrollbar.button": f"noreverse bg:default {TEXT_MUTED}",
    "bottom-toolbar": "noreverse bg:default",
    "bottom-toolbar.text": "noreverse bg:default",
    "hud.separator": SEPARATOR,
    "hud.model": BRAND_PRIMARY,
    "hud.label": TEXT_SUBTLE,
    "hud.path": TEXT_MUTED,
    "hud.metric": BRAND_ACCENT,
    "status.spinner": BRAND_PRIMARY,
    "status.label": TEXT_PRIMARY,
    "status.meta": TEXT_SUBTLE,
    "trace.branch": BRAND_DEEP,
    "trace.content": f"{TEXT_MUTED} italic",
    "composer.placeholder": f"{TEXT_SUBTLE} italic",
}


CHOICE_STYLE_RULES = {
    "choice": f"noreverse bg:default {TEXT_PRIMARY}",
    "choice.selected": f"noreverse bg:default {BRAND_ACCENT} bold",
    "choice.unselected": f"noreverse bg:default {TEXT_SUBTLE}",
    "prompt": f"noreverse bg:default {BRAND_PRIMARY} bold",
    "separator": f"noreverse bg:default {SEPARATOR}",
    "frame": f"noreverse bg:default {TEXT_SUBTLE}",
    "frame.label": f"noreverse bg:default {BRAND_ACCENT}",
}


RICH_HUD_STYLES = {
    "class:hud.separator": SEPARATOR,
    "class:hud.model": BRAND_PRIMARY,
    "class:hud.label": TEXT_SUBTLE,
    "class:hud.path": TEXT_MUTED,
    "class:hud.metric": BRAND_ACCENT,
}
