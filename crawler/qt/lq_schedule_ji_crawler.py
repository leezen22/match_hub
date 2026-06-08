import time
from datetime import datetime
from config import scrawler_config
from utils.webUtil import WebUtil
import xml.etree.ElementTree as ET

Domain = "$"
DataType = "!"
SplitRecord = "^"
SplitColumn = ","


class ScheduleCrawler(object):
    def __init__(self):
        pass

    @property
    def qt_web_bf_header(self):
        header = {
            'Host': scrawler_config.qt_lq_live_host,
            'Referer': scrawler_config.qt_lq_web_ji_url
        }
        return header

    @property
    def qt_mobile_ji_header(self):
        header = {
            'Host': scrawler_config.qt_mobile_host,
            'Referer': scrawler_config.qt_lq_mobile_ji
        }
        return header

    @property
    def qt_mobile_bf_url(self):
        return scrawler_config.qt_lq_mobile_ji_score

    @property
    def qt_web_score_url(self):
        t = time.time()
        timestamp = int(t) * 1000
        return "{0}?&t={1}".format(scrawler_config.qt_lq_web_ji_score_url, timestamp)

    def qt_mobile_get_ji(self, companyId=8):
        result = {'state': 0, 'league': {}, 'bf': []}

        webResponse = WebUtil.requests_get(self.qt_mobile_bf_url,
                                           headers=self.qt_mobile_ji_header, encoding="utf-8")
        if webResponse[0] == 1:
            arrData = webResponse[1].split("$$")
            leagueData = arrData[0]
            scoreData = arrData[1]

            if datetime.now().hour >= 16:
                matchDate = datetime.now().strftime("%Y-%m-%d")
            else:
                matchDate = (datetime.now() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")

            oddsData = self.qt_mob_get_odds(matchDate, companyId)['odds']
            odds_scheIds = oddsData.keys()

            arrLeague = leagueData.split("!")
            leaguesDict = {}
            for i in range(len(arrLeague)):
                league = QtMobLeague(arrLeague[i])
                leaguesDict[league['leagueId']] = league
            result['league'] = leaguesDict
            leagueIds = leaguesDict.keys()

            if scoreData != '':
                arr = scoreData.split("!")
                for j in range(len(arr)):
                    score = QtMobScore(arr[j])
                    leagueId = score['leagueId']
                    scheduleId = score['scheduleId']
                    if leagueId in leagueIds:
                        score['leagueName'] = leaguesDict[leagueId]['leagueName']
                    if scheduleId in odds_scheIds:
                        score['odds'] = oddsData[scheduleId]
                    result['bf'].append(score)
            result['state'] = 1
        return result

    def qt_web_get_ji(self, companyId=8):
        result = {'state': 0, 'bf': []}
        webResponse = WebUtil.requests_get(self.qt_web_score_url, headers=self.qt_web_bf_header, encoding="gbk")
        if webResponse[0] == 1:
            # 赔率信息
            oddsData = self.qt_web_get_odds(companyId)
            odds_state = oddsData['state']
            odds_scheIds = oddsData['odds'].keys()
            root = ET.fromstring(webResponse[1])
            for element in root.find('m'):
                item_str = element.text
                score = QtWebScore(item_str)
                scheduleId = score['scheduleId']
                if odds_state == 1 and scheduleId in odds_scheIds:
                    score['odds'] = oddsData['odds'][scheduleId]
                result['bf'].append(score)
            result['state'] = 1
        return result

    def qt_web_get_score(self):
        result = {'state': 0, 'bf': []}
        webResponse = WebUtil.requests_get(self.qt_web_score_url, headers=self.qt_web_bf_header, encoding="gbk")
        if webResponse[0] == 1:
            root = ET.fromstring(webResponse[1])
            for element in root.find('m'):
                item_str = element.text
                score = QtWebScore(item_str)
                result['bf'].append(score)
            result['state'] = 1
        else:
            result['state'] = 0
        return result

    @staticmethod
    def qt_web_get_odds(companyId=8):
        t = time.time()
        timestamp = int(t) * 1000
        url = "{0}{1}.xml?{2}".format(scrawler_config.qt_lq_web_ji_odds_url, companyId, timestamp)
        header = {
            'Host': scrawler_config.qt_lq_live_host,
            "Referer": scrawler_config.qt_lq_web_ji_url
        }
        result = qt_web_getOdds(url, header, companyId)
        return result

    @staticmethod
    def qt_mob_get_odds(matchDate, companyId):
        result = {'state': 0, 'odds': {}}
        t = time.time()
        timestamp = int(t) * 1000
        url = "{0}?date={1}&cid={2}&{3}".format(scrawler_config.qt_lq_mobile_odds, matchDate, companyId, timestamp)
        header = {
            'Host': scrawler_config.qt_mobile_host,
            "Referer": scrawler_config.qt_lq_mobile_odds_home
        }
        webResponse = WebUtil.requests_get(url, headers=header, encoding="utf-8")
        if webResponse[0] == 1:
            arr = webResponse[1].split("$$")
            oddsArr = arr[1].split("!")
            for item in oddsArr:
                odds = QtMobOdds(item, companyId)
                result['odds'][odds['scheduleId']] = odds
            result['state'] = 1
        return result


def qt_web_getOdds(url, header, companyId):
    result = {'state': 0, 'odds': {}}
    webResponse = WebUtil.requests_get(url, headers=header, encoding="utf-8")
    if webResponse[0] == 1:
        root = ET.fromstring(webResponse[1])
        for element in root.find('match'):
            item_str = element.text
            odds = QtWebOdds(item_str, companyId)
            result['odds'][odds['scheduleId']] = odds
        result['state'] = 1
    return result


def QtMobOdds(oddsData, companyId):
    odds = {}
    infoArr = oddsData.split("^")
    scheduleId = infoArr[0]
    matchTime = datetime.strptime(infoArr[2], "%Y%m%d%H%M%S")
    matchTimeStr = datetime.strftime(matchTime, '%Y-%m-%d %H:%M')
    matchState = infoArr[5]
    homeScore = infoArr[6]
    awayScore = infoArr[7]

    homeOdds_F = infoArr[8]
    AsianOdds_F = infoArr[9]
    awayOdds_F = infoArr[10]

    homeOdds = infoArr[11]
    AsianOdds = infoArr[12]
    awayOdds = infoArr[13]

    highOdds_F = infoArr[14]
    totalGoal_F = infoArr[15]
    lowOdds_F = infoArr[16]

    highOdds = infoArr[17]
    totalGoal = infoArr[18]
    lowOdds = infoArr[19]

    homeWin_F = infoArr[20]
    awayWin_F = infoArr[21]

    homeWin = infoArr[22]
    awayWin = infoArr[23]

    values = [scheduleId, companyId, matchState, matchTime, homeScore, awayScore,
              homeOdds_F, AsianOdds_F, awayOdds_F,
              homeOdds, AsianOdds, awayOdds,
              highOdds_F, totalGoal_F, lowOdds_F,
              highOdds, totalGoal, lowOdds,
              homeWin_F, awayWin_F,
              homeWin, awayWin]
    keys = ['scheduleId', 'companyId', 'matchState', 'matchTimeStr', 'homeScore', 'awayScore',
            'homeOdds_F', 'AsianOdds_F', 'awayOdds_F',
            'homeOdds', 'AsianOdds', 'awayOdds',
            'highOdds_F', 'totalGoal_F', 'lowOdds_F',
            'highOdds', 'totalGoal', 'lowOdds',
            'homeWin_F', 'awayWin_F',
            'homeWin', 'awayWin']
    for i in range(len(values)):
        odds[keys[i]] = values[i]
    # if int(matchState)>0 or int(matchState) == -1 or int(matchState)==0:
    #     if int(matchState)==0:
    return odds


def QtWebOdds(oddsData, companyId):
    odds = {}
    try:
        arrTr = oddsData.split(",")
        scheduleId = arrTr[0]
        AsianGoal = float(arrTr[1])
        homeOdds = round(float(arrTr[2]),2)
        awayOdds = round(float(arrTr[3]),2)
        totalGoal = float(arrTr[4])
        if arrTr[5] == '':
            highOdds = round(0,2)
        else:
            highOdds = round(float(arrTr[5]),2)
        if arrTr[6] == '':
            lowOdds = round(0,2)
        else:
            lowOdds = round(float(arrTr[6]),2)
        zoudi = arrTr[7]
        asianOdds = {'homeOdds': homeOdds, 'goal': AsianGoal, 'awayOdds':awayOdds}
        totalOdds = {'highOdds': highOdds, 'goal': totalGoal, 'lowOdds':lowOdds}
        odds = {'scheduleId': scheduleId,  'zoudi': zoudi, 'asianOdds': asianOdds, 'totalOdds': totalOdds}
    except Exception as e:
        print(e)
    return odds


def QtMobScore(scoreData):
    score = {}
    odds = None
    arrTr = scoreData.split("^")
    scheduleId = arrTr[0]
    leagueId = arrTr[1]
    matchState = int(arrTr[4])
    matchTime = datetime.strptime(arrTr[3], "%Y%m%d%H%M%S")
    matchTimeStr = datetime.strftime(matchTime, '%Y-%m-%d %H:%M')
    remainTime = arrTr[5]
    homeTeam = arrTr[6]
    awayTeam = arrTr[7]
    addCount = int(arrTr[25])
    homeScore = arrTr[8]
    awayScore = arrTr[9]
    homeHalf = arrTr[34]
    awayHalf = arrTr[35]
    homeScore1 = arrTr[15]
    awayScore1 = arrTr[16]
    homeScore2 = arrTr[17]
    awayScore2 = arrTr[18]
    homeScore3 = arrTr[19]
    awayScore3 = arrTr[20]
    homeScore4 = arrTr[21]
    awayScore4 = arrTr[22]
    homeAdd = arrTr[23]
    awayAdd = arrTr[24]
    homeOrder = arrTr[31]
    if homeOrder != "":
        homeOrder = "[" + homeOrder + "]"
    awayOrder = arrTr[32]
    if awayOrder != "":
        awayOrder = "[" + awayOrder + "]"
    leagueName = ""
    leagueType = arrTr[33]
    leagueColor = arrTr[2]
    caiPiaoHao = arrTr[14]
    # 是否有动画直播
    isActShow = (arrTr[36] == "1")
    # isShow = True
    # isTop = False
    # adImages = ""
    # 总分
    # total = arrTr[28]
    # AsianOdds = arrTr[10]
    keys = ['scheduleId', 'leagueId', 'leagueName', 'leagueType', 'matchTime',
            'matchState', 'remainTime', 'homeTeam', 'awayTeam', 'addCount',
            'homeScore', 'awayScore', 'homeHalf', 'awayHalf',
            'homeScore1', 'awayScore1', 'homeScore2', 'awayScore2',
            'homeScore3', 'awayScore3', 'homeScore4', 'awayScore4',
            'homeAdd', 'awayAdd',
            'homeOrder', 'awayOrder',
            'odds',
            'caiPiaoHao', 'isActShow'
            ]
    values = [scheduleId, leagueId, leagueName, leagueType, matchTimeStr,
              matchState, remainTime,  homeTeam, awayTeam, addCount,
              homeScore, awayScore, homeHalf, awayHalf,
              homeScore1, awayScore1, homeScore2, awayScore2, homeScore3, awayScore3, homeScore4, awayScore4,
              homeAdd, awayAdd,
              homeOrder, awayOrder,
              odds,
              caiPiaoHao, isActShow]
    for i in range(len(values)):
        score[keys[i]] = values[i]
    # for i in range(10, 24):
    #     if score[keys[i]] == '':
    #         score[keys[i]] = None
    return score


# 初始化比分
def QtWebScore(infoStr):
    score = {}
    arr = infoStr.split(SplitRecord)
    try:
        scheduleId = arr[0]
        leagueNames = arr[1].split(SplitColumn)
        leagueName = leagueNames[0]
        leagueType = int(arr[2])
        leagueColor = arr[3]
        timeYear = arr[37]
        matchTime_str = "{0}年{1}".format(timeYear, arr[4].replace("<br>", ' '))
        matchTime = datetime.strptime(matchTime_str, '%Y年%m月%d日 %H:%M')
        matchTime = datetime.strftime(matchTime, '%Y-%m-%d %H:%M')

        matchState = int(arr[5])
        remainTime = arr[6]
        homeTeamId = arr[7]
        homeTeams = getTeamAndOrder(arr[8])
        homeTeam = homeTeams[0]
        homeOrder = homeTeams[1]
        awayTeamId = arr[9]
        awayTeams = getTeamAndOrder(arr[10])
        awayTeam = awayTeams[0]
        awayOrder = awayTeams[1]
        homeScore = getInt(arr[11])
        awayScore = getInt(arr[12])
        homeScore1 = getInt(arr[13])
        awayScore1 = getInt(arr[14])
        homeScore2 = getInt(arr[15])
        awayScore2 = getInt(arr[16])
        homeScore3 = getInt(arr[17])
        awayScore3 = getInt(arr[18])
        homeScore4 = getInt(arr[19])
        awayScore4 = getInt(arr[20])
        addCount = int(arr[21])
        homeAdd1 = getInt(arr[22])
        awayAdd1 = getInt(arr[23])
        homeAdd2 = getInt(arr[24])
        awayAdd2 = getInt(arr[25])
        homeAdd3 = getInt(arr[26])
        awayAdd3 = getInt(arr[27])
        leagueKind = int(arr[32])
        europeOdds = arr[35].split(',')
        homeWin = europeOdds[0]
        awayWin = europeOdds[1]
        odds = None
        leagueId = arr[36]
        if leagueType == 4:
            if homeScore2 >= 0:
                homeHalf = homeScore1 + homeScore2
            else:
                homeHalf = homeScore1 + 0
            if awayScore2 >= 0:
                awayHalf = awayScore1 + awayScore2
            else:
                awayHalf = awayScore1 + 0
        else:
            homeHalf = homeScore1
            awayHalf = awayScore1
        # infoSclassId = arr[33]
        # goalWin = int(arr[34])
        # isTech = arr[28] == "True"
        # tv = arr[29]
        # textLive = arr[30]
        # explain = arr[31]
        # timeYear = arr[37]
        # isNeutral = arr[39] == "1"
        # isLive = arr[40] == "1"
        keys = ['scheduleId', 'leagueId', 'leagueName', 'leagueKind', 'leagueType', 'matchTime',
                'matchState', 'remainTime', 'homeTeamId', 'homeTeam', 'awayTeamId', 'awayTeam', 'addCount',
                'homeScore', 'awayScore', 'homeHalf', 'awayHalf',
                'homeScore1', 'awayScore1', 'homeScore2', 'awayScore2',
                'homeScore3', 'awayScore3', 'homeScore4', 'awayScore4',
                'homeAdd1', 'awayAdd1', 'homeAdd2', 'awayAdd2', 'homeAdd3', 'awayAdd3',
                'homeWin', 'awayWin',
                'homeOrder', 'awayOrder',
                'odds'
                ]
        values = [scheduleId, leagueId, leagueName, leagueKind, leagueType, matchTime,
                  matchState, remainTime, homeTeamId, homeTeam, awayTeamId, awayTeam, addCount,
                  homeScore, awayScore, homeHalf, awayHalf,
                  homeScore1, awayScore1, homeScore2, awayScore2, homeScore3, awayScore3, homeScore4, awayScore4,
                  homeAdd1, awayAdd1, homeAdd2, awayAdd2, homeAdd3, awayAdd3,
                  homeWin, awayWin,
                  homeOrder, awayOrder,
                  odds]
        for i in range(len(values)):
            score[keys[i]] = values[i]
        for i in range(13, 31):
            if score[keys[i]] < 0:
                score[keys[i]] = ''
    except Exception as e:
        print(e)
    return score


def QtMobLeague(leagueData):
    league = {}
    arrTr = leagueData.split("^")
    leagueId = arrTr[1]
    leagueName = arrTr[0]
    isLevel1 = arrTr[2]
    values = [leagueId, leagueName, isLevel1]
    keys = ['leagueId', 'leagueName', 'isLevel1']
    for i in range(len(values)):
        league[keys[i]] = values[i]
    return league


def getTeamAndOrder(infoStr):
    arr = []
    teams = infoStr.split(SplitColumn)
    teamArr = teams[0].split('[')
    arr.append(teamArr[0])
    if len(teamArr) > 1:
        arr.append(teamArr[1].replace("]", ""))
    else:
        arr.append('')
    return arr


def getInt(intStr):
    if intStr == '':
        return -1
    else:
        return int(intStr)


if __name__ == '__main__':
    crawler = ScheduleCrawler()
    data = crawler.qt_web_get_ji(8)
    print(data)
    # jue = "386208^NBL1(中),NBL1(中)^4^#DFCF20^05月31日<br>17:45^-5^^6418^北阿德莱德火箭[5],北阿德萊德火箭[5],North AdelaIde Rockets[5]^6419^中央区狮子会[6],中央區獅子會[6],Central Districts Lions[6]^^^^^^^^^^^0^^^^^^^^^^^1^^,^20 赛季^常规赛^441^True^^^^2020^False^0"
    # # print(type(jue))
    # arr = jue.split("^")
    # match = matchModel(arr)
    # print(match)
    # WebUtil.loadfile(,)