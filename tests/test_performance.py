"""Tests for TTFT/TPOT aggregation and HUD presentation."""

import os
import unittest
from unittest.mock import patch

from src.cli.hud import HudState
from src.performance import ModelTiming, PerformanceTracker, TurnPerformance


class PerformanceTrackerTests(unittest.TestCase):
    def test_averages_ttft_and_weights_tpot_by_token_intervals(self):
        tracker = PerformanceTracker()
        tracker.record(
            TurnPerformance(
                requests=(
                    ModelTiming(0.2, 0.9, 10),
                    ModelTiming(0.4, 0.2, 3),
                ),
                end_to_end_seconds=2.0,
            )
        )

        snapshot = tracker.snapshot()
        self.assertEqual(snapshot.turns, 1)
        self.assertEqual(snapshot.model_calls, 2)
        self.assertAlmostEqual(snapshot.average_ttft_seconds, 0.3)
        self.assertAlmostEqual(snapshot.average_tpot_seconds, 0.1)

    def test_turn_exposes_its_own_weighted_metrics(self):
        performance = TurnPerformance(
            requests=(
                ModelTiming(0.1, 0.4, 5),
                ModelTiming(0.3, 0.2, 3),
            )
        )

        self.assertAlmostEqual(performance.average_ttft_seconds, 0.2)
        self.assertAlmostEqual(performance.average_tpot_seconds, 0.1)

    def test_empty_tracker_uses_unavailable_values(self):
        snapshot = PerformanceTracker().snapshot()
        self.assertIsNone(snapshot.average_ttft_seconds)
        self.assertIsNone(snapshot.average_tpot_seconds)

    def test_hud_exposes_navigation_and_average_metrics(self):
        hud = HudState(
            model_name=lambda: "claude-test",
            context_window_tokens=200_000,
            context_used_tokens=90_000,
        )
        hud.tracker.record(
            TurnPerformance(
                requests=(ModelTiming(0.125, 0.45, 10),),
                end_to_end_seconds=0.8,
            )
        )

        text = hud.plain_text()
        self.assertIn("claude-test · Context 55% left", text)
        self.assertIn("TTFT 125ms", text)
        self.assertIn("TPOT 50ms", text)
        self.assertNotIn("NANO", text)
        self.assertNotIn("calls", text)

    def test_wide_hud_uses_compact_working_directory(self):
        hud = HudState(
            model_name=lambda: "claude-test",
            context_window_tokens=200_000,
        )
        with (
            patch(
                "src.cli.hud.shutil.get_terminal_size",
                return_value=os.terminal_size((140, 24)),
            ),
            patch(
                "src.cli.hud.HudState._working_directory",
                return_value=r"~\Project\nano-claude",
            ),
        ):
            text = hud.plain_text()

        self.assertEqual(
            text,
            r"claude-test · Context 100% left · ~\Project\nano-claude · "
            "TTFT -- · TPOT -- ·",
        )


if __name__ == "__main__":
    unittest.main()
