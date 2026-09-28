import unittest
from types import SimpleNamespace
from unittest.mock import patch

from crawler.qt.lq_league_crawler import LeagueCrawler
from utils.webUtil import WebUtil


class BasketballLeagueRequestTest(unittest.TestCase):
    def test_metadata_requests_are_direct_and_use_a_fixed_browser_agent(self):
        context = SimpleNamespace(arr=[[1, "Country", "", 1, ["2,NBA,1,2026"]]])
        with patch.object(
            WebUtil,
            "requests_get",
            side_effect=[(4, ""), (1, "var arr=[];")],
        ) as request, patch(
            "crawler.qt.lq_league_crawler.js2pyUtil.js2c",
            return_value=(1, context),
        ):
            leagues = LeagueCrawler().get_league_metadata_web()

        self.assertEqual(leagues[0]["league_id"], 2)
        self.assertEqual(len(request.call_args_list), 2)
        for call in request.call_args_list:
            self.assertTrue(call.args[0].startswith("https://nba.titan007.com/jsData/"))
            self.assertIs(call.kwargs["trust_env"], False)
            self.assertIn("Mozilla/5.0", call.kwargs["headers"]["User-Agent"])

    def test_required_league_list_failure_is_not_silent(self):
        with patch.object(WebUtil, "requests_get", side_effect=[(4, ""), (4, "")]):
            with self.assertRaisesRegex(RuntimeError, "league list request failed"):
                LeagueCrawler().get_league_metadata_web()

    def test_web_util_preserves_explicit_user_agent(self):
        response = SimpleNamespace(status_code=200, text="var arr=[];")
        with patch("utils.webUtil.requests.Session") as session_class:
            session = session_class.return_value
            session.get.return_value = response
            result = WebUtil.requests_get(
                "https://nba.titan007.com/jsData/infoHeader_cn.js",
                headers={"User-Agent": "fixed-agent"},
                trust_env=False,
                retry_time=1,
                sleep=False,
            )

        self.assertEqual(result, [1, "var arr=[];"])
        self.assertIs(session.trust_env, False)
        self.assertEqual(session.get.call_args.kwargs["headers"]["User-Agent"], "fixed-agent")


if __name__ == "__main__":
    unittest.main()
