import datetime
import random
import time
import js2py
import requests
from bs4 import BeautifulSoup
from config import scrawler_config, common_config
from utils import sql_util_local

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
        odds_html = requests.get(first_odds_url, headers=bf_mobile_headers, timeout=5).text
        soup = BeautifulSoup(odds_html, 'html.parser')
        odds_script = soup.find('script')
        if odds_script:
            context = js2py.EvalJs()
            context.execute(odds_script.get_text())
            odds_data = context.oddsData
    except Exception as e:
        print(first_odds_url)
        print(e)
    return odds_data