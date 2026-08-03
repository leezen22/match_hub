from __future__ import annotations

import unittest
from unittest.mock import patch

import zq_update
from utils.webUtil import WebUtil


SEASONS = "var arrSeason = ['2026','2025'];"
LEAGUE_PAGE = """
<html>
  <head><title>2026赛季美预备联赛程资料统计</title></head>
  <body>
    <script>
      var selectSeason = '2026';
      var SclassID = 2343;
      var SubSclassID = 0;
    </script>
    <script src="/jsData/matchResult/2026/s2343.js?version=1"></script>
  </body>
</html>
"""


class FootballDetailMetadataFallbackTest(unittest.TestCase):
    def test_catalog_miss_resolves_identity_bound_detail_metadata(self) -> None:
        responses = [(1, SEASONS), (1, LEAGUE_PAGE)]

        with (
            patch.object(zq_update, "_resolve_league_by_id", return_value=None),
            patch.object(WebUtil, "requests_get", side_effect=responses),
        ):
            plan = zq_update.parse_natural_update_request(
                "",
                league_id=2343,
                action="schedule",
            )

        self.assertEqual(plan["league_name"], "美预备联")
        self.assertEqual(plan["season"], "2026")
        self.assertEqual(plan["league_type"], 1)
        self.assertEqual(plan["if_have_sub"], 0)
        self.assertEqual(plan["metadata_binding_status"], "detail_page_resolved")

    def test_detail_page_identity_conflict_fails_closed(self) -> None:
        conflicting_page = LEAGUE_PAGE.replace("SclassID = 2343", "SclassID = 999")

        with (
            patch.object(WebUtil, "requests_get", side_effect=[(1, SEASONS), (1, conflicting_page)]),
            self.assertRaisesRegex(ValueError, "identity conflict"),
        ):
            zq_update._resolve_league_detail_by_id(2343)

    def test_explicit_metadata_does_not_call_detail_fallback(self) -> None:
        with (
            patch.object(zq_update, "_resolve_league_by_id", return_value=None),
            patch.object(
                zq_update,
                "_resolve_league_detail_by_id",
                side_effect=AssertionError("explicit plan must not access detail source"),
            ),
        ):
            plan = zq_update.parse_natural_update_request(
                "",
                league_id=2343,
                season="2026",
                league_type=1,
                if_have_sub=0,
                action="schedule",
            )

        self.assertEqual(
            plan["metadata_binding_status"],
            "explicit_parameters_without_catalog_match",
        )


if __name__ == "__main__":
    unittest.main()
