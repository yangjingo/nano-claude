"""Compact prompt-toolkit HUD for navigation and live session metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Callable

from prompt_toolkit.formatted_text import StyleAndTextTuples
from rich.text import Text

from ..performance import PerformanceTracker, format_latency
from .theme import RICH_HUD_STYLES


@dataclass
class HudState:
    """Mutable presentation state kept outside of the agent runtime."""

    model_name: Callable[[], str]
    tracker: PerformanceTracker = field(default_factory=PerformanceTracker)
    context_window_tokens: int | None = None
    context_used_tokens: int = 0

    def _context_value(self) -> str:
        if not self.context_window_tokens:
            return "--"
        remaining = max(
            0.0,
            1 - (self.context_used_tokens / self.context_window_tokens),
        )
        return f"{remaining:.0%}"

    @staticmethod
    def _working_directory() -> str:
        cwd = Path.cwd()
        try:
            return str(Path("~") / cwd.relative_to(Path.home()))
        except ValueError:
            return str(cwd)

    def formatted_text(self) -> StyleAndTextTuples:
        snapshot = self.tracker.snapshot()
        width = shutil.get_terminal_size(fallback=(100, 24)).columns
        sections: StyleAndTextTuples = [
            ("class:hud.model", f"  {self.model_name()}"),
            ("class:hud.separator", " · "),
            ("class:hud.label", "Context "),
            ("class:hud.metric", self._context_value()),
            ("class:hud.label", " left"),
            ("class:hud.separator", " · "),
            ("class:hud.label", "TTFT "),
            (
                "class:hud.metric",
                format_latency(snapshot.average_ttft_seconds),
            ),
            ("class:hud.separator", " · "),
            ("class:hud.label", "TPOT "),
            (
                "class:hud.metric",
                format_latency(snapshot.average_tpot_seconds),
            ),
            ("class:hud.separator", " · "),
        ]
        if width >= 100:
            sections[6:6] = [
                ("class:hud.path", self._working_directory()),
                ("class:hud.separator", " · "),
            ]
        return sections

    def plain_text(self) -> str:
        """Fallback representation for non-interactive terminals and tests."""
        return "".join(text for _, text in self.formatted_text()).strip()

    def rich_text(self) -> Text:
        """Render the same background-free HUD inside a Rich live view."""
        rendered = Text()
        for style_name, content in self.formatted_text():
            rendered.append(content, style=RICH_HUD_STYLES.get(style_name, ""))
        return rendered
