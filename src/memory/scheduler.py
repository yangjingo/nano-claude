"""Cron scheduler for blood moon consolidation.

Triggers /dream periodically based on:
1. Cron expression (e.g., "0 3 * * *" for 3 AM daily)
2. Accumulated token threshold (default 5000)
3. Idle time detection (default 30 minutes)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional


@dataclass
class CronExpression:
    """Simple cron expression parser (5-field: min hour dom month dow)."""

    raw: str
    minute: str = "0"
    hour: str = "3"
    dom: str = "*"
    month: str = "*"
    dow: str = "*"

    def __post_init__(self) -> None:
        parts = self.raw.strip().split()
        if len(parts) == 5:
            self.minute, self.hour, self.dom, self.month, self.dow = parts

    def matches(self, dt: datetime) -> bool:
        """Check if the given datetime matches this cron expression.

        Args:
            dt: Datetime to check.

        Returns:
            True if matches.
        """
        return (
            self._field_matches(self.minute, dt.minute, 0, 59)
            and self._field_matches(self.hour, dt.hour, 0, 23)
            and self._field_matches(self.dom, dt.day, 1, 31)
            and self._field_matches(self.month, dt.month, 1, 12)
            and self._field_matches(self.dow, dt.isoweekday() % 7, 0, 6)
        )

    @staticmethod
    def _field_matches(field: str, value: int, lo: int, hi: int) -> bool:
        """Check if a cron field value matches.

        Supports: *, specific values, comma-separated, ranges (1-5).
        """
        if field == "*":
            return True

        for part in field.split(","):
            part = part.strip()
            if "-" in part:
                range_parts = part.split("-")
                if len(range_parts) == 2:
                    try:
                        low, high = int(range_parts[0]), int(range_parts[1])
                        if low <= value <= high:
                            return True
                    except ValueError:
                        continue
            else:
                try:
                    if int(part) == value:
                        return True
                except ValueError:
                    continue

        return False


# Default: every day at 3 AM
DEFAULT_CRON = "0 3 * * *"
DEFAULT_TOKEN_THRESHOLD = 5000
DEFAULT_IDLE_MINUTES = 30


@dataclass
class TokenAccumulator:
    """Track accumulated new tokens to decide if consolidation is worthwhile."""

    _count: int = 0
    _threshold: int = DEFAULT_TOKEN_THRESHOLD

    def add(self, tokens: int) -> None:
        """Add tokens to the accumulator."""
        self._count += tokens

    def reset(self) -> int:
        """Reset and return the accumulated count."""
        count = self._count
        self._count = 0
        return count

    @property
    def count(self) -> int:
        return self._count

    @property
    def is_above_threshold(self) -> bool:
        return self._count >= self._threshold

    def __repr__(self) -> str:
        return f"TokenAccumulator({self._count}/{self._threshold})"


@dataclass
class IdleDetector:
    """Detect user idle time based on filesystem activity."""

    _last_activity: float = field(default_factory=time.time)
    _idle_minutes: int = DEFAULT_IDLE_MINUTES

    def touch(self) -> None:
        """Record user activity."""
        self._last_activity = time.time()

    @property
    def idle_seconds(self) -> float:
        return time.time() - self._last_activity

    @property
    def is_idle(self) -> bool:
        return self.idle_seconds >= self._idle_minutes * 60

    @property
    def idle_minutes(self) -> float:
        return self.idle_seconds / 60


@dataclass
class BloodMoonScheduler:
    """Scheduler for blood moon consolidation.

    Combines cron timing, token accumulation, and idle detection.
    """

    cron: CronExpression = field(default_factory=lambda: CronExpression(DEFAULT_CRON))
    token_accumulator: TokenAccumulator = field(default_factory=TokenAccumulator)
    idle_detector: IdleDetector = field(default_factory=IdleDetector)
    _last_trigger: Optional[datetime] = None
    _min_interval_minutes: int = 60  # Don't trigger more than once per hour

    def should_trigger(self) -> bool:
        """Check if blood moon should trigger now.

        All three conditions must be met:
        1. Cron expression matches current time
        2. Accumulated tokens >= threshold
        3. User has been idle for long enough

        Returns:
            True if all conditions are met.
        """
        now = datetime.now()

        # Check minimum interval
        if self._last_trigger is not None:
            elapsed = (now - self._last_trigger).total_seconds() / 60
            if elapsed < self._min_interval_minutes:
                return False

        # Check all three conditions
        cron_match = self.cron.matches(now)
        tokens_ok = self.token_accumulator.is_above_threshold
        idle_ok = self.idle_detector.is_idle

        if cron_match and tokens_ok and idle_ok:
            self._last_trigger = now
            return True

        return False

    def record_activity(self, tokens: int = 0) -> None:
        """Record user activity and optional token count.

        Args:
            tokens: Number of new tokens generated.
        """
        self.idle_detector.touch()
        if tokens > 0:
            self.token_accumulator.add(tokens)

    def reset(self) -> None:
        """Reset after a successful consolidation."""
        self.token_accumulator.reset()
        self._last_trigger = datetime.now()

    @property
    def status(self) -> str:
        """Human-readable status for debugging."""
        parts = [
            f"Cron: {self.cron.raw}",
            f"Tokens: {self.token_accumulator}",
            f"Idle: {self.idle_detector.idle_minutes:.0f}min / {self.idle_detector._idle_minutes}min",
        ]
        if self._last_trigger:
            parts.append(f"Last trigger: {self._last_trigger.strftime('%Y-%m-%d %H:%M')}")
        return " | ".join(parts)
