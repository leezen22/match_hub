from __future__ import annotations

import unittest
from unittest.mock import patch

import update_request
import zq_update


class FootballExplicitMetadataPlanningTest(unittest.TestCase):
    def test_complete_explicit_metadata_builds_plan_without_catalog_match(self) -> None:
        with patch.object(zq_update, "_resolve_league_by_id", return_value=None):
            plan = zq_update.parse_natural_update_request(
                "",
                league_id=2343,
                season="2026",
                league_type=1,
                if_have_sub=0,
                action="schedule",
            )

        self.assertEqual(plan["league_id"], 2343)
        self.assertIsNone(plan["league_name"])
        self.assertEqual(plan["season"], "2026")
        self.assertEqual(plan["league_type"], 1)
        self.assertEqual(plan["if_have_sub"], 0)
        self.assertEqual(
            plan["metadata_binding_status"],
            "explicit_parameters_without_catalog_match",
        )
        self.assertEqual(
            plan["command"],
            [
                "zq_update.py",
                "schedule-league-season",
                "--league-id",
                "2343",
                "--season",
                "2026",
                "--league-type",
                "1",
                "--if-have-sub",
                "0",
            ],
        )

    def test_catalog_miss_lists_metadata_required_for_safe_plan(self) -> None:
        with (
            patch.object(zq_update, "_resolve_league_by_id", return_value=None),
            patch.object(zq_update, "_resolve_league_detail_by_id", return_value=None),
            self.assertRaisesRegex(
                ValueError,
                "provide explicit season, league_type, if_have_sub",
            ),
        ):
            zq_update.parse_natural_update_request(
                "",
                league_id=2343,
                action="data",
            )

    def test_structured_entrypoint_accepts_complete_explicit_metadata(self) -> None:
        with patch.object(zq_update, "_resolve_league_by_id", return_value=None):
            plan = update_request.parse_structured_update_request(
                sport="football",
                league_id=2343,
                season="2026",
                league_type=1,
                if_have_sub=0,
                action="schedule",
            )

        self.assertEqual(plan["input_mode"], "structured")
        self.assertEqual(
            plan["metadata_binding_status"],
            "explicit_parameters_without_catalog_match",
        )
        self.assertFalse(plan.get("executed", False))


if __name__ == "__main__":
    unittest.main()
