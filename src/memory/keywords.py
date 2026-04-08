"""Keyword matching rules for blood moon consolidation.

Uses compound patterns with scoring to avoid false positives.
Single broad keywords like "之前" are replaced with compound patterns
that require surrounding context (e.g., "截止.*之前").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """Types of extractable signals."""

    PREFERENCE = "preference"
    ERROR = "error"
    DECISION = "decision"
    DEADLINE = "deadline"


@dataclass
class MatchedSignal:
    """A signal extracted from transcript text."""

    signal_type: SignalType
    matched_keyword: str
    context: str  # Surrounding text (before + after)
    line_number: int
    source_file: str
    score: float = 1.0  # Confidence score 0.0-1.0

    @property
    def category(self) -> str:
        return self.signal_type.value


# ── Compound patterns with weights ──────────────────────────────────
# Each tuple: (compiled_regex, weight, english_tag)
# weight: higher = more specific/reliable signal
# english_tag: used for memory file naming

_PREFERENCE_RULES = [
    # Specific compound patterns (high weight)
    (r"不要用\s+mock", 0.95, "no_mock_testing"),
    (r"不要用\s+emoji", 0.95, "no_emoji_commits"),
    (r"prefer\s+\S+\s+over", 0.90, "tool_preference"),
    (r"never\s+use\s+\S+", 0.90, "avoid_tool"),
    (r"always\s+use\s+\S+", 0.90, "preferred_tool"),
    # General preference patterns (medium weight)
    (r"不要用", 0.70, "avoid_pattern"),
    (r"别用", 0.70, "avoid_pattern"),
    (r"我习惯", 0.75, "user_habit"),
    (r"我喜欢", 0.75, "user_preference"),
    (r"总是", 0.60, "user_habit"),
]

_ERROR_RULES = [
    # Specific compound patterns
    (r"incident", 0.90, "production_incident"),
    (r"regression", 0.90, "code_regression"),
    (r"线上.*(失败|错误|挂)", 0.85, "prod_failure"),
    (r"prod.*(挂|fail|broken)", 0.85, "prod_failure"),
    (r"mock.*通过.*prod.*挂", 0.95, "mock_prod_divergence"),
    # General patterns (lower weight to reduce noise)
    (r"\bbug\b", 0.40, "bug_report"),
    (r"fix", 0.35, "bug_fix"),
    (r"crash", 0.80, "crash_report"),
    (r"broken", 0.75, "broken_feature"),
    (r"unexpected", 0.60, "unexpected_behavior"),
]

_DECISION_RULES = [
    # Specific compound patterns
    (r"决定用\s+\S+", 0.90, "tech_decision"),
    (r"我们选[了]?\s*\S+", 0.90, "tech_choice"),
    (r"go\s+with\s+\S+", 0.85, "go_with"),
    (r"switch\s+to\s+\S+", 0.90, "tech_migration"),
    (r"migrate\s+to\s+\S+", 0.90, "tech_migration"),
    (r"let's\s+use\s+\S+", 0.85, "tech_choice"),
    # General patterns
    (r"我们用", 0.70, "tech_choice"),
    (r"改成", 0.65, "refactor_decision"),
    (r"换成", 0.65, "tech_swap"),
]

_DEADLINE_RULES = [
    # Specific compound patterns (require context, not bare "之前")
    (r"截止.*之前", 0.90, "deadline_before"),
    (r"deadline\s+is\s+\S+", 0.90, "deadline_explicit"),
    (r"by\s+(friday|monday|tuesday|wednesday|thursday|saturday|sunday)", 0.85, "deadline_day"),
    (r"合并冻结", 0.95, "merge_freeze"),
    (r"merge\s+freeze", 0.95, "merge_freeze"),
    (r"ship\s+by", 0.85, "ship_deadline"),
    (r"release\s+\d", 0.80, "release_target"),
    (r"截止", 0.75, "deadline"),
    (r"freeze", 0.70, "freeze"),
    # "之前" only when preceded by a deadline-related word
    (r"(截止|deadline|due|release|ship|freeze).*之前", 0.80, "deadline_before"),
]

# All rules indexed by signal type
COMPOUND_RULES: dict[SignalType, list[tuple]] = {
    SignalType.PREFERENCE: _PREFERENCE_RULES,
    SignalType.ERROR: _ERROR_RULES,
    SignalType.DECISION: _DECISION_RULES,
    SignalType.DEADLINE: _DEADLINE_RULES,
}

# Minimum score threshold — signals below this are discarded
MIN_SCORE = 0.5


class KeywordMatcher:
    """Scan transcript lines for memory-worthy signals using compound patterns."""

    def __init__(
        self,
        rules: dict[SignalType, list[tuple]] | None = None,
        min_score: float = MIN_SCORE,
        context_lines: int = 2,
    ):
        """Initialize matcher.

        Args:
            rules: Compound rules dict (uses defaults if None).
            min_score: Minimum confidence score to accept a signal.
            context_lines: Number of lines before/after to capture.
        """
        self._rules = rules or COMPOUND_RULES
        self._min_score = min_score
        self._context_lines = context_lines

        # Compile regex patterns
        self._compiled: dict[SignalType, list[tuple[re.Pattern, float, str]]] = {}
        for stype, rule_list in self._rules.items():
            self._compiled[stype] = [
                (re.compile(pattern, re.IGNORECASE), weight, tag)
                for pattern, weight, tag in rule_list
            ]

    def scan_lines(
        self,
        lines: list[str],
        source_file: str = "",
    ) -> list[MatchedSignal]:
        """Scan a list of transcript lines for signals.

        For each line, finds the highest-scoring match across all types.
        Only returns signals above min_score.

        Args:
            lines: Transcript text lines.
            source_file: Source file path for attribution.

        Returns:
            List of matched signals, ordered by line number.
        """
        signals: list[MatchedSignal] = []
        total_lines = len(lines)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            best: Optional[tuple[SignalType, re.Match, float, str]] = None

            for stype, compiled_rules in self._compiled.items():
                for pattern, weight, tag in compiled_rules:
                    match = pattern.search(stripped)
                    if match:
                        score = weight
                        if best is None or score > best[2]:
                            best = (stype, match, score, tag)
                        break  # Best match per type for this line

            if best is None or best[2] < self._min_score:
                continue

            stype, match, score, tag = best

            # Adaptive context window: cap at file size
            ctx = min(self._context_lines, total_lines)
            start = max(0, i - ctx)
            end = min(total_lines, i + ctx + 1)
            context_lines_list = [
                l.strip() for l in lines[start:end] if l.strip()
            ]
            context = "\n".join(context_lines_list)

            signals.append(
                MatchedSignal(
                    signal_type=stype,
                    matched_keyword=match.group(),
                    context=context,
                    line_number=i + 1,
                    source_file=source_file,
                    score=score,
                )
            )

        return signals

    def scan_file(self, file_path: str) -> list[MatchedSignal]:
        """Scan a transcript file for signals.

        Args:
            file_path: Path to transcript file (.jsonl, .md, .txt).

        Returns:
            List of matched signals.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            lines = content.splitlines()
            return self.scan_lines(lines, source_file=file_path)
        except (IOError, OSError):
            return []

    def deduplicate(self, signals: list[MatchedSignal]) -> list[MatchedSignal]:
        """Remove duplicate signals based on tag + similar context.

        Keeps the highest-scoring signal when duplicates are found.

        Args:
            signals: List of signals to deduplicate.

        Returns:
            Deduplicated list, sorted by score descending.
        """
        seen: dict[str, MatchedSignal] = {}

        for sig in signals:
            # Key: signal type + first 80 chars of context
            key = f"{sig.signal_type.value}:{sig.context[:80]}"
            if key not in seen or sig.score > seen[key].score:
                seen[key] = sig

        return sorted(seen.values(), key=lambda s: s.score, reverse=True)

    def derive_keywords(self, signals: list[MatchedSignal]) -> list[str]:
        """Extract candidate search terms from matched signals.

        Used by the dreamer loop to grep/glob for related source files.

        Args:
            signals: Already matched signals.

        Returns:
            List of search terms (filenames, identifiers, concepts).
        """
        terms: set[str] = set()

        for sig in signals:
            ctx = sig.context
            # Extract quoted terms (e.g., "Redis", "mock", "ruff")
            for match in re.finditer(r'"([^"]+)"', ctx):
                terms.add(match.group(1))
            for match in re.finditer(r"'([^']+)'", ctx):
                terms.add(match.group(1))
            # Extract identifiers after common verbs
            for pattern in [r"用\s+(\S+)", r"use\s+(\S+)", r"选[了]?\s*(\S+)"]:
                for match in re.finditer(pattern, ctx, re.IGNORECASE):
                    word = match.group(1).strip("，。,. ")
                    if len(word) >= 2:
                        terms.add(word)

        return sorted(terms)
