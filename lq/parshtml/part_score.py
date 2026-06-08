from bs4 import BeautifulSoup
from config import lqconfig_qt
from utils import js2pyUtil, dateUtil
from utils.webUtil import WebUtil


# 获取已完场比赛小节和加时比分
def get_PartScore(matchid):
    # headers = {"Host": "nba.titan007.com",
    #            "Referer": "http://nba.titian007.com/",
    #          "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
    # }

    # techtxtlive = 'http://nba.titan007.com/cn/Tech/TechTxtLive.aspx'

    matchdict = {}
    Addtimes = ['Add1', 'Add2', 'Add3', 'Add4', 'Add5']
    url = lqconfig_qt.techtxtlive + '?' + 'matchid=' + str(matchid)
    # page = common_util.getWebContent('collect partscore', url, headers=lanqiu_config_qt.headers)
    webresponse = WebUtil.requests_get(url, headers=lqconfig_qt.headers)
    content = webresponse[1]

    if content != '' and webresponse[0] == 1:
        soup = BeautifulSoup(content, 'html.parser')
        # soup = BeautifulSoup(page.content, 'html.parser', from_encoding="gb18030")
        scoretr = soup.select('body div table.t_bf tr')
        ths = scoretr[0].select('th')
        state_data = ths[0].text.strip().split("\xa0")
        sign = lqconfig_qt.matchstate[state_data[0]]
        # 比赛未开场，不需更新比分
        if sign != 0:
            if soup.find(id='homeHeadScore').text != '':
                matchdict['homeScore'] = soup.find(id='homeHeadScore').text
            if soup.find(id='guestHeadScore').text != '':
                matchdict['awayScore'] = soup.find(id='guestHeadScore').text
            home_tr = scoretr[1]
            away_tr = scoretr[2]
            home_tds = home_tr.select('td')
            away_tds = away_tr.select('td')
            number = len(home_tds)
            if number > 5:
                if home_tds[1].text != '':
                    matchdict['homeScore1'] = home_tds[0].text
                if home_tds[2].text != '':
                    matchdict['homeScore2'] = home_tds[1].text
                if home_tds[3].text != '':
                    matchdict['homeScore3'] = home_tds[2].text
                if home_tds[4].text != '':
                    matchdict['homeScore4'] = home_tds[3].text
                if away_tds[1].text != '':
                    matchdict['awayScore1'] = away_tds[0].text
                if away_tds[2].text != '':
                    matchdict['awayScore2'] = away_tds[1].text
                if away_tds[3].text != '':
                    matchdict['awayScore3'] = away_tds[2].text
                if away_tds[4].text != '':
                    matchdict['awayScore4'] = away_tds[3].text
            if number > 6:
                for i in range(number - 6):
                    Addtime = Addtimes[i]
                    if home_tds[4 + i].text != '' and home_tds[4 + i].text != '-':
                        matchdict['home' + Addtime] = home_tds[4 + i].text
                    if away_tds[4 + i].text != ''and away_tds[4 + i].text != '-':
                        matchdict['away' + Addtime] = away_tds[4 + i].text
            matchdict['matchState'] = sign
            # 更新本节或加时剩余时间
            if len(state_data) > 1:
                matchdict['remainTime'] = state_data[1]
            else:
                matchdict['remainTime'] = ''
            # 如比赛已完场、中场、下半场或者加时，更新半场比分
            if sign == -1 or sign > 2:
                if ('homeScore1' in matchdict) and ('homeScore2' in matchdict) and \
                        ('awayScore1' in matchdict) and ('awayScore2' in matchdict):
                    matchdict['homeHalf'] = int(matchdict['homeScore1']) + int(matchdict['homeScore2'])
                    matchdict['awayHalf'] = int(matchdict['awayScore1']) + int(matchdict['awayScore2'])
            # 如比赛已完场，本次采集后，未来不再采集本场比赛比分
            if sign == -1:
                matchdict['partscore_f'] = 2
            else:
                matchdict['partscore_f'] = 1
            # 记录本次更新时间
            matchdict['updateTime'] = dateUtil.getNowTime()
            print(str(matchid) + ": " + str(matchdict))
    return matchdict


# if __name__ == '__main__':
#     # upScheJs()
#     # upSchedule()
#     matchdict = get_PartScore(121078)
#     print(matchdict)