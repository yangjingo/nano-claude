"""Latency measurements shared by the agent runtime and terminal HUD."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelTiming:
    """Timing for one model request within an agentic turn."""

    ttft_seconds: float
    generation_seconds: float
    output_tokens: int

    @property
    def token_intervals(self) -> int:
        """Number of intervals represented by the generated token count."""
        return max(self.output_tokens - 1, 0)

    @property
    def tpot_seconds(self) -> float | None:
        if not self.token_intervals:
            return None
        return self.generation_seconds / self.token_intervals


@dataclass(frozen=True)
class TurnPerformance:
    """Model timings plus end-to-end latency for one user turn."""

    requests: tuple[ModelTiming, ...] = ()
    end_to_end_seconds: float = 0.0

    @property
    def average_ttft_seconds(self) -> float | None:
        if not self.requests:
            return None
        return sum(request.ttft_seconds for request in self.requests) / len(
            self.requests
        )

    @property
    def average_tpot_seconds(self) -> float | None:
        intervals = sum(request.token_intervals for request in self.requests)
        if not intervals:
            return None
        generation = sum(
            request.generation_seconds
            for request in self.requests
            if request.token_intervals
        )
        return generation / intervals


@dataclass(frozen=True)
class PerformanceSnapshot:
    turns: int
    model_calls: int
    average_ttft_seconds: float | None
    average_tpot_seconds: float | None


@dataclass
class PerformanceTracker:
    """Aggregate exact request timings without coupling them to the UI."""

    turns: int = 0
    _ttft_total: float = 0.0
    _model_calls: int = 0
    _generation_total: float = 0.0
    _token_intervals: int = 0

    def record(self, performance: TurnPerformance | None) -> None:
        if performance is None or not performance.requests:
            return

        self.turns += 1
        for request in performance.requests:
            self._ttft_total += max(request.ttft_seconds, 0.0)
            if request.token_intervals:
                self._generation_total += max(request.generation_seconds, 0.0)
                self._token_intervals += request.token_intervals
            self._model_calls += 1

    def snapshot(self) -> PerformanceSnapshot:
        average_ttft = (
            self._ttft_total / self._model_calls if self._model_calls else None
        )
        average_tpot = (
            self._generation_total / self._token_intervals
            if self._token_intervals
            else None
        )
        return PerformanceSnapshot(
            turns=self.turns,
            model_calls=self._model_calls,
            average_ttft_seconds=average_ttft,
            average_tpot_seconds=average_tpot,
        )


def format_latency(seconds: float | None) -> str:
    """Format latency compactly enough for a single-line terminal HUD."""
    if seconds is None:
        return "--"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"
