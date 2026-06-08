from datetime import datetime
from config import scrawler_config
from utils.webUtil import WebUtil

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
    def qt_mobile_header(self):
        header = {
            'Host': scrawler_config.qt_mobile_host,
            "Referer": scrawler_config.qt_zq_mobile_sc
        }
        return header

    @property
    def qt_mobile_url(self):
        return scrawler_config.qt_zq_mobile_sc_bf

    def qt_mobile_get_bf(self):
        bf = {'state': 0, 'score': [], 'league': {}}
        query = {'date': self.matchDate}
        webResponse = WebUtil.requests_post(self.qt_mobile_url, headers=self.qt_mobile_header,
                                            data=query, encoding="utf-8")
        if webResponse[0] == 1:
            tecData = webResponse[1].split("$$$$$")
            arrData = tecData[0].split("$")
            leagueArr = arrData[0].split("!")
            for item in leagueArr:
                league = QtLeague(item)
                bf['league'][league['leagueId']] = league
            scoreArr = arrData[1].split("!")
            for item in scoreArr:
                score = QtScore(item)
                leagueId = score['leagueId']
                score['leagueColor'] = bf['league'][leagueId]['leagueColor']
                score['leagueName'] = bf['league'][leagueId]['leagueName']
                score['isShow'] = bf['league'][leagueId]['isShow']
                bf['score'].append(score)
            bf['state'] = 1
        return bf


def QtScore(data):
    score = {}
    arrTr = data.split("^")
    scheduleId = arrTr[0]
    leagueId = arrTr[1]
    matchState = int(arrTr[2])
    matchTime = datetime.strptime(arrTr[3], "%Y%m%d%H%M%S")
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

    leagueName = ""
    leagueColor = ""
    cupExplain = arrTr[21]
    isShow = True
    liveTv = arrTr[22]
    homeOdds = arrTr[23]
    goal = Goal2GoalCn(arrTr[24])
    awayOdds = arrTr[25]
    if matchState == -1:
        AsianOddsResult = CalcAsianOddsResult(homeScore, awayScore, arrTr[24])
    else:
        AsianOddsResult = ""
    values = [scheduleId, leagueId, matchState, matchTimeStr, homeTeam, awayTeam,
              homeScore, awayScore, homeHalf, awayHalf,
              homeRed, awayRed, homeYellow, awayYellow,
              homeOrder, awayOrder,
              leagueName, leagueColor, cupExplain,
              homeOdds, goal, awayOdds, AsianOddsResult,
              caiPiaoHao, isZhenRong, isShow, liveTv]
    keys = ['scheduleId', 'leagueId', 'matchState', 'matchTimeStr', 'homeTeam', 'awayTeam',
            'homeScore', 'awayScore', 'homeHalf', 'awayHalf',
            'homeRed', 'awayRed', 'homeYellow', 'awayYellow',
            'homeOrder', 'awayOrder',
            'leagueName', 'leagueColor', 'cupExplain',
            'homeOdds', 'goal', 'awayOdds', 'AsianOddsResult',
            'caiPiaoHao', 'isZhenRong', 'isShow', 'liveTv']
    for i in range(len(keys)):
        score[keys[i]] = values[i]
    return score


def QtLeague(leagueData):
    league = {}
    arrTr = leagueData.split("^")
    leagueId = arrTr[1]
    leagueName = arrTr[0]
    isLevel1 = (arrTr[2] == "1")
    leagueColor = arrColor[int(leagueId) % 16]
    isShow = (arrTr[2] == "1")
    isTmpShow = (arrTr[2] == "1")
    values = [leagueId, leagueName, isLevel1, leagueColor, isShow, isTmpShow]
    keys = ['leagueId', 'leagueName', 'isLevel1', 'leagueColor', 'isShow', 'isTmpShow']
    for i in range(len(keys)):
        league[keys[i]] = values[i]
    return league


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
    result = ""
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
    crawler = ScheduleCrawler('2020-06-02')
    data = crawler.qt_mobile_get_bf()
    print(data)
    # jue = "386208^NBL1(中),NBL1(中)^4^#DFCF20^05月31日<br>17:45^-5^^6418^北阿德莱德火箭[5],北阿德萊德火箭[5],North AdelaIde Rockets[5]^6419^中央区狮子会[6],中央區獅子會[6],Central Districts Lions[6]^^^^^^^^^^^0^^^^^^^^^^^1^^,^20 赛季^常规赛^441^True^^^^2020^False^0"
    # # print(type(jue))
    # arr = jue.split("^")
    # match = matchModel(arr)
    # print(match)

