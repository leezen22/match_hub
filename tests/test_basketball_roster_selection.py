import unittest
from datetime import datetime
from unittest.mock import patch

from lq.service import roster
from lq_update import update_roster_info


class BasketballRosterSelectionTest(unittest.TestCase):
    def test_no_cutoff_keeps_existing_all_team_scope(self):
        teams = [{"teamID": 1, "leagueID": 2, "name_j": "one"},
                 {"teamID": 2, "leagueID": 2, "name_j": "two"}]
        selected = []
        with patch.object(roster, "migrate"), patch.object(
            roster.sql_util, "select_dicts", return_value=teams
        ) as select, patch.object(
            roster, "update_team_roster", side_effect=lambda team_id, **_kwargs: selected.append(team_id)
        ):
            result = roster.update_all_team_rosters(updated_before=None)

        self.assertEqual(selected, [1, 2])
        self.assertEqual(result["total"], 2)
        self.assertEqual(select.call_count, 1)

    def test_updated_before_selects_old_and_never_successful_teams(self):
        teams = [
            {"teamID": 1, "leagueID": 2, "name_j": "old"},
            {"teamID": 2, "leagueID": 2, "name_j": "boundary"},
            {"teamID": 3, "leagueID": 2, "name_j": "never"},
        ]
        successes = [
            {"teamID": 1, "last_success_at": datetime(2026, 10, 11)},
            {"teamID": 2, "last_success_at": datetime(2026, 10, 12)},
        ]
        selected = []

        def select_dicts(query):
            return successes if "MAX(captured_at)" in query else teams

        def collect(team_id, **_kwargs):
            selected.append(team_id)
            return {"team_id": team_id}

        with patch.object(roster, "migrate"), patch.object(
            roster.sql_util, "select_dicts", side_effect=select_dicts
        ), patch.object(roster, "update_team_roster", side_effect=collect):
            result = roster.update_all_team_rosters(
                updated_before="2026-10-12", fetch_photos=False
            )

        self.assertEqual(selected, [1, 3])
        self.assertEqual((result["total"], result["success"], result["failed"]), (2, 2, 0))

    def test_filter_precedes_offset_and_limit(self):
        teams = [{"teamID": team_id, "leagueID": 2, "name_j": str(team_id)} for team_id in range(1, 5)]
        successes = [{"teamID": 1, "last_success_at": datetime(2026, 10, 13)}]
        selected = []

        def select_dicts(query):
            return successes if "MAX(captured_at)" in query else teams

        with patch.object(roster, "migrate"), patch.object(
            roster.sql_util, "select_dicts", side_effect=select_dicts
        ), patch.object(
            roster, "update_team_roster", side_effect=lambda team_id, **_kwargs: selected.append(team_id)
        ):
            result = roster.update_all_team_rosters(
                updated_before="2026-10-12 00:00:00", offset=1, limit=1
            )

        self.assertEqual(selected, [3])
        self.assertEqual(result["total"], 1)

    def test_missing_only_remains_an_intersection(self):
        teams = [{"teamID": 1, "leagueID": 2, "name_j": "old"},
                 {"teamID": 2, "leagueID": 2, "name_j": "never"}]

        def select_dicts(query):
            if "SELECT DISTINCT teamID FROM lq_team_roster_snapshot_batch" in query:
                return [{"teamID": 1}]
            if "MAX(captured_at)" in query:
                return [{"teamID": 1, "last_success_at": datetime(2026, 10, 1)}]
            return teams

        selected = []
        with patch.object(roster, "migrate"), patch.object(
            roster.sql_util, "select_dicts", side_effect=select_dicts
        ), patch.object(
            roster, "update_team_roster", side_effect=lambda team_id, **_kwargs: selected.append(team_id)
        ):
            roster.update_all_team_rosters(missing_only=True, updated_before="2026-10-12")

        self.assertEqual(selected, [2])

    def test_invalid_cutoff_fails_before_database_work(self):
        with patch.object(roster, "migrate") as migrate:
            with self.assertRaises(ValueError):
                roster.update_all_team_rosters(updated_before="not-a-date")
        migrate.assert_not_called()

    def test_entrypoint_forwards_cutoff(self):
        with patch.object(roster, "update_all_team_rosters", return_value={"total": 0}) as update:
            update_roster_info(all_leagues=True, updated_before="2026-10-12")
        self.assertEqual(update.call_args.kwargs["updated_before"], "2026-10-12")


if __name__ == "__main__":
    unittest.main()
