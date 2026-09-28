import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from zq.service import schedulejs


class FootballScheduleJsTest(unittest.TestCase):
    def test_recent_finished_season_rows_are_closed(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "36#2025#36.js", "leagueId": 36, "matchSeason": "2025", "fileName": "36.js"}
        season_stats = {(36, "2025"): (100, 100, now - timedelta(days=31))}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_load_schedule_completion_stats", return_value={}), patch.object(
            schedulejs, "_batch_mark_schedule_states"
        ) as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [])
        mark_states.assert_called_once_with(["36#2025#36.js"], schedulejs.SCHETASK_STATE_FINISHED)

    def test_recent_unfinished_season_rows_stay_active(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "36#2025-2026#36.js", "leagueId": 36, "matchSeason": "2025-2026", "fileName": "36.js"}
        season_stats = {(36, "2025-2026"): (100, 99, now - timedelta(days=31))}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_load_schedule_completion_stats", return_value={}), patch.object(
            schedulejs, "_is_schedule_row_locally_finished", return_value=False
        ), patch.object(schedulejs, "_batch_mark_schedule_states") as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [row])
        mark_states.assert_called_once_with([], schedulejs.SCHETASK_STATE_FINISHED)

    def test_expired_recent_season_rows_are_closed_by_season_label(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "36#2025#36.js", "leagueId": 36, "matchSeason": "2025", "fileName": "36.js"}
        season_stats = {(36, "2025"): (100, 99, now + timedelta(days=10))}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_load_schedule_completion_stats", return_value={}), patch.object(
            schedulejs, "_batch_mark_schedule_states"
        ) as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [])
        mark_states.assert_called_once_with(["36#2025#36.js"], schedulejs.SCHETASK_STATE_FINISHED)

    def test_current_cross_year_season_label_stays_active_when_unfinished(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "36#2025-2026#36.js", "leagueId": 36, "matchSeason": "2025-2026", "fileName": "36.js"}
        season_stats = {(36, "2025-2026"): (100, 99, now + timedelta(days=10))}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_load_schedule_completion_stats", return_value={}), patch.object(
            schedulejs, "_is_schedule_row_locally_finished", return_value=False
        ), patch.object(schedulejs, "_batch_mark_schedule_states") as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [row])
        mark_states.assert_called_once_with([], schedulejs.SCHETASK_STATE_FINISHED)

    def test_rows_outside_recent_seasons_are_marked_finished(self):
        rows = [
            {"scheKey": "36#2024#36.js", "leagueId": 36, "matchSeason": "2024", "fileName": "36.js"},
            {"scheKey": "36#2026#36.js", "leagueId": 36, "matchSeason": "2026", "fileName": "36.js"},
        ]

        with patch.object(schedulejs, "_recent_schetask_seasons_by_league", return_value={36: {"2026"}}), patch.object(
            schedulejs, "_schedule_work_file_exists", return_value=False
        ), patch.object(schedulejs, "_batch_mark_schedule_states") as mark_states:
            filtered = schedulejs._filter_recent_schedule_rows(rows, season_count=1)

        self.assertEqual(filtered, [rows[1]])
        mark_states.assert_called_once_with(["36#2024#36.js"], schedulejs.SCHETASK_STATE_FINISHED)

    def test_consumed_expired_season_file_is_marked_finished(self):
        with patch.object(schedulejs, "_is_file_season_label_expired", return_value=True):
            state = schedulejs._resolve_schedule_state(
                [{"MatchState": 0, "MatchTime": "2025-08-01 12:00"}],
                "/tmp/2025/36.js",
            )

        self.assertEqual(state, schedulejs.SCHETASK_STATE_FINISHED)


if __name__ == "__main__":
    unittest.main()
