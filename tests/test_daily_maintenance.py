import json
import io
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import daily_maintenance
from scripts.windows.tee_daily_maintenance import TeeStream


class DailyMaintenanceTest(unittest.TestCase):
    def test_runs_five_steps_in_order_then_skips_within_24_hours(self):
        calls = []
        updater = types.ModuleType("lq_update")
        for name in (
            "update_schedule_js_active",
            "update_schedule",
            "update_score",
            "update_odds",
            "update_details",
        ):
            setattr(updater, name, lambda *args, _name=name, **kwargs: calls.append((_name, kwargs)))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(daily_maintenance, "LOCK_DIR", root / "locks"), patch.object(
                daily_maintenance, "LOCK_PATH", root / "locks" / "daily_maintenance.lock"
            ), patch.object(daily_maintenance, "STATE_DIR", root / "state"), patch.object(
                daily_maintenance, "STATE_PATH", root / "state" / "daily_maintenance.json"
            ), patch.object(
                daily_maintenance,
                "_parse_args",
                return_value=SimpleNamespace(min_interval_hours=24, force=False),
            ), patch.dict(sys.modules, {"lq_update": updater}):
                self.assertEqual(daily_maintenance.main(), 0)
                self.assertEqual(daily_maintenance.main(), 0)

            state = json.loads((root / "state" / "daily_maintenance.json").read_text(encoding="utf-8"))

        self.assertEqual(
            [name for name, _ in calls],
            [
                "update_schedule_js_active",
                "update_schedule",
                "update_score",
                "update_odds",
                "update_details",
            ],
        )
        self.assertEqual(calls[0][1], {"all_leagues": True, "season_count": 3})
        self.assertEqual(state["workflow_version"], daily_maintenance.WORKFLOW_VERSION)
        self.assertEqual(state["last_skip_reason"], "min_interval")

    def test_previous_schedule_only_success_does_not_skip_full_update(self):
        old_state = {"last_success_at": datetime.now().isoformat(timespec="seconds")}
        self.assertEqual(daily_maintenance._should_skip_for_interval(old_state, 24), (False, None))

    def test_failed_attempt_is_not_retried_hourly(self):
        state = {
            "workflow_version": daily_maintenance.WORKFLOW_VERSION,
            "last_attempt_at": datetime.now().isoformat(timespec="seconds"),
            "last_result": "failed",
        }
        should_skip, _ = daily_maintenance._should_skip_for_interval(state, 24)
        self.assertTrue(should_skip)

    def test_interrupted_attempt_retries_at_next_check(self):
        state = {
            "workflow_version": daily_maintenance.WORKFLOW_VERSION,
            "last_attempt_at": datetime.now().isoformat(timespec="seconds"),
            "last_result": "interrupted",
        }
        self.assertEqual(daily_maintenance._should_skip_for_interval(state, 24), (False, None))

    def test_failed_schedule_summary_marks_step_failed(self):
        step = daily_maintenance._run_step("basketball.update_schedule_js_active", lambda: {"failed": 2})
        self.assertFalse(step["ok"])
        self.assertIn("2 item(s) failed", step["error"])

    def test_current_step_is_visible_while_callback_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state = {}

            def check_status():
                current = json.loads(state_path.read_text(encoding="utf-8"))
                self.assertEqual(current["current_step"], "basketball.update_score")

            with patch.object(daily_maintenance, "STATE_DIR", Path(directory)), patch.object(
                daily_maintenance, "STATE_PATH", state_path
            ):
                step = daily_maintenance._run_step("basketball.update_score", check_status, state, 3, 5)
                current = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertTrue(step["ok"])
        self.assertIsNone(current["current_step"])
        self.assertIsNone(current["current_step_label"])
        self.assertEqual(current["last_completed_step_label"], "比分")

    def test_console_output_is_logged_with_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.log"
            console = io.StringIO()
            stream = TeeStream(console, path)
            stream.handler.maxBytes = 20
            stream.handler.backupCount = 1
            try:
                for _ in range(5):
                    stream.write("progress\n")
            finally:
                stream.close()

            self.assertEqual(console.getvalue(), "progress\n" * 5)
            self.assertTrue(path.with_suffix(".log.1").exists())


if __name__ == "__main__":
    unittest.main()
