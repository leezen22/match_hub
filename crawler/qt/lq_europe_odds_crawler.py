import re
from datetime import datetime
from bs4 import BeautifulSoup
from config import scrawler_config
from dao.lq_match_dao import LqMatchDao
from utils import js2pyUtil, sql_util
from utils.dateUtil import utc2local, getNowTime
from utils.webUtil import WebUtil


class EuropeOddsCrawler(object):
    def __init__(self, matchId, scheduleId=None, matchState=None, eurOdds_f=None, matchTime=None,
                 matchSeason=None, leagueId=None):
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.matchState = matchState
        self.eurOdds_f = eurOdds_f
        self.matchTime = matchTime
        self.matchSeason = matchSeason
        self.leagueId = leagueId

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_host(self):
        return scrawler_config.qt_lq_web_host

    @property
    def qt_mobile_url(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_lq_mobile_europeOdds_url, self.scheduleId)

    @property
    def qt_web_url(self):
        scheduleId = str(self.scheduleId)
        return "{0}/{1}/{2}/{3}.js".format(scrawler_config.qt_lq_web_europeOddsJs_url,
                                           scheduleId[0:1], scheduleId[1:3], scheduleId)

    @property
    def qt_web_referer(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_lq_web_europeOdds_url, self.scheduleId)

    @property
    def qt_web_pre_keys(self):
        keys = ['homeWin', 'awayWin', 'modifyTime',
                'kelly_Home', 'kelly_away',
                'oddsType', 'isBet',
                'oddsId_Q', 'matchId', 'scheduleId', 'companyId']
        return keys

    def qt_web_get(self, hasDetail=False):
        headers = {"Host": self.qt_web_host, "Referer": self.qt_web_referer}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'eurOdds_f': self.eurOdds_f, "odds": []}
        if self.matchState is None:
            result = LqMatchDao.select_dicts(['matchId', 'matchState'], {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            oddsData['matchState'] = matchState
        else:
            oddsData['matchState'] = self.matchState
        webResponse = WebUtil.requests_get(self.qt_web_url, headers=headers, retry_time=1, sleep=False)
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
                print("lq europe web odds parse failed: scheduleId={0}, error={1}".format(self.scheduleId, e))
                if oddsData['odds']:
                    oddsData['state'] = 1
        # 返回亚指开盘公司初盘和终盘盘口
        elif webResponse[0] == 4:
            oddsData['state'] = 4
        return oddsData

    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'eurOdds_f': self.eurOdds_f,
                    "odds": []}
        if self.matchState is None:
            result = LqMatchDao.select_dicts(['matchId', 'matchState'],
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
                        companyOdds = {'companyId': item['cId'], 'companyName': item['cId'],
                                       'homeWin_F': item['hw'], 'awayWin_F': item['gw'],
                                       'homeWin': item['rh'], 'awayWin': item['rg'],
                                       'matchId': self.matchId, 'scheduleId': self.scheduleId
                                       }
                        oddsData['odds'].append(companyOdds)
            except Exception as e:
                print("lq europe mobile odds parse failed: scheduleId={0}, error={1}".format(self.scheduleId, e))
                if oddsData['odds']:
                    oddsData['state'] = 1
                # 获取页面成功
            else:
                oddsData['state'] = 1
        elif webResponse[0] == 4:
            oddsData['state'] = 4
        return oddsData

    def qt_web_load_europeJS(self):
        state = 0
        if self.matchTime is None or self.matchSeason is None or self.leagueId is None:
            result = LqMatchDao.select_dicts(['matchId', 'matchState', 'matchTime', 'matchSeason', 'leagueId'],
                                             {'matchId': self.matchId}, isDis=True)
            matchTime = result[0]['matchTime']
            season = result[0]['matchSeason']
            leagueId = result[0]['leagueId']
        else:
            matchTime = self.matchTime
            season = self.matchSeason
            leagueId = self.leagueId

        matchYear = matchTime.year
        headers = {"Host": self.qt_web_host, "Referer": self.qt_web_referer}
        file_dir = "{0}\\{1}\\{2}\\".format(scrawler_config.lq_europJS_dir, leagueId, season)
        file_name = "{0}_{1}".format(self.matchId, self.scheduleId) + ".js"
        filePath = file_dir + file_name
        result = WebUtil.loadFileByName(self.qt_web_url, filePath, headers)
        if result == 1:
            state = 1
        return state


def get_byJS(jsContent, matchId, scheduleId=None, hasDetail=True):
    oddsData = {'state': 0, 'odds': {}, 'detail': {}}
    company_odds = []
    oddsDetails = {}
    try:
        fixed_content = " var ScheduleID; var game; var gameDetail;"
        jsContent = fixed_content + jsContent
        parse_result = js2pyUtil.js2c(
            jsContent,
            source="lq_europe_odds_js:{0}".format(scheduleId or matchId),
            required_names=("MatchTime", "game"),
        )
        if parse_result[0] != 1:
            return oddsData
        context = parse_result[1]
        utctime_str = context.MatchTime
        matchTime = getLocaltime(utctime_str)
        scheduleId = context.ScheduleID
        companyDict = {}
        if context.game:
            game = context.game
            for item in game:
                odds = item.split("|")
                companyId = odds[0]
                # 主流公司 + 交易所 + 10Bet,立博，金宝博
                if odds[17] == '1' or odds[18] == '1' or (companyId in ['369', '83', '367']):
                    # 无开盘公司英文名称字段
                    if len(odds) == 19:
                        odds.append(None)
                    odds[15] = getLocaltime(odds[15]).strftime("%Y-%m-%d %H:%M:%S")
                    odds[16] = odds[16].split("(")[0]
                    odds.append(scheduleId)
                    odds.append(matchId)
                    del odds[19]
                    del odds[18]
                    del odds[17]
                    del odds[2]
                    columns = ['companyId', 'oddsId_Q',
                               'homeWin_F', 'awayWin_F', 'probability_H0', 'probability_G0', 'back_F',
                               'homeWin', 'awayWin', 'probability_H1', 'probability_G1', 'back',
                               'kelly_Home', 'kelly_away', 'modifyTime', 'companyName',
                               'scheduleId', 'matchId']
                    oddsDict = {}
                    for i in range(0, len(odds)):
                        if odds[i] != '' and odds[i] is not None:
                            oddsDict[columns[i]] = odds[i]
                    companyDict[odds[1]] = companyId
                    company_odds.append(oddsDict)
            oddsData['odds'] = company_odds
            oddsData['state'] = 1
        else:
            oddsData['state'] = 0
        # 提取赛前变化记录
        if hasDetail and context.gameDetail:
            gameDetail = context.gameDetail
            for item in gameDetail:
                odds_data = item.split("^")
                oddsID = odds_data[0]
                oddID_details = []
                # 指定开盘公司范围
                if oddsID in companyDict.keys():
                    companyId = companyDict[oddsID]
                    # 数据异常则修复，无异常返回原数据
                    fixed_data = fixed_detail(odds_data[1])
                    details_data = fixed_data.split(";")
                    for cell in details_data:
                        detail = cell.split("|")
                        if len(cell) > 0:
                            modifyTime = detail[2]
                            modifyTime_fixed = getModifyTime(matchTime, modifyTime, '即')
                            detail[2] = modifyTime_fixed
                            if len(detail) == 3:
                                detail = detail + [None, None]
                            # detail.append(oddsID)
                            # 赔率类型，即时盘
                            # 'oddsType', 'isBet', 'oddsId_Q', 'matchId', 'scheduleId', 'companyId'
                            detail = detail + [1, 1, oddsID, matchId, scheduleId, companyId]
                            oddID_details.append(detail)
                    oddID_details.reverse()
                    oddsDetails[companyDict[oddsID]] = oddID_details
        if hasDetail:
            oddsData['pre'] = oddsDetails
    except Exception as e:
        print(e)
        if company_odds:
            oddsData['odds'] = company_odds
            oddsData['state'] = 1
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
        if len(detail) >= 3:
            modifyTime = detail[2]
            if len(modifyTime) > 11:
                handList.append(modifyTime)
    for item in handList:
        fixed = item[0:11] + ";" + item[11:]
        details_str = details_str.replace(item, fixed)
    return details_str


if __name__ == '__main__':
    crawler = EuropeOddsCrawler(208685, 386818, 0, 1)
    data2 = crawler.qt_web_get(hasDetail=True)
    print(data2)


    # companyList = [3, 6, 11, 17, 26, 43, 45, 77, 82, 83, 214, 265, 272, 317, 341, 367, 368, 369, 431, 446, 458, 478, 519]
    # for cid in companyList:
    #     sql = " update lq_europe_pre_{0} set kind=6 where kind is NULL".format(cid)
    #     sql_util.sqlExecute(sql)
