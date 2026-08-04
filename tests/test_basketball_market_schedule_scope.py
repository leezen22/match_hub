from __future__ import annotations

import unittest
from unittest.mock import patch

import lq_update
from lq.service.lqodds import LqOddsService, _schedule_id_sql_filter


class BasketballMarketScheduleScopeTest(unittest.TestCase):
    def test_schedule_id_parser_requires_positive_integer_set(self) -> None:
        self.assertEqual(
            lq_update._parse_schedule_ids("705153,705152,705153"),
            [705152, 705153],
        )
        self.assertIsNone(lq_update._parse_schedule_ids(None))
        with self.assertRaisesRegex(ValueError, "positive integers"):
            lq_update._parse_schedule_ids("705152,bad")

    def test_odds_queries_are_limited_to_verified_schedule_ids(self) -> None:
        queries = []

        with patch(
            "lq.service.lqodds.sql_util.select",
            side_effect=lambda query: queries.append(query) or [],
        ):
            LqOddsService.upOdds(
                lookback_days=1,
                until_days=1,
                schedule_ids=[705153, 705152],
            )

        self.assertEqual(len(queries), 2)
        self.assertTrue(
            all("scheduleID in (705152,705153)" in query for query in queries)
        )

    def test_detail_query_is_limited_to_verified_schedule_ids(self) -> None:
        queries = []

        with patch(
            "lq.service.lqodds.LqAsianOddsDao.select",
            side_effect=lambda query: queries.append(query) or [],
        ):
            LqOddsService.up_2in1Details_byCid(
                8,
                3,
                lookback_days=1,
                until_days=1,
                schedule_ids=[705153, 705152],
            )

        self.assertEqual(len(queries), 1)
        self.assertIn("sche.scheduleID in (705152,705153)", queries[0])

    def test_explicit_empty_schedule_scope_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integers"):
            _schedule_id_sql_filter([], "scheduleID")


if __name__ == "__main__":
    unittest.main()
