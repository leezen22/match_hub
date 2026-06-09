import re
from datetime import datetime
from bs4 import BeautifulSoup
from config import scrawler_config
from dao.zq_match_dao import ZqMatchDao
from utils import js2pyUtil
from utils.dateUtil import utc2local
from utils.webUtil import WebUtil


class EuropeOddsCrawler(object):
    def __init__(self, matchId, scheduleId=None, matchState=None, finished=None, matchTime=None,
                 matchSeason=None, leagueId=None):
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.matchState = matchState
        self.finished = finished
        self.matchTime = matchTime
        self.matchSeason = matchSeason
        self.leagueId = leagueId

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_host(self):
        return scrawler_config.qt_zq_1X2_host

    @property
    def qt_mobile_url(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_zq_mobile_europeOdds_url, self.scheduleId)

    @property
    def qt_web_url(self):
        return "{0}/{1}.js".format(scrawler_config.qt_zq_web_europeOddsJs_url, self.scheduleId)

    @property
    def qt_web_referer(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_zq_web_europeOdds_url, self.scheduleId)

    @property
    def qt_web_pre_keys(self):
        keys = ['homeWin', 'standoff', 'awayWin', 'modifyTime',
                'kelly_Home', 'kelly_Off', 'kelly_away',
                'oddsId_Q', 'matchId', 'scheduleId', 'companyId']
        return keys

    def qt_web_get(self, hasDetail=False):
        headers = {"Host": self.qt_web_host, "Referer": self.qt_web_referer}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'finished': self.finished, "odds": []}
        if self.matchState is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchState'], {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            oddsData['matchState'] = matchState
        else:
            oddsData['matchState'] = self.matchState
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_web_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            try:
                data = get_byJS(content, self.matchId, self.scheduleId, hasDetail)
                oddsData['state'] = data['state']
                oddsData['odds'] = data['odds']
                if hasDetail:
                    oddsData['keys_pre'] = self.qt_web_pre_keys
                    oddsData['pre'] = data['pre']
            except Exception as e:
                print(content)
                print(e)
        # 返回亚指开盘公司初盘和终盘盘口
        return oddsData

    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host}
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
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_mobile_url, headers=headers)
        if webResponse[0] == 1 and webResponse[1] != '':
            # 获取页面成功
            try:
                soup = BeautifulSoup(webResponse[1], "html.parser")
                pattern = re.compile(r"var hData", re.MULTILINE | re.DOTALL)
                script_tag = soup.find("script", text=pattern)
                if script_tag is None:
                    return oddsData
                script = str(script_tag).replace('<script type="text/javascript">', '').replace('</script>', '').strip()
                parse_result = js2pyUtil.js2c(
                    script,
                    source=self.qt_mobile_url,
                    required_names=("hData",),
                )
                if parse_result[0] != 1:
                    return oddsData
                context = parse_result[1]
                hData = context.hData
                for item in hData:
                    if item['ct'] == 1:
                        companyOdds = {'companyId': item['cId'], 'companyName': item['cn'],
                                       'homeWin_F': item['hw'], 'standOff_F': item['so'], 'awayWin_F': item['gw'],
                                       'homeWin': item['rh'], 'standOff': item['rs'], 'awayWin': item['rg'],
                                       'matchId': self.matchId, 'scheduleId': self.scheduleId
                                       }
                        oddsData['odds'].append(companyOdds)
            except Exception as e:
                print(e)
                # 获取页面成功
            else:
                oddsData['state'] = 1
        # 返回亚指开盘公司初盘和终盘盘口
        return oddsData

    def qt_web_load_europeJS(self):
        state = 0
        if self.matchTime is None or self.matchSeason is None or self.leagueId is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchState', 'matchTime', 'matchSeason', 'leagueId'],
                                             {'matchId': self.matchId}, isDis=True)
            season = result[0]['matchSeason']
            leagueId = result[0]['leagueId']
        else:
            season = self.matchSeason
            leagueId = self.leagueId

        headers = {"Host": self.qt_web_host, "Referer": self.qt_web_referer}
        file_dir = "{0}\\{1}\\{2}\\".format(scrawler_config.zq_europJS_dir, leagueId, season)
        file_name = "{0}_{1}".format(self.matchId, self.scheduleId) + ".js"
        filePath = file_dir + file_name
        result = WebUtil.loadFileByName(self.qt_web_url, filePath, headers)
        if result == 1:
            state = 1
        return state


def get_byJS(jsContent, matchId, scheduleId=None, hasDetail=True):
    oddsData = {'state': 0, 'odds': [], 'detail': {}}
    company_odds = []
    oddsDetails = {}
    try:
        fixed_content = " var ScheduleId; var game; var gameDetail;"
        jsContent = fixed_content + jsContent
        parse_result = js2pyUtil.js2c(
            jsContent,
            source="zq_europe_odds_js:{0}".format(scheduleId or matchId),
            required_names=("MatchTime", "game"),
        )
        if parse_result[0] != 1:
            return oddsData
        context = parse_result[1]
        utctime_str = context.MatchTime
        matchTime = getLocaltime(utctime_str)
        currentScheduleId = context.ScheduleID
        oddsIdDict = {}
        if context.game and scheduleId == currentScheduleId:
            game = context.game
            for data in game:
                oddsDict = {}
                odds = data.split("|")
                if odds[23] == '1' or odds[22] == '1':
                    companyId = odds[0]
                    oddsId_Q = odds[1]
                    odds[20] = getLocaltime(odds[20]).strftime("%Y-%m-%d %H:%M:%S")
                    odds[21] = odds[21].split("(")[0]
                    del odds[22:]
                    del odds[2]
                    odds = odds + [matchId, scheduleId]
                    columns = ['companyId', 'oddsId_Q',
                               'homeWin_F', 'standoff_F', 'awayWin_F', 'probability_H0', 'probability_T0',
                               'probability_G0', 'back_F',
                               'homeWin', 'standoff', 'awayWin', 'probability_H1', 'probability_T1', 'probability_G1',
                               'back', 'kelly_Home', 'kelly_Off', 'kelly_away', 'modifyTime',
                               'companyName', 'matchId', 'scheduleId']
                    for i in range(0, len(odds)):
                        if odds[i] != '' and odds[i] is not None and columns[i] in ['companyId', 'oddsId_Q', 'homeWin_F', 'standoff_F', 'awayWin_F', 'homeWin', 'standoff', 'awayWin', 'modifyTime', 'companyName', 'matchId', 'scheduleId']:
                            oddsDict[columns[i]] = odds[i]
                    oddsIdDict[oddsId_Q] = companyId
                    company_odds.append(oddsDict)
            oddsData['odds'] = company_odds
            oddsData['state'] = 1
        if hasDetail and context.gameDetail and scheduleId == currentScheduleId:
            gameDetail = context.gameDetail
            for data in gameDetail:
                dList = data.split("^")
                oddsId_Q = dList[0]
                oddId_details = []
                if oddsId_Q in oddsIdDict.keys():
                    companyId = oddsIdDict[oddsId_Q]
                    # 数据异常则修复，无异常返回原数据
                    fixed_data = fixed_detail(dList[1])
                    details_data = fixed_data.split(";")
                    for item in details_data:
                        odds_detail = item.split("|")
                        if len(odds_detail) == 5 or len(odds_detail) == 8:
                            modifyTime = odds_detail[3]
                            modifyTime_fixed = getModifyTime(matchTime, modifyTime, '即')
                            odds_detail[3] = modifyTime_fixed
                            if len(odds_detail) == 4:
                                odds_detail = odds_detail + [None, None, None]
                            odds_detail = odds_detail + [oddsId_Q, matchId, scheduleId, companyId]
                            oddId_details.append(odds_detail)
                    oddId_details.reverse()
                    # detail[oddsId] = oddId_details
                    oddsDetails[companyId] = oddId_details
        if hasDetail:
            oddsData['pre'] = oddsDetails
    except Exception as e:
        print(e)
    return oddsData


def getModifyTime(matchTime, modifyTime, oddsType):
    match_y = matchTime.year
    match_m = matchTime.month
    modify_m = int(modifyTime[0:2])
    if oddsType == '即' and modify_m > match_m:
        modify_y = match_y - 1
    elif oddsType == '滚' and modify_m < match_m and modify_m == 1:
        modify_y = match_y + 1
    else:
        modify_y = match_y
    modifyTime = str(modify_y) + '-' + modifyTime
    return modifyTime


def getLocaltime(utctime_str):
    t2 = utctime_str.split(",")
    month = int(t2[1].split('-')[0])
    utc_tm = datetime(int(t2[0]), month, int(t2[2]), int(t2[3]), int(t2[4]), int(t2[5]))
    localtime = utc2local(utc_tm)
    return localtime


def fixed_detail(details_str):
    handList = []
    detail_list = details_str.split(";")
    for data in detail_list:
        detail = data.split("|")
        if len(detail) >= 4:
            modifyTime = detail[3]
            if len(modifyTime) > 11:
                handList.append(modifyTime)
    for item in handList:
        fixed = item[0:11] + ";" + item[11:]
        details_str = details_str.replace(item, fixed)
    return details_str


# if __name__ == '__main__':
#     crawler = EuropeOddsCrawler(2706130, 2706130, -1)
#     data2 = crawler.qt_web_get(hasDetail=True)
#     print(data2)
