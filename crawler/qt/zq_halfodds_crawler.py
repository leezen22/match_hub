import datetime
import random
import time
from bs4 import BeautifulSoup
from config import scrawler_config, common_config
from utils import sql_util_local
from utils import js2pyUtil
from utils.webUtil import WebUtil

def get_halfodds_goals(scheduleID, companyID):
    odds_data = None
    first_odds_url = "{0}?scheid={1}&oddsType=2&isHalf=1&companyId={2}".format(scrawler_config.qt_zq_mobile_oddsDetail,
                                                                               scheduleID, companyID)
    print(first_odds_url)
    bf_mobile_headers = {"Host": scrawler_config.qt_mobile_host,
                         "User-Agent": random.choice(common_config.mobile_agents),
                         'Sec-Fetch-Mode': 'navigate',
                         'Referer': "{0}/{1}.htm".format(scrawler_config.qt_zq_mobile_live, scheduleID),
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                                   'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
                         }
    try:
        web_response = WebUtil.requests_get(
            first_odds_url,
            headers=bf_mobile_headers,
            timeout=5,
            sourceName="zq_halfodds_goals",
        )
        if web_response[0] != 1:
            return odds_data
        odds_html = web_response[1]
        soup = BeautifulSoup(odds_html, 'html.parser')
        odds_script = soup.find('script')
        if odds_script:
            parse_result = js2pyUtil.js2c(
                odds_script.get_text(),
                source=first_odds_url,
                required_names=("oddsData",),
            )
            if parse_result[0] != 1:
                return odds_data
            context = parse_result[1]
            odds_data = context.oddsData
    except Exception as e:
        print(first_odds_url)
        print(e)
    return odds_data
