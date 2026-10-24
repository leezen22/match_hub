import unittest
from unittest.mock import patch

import lq_update
from utils import sql_util


class BasketballEnrichmentPendingTest(unittest.TestCase):
    def test_all_leagues_recent_seasons_are_scoped_per_league(self):
        seasons = [
            (1, "26-27", None),
            (1, "25-26", None),
            (1, "24-25", None),
            (2, "26", None),
            (2, "25", None),
            (2, "24", None),
        ]
        with patch.object(sql_util, "select_rows", return_value=seasons):
            clause = lq_update._all_league_recent_season_where(2, sql_util)

        self.assertIn("leagueId=1 and matchSeason in ('26-27','25-26')", clause)
        self.assertIn("leagueId=2 and matchSeason in ('26','25')", clause)
        self.assertNotIn("24-25", clause)
        self.assertNotIn("'24'", clause)

    def test_all_leagues_pending_applies_season_count_without_network(self):
        selected_queries = []

        def select_rows(query):
            selected_queries.append(query)
            if "GROUP BY leagueId,matchSeason" in query:
                return [(1, "26-27", None), (1, "25-26", None), (1, "24-25", None)]
            return [(101,)]

        with patch.object(sql_util, "select_dicts", return_value=[
            {"Field": "technical_f"}, {"Field": "textlive_f"}
        ]), patch.object(sql_util, "sqlExecute"), patch.object(
            sql_util, "select_rows", side_effect=select_rows
        ), patch.object(lq_update, "update_match_enrichment") as update:
            selected = lq_update.update_enrichment_pending(all_leagues=True, season_count=2, limit=1)

        self.assertEqual(selected, [101])
        self.assertEqual(len(selected_queries), 2)
        self.assertIn("leagueId=1 and matchSeason in ('26-27','25-26')", selected_queries[1])
        self.assertNotIn("24-25", selected_queries[1])
        self.assertNotIn("matchTime >=", selected_queries[1])
        update.assert_called_once_with(101)

    def test_no_local_seasons_fails_closed(self):
        with patch.object(sql_util, "select_rows", return_value=[]):
            clause = lq_update._all_league_recent_season_where(2, sql_util)
        self.assertEqual(clause, "(1=0)")

    def test_pending_does_not_mark_empty_technical_complete_without_collection(self):
        with patch.object(sql_util, 'select_dicts', return_value=[
            {'Field': 'technical_f'}, {'Field': 'textlive_f'}
        ]), patch.object(sql_util, 'sqlExecute') as execute, patch.object(
            sql_util, 'select_rows', return_value=[(101,)]
        ), patch.object(lq_update, 'update_match_enrichment') as update:
            lq_update.update_enrichment_pending(all_leagues=True, limit=1)
        assert all('SET technical_f=' not in call.args[0] for call in execute.call_args_list)
        update.assert_called_once_with(101)

    def test_invalid_season_count_fails_before_query(self):
        with patch.object(sql_util, "select_rows") as select:
            with self.assertRaises(ValueError):
                lq_update._all_league_recent_season_where(0, sql_util)
        select.assert_not_called()


if __name__ == "__main__":
    unittest.main()
