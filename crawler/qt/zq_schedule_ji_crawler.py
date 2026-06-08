import time
from datetime import datetime, timedelta
from config import scrawler_config
from utils import js2pyUtil
from utils.webUtil import WebUtil
import xml.etree.ElementTree as ET

Domain = "$"
DataType = "!"
SplitRecord = "^"
SplitColumn = ","
arrColor = ["#006666", "#518ed2", "#e8811a", "#949720", "#8f6dd6", "#53ac98", "#ff9966", "#a2e76f", "#8d8abd",
            "#996733", "#8c8a64", "#999012", "#ff6633", "#ca00ca", "#1ba570", "#990099"]

GoalCn2 = ["0", "0/0.5", "0.5", "0.5/1", "1", "1/1.5", "1.5", "1.5/2", "2", "2/2.5", "2.5", "2.5/3", "3", "3/3.5",
           "3.5", "3.5/4", "4", "4/4.5", "4.5", "4.5/5", "5", "5/5.5", "5.5", "5.5/6", "6", "6/6.5", "6.5", "6.5/7",
           "7", "7/7.5", "7.5", "7.5/8", "8", "8/8.5", "8.5", "8.5/9", "9", "9/9.5", "9.5", "9.5/10", "10", "10/10.5",
           "10.5", "10.5/11", "11", "11/11.5", "11.5", "11.5/12", "12", "12/12.5", "12.5", "12.5/13", "13", "13/13.5",
           "13.5", "13.5/14", "14"]


class ScheduleCrawler(object):
    def __init__(self, matchDate=None):
        self.matchDate = matchDate

    @property
    def qt_mobile_ji_header(self):
        header = {
            'Host': scrawler_config.qt_mobile_host,
            "Referer": scrawler_config.qt_zq_mobile_ji
        }
        return header

    @property
    def qt_web_ji_header(self):
        header = {
            'Host': scrawler_config.qt_zq_live_host,
            "Referer": scrawler_config.qt_zq_web_ji
        }
        return header

    @property
    def qt_web_ji_odds_header(self):
        header = {
            'Host': scrawler_config.qt_zq_live_host,
            "Referer": scrawler_config.qt_zq_web_ji
        }
        return header

    @property
    def qt_mobile_bf_url(self):
        return scrawler_config.qt_zq_mobile_ji_bf

    @property
    def qt_mobile_odds_url(self):
        return scrawler_config.qt_zq_mobile_ji_0dds

    @property
    def qt_web_bf_url(self):
        t = time.time()
        timestamp = int(t) * 1000
        return "{0}?r=007{1}".format(scrawler_config.qt_zq_web_ji_bf, timestamp)

    def qt_mobile_get_ji(self):
        result = {'state': 0, 'bf': [], 'league': {}}
        webResponse = WebUtil.requests_get(self.qt_mobile_bf_url,
                                           headers=self.qt_mobile_ji_header, encoding="utf-8")
        if webResponse[0] == 1:
            arrData = webResponse[1].split("$$")
            # 联赛信息
            leaguesDict = {}
            leagueArr = arrData[0].split("!")
            for item in leagueArr:
                league = QtMobLeague(item, 0)
                leaguesDict[league['leagueId']] = league
            result['league'] = leaguesDict
            leagueIds = leaguesDict.keys()
            # 赔率信息
            oddsData = qt_get_odds(self.qt_mobile_odds_url, self.qt_mobile_ji_header, 3)
            odds_state = oddsData['state']
            odds_scheIds = oddsData['odds'].keys()
            # 信息融合
            scoreArr = arrData[1].split("!")
            print(scoreArr[0])
            for item in scoreArr:
                score = QtMobileJiScore(item)
                leagueId = score['leagueId']
                scheduleId = score['scheduleId']
                if leagueId in leagueIds:
                    score['leagueColor'] = leaguesDict[leagueId]['leagueColor']
                    score['leagueName'] = leaguesDict[leagueId]['leagueName']
                    score['countryName'] = leaguesDict[leagueId]['countryName']
                    score['isShow'] = leaguesDict[leagueId]['isShow']
                    score['countrySort'] = leaguesDict[leagueId]['countrySort']
                if odds_state == 1 and scheduleId in odds_scheIds:
                    score['odds'] = oddsData['odds'][scheduleId]
                result['bf'].append(score)
            result['state'] = 1
        return result

    def qt_web_get_ji(self, companyId=3):
        result = {'state': 0, 'bf': [], 'league': {}}
        webResponse = WebUtil.requests_get(self.qt_web_bf_url,
                                           headers=self.qt_web_ji_header, encoding="utf-8")
        if webResponse[0] == 1:
            # 赔率信息
            oddsData = self.qt_web_get_odds(companyId)
            # qt_web_getOdds(companyId)
            odds_state = oddsData['state']
            odds_scheIds = oddsData['odds'].keys()
            # fixed = "var ShowBf= function (){};" + webResponse[1]
            fixed = webResponse[1].replace("ShowBf();", "")
            parse_result = js2pyUtil.js2c(fixed, source=self.qt_web_bf_url, required_names=("A",))
            if parse_result[0] != 1:
                return result
            context = parse_result[1]
            A = context.A
            for i in range(1, len(A)):
                score = QtWebJiScore(A[i])
                scheduleId = score['scheduleId']
                if odds_state == 1 and scheduleId in odds_scheIds:
                    score['odds'] = oddsData['odds'][scheduleId]
                result['bf'].append(score)
            result['state'] = 1
        return result

    def qt_web_get_score(self):
        result = {'state': 0, 'bf': [], 'league': {}}
        webResponse = WebUtil.requests_get(self.qt_web_bf_url,
                                           headers=self.qt_web_ji_header, encoding="utf-8")
        if webResponse[0] == 1:
            # fixed = "var ShowBf= function (){};" + webResponse[1]
            fixed = webResponse[1].replace("ShowBf();", "")
            parse_result = js2pyUtil.js2c(fixed, source=self.qt_web_bf_url, required_names=("A",))
            if parse_result[0] != 1:
                return result
            context = parse_result[1]
            A = context.A
            for i in range(1, len(A)):
                score = QtWebJiScore(A[i])
                result['bf'].append(score)
            result['state'] = 1
        return result

    def qt_mobile_get_score(self):
        result = {'state': 0, 'bf': [], 'league': {}}
        webResponse = WebUtil.requests_get(self.qt_mobile_bf_url,
                                           headers=self.qt_mobile_ji_header, encoding="utf-8")
        if webResponse[0] == 1:
            arrData = webResponse[1].split("$$")
            # leagueData = arrData[0]
            leaguesDict = {}
            leagueArr = arrData[0].split("!")
            for item in leagueArr:
                league = QtMobLeague(item, 0)
                leaguesDict[league['leagueId']] = league
            result['league'] = leaguesDict
            # scoreData = arrData[1]
            scoreArr = arrData[1].split("!")
            for item in scoreArr:
                score = QtMobileJiScore(item)
                leagueId = score['leagueId']
                score['leagueColor'] = leaguesDict[leagueId]['leagueColor']
                score['leagueName'] = leaguesDict[leagueId]['leagueName']
                score['countryName'] = leaguesDict[leagueId]['countryName']
                score['isShow'] = leaguesDict[leagueId]['isShow']
                score['countrySort'] = leaguesDict[leagueId]['countrySort']
                result['bf'].append(score)
            result['state'] = 1
        return result

    def qt_mobile_get_odds(self):
        result = qt_get_odds(self.qt_mobile_odds_url, self.qt_mobile_ji_header, 3)
        return result

    @staticmethod
    def qt_web_get_odds(companyId=3):
        result = qt_web_getOdds(companyId)
        return result


def qt_web_getOdds(companyId=3):
    t = time.time()
    timestamp = int(t) * 1000
    url = "{0}/goal{1}.xml?r=007{2}".format(scrawler_config.qt_zq_web_ji_0dds, companyId, timestamp)
    header = {
        'Host': scrawler_config.qt_zq_live_host,
        "Referer": "{0}/index2in1.aspx?Id={1}".format(scrawler_config.qt_zq_web_ji, companyId)
    }
    result = qt_get_odds(url, header, companyId)
    return result


def qt_get_odds(url, header, companyId):
    result = {'state': 0, 'odds': {}}
    webResponse = WebUtil.requests_get(url, headers=header, encoding="utf-8")
    if webResponse[0] == 1:
        root = ET.fromstring(webResponse[1])
        for element in root.find('match'):
            item_str = element.text
            odds = QtOdds(item_str, companyId)
            result['odds'][odds['scheduleId']] = odds
        result['state'] = 1
    return result


def QtWebJiScore(arrTr):
    score = {}
    odds = None
    scheduleId = arrTr[0]
    leagueColor = arrTr[1]
    leagueId = arrTr[45]
    leagueName = arrTr[2]
    matchTime = AmountTimeDiff(arrTr[11], arrTr[36], arrTr[43], 2)
    matchState = arrTr[13]
    # 比赛开始时间 时:分
    matchTime1 = arrTr[11]
    # 比赛开始时间 或 下半场开始时间
    matchTime2 = arrTr[12]
    happenTime = strState(matchState, matchTime2)
    homeTeam = arrTr[5]
    awayTeam = arrTr[8]
    homeTeamId = arrTr[37]
    awayTeamId = arrTr[38]
    homeScore = arrTr[14]
    awayScore = arrTr[15]
    homeHalf = arrTr[16]
    awayHalf = arrTr[17]
    homeRed = arrTr[18]
    awayRed = arrTr[19]
    homeYellow = arrTr[20]
    awayYellow = arrTr[21]
    homeOrder = arrTr[22]
    awayOrder = arrTr[23]
    homeCorner = arrTr[48]
    awayCorner = arrTr[49]
    values = [scheduleId, leagueId, leagueName, matchTime, matchState, happenTime,
              homeTeam, awayTeam, homeTeamId, awayTeamId,
              homeScore, awayScore, homeHalf, awayHalf,
              homeRed, awayRed, homeYellow, awayYellow, homeCorner, awayCorner,
              odds,
              homeOrder, awayOrder, leagueColor]
    keys = ['scheduleId', 'leagueId', 'leagueName', 'matchTime', 'matchState', 'happenTime',
            'homeTeam', 'awayTeam', 'homeTeamId', 'awayTeamId',
            'homeScore', 'awayScore', 'homeHalf', 'awayHalf',
            'homeRed', 'awayRed', 'homeYellow', 'awayYellow', 'homeCorner', 'awayCorner',
            'odds',
            'homeOrder', 'awayOrder', 'leagueColor']

    for i in range(len(keys)):
        score[keys[i]] = values[i]
    return score


def QtMobileJiScore(scoreData):
    score = {}
    arrTr = scoreData.split("^")
    scheduleId = arrTr[0]
    leagueId = arrTr[1]
    matchState = int(arrTr[2])
    # matchTime = arrTr[3]
    # matchTimeStr = arrTr[3][8:10] + ":" + arrTr[3][10:12]
    matchTime = datetime.strptime(arrTr[3], "%Y%m%d%H%M%S")
    happenTime = ''
    matchTimeStr = datetime.strftime(matchTime, '%Y-%m-%d %H:%M')
    matchTime2 = arrTr[4]
    homeTeam = arrTr[5]
    awayTeam = arrTr[6]
    homeScore = arrTr[7]
    awayScore = arrTr[8]
    homeHalf = arrTr[9]
    awayHalf = arrTr[10]
    homeRed = arrTr[11]
    awayRed = arrTr[12]
    homeYellow = arrTr[13]
    awayYellow = arrTr[14]
    caiPiaoHao = arrTr[16]
    isZhenRong = (arrTr[18] == "1")
    homeOrder = arrTr[19]
    if homeOrder != "":
        homeOrder = "[" + homeOrder + "]"
    awayOrder = arrTr[20]
    if awayOrder != "":
        awayOrder = "[" + awayOrder + "]"
    liveTv = arrTr[23]
    leagueName = ""
    leagueColor = ""
    cupExplain = explainList(arrTr[21], homeTeam, awayTeam)
    cupExplainText = arrTr[21]
    if arrTr[21] != "" and arrTr[28] != "":
        cupExplain += "<br/>" + arrTr[28]
    elif arrTr[21] == "" and arrTr[28] != "":
        cupExplain = arrTr[28]
    hasCorner = arrTr[27]
    homeCorner = arrTr[25]
    awayCorner = arrTr[26]

    isShow = True
    odds = None
    isTop = False
    adImages = ""
    adIndex = -1
    countryId = arrTr[33]
    countryName = ""
    countrySort = 0
    firstAsianOdds = arrTr[15]
    firstOverUnder = arrTr[31]
    # 是否有动画直播
    isActShow = arrTr[34]
    keys = ['scheduleId', 'leagueId', 'leagueName', 'matchTime', 'matchState', 'happenTime',
            'homeTeam', 'awayTeam',
            'homeScore', 'awayScore', 'homeHalf', 'awayHalf',
            'homeRed', 'awayRed', 'homeYellow', 'awayYellow', 'homeCorner', 'awayCorner',
            'odds',
            'homeOrder', 'awayOrder', 'leagueColor', 'cupExplain', 'caiPiaoHao',
            'hasCorner', 'isZhenRong', 'isShow', 'isTop', 'liveTv',
            'countryId', 'countryName', 'countrySort',
            'firstAsianOdds', 'firstOverUnder', 'isActShow']
    values = [scheduleId, leagueId, leagueName, matchTimeStr, matchState, happenTime,
              homeTeam, awayTeam,
              homeScore, awayScore, homeHalf, awayHalf,
              homeRed, awayRed, homeYellow, awayYellow, homeCorner, awayCorner,
              odds,
              homeOrder, awayOrder, leagueColor, cupExplain, caiPiaoHao,
              hasCorner, isZhenRong, isShow, isTop, liveTv,
              countryId, countryName, countrySort,
              firstAsianOdds, firstOverUnder, isActShow]
    for i in range(len(keys)):
        score[keys[i]] = values[i]
    return score


def QtMobLeague(leagueData, kind):
    league = {}
    arrTr = leagueData.split("^")
    leagueId = arrTr[1]
    leagueName = arrTr[0]
    isLevel1 = arrTr[2]
    leagueColor = arrColor[int(leagueId) % 16]
    isShow = True
    if kind == 0:
        isShow = arrTr[2]
    isTmpShow = True
    if kind == 0:
        isTmpShow = arrTr[2]
    countryId = arrTr[4]
    countryName = arrTr[5]
    countrySort = arrTr[6]
    values = [leagueId, leagueName, isLevel1, leagueColor, isShow, isTmpShow,
              countryId, countryName, countrySort]
    keys = ['leagueId', 'leagueName', 'isLevel1', 'leagueColor', 'isShow', 'isTmpShow',
            'countryId', 'countryName', 'countrySort']
    for i in range(len(keys)):
        league[keys[i]] = values[i]
    return league


#  13 ，1 有走地，2 正在走地. 1 不显示 0 显示
def QtOdds(oddsData, companyId):
    odds = {}
    arrTr = oddsData.split(",")
    scheduleId = arrTr[0]
    AsianOdds = arrTr[2]
    homeOdds = arrTr[3]
    awayOdds = arrTr[4]
    homeWin = arrTr[6]
    standOff = arrTr[7]
    awayWin = arrTr[8]
    totalGoal = arrTr[10]
    if arrTr[11] == '':
        highOdds = 0
    else:
        highOdds = arrTr[11]
    if arrTr[12] == '':
        lowOdds = 0
    else:
        lowOdds = arrTr[12]
    # 1 有走地，2 正在走地
    zoudi = arrTr[13]
    # 1 封盘 0不封盘
    asianClosed = arrTr[14]
    totalClosed = arrTr[15]
    eurClosed = arrTr[16]
    values = [scheduleId, companyId,
              AsianOdds, homeOdds, awayOdds,
              totalGoal, highOdds, lowOdds,
              homeWin, standOff, awayWin,
              zoudi, asianClosed, totalClosed, eurClosed
              ]
    keys = ['scheduleId', 'companyId',
            'AsianOdds', 'homeOdds', 'awayOdds',
            'totalGoal', 'highOdds', 'lowOdds',
            'homeWin', 'standOff', 'awayWin',
            'zoudi', 'asianClosed', 'totalClosed', 'eurClosed'
            ]
    for i in range(len(keys)):
        odds[keys[i]] = values[i]
    return odds


def strState(matchState, timeStr):
    stateStr = scrawler_config.zq_matchState[str(matchState)]
    timeArr = timeStr.split(",")
    timeStr2 = timeArr[0] + "," + str(int(timeArr[1]) + 1) + "," + timeArr[2] + "," + timeArr[3] + "," \
               + timeArr[4] + "," + timeArr[5]
    t2 = datetime.strptime(timeStr2, "%Y,%m,%d,%H,%M,%S")
    seconds = (datetime.now() - t2).seconds
    days = (datetime.now() - t2).days
    if days < 1:
        if matchState == "1":
            goTime = (datetime.now() - t2).seconds % 60
            if goTime > 45:
                goTime = "45+"
            elif goTime < 1:
                goTime = "1"
            stateStr = goTime
        elif matchState == "3":
            goTime = int(seconds / 60) + 46
            if goTime > 90:
                goTime = "90+"
            elif goTime < 46:
                goTime = "46"
            stateStr = goTime
    return stateStr


def AmountTimeDiff(dateStr, dateStr2, yearStr, rtvFormat):
    timeStr = yearStr + "-" + dateStr2 + " " + dateStr
    d1 = datetime.strptime(timeStr, "%Y-%m-%d %H:%M")
    if rtvFormat == 0:
        return datetime.strftime(d1, "%Y,%m,%d,%H,%M,%S")
    elif rtvFormat == 1:
        return datetime.strftime(d1, "%m月%d日%H:%M")
    elif rtvFormat == 2:
        return datetime.strftime(d1, "%Y-%m-%d %H:%M")


def explainList(exList, homeTeam, awayTeam):
    if exList == "" or exList is None:
        return ""
    exText = []
    gex4 = exList.split("")
    if gex4[0] != "":
        exText.appen(gex4[0].replace(",", "分钟[") + "]")
    if gex4[1] != "":
        exText.appen("二回合[" + gex4[1] + "]")
    if gex4[2] != "":
        exText.appen(gex4[2].replace("1,", "120分钟[").replace("2,", "加时[").replace("3,", "加时中[") + "]")
    if gex4[3] != "":
        exText.appen("点球[" + gex4[3] + "]")
    if gex4[4] == "1":
        exText.appen(homeTeam + "赢")
    elif gex4[4] == "2":
        exText.appen(awayTeam + "赢")
    return exText.join(",")


def Goal2GoalCn(goal):
    if goal == "":
        return ""
    else:
        goal = float(goal)
        if goal > 10 or goal < -10:
            return str(goal) + ""
        if goal >= 0:
            return GoalCn2[int(goal * 4)]
        else:
            return "-" + GoalCn2[abs(int(goal * 4))]


def CalcAsianOddsResult(homeScore, awayScore, goal):
    if goal == "":
        return ""
    diff = int(homeScore) - int(awayScore) - float(goal)
    if diff > 0:
        result = "赢"
    elif diff < 0:
        result = "输"
    else:
        result = "走"
    return result


if __name__ == '__main__':
    crawler = ScheduleCrawler()
    data = crawler.qt_mobile_get_ji()
    print(data)
    # jue = "386208^NBL1(中),NBL1(中)^4^#DFCF20^05月31日<br>17:45^-5^^6418^北阿德莱德火箭[5],北阿德萊德火箭[5],North AdelaIde Rockets[5]^6419^中央区狮子会[6],中央區獅子會[6],Central Districts Lions[6]^^^^^^^^^^^0^^^^^^^^^^^1^^,^20 赛季^常规赛^441^True^^^^2020^False^0"
    # # print(type(jue))
    # arr = jue.split("^")
    # match = matchModel(arr)
    # print(match)
