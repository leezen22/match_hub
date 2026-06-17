import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from config import scrawler_config
from dao.zq_match_dao import ZqMatchDao
from utils.webUtil import WebUtil


class TotalOddsCrawler(object):
    def __init__(self, matchId, scheduleId=None, matchState=None, finished=None, is_half=False):
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.matchState = matchState
        self.finished = finished
        self.is_half = is_half

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_host(self):
        return scrawler_config.qt_zq_web_host

    @property
    def qt_web_referer(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_zq_web_europeOdds_url, self.scheduleId)

    @property
    def qt_mobile_url(self):
        return "{0}&scheid={1}&isHalf={2}".format(
            scrawler_config.qt_zq_mobile_totalOdds_url,
            self.scheduleId,
            1 if self.is_half else 0,
        )

    @property
    def qt_web_url(self):
        return "{0}?id={1}".format(scrawler_config.qt_zq_web_totalOdds_url, self.scheduleId)

    def qt_web_get(self):
        headers = {"Host": self.qt_web_host}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'finished': self.finished,
                    "odds": []}
        if self.matchState is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchState'],
                                             {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            oddsData['matchState'] = matchState
        else:
            oddsData['matchState'] = self.matchState
        headers['Referer'] = self.qt_web_referer
        response = WebUtil.requests_get(self.qt_web_url, headers)
        if response[0] == 1 and response[1] != '':
            soup = BeautifulSoup(response[1], 'html.parser')
            table_odds = soup.select('body div#webmain table#odds')[0]
            # table_odds = soup.find(id='odds')
            odds_collect = collect_web_odds(table_odds, self.matchId, self.scheduleId)
            if odds_collect['state'] == 0:
                oddsData['state'] = 2
            else:
                oddsData['state'] = 1
                oddsData['odds'] = odds_collect['odds']
        return oddsData

    # 只包含赛前初盘+即时盘，无滚球盘口
    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'finished': self.finished,
                    'isHalf': self.is_half, "odds": []}
        if self.matchState is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchState'],
                                             {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            oddsData['matchState'] = matchState
        else:
            oddsData['matchState'] = self.matchState
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_mobile_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            try:
                jsonData = json.loads(webResponse[1])
            except Exception as e:
                print("zq total odds json parse failed: scheduleId={0}, error={1}".format(self.scheduleId, e))
            else:
                companyList = jsonData.get('companies', [])
                if not companyList:
                    print("zq total odds companies missing: scheduleId={0}".format(self.scheduleId))
                for company in companyList:
                    try:
                        companyId = company['companyId']
                        companyName = company['nameCn']
                        oddsDataList = company['details']
                    except Exception as e:
                        print("zq total odds company base field missing: scheduleId={0}, error={1}".format(
                            self.scheduleId, e))
                        continue
                    if len(oddsDataList) > 0 and oddsDataList[0]['num'] == 1:
                        company_data = oddsDataList[0]
                        homeOdds_F = company_data.get("firstHomeOdds")
                        goal_F = company_data.get("firstDrawOdds", 0)
                        guestOdds_F = company_data.get("firstAwayOdds")
                        homeOdds = company_data.get("homeOdds")
                        goal = company_data.get("drawOdds", 0)
                        guestOdds = company_data.get("awayOdds")
                        modify_ts = company_data.get("modifyTime")
                        if any(v is None for v in [homeOdds_F, guestOdds_F, homeOdds, guestOdds, modify_ts]):
                            print("zq total odds company missing odds: scheduleId={0}, companyId={1}".format(
                                self.scheduleId, companyId))
                            continue
                        timeStamp = int(modify_ts)
                        dateArray = datetime.fromtimestamp(timeStamp)
                        modifyTime = dateArray.strftime("%Y-%m-%d %H:%M:%S")
                        company_odds = [
                            self.matchId, self.scheduleId, companyId, companyName,
                            homeOdds_F, goal_F, guestOdds_F,
                            homeOdds, goal, guestOdds,
                            modifyTime,
                        ]
                        if self.is_half:
                            keys = [
                                'matchId', 'scheduleId', 'companyId', 'companyName',
                                'halfHighOdds_F', 'halfGoal_F', 'halfLowOdds_F',
                                'halfHighOdds', 'halfGoal', 'halfLowOdds', 'halfModifyTime',
                            ]
                        else:
                            keys = [
                                'matchId', 'scheduleId', 'companyId', 'companyName',
                                'highOdds_F', 'goal_F', 'lowOdds_F',
                                'highOdds', 'goal', 'lowOdds', 'modifyTime',
                            ]
                        oddsDict = {}
                        for j in range(0, len(company_odds)):
                            if company_odds[j] != '' and company_odds[j] is not None:
                                oddsDict[keys[j]] = company_odds[j]
                        oddsData['odds'].append(oddsDict)

                if oddsData['odds']:
                    oddsData['state'] = 1
        # 返回亚指开盘公司初盘和终盘盘口
        return oddsData

    # @property
    # def qt_web_keys(self):
    #     keys = [
    #         'matchId', 'scheduleId', 'companyId', 'companyName',
    #         'highOdds_F', 'goal_F', 'lowOdds_F',
    #         'highOdds', 'goal', 'lowOdds',
    #         'highOdds_R', 'goal_R', 'lowOdds_R']
    #     return keys
    #
    # @property
    # def qt_mobile_keys(self):
    #     keys = [
    #         'matchId', 'scheduleId', 'companyId', 'companyName',
    #         'highOdds_F', 'goal_F', 'lowOdds_F',
    #         'highOdds', 'goal', 'lowOdds','modifyTime'
    #     ]
    #     return keys


def collect_web_odds(soup, matchId, scheduleId):
    oddsResult = {'state': 0, "odds": []}
    companyDict = {'1': '澳门', '3': 'Crown', '8': 'Bet365', '12': '易胜博', '14': '韦德',
                   '17': '明陞', '22': '10BET', '23': '金宝博', '24': '12bet', '31': '利记',
                   '35': '盈禾', '42': '18Bet', '47': '平博', '48': '香港马会', '4': '立博'}
    try:
        # odds_trs = soup.select('table#odds tr')
        odds_trs = soup.select('tr')
        count_tr = len(odds_trs)
        if count_tr < 3:
            pass
        elif count_tr == 3 and len(odds_trs[2].select('td')) < 3:
            oddsResult['state'] = 1
        else:
            for i in range(2, count_tr - 2):
                tds = odds_trs[i].find_all('td')
                if odds_trs[i].has_attr('companyid'):
                    companyId = odds_trs[i].get('companyid')
                else:
                    companyId = tds[1].find('span').get('companyid')
                companyName = companyDict[str(companyId)]

                if len(tds) == 1:
                    num = 0
                elif tds[1].get_text().strip() == '':
                    num = 1
                else:
                    num = int(tds[1].get_text().strip().split('盘口')[-1])

                if num == 1:
                    if tds[2].get_text().strip() != '':
                        homeOdds_F = tds[2].get_text()
                    else:
                        homeOdds_F = None
                    if tds[3].get('goals') is not None and tds[3].get('goals').strip() != '':
                        goal_F = tds[3].get('goals')
                    else:
                        goal_F = None
                    if tds[4].get_text().strip() != '':
                        guestOdds_F = tds[4].get_text()
                    else:
                        guestOdds_F = None

                    if tds[5].get_text().strip() != '':
                        homeOdds_R = tds[5].get_text()
                    else:
                        homeOdds_R = None
                    if tds[6].get('goals') is not None and tds[6].get('goals').strip() != '':
                        goal_R = tds[6].get('goals')
                    else:
                        goal_R = None
                    if tds[7].get_text().strip() != '':
                        guestOdds_R = tds[7].get_text()
                    else:
                        guestOdds_R = None

                    if tds[8].get_text().strip() != '':
                        homeOdds = tds[8].get_text()
                    else:
                        homeOdds = None
                    if tds[9].get('goals') is not None and tds[9].get('goals').strip() != '':
                        goal = tds[9].get('goals')
                    else:
                        goal = None
                    if tds[10].get_text().strip() != '':
                        guestOdds = tds[10].get_text()
                    else:
                        guestOdds = None
                    company_odds = [matchId, scheduleId, companyId, companyName,
                                    homeOdds_F, goal_F, guestOdds_F,
                                    homeOdds, goal, guestOdds,
                                    homeOdds_R, goal_R, guestOdds_R
                                    ]
                    keys = [
                        'matchId', 'scheduleId', 'companyId', 'companyName',
                        'highOdds_F', 'goal_F', 'lowOdds_F',
                        'highOdds', 'goal', 'lowOdds',
                        'highOdds_R', 'goal_R', 'lowOdds_R']
                    oddsDict = {}
                    for j in range(0, len(company_odds)):
                        if company_odds[j] != '' and company_odds[j] is not None:
                            oddsDict[keys[j]] = company_odds[j]
                    oddsResult['odds'].append(oddsDict)
            oddsResult['state'] = 1
    except Exception as e:
        print(e)
        # common_util.logline(common_config.soup_e, ['zq.getAsianOdds', url, e])
        oddsResult['state'] = 0

    return oddsResult


# if __name__ == '__main__':
#     totalCrawler = TotalOddsCrawler(199152, 1736607, -1)
#     data = totalCrawler.qt_web_get()
#     print(data)
    # t = time.time()
    # print(int(t)*1000)
