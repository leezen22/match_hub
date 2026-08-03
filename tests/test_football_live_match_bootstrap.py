import unittest
from unittest.mock import patch

from zq.live_match_bootstrap import (
    build_live_match_bootstrap_plan,
    persist_live_match_bootstrap,
)


REALTIME_ROW = (
    "3047987^#0099cc^美预备联^美預備聯^^圣何塞地震后备队^聖荷西地震後備隊^^"
    "奥斯汀FC II队^奧斯丁FC II隊^^10:30^2026,7,3,11,43,53^5^1^1^0^1^0^0^1^1^^^"
    "0^0^^^True^-0.25^^^^^^^8-3^61310^65764^^41^0^;|;|;|;;;3-3;^2026^0^2343^"
    "2.75^0^6^1^1^1^^0^^^^^^^0^0^0^0^0^点球[3-3]^點球[3-3]^点球[3-3]^0"
)
REALTIME = "var A=Array(2);var matchcount=1;A[1]=\"{}\".split('^');".format(REALTIME_ROW)


def analysis_header(*, home_id="61310", away_id="65764", league_id="2343"):
    row = [""] * 74
    row[0] = "圣何塞地震后备队"
    row[1] = "奥斯汀FC II队"
    row[2] = "聖荷西地震後備隊"
    row[3] = "奧斯丁FC II隊"
    row[4] = "-1"
    row[5] = "20260803103000"
    row[13] = league_id
    row[15] = "美预备联"
    row[17] = home_id
    row[18] = away_id
    row[25] = "20260803125350"
    row[72] = "3047987"
    return "^".join(row)


METADATA = {
    "league_id": 2343,
    "league_name": "美预备联",
    "league_type": 1,
    "if_have_sub": 0,
    "seasons": ["2026"],
    "metadata_binding_status": "detail_page_resolved",
}


class FootballLiveMatchBootstrapTest(unittest.TestCase):
    def test_builds_schedule_only_plan_from_independent_sources(self):
        plan = build_live_match_bootstrap_plan(
            3047987,
            REALTIME,
            analysis_header(),
            METADATA,
        )

        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["schedule_row"]["homeTeamID"], 61310)
        self.assertEqual(plan["schedule_row"]["awayTeamID"], 65764)
        self.assertEqual(plan["schedule_row"]["matchState"], -1)
        self.assertEqual(plan["lifecycle_observation"]["realtime_state"], 5)
        self.assertEqual(plan["lifecycle_observation"]["analysis_state"], -1)
        self.assertNotIn("homeScore", plan["schedule_row"])
        self.assertIn("penalty_score", plan["excluded"])
        self.assertEqual(plan["time_semantics"]["storage_timezone"], "UTC+08:00")

    def test_rejects_team_identity_conflict(self):
        with self.assertRaisesRegex(ValueError, "home_team_id"):
            build_live_match_bootstrap_plan(
                3047987,
                REALTIME,
                analysis_header(home_id="999"),
                METADATA,
            )

    def test_rejects_incomplete_realtime_batch(self):
        incomplete = REALTIME.replace("matchcount=1", "matchcount=2")
        with self.assertRaisesRegex(ValueError, "batch incomplete"):
            build_live_match_bootstrap_plan(
                3047987,
                incomplete,
                analysis_header(),
                METADATA,
            )

    def test_rejects_match_time_conflict(self):
        with self.assertRaisesRegex(ValueError, "clock conflict"):
            build_live_match_bootstrap_plan(
                3047987,
                REALTIME,
                analysis_header().replace("20260803103000", "20260803110000"),
                METADATA,
            )

    def test_rejects_analysis_older_than_realtime_state_reference(self):
        with self.assertRaisesRegex(ValueError, "time order conflict"):
            build_live_match_bootstrap_plan(
                3047987,
                REALTIME,
                analysis_header().replace("20260803125350", "20260803110000"),
                METADATA,
            )

    def test_persistence_commits_all_identity_rows_in_one_transaction(self):
        plan = build_live_match_bootstrap_plan(3047987, REALTIME, analysis_header(), METADATA)
        connection = FakeConnection()

        with patch("zq.live_match_bootstrap._connect", return_value=connection):
            result = persist_live_match_bootstrap(plan)

        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["system_match_id"], 1989905)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        inserts = [sql for sql, _ in connection.cursor_instance.calls if sql.startswith("INSERT")]
        self.assertEqual(len(inserts), 4)
        self.assertFalse(any("homeScore" in sql or "awayScore" in sql for sql in inserts))

    def test_persistence_rolls_back_when_schedule_insert_fails(self):
        plan = build_live_match_bootstrap_plan(3047987, REALTIME, analysis_header(), METADATA)
        connection = FakeConnection(fail_schedule_insert=True)

        with patch("zq.live_match_bootstrap._connect", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "schedule insert failed"):
                persist_live_match_bootstrap(plan)

        self.assertFalse(connection.committed)
        self.assertTrue(connection.rolled_back)


class FakeConnection:
    def __init__(self, *, fail_schedule_insert=False):
        self.cursor_instance = FakeCursor(fail_schedule_insert=fail_schedule_insert)
        self.committed = False
        self.rolled_back = False

    def cursor(self, _cursor_type):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class FakeCursor:
    def __init__(self, *, fail_schedule_insert=False):
        self.fail_schedule_insert = fail_schedule_insert
        self.calls = []
        self.last_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params):
        self.last_sql = sql
        self.calls.append((sql, params))
        if self.fail_schedule_insert and sql.startswith("INSERT INTO zq_schedule"):
            raise RuntimeError("schedule insert failed")

    def fetchone(self):
        if self.last_sql.startswith("SELECT matchID FROM zq_schedule"):
            return {"matchID": 1989905}
        return None


if __name__ == "__main__":
    unittest.main()
