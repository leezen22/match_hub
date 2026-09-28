import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from lq.service import schedule
from lq.service import schedulejs


class BasketballScheduleSummaryTest(unittest.TestCase):
    def test_failed_file_is_retained_and_reported(self):
        with patch.object(schedule, "_schedule_work_files", return_value=["good.js", "bad.js"]), patch.object(
            schedule, "_get_task_time", return_value=datetime.now()
        ), patch.object(
            schedule, "upScheduleByFile", side_effect=[True, False]
        ), patch.object(
            schedule.os.path, "exists", return_value=True
        ), patch.object(
            schedule.os, "remove"
        ) as remove, patch.object(
            schedule.fileUtil, "logLine"
        ), patch.object(
            schedule.sql_util, "upData"
        ):
            summary = schedule.upSchedule()

        self.assertEqual(summary, {"selected": 2, "success": 1, "failed": 1})
        remove.assert_called_once_with("good.js")

    def test_cup_file_uses_numeric_league_id(self):
        self.assertEqual(schedule._schedule_key_from_file("work/24/c455.js"), "455#24#c455.js")
        self.assertEqual(schedule._schedule_key_from_file("work/25-26/l2_1.js"), "2#25-26#l2_1.js")

    def test_failed_playoff_discovery_is_included_in_schedule_result(self):
        with patch.object(schedulejs, "_ensure_schedule_crawler_tracking_columns"), patch.object(
            schedulejs, "_discover_due_playoff_schedule_js", return_value={"failed": 1}
        ), patch.object(
            schedulejs, "_select_active_schedule_js_rows", return_value=[]
        ), patch.object(
            schedulejs, "_advance_task_time"
        ), patch.object(
            schedulejs.fileUtil, "logLine"
        ):
            result = schedulejs.upActiveScheJs(league_ids=(2,))

        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["playoff_discovery_failed"], 1)

    def test_failed_playoff_request_is_counted(self):
        with patch.object(
            schedulejs, "_active_playoff_leagues", return_value=[{"league_id": 2, "kind_type": 1}]
        ), patch.object(
            schedulejs, "_latest_local_league_season", return_value="26"
        ), patch.object(
            schedulejs, "_regular_season_end_time", return_value=datetime.now() - timedelta(days=1)
        ), patch.object(
            schedulejs, "_should_discover_playoff_js", return_value=True
        ), patch.object(
            schedulejs, "_discover_playoff_schedule_js", return_value={"ok": False}
        ):
            result = schedulejs._discover_due_playoff_schedule_js(league_ids=(2,))

        self.assertEqual(result, {"selected": 1, "success": 0, "failed": 1})

    def test_recent_finished_season_rows_are_closed(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "2#26#l2_2.js", "leagueId": 2, "matchSeason": "26", "fileName": "l2_2.js"}
        season_stats = {(2, "26"): (100, 100, now - timedelta(days=40), 1)}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_batch_mark_schedule_states") as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [])
        mark_states.assert_called_once_with(["2#26#l2_2.js"], schedulejs.SCHEDULE_CRAWLER_STATE_FINISHED)

    def test_recent_unfinished_season_rows_stay_active(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "2#26#l2_2.js", "leagueId": 2, "matchSeason": "26", "fileName": "l2_2.js"}
        season_stats = {(2, "26"): (100, 99, now - timedelta(days=20), 1)}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_is_schedule_row_locally_finished", return_value=False), patch.object(
            schedulejs, "_batch_mark_schedule_states"
        ) as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [row])
        mark_states.assert_called_once_with([], schedulejs.SCHEDULE_CRAWLER_STATE_FINISHED)

    def test_expired_recent_season_rows_are_closed_by_season_label(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "477#25#l477_2.js", "leagueId": 477, "matchSeason": "25", "fileName": "l477_2.js"}
        season_stats = {(477, "25"): (896, 868, now + timedelta(days=10), 1)}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_load_schedule_scope_completion_stats", return_value={}), patch.object(
            schedulejs, "_batch_mark_schedule_states"
        ) as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [])
        mark_states.assert_called_once_with(["477#25#l477_2.js"], schedulejs.SCHEDULE_CRAWLER_STATE_FINISHED)

    def test_current_cross_year_season_label_stays_active_when_unfinished(self):
        now = datetime(2026, 9, 28, 12, 0, 0)
        row = {"scheKey": "18#25-26#l18_1_2026_4.js", "leagueId": 18, "matchSeason": "25-26", "fileName": "l18_1_2026_4.js"}
        season_stats = {(18, "25-26"): (100, 99, now - timedelta(days=30), 1)}

        with patch.object(schedulejs, "_schedule_work_file_exists", return_value=False), patch.object(
            schedulejs, "_load_season_completion_stats", return_value=season_stats
        ), patch.object(schedulejs, "_load_schedule_scope_completion_stats", return_value={}), patch.object(
            schedulejs, "_is_schedule_row_locally_finished", return_value=False
        ), patch.object(schedulejs, "_batch_mark_schedule_states") as mark_states:
            rows = schedulejs._close_locally_finished_schedule_rows([row], now)

        self.assertEqual(rows, [row])
        mark_states.assert_called_once_with([], schedulejs.SCHEDULE_CRAWLER_STATE_FINISHED)

    def test_rows_outside_recent_seasons_are_marked_finished(self):
        rows = [
            {"scheKey": "2#24#l2_1.js", "leagueId": 2, "matchSeason": "24", "fileName": "l2_1.js"},
            {"scheKey": "2#26#l2_1.js", "leagueId": 2, "matchSeason": "26", "fileName": "l2_1.js"},
        ]

        with patch.object(schedulejs, "_recent_schedule_crawler_seasons_by_league", return_value={2: {"26"}}), patch.object(
            schedulejs, "_schedule_work_file_exists", return_value=False
        ), patch.object(schedulejs, "_batch_mark_schedule_states") as mark_states:
            filtered = schedulejs._filter_recent_schedule_rows(rows, season_count=1)

        self.assertEqual(filtered, [rows[1]])
        mark_states.assert_called_once_with(["2#24#l2_1.js"], schedulejs.SCHEDULE_CRAWLER_STATE_FINISHED)

    def test_regular_schedule_month_file_scope_includes_year(self):
        self.assertEqual(
            schedulejs._schedule_row_match_scope({"fileName": "l518_1_2025_11.js"}),
            {"match_kind": 1, "year": 2025, "month": 11},
        )

    def test_consumed_expired_season_file_is_marked_finished(self):
        matches = [{"matchState": 0, "matchTime": "2025-08-01 12:00"}]

        self.assertEqual(
            schedule._resolve_schedule_crawler_state(matches, "l", "1", season_expired=True),
            schedulejs.SCHEDULE_CRAWLER_STATE_FINISHED,
        )


if __name__ == "__main__":
    unittest.main()
