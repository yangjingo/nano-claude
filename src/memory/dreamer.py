"""Blood Moon consolidation engine.

L6: Self-refining agent-loop that scans transcripts, extracts signals,
discovers related source files via grep/glob, and consolidates into memories.

The loop iterates until convergence:
  Round 1: Keyword scan transcripts → extract raw signals
  Round 2: Derive search terms from signals → grep/glob source files
           → enrich signal context with real code references
  Round 3: Deduplicate + normalize → match against existing memories
  (converges when no new signals are found)
"""

from __future__ import annotations

import os
import re
import glob as globmod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .keywords import KeywordMatcher, MatchedSignal, SignalType
from .models import DreamResult, MemoryEntry, MemoryType
from .storage import LocalStorage
from .index import rebuild_index


# Transcript file extensions to scan
TRANSCRIPT_EXTENSIONS = {".jsonl", ".md", ".txt", ".log"}

# Maximum rounds for the self-refining loop
MAX_ROUNDS = 5

# Minimum context similarity to consider a signal as "already covered"
CONTEXT_SIMILARITY_THRESHOLD = 0.5

# Source file extensions to grep/glob for context enrichment
SOURCE_EXTENSIONS = {".py", ".ts", ".js", ".rs", ".go", ".java", ".md", ".yaml", ".yml", ".toml"}

# Maximum source files to attach per signal (avoid context explosion)
MAX_SOURCE_FILES_PER_SIGNAL = 3


@dataclass
class ConsolidationCandidate:
    """A signal that may become a memory entry."""

    signal: MatchedSignal
    action: str = "create"  # create | update | merge | skip
    matched_memory: Optional[MemoryEntry] = None
    confidence: float = 0.0
    source_files: list[str] = field(default_factory=list)


@dataclass
class RoundResult:
    """Result of a single loop round."""

    round_num: int
    new_signals: int
    total_signals: int
    search_terms: list[str] = field(default_factory=list)
    source_files_found: int = 0


def _normalize_relative_dates(text: str, reference_date: Optional[datetime] = None) -> str:
    """Convert relative date references to absolute dates."""
    ref = reference_date or datetime.now()

    patterns = [
        # Chinese
        (r"昨天", (ref - timedelta(days=1)).strftime("%Y-%m-%d")),
        (r"前天", (ref - timedelta(days=2)).strftime("%Y-%m-%d")),
        (r"今天", ref.strftime("%Y-%m-%d")),
        (r"明天", (ref + timedelta(days=1)).strftime("%Y-%m-%d")),
        (r"后天", (ref + timedelta(days=2)).strftime("%Y-%m-%d")),
        # English
        (r"\byesterday\b", (ref - timedelta(days=1)).strftime("%Y-%m-%d")),
        (r"\btoday\b", ref.strftime("%Y-%m-%d")),
        (r"\btomorrow\b", (ref + timedelta(days=1)).strftime("%Y-%m-%d")),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    return text


def _signal_to_memory_type(signal: MatchedSignal) -> MemoryType:
    """Map signal type to memory type."""
    return {
        SignalType.PREFERENCE: MemoryType.FEEDBACK,
        SignalType.ERROR: MemoryType.FEEDBACK,
        SignalType.DECISION: MemoryType.PROJECT,
        SignalType.DEADLINE: MemoryType.PROJECT,
    }.get(signal.signal_type, MemoryType.PROJECT)


def _generate_memory_name(signal: MatchedSignal) -> str:
    """Generate an English semantic name from a signal.

    Uses the matched keyword's alphanumeric content, falling back
    to signal type. Produces names like 'no_mock_testing', 'redis_decision'.
    """
    keyword = signal.matched_keyword.strip()

    # Extract alphanumeric words
    words = re.findall(r"[a-zA-Z0-9_]+", keyword)
    if words:
        # Join and truncate
        base = "_".join(w.lower() for w in words if len(w) > 1)
        if base:
            return base[:40]

    # Fallback: type + line number
    return f"{signal.signal_type.value}_line{signal.line_number}"


def _similarity(a: str, b: str) -> float:
    """Word-overlap Jaccard similarity."""
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _find_project_root() -> str:
    """Find project root by walking up from this file."""
    path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    while path != os.path.dirname(path):
        if os.path.exists(os.path.join(path, ".git")) or os.path.exists(os.path.join(path, "CLAUDE.md")):
            return path
        path = os.path.dirname(path)
    return path


class BloodMoon:
    """Blood Moon consolidation engine.

    Self-refining loop:
      Round 1: Scan transcripts for keyword matches
      Round 2: Derive search terms → grep/glob source files → enrich context
      Round 3+: Repeat until no new signals emerge (convergence)
    """

    def __init__(
        self,
        storage: Optional[LocalStorage] = None,
        matcher: Optional[KeywordMatcher] = None,
        transcript_dirs: Optional[list[str]] = None,
        project_root: Optional[str] = None,
    ):
        self.storage = storage or LocalStorage()
        self.matcher = matcher or KeywordMatcher()
        self.transcript_dirs = transcript_dirs or []
        self.project_root = project_root or _find_project_root()

        if not self.transcript_dirs:
            default_dir = os.path.join(self.project_root, ".nano_claude", "transcripts")
            if os.path.isdir(default_dir):
                self.transcript_dirs.append(default_dir)

    def consolidate(
        self,
        transcript_files: Optional[list[str]] = None,
        reference_date: Optional[datetime] = None,
        verbose: bool = False,
    ) -> DreamResult:
        """Run the full blood moon consolidation loop.

        Args:
            transcript_files: Specific files to scan (auto-discovers if None).
            reference_date: Base date for normalization.
            verbose: Print round-by-round progress.

        Returns:
            DreamResult with consolidation statistics.
        """
        ref = reference_date or datetime.now()
        result = DreamResult(total=0)

        # Phase 1: Discover transcript files
        files = transcript_files or self._discover_transcripts()
        if not files:
            return result

        # Phase 2: Self-refining extraction loop
        all_signals, round_log = self._extract_loop(files, verbose=verbose)
        if not all_signals:
            return result

        result.total = len(all_signals)

        # Phase 3: Match against existing memories and consolidate
        candidates = self._match_against_existing(all_signals)
        files_touched = self._apply_consolidation(candidates, ref)

        for c in candidates:
            if c.action == "create":
                result.created += 1
            elif c.action == "update":
                result.updated += 1
            elif c.action == "merge":
                result.merged += 1
            elif c.action == "skip":
                result.pruned += 1

        result.files = files_touched
        result.updated_names = [c.signal.matched_keyword for c in candidates if c.action in ("create", "update")]

        rebuild_index(self.storage)
        return result

    def _discover_transcripts(self) -> list[str]:
        """Find transcript files in configured directories."""
        files = []
        for directory in self.transcript_dirs:
            if not os.path.isdir(directory):
                continue
            for filename in os.listdir(directory):
                ext = os.path.splitext(filename)[1].lower()
                if ext in TRANSCRIPT_EXTENSIONS:
                    files.append(os.path.join(directory, filename))
        return sorted(files)

    def _extract_loop(
        self,
        files: list[str],
        verbose: bool = False,
    ) -> tuple[list[MatchedSignal], list[RoundResult]]:
        """Self-refining extraction loop.

        Round 1: Scan transcripts → raw signals
        Round 2: Derive keywords from signals → grep/glob source files
                 → attach file paths to signals as context enrichment
        Round 3+: Derive new keywords from enriched context → re-scan
                 only transcripts → loop until no new signals

        Key principle: grep/glob enriches signals with file references,
        it does NOT scan source code for new signals (that would match
        pattern definitions, comments, etc. and create noise).

        Args:
            files: Transcript file paths.
            verbose: Print progress.

        Returns:
            Tuple of (final signals, round log).
        """
        round_log: list[RoundResult] = []
        # Map: signal id → list of related source file paths
        signal_sources: dict[int, list[str]] = {}

        # ── Round 1: Initial transcript scan ─────────────────
        signals = self._scan_transcripts(files)
        accumulated = self.matcher.deduplicate(signals)
        round_log.append(RoundResult(
            round_num=1,
            new_signals=len(accumulated),
            total_signals=len(accumulated),
        ))

        if verbose:
            print(f"  Round 1: {len(accumulated)} signals from transcripts")

        # ── Round 2: Derive keywords → grep/glob → enrich ────
        prev_count = len(accumulated)
        search_terms = self.matcher.derive_keywords(accumulated)

        if search_terms:
            source_files = self._discover_source_files(search_terms)

            # Attach source files to matching signals (enrichment, not scanning)
            for sig in accumulated:
                related = self._match_signal_to_files(sig, source_files)
                if related:
                    signal_sources[id(sig)] = related

            round_log.append(RoundResult(
                round_num=2,
                new_signals=0,
                total_signals=len(accumulated),
                search_terms=search_terms[:10],
                source_files_found=len(source_files),
            ))

            if verbose:
                print(f"  Round 2: grep/glob found {len(source_files)} files, "
                      f"enriched {len(signal_sources)} signals")
                print(f"           terms: {search_terms[:5]}")

        # ── Round 3+: Re-scan transcripts with refined keywords ─
        # Build supplementary patterns from derived keywords
        # (only terms that look like meaningful identifiers, not noise)
        extra_terms = [t for t in search_terms if len(t) >= 3 and t[0].isalpha()]
        if extra_terms:
            # Create a supplementary matcher with project-specific patterns
            extra_rules = {}
            for stype in SignalType:
                extra_rules[stype] = [
                    (re.escape(term), 0.55, f"derived_{term.lower()}")
                    for term in extra_terms
                ]
            refined_matcher = KeywordMatcher(rules=extra_rules, min_score=0.5)

            new_signals = self._scan_transcripts_with(files, refined_matcher)
            if new_signals:
                accumulated.extend(new_signals)
                accumulated = self.matcher.deduplicate(accumulated)

                new_count = len(accumulated) - prev_count
                round_log.append(RoundResult(
                    round_num=3,
                    new_signals=new_count,
                    total_signals=len(accumulated),
                    search_terms=extra_terms[:10],
                    source_files_found=0,
                ))

                if verbose:
                    print(f"  Round 3: +{new_count} signals from refined keywords")
            else:
                round_log.append(RoundResult(
                    round_num=3,
                    new_signals=0,
                    total_signals=len(accumulated),
                    search_terms=extra_terms[:10],
                    source_files_found=0,
                ))

        # Final pass: normalize dates + attach source files to context
        for signal in accumulated:
            signal.context = _normalize_relative_dates(signal.context)
            src_files = signal_sources.get(id(signal), [])
            if src_files:
                signal.context += "\n\n**Related files:**\n"
                for sf in src_files[:MAX_SOURCE_FILES_PER_SIGNAL]:
                    rel = os.path.relpath(sf, self.project_root)
                    signal.context += f"- `{rel}`\n"

        return accumulated, round_log

    def _scan_transcripts_with(
        self,
        files: list[str],
        matcher: KeywordMatcher,
    ) -> list[MatchedSignal]:
        """Scan transcript files with a specific matcher."""
        signals: list[MatchedSignal] = []
        for file_path in files:
            sigs = matcher.scan_file(file_path)
            signals.extend(sigs)
        return signals

    def _match_signal_to_files(
        self,
        signal: MatchedSignal,
        source_files: list[str],
    ) -> list[str]:
        """Match a signal to related source files by keyword overlap.

        Args:
            signal: Extracted signal.
            source_files: Discovered source file paths.

        Returns:
            List of matching file paths.
        """
        matched = []
        signal_words = set(re.findall(r"\w+", signal.context.lower()))

        for file_path in source_files:
            filename = os.path.basename(file_path).lower()
            # Check if filename contains any signal words
            filename_words = set(re.findall(r"\w+", os.path.splitext(filename)[0]))
            if signal_words & filename_words:
                matched.append(file_path)
                continue

            # Check file content for keyword overlap (limited scan)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    # Only read first 2KB for quick check
                    head = f.read(2048).lower()
                head_words = set(re.findall(r"\w+", head))
                overlap = signal_words & head_words
                if len(overlap) >= 2:
                    matched.append(file_path)
            except (IOError, OSError):
                pass

        return matched[:MAX_SOURCE_FILES_PER_SIGNAL]

    def _scan_transcripts(self, files: list[str]) -> list[MatchedSignal]:
        """Scan transcript files for signals."""
        all_signals: list[MatchedSignal] = []
        for file_path in files:
            signals = self.matcher.scan_file(file_path)
            all_signals.extend(signals)
        return all_signals

    def _discover_source_files(self, search_terms: list[str]) -> list[str]:
        """Use grep/glob to find source files related to search terms.

        Two strategies:
        1. Glob: find files whose name contains a search term
        2. Grep: find files whose content contains a search term

        Args:
            search_terms: Derived keywords from signals.

        Returns:
            List of source file paths (deduplicated).
        """
        found: set[str] = set()

        for term in search_terms:
            term_clean = term.strip().lower()
            if len(term_clean) < 2:
                continue

            # Strategy 1: Glob for filenames containing the term
            try:
                pattern = os.path.join(self.project_root, "**", f"*{term_clean}*")
                for ext in SOURCE_EXTENSIONS:
                    for match in globmod.glob(pattern + ext, recursive=True):
                        # Skip .nano_claude, __pycache__, node_modules, .git
                        rel = os.path.relpath(match, self.project_root)
                        skip_prefixes = (
                            ".nano_claude", "__pycache__", "node_modules",
                            ".git", ".venv", "venv", "dist", "build",
                        )
                        if any(rel.startswith(p) for p in skip_prefixes):
                            continue
                        found.add(match)
            except (re.error, OSError):
                pass

            # Strategy 2: Grep for content containing the term
            try:
                pattern = os.path.join(self.project_root, "**", f"*")
                for ext in SOURCE_EXTENSIONS:
                    for match in globmod.glob(pattern + ext, recursive=True):
                        rel = os.path.relpath(match, self.project_root)
                        skip_prefixes = (
                            ".nano_claude", "__pycache__", "node_modules",
                            ".git", ".venv", "venv", "dist", "build",
                        )
                        if any(rel.startswith(p) for p in skip_prefixes):
                            continue
                        try:
                            with open(match, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            if term_clean in content.lower():
                                found.add(match)
                        except (IOError, OSError):
                            pass
            except (re.error, OSError):
                pass

        return sorted(found)

    def _match_against_existing(
        self, signals: list[MatchedSignal]
    ) -> list[ConsolidationCandidate]:
        """Compare extracted signals against existing memories.

        Uses score-weighted matching: higher-scored signals are preferred.
        """
        existing = self.storage.load_all()
        candidates = []

        for signal in signals:
            candidate = ConsolidationCandidate(signal=signal)
            candidate.confidence = signal.score

            best_match = None
            best_sim = 0.0

            for memory in existing:
                sim = _similarity(signal.context, memory.content)
                if sim > best_sim:
                    best_sim = sim
                    best_match = memory

            if best_sim >= 0.8 and best_match is not None:
                candidate.action = "skip"
                candidate.matched_memory = best_match
            elif best_sim >= CONTEXT_SIMILARITY_THRESHOLD and best_match is not None:
                candidate.action = "update"
                candidate.matched_memory = best_match
            else:
                candidate.action = "create"

            candidates.append(candidate)

        # Sort by confidence descending — high-quality signals first
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates

    def _apply_consolidation(
        self,
        candidates: list[ConsolidationCandidate],
        reference_date: datetime,
    ) -> list[str]:
        """Apply consolidation actions. Returns list of file paths touched."""
        files_touched: list[str] = []
        for candidate in candidates:
            if candidate.action == "skip":
                continue

            mem_type = _signal_to_memory_type(candidate.signal)
            normalized_context = _normalize_relative_dates(
                candidate.signal.context, reference_date
            )

            if candidate.action == "create":
                name = _generate_memory_name(candidate.signal)
                base_name = name
                counter = 1
                while self.storage.exists(name):
                    name = f"{base_name}_{counter}"
                    counter += 1

                # Build content: signal context + source file references
                content = normalized_context
                if candidate.source_files:
                    content += "\n\n**Source files:**\n"
                    for sf in candidate.source_files[:MAX_SOURCE_FILES_PER_SIGNAL]:
                        rel = os.path.relpath(sf, self.project_root)
                        content += f"- `{rel}`\n"

                # Description: the matched line itself, not the context window
                matched_line = ""
                for l in normalized_context.split("\n"):
                    if candidate.signal.matched_keyword.lower() in l.lower():
                        matched_line = l.strip()
                        break
                description = matched_line[:150] if matched_line else name

                entry = MemoryEntry(
                    name=name,
                    description=description,
                    type=mem_type,
                    content=content,
                    created=reference_date,
                )
                path = self.storage.save(entry)
                if path:
                    files_touched.append(path)

            elif candidate.action == "update":
                memory = candidate.matched_memory
                if memory:
                    # Backup old version before update
                    if memory.file_path and os.path.exists(memory.file_path):
                        archive_path = memory.file_path + ".bak"
                        try:
                            with open(memory.file_path, "r", encoding="utf-8") as f:
                                old_content = f.read()
                            with open(archive_path, "w", encoding="utf-8") as f:
                                f.write(old_content)
                        except (IOError, OSError):
                            pass

                    memory.content = (
                        f"{memory.content}\n\n---\n"
                        f"Blood Moon update ({reference_date.strftime('%Y-%m-%d')}):\n"
                        f"{normalized_context}"
                    )
                    memory.updated = reference_date
                    path = self.storage.save(memory)
                    if path:
                        files_touched.append(path)

            elif candidate.action == "merge":
                memory = candidate.matched_memory
                if memory:
                    memory.content = (
                        f"{memory.content}\n\n---\n"
                        f"Merged signal ({reference_date.strftime('%Y-%m-%d')}):\n"
                        f"{normalized_context}"
                    )
                    memory.updated = reference_date
                    path = self.storage.save(memory)
                    if path:
                        files_touched.append(path)

        return files_touched
