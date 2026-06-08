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
    def __init__(self, matchDate):
        self.matchDate = matchDate

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_header(self):
        header = {
            'Host': scrawler_config.qt_lq_bf_host,
            'Referer': scrawler_config.qt_lq_web_sc_home
        }
        return header

    @property
    def qt_mobile_url(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_lq_mobile_asianOdds_url, self.scheduleId)

    @property
    def qt_web_url(self):
        t = time.time()
        timestamp = int(t) * 1000
        # "http://bf.win007.com/nba_date.aspx?date=2020-5-30&h=0&m=0&s=1&t=1590901717000"
        return "{0}?date={1}&h=0&m=0&s=1&t={2}".format(scrawler_config.qt_lq_web_sc_date,
                                                       self.matchDate, timestamp)

    def qt_web_get_bf(self):
        bf = {'state': 0, 'data': []}
        webResponse = WebUtil.requests_get(self.qt_web_url, headers=self.qt_web_header, encoding="gbk")
        if webResponse[0] == 1:
            root = ET.fromstring(webResponse[1])
            for element in root.find('m'):
                item_str = element.text
                item = QtWebScore(item_str)
                bf['data'].append(item)
            bf['state'] = 1
        else:
            bf['state'] = 0
        return bf


def QtWebScore(infoArr):
    score = {}
    try:
        arr = infoArr.split(SplitRecord)
        scheduleId = int(arr[0])
        leagueNames = arr[1].split(SplitColumn)
        leagueName = leagueNames[0]
        # 小节数
        leagueType = int(arr[2])
        leagueColor = arr[3]
        timeYear = arr[42]
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
        homeOne = getInt(arr[13])
        awayOne = getInt(arr[14])
        homeTwo = getInt(arr[15])
        awayTwo = getInt(arr[16])
        homeThree = getInt(arr[17])
        awayThree = getInt(arr[18])
        homeFour = getInt(arr[19])
        awayFour = getInt(arr[20])
        addCount = getInt(arr[21])
        homeAdd1 = getInt(arr[22])
        awayAdd1 = getInt(arr[23])
        homeAdd2 = getInt(arr[24])
        awayAdd2 = getInt(arr[25])
        homeAdd3 = getInt(arr[26])
        awayAdd3 = getInt(arr[27])
        leagueKind = int(arr[32])
        europeOdds = arr[34].split(",")
        homeWin = europeOdds[0]
        awayWin = europeOdds[1]
        leagueId = arr[37]
        if leagueType == 4:
            if homeTwo >= 0:
                homeHalf = homeOne + homeTwo
            else:
                homeHalf = homeOne + 0
            if awayTwo >= 0:
                awayHalf = awayOne + awayTwo
            else:
                awayHalf = awayOne + 0
        else:
            homeHalf = homeOne
            awayHalf = awayOne
        keys = ['scheduleId', 'leagueId', 'leagueName', 'leagueKind', 'leagueType', 'matchTime',
                'matchState', 'remainTime', 'homeTeamId', 'homeTeam', 'awayTeamId', 'awayTeam', 'addCount',
                'homeScore', 'awayScore', 'homeHalf', 'awayHalf',
                'homeOne', 'awayOne', 'homeTwo', 'awayTwo', 'homeThree', 'awayThree', 'homeFour', 'awayFour',
                'homeAdd1', 'awayAdd1', 'homeAdd2', 'awayAdd2', 'homeAdd3', 'awayAdd3',
                'homeWin', 'awayWin',
                'homeOrder', 'awayOrder'
                ]
        values = [scheduleId, leagueId, leagueName, leagueKind, leagueType, matchTime,
                  matchState, remainTime, homeTeamId, homeTeam, awayTeamId, awayTeam, addCount,
                  homeScore, awayScore, homeHalf, awayHalf,
                  homeOne, awayOne, homeTwo, awayTwo, homeThree, awayThree, homeFour, awayFour,
                  homeAdd1, awayAdd1, homeAdd2, awayAdd2, homeAdd3, awayAdd3,
                  homeWin, awayWin,
                  homeOrder, awayOrder]
        for i in range(len(values)):
            score[keys[i]] = values[i]
        for i in range(13, 31):
            if score[keys[i]] < 0:
                score[keys[i]] = ''
        # textLive = arr[30]
        # explain = arr[31]
        # timeYear = arr[42]
        # match['isNeutral'] = arr[39] == "1"
        # match['isLive'] = arr[40] == "1"
        # match['infoSclassId'] = arr[38]
        # match['goalWin'] = int(arr[34])
    except Exception as e:
        print(e)
    return score


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
    crawler = ScheduleCrawler('2024-03-13')
    data = crawler.qt_web_get_bf()
    print(data)
    # jue = "386208^NBL1(中),NBL1(中)^4^#DFCF20^05月31日<br>17:45^-5^^6418^北阿德莱德火箭[5],北阿德萊德火箭[5],North AdelaIde Rockets[5]^6419^中央区狮子会[6],中央區獅子會[6],Central Districts Lions[6]^^^^^^^^^^^0^^^^^^^^^^^1^^,^20 赛季^常规赛^441^True^^^^2020^False^0"
    # # print(type(jue))
    # arr = jue.split("^")
    # match = matchModel(arr)
    # print(match)
    # WebUtil.loadfile(,)