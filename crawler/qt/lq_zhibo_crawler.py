import re
import threading
from bs4 import BeautifulSoup
from config import scrawler_config
from utils import js2pyUtil
from utils.webUtil import WebUtil


class ZhiBoCrawler(object):
    def __init__(self, matchId, scheduleId=None, partScore_F=None, teamTech=None,
                 hasPartScore=True, hasTeamTech=False, hasLiveText=False, hasPlayerTech=False):
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.hasPartScore = hasPartScore
        self.hasTeamTech = hasTeamTech
        self.hasLiveText = hasLiveText
        self.hasPlayerTech = hasPlayerTech
        self.partScore_F = partScore_F
        self.teamTech = teamTech

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_host(self):
        return scrawler_config.qt_lq_web_host

    @property
    def qt_mobile_url(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_lq_mobile_zhiBo_url, self.scheduleId)

    @property
    def qt_web_url(self):
        return "{0}?matchid={1}".format(scrawler_config.qt_lq_web_zhiBo_url, self.scheduleId)

    def qt_web_get(self):
        headers = {"Host": self.qt_web_host, 'Referer': scrawler_config.qt_lq_web_home}
        data = {'state': 0}
        response = WebUtil.requests_get(self.qt_web_url, headers=headers)
        state = response[0]
        if state == 1 and response[1] != '':
            soup = BeautifulSoup(response[1], 'html.parser')
            table_parScore = soup.select('body div table.t_bf')[0]
            print(table_parScore)
            threads = []
            if self.hasPartScore:
                partThread = DetailThread(web_get_partScore, args=(table_parScore, self.matchId, self.scheduleId))
                threads.append(partThread)
            # 启动线程
            for t in threads:
                t.start()
            # 等待所有线程完成
            for t in threads:
                t.join()
            if self.hasPartScore:
                data['partScore'] = partThread.get_result()
            data['state'] = 1
        return data

    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host,
                   "Referer": scrawler_config.qt_lq_mobile_ji}
        data = {'state': 0}
        response = WebUtil.requests_get(self.qt_mobile_url, headers=headers, isMobile=True)
        state = response[0]
        if state == 1 and response[1] != '':
            soup = BeautifulSoup(response[1], "html.parser")
            pattern = re.compile(r"var _isCup", re.MULTILINE | re.DOTALL)
            tech_tag = soup.find("script", text=pattern)
            threads = []
            if self.hasPartScore:
                partThread = DetailThread(mobile_get_partScore, args=(tech_tag, self.matchId, self.scheduleId))
                threads.append(partThread)
            # 启动线程
            for t in threads:
                t.start()
            # 等待所有线程完成
            for t in threads:
                t.join()
            if self.hasPartScore:
                data['partScore'] = partThread.get_result()
            data['state'] = 1
        return data


class DetailThread(threading.Thread):
    def __init__(self, func, args=()):
        super(DetailThread, self).__init__()
        self.func = func
        self.args = args
        self.result = None

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        threading.Thread.join(self)
        try:
            return self.result
        except Exception as e:
            print(e)
            return None


def web_get_partScore(soup, matchId, scheduleId):
    partScore = {'state': 0, 'matchId': matchId, 'scheduleId': scheduleId, 'data': {}}
    AddTimes = ['Add1', 'Add2', 'Add3', 'Add4', 'Add5']
    try:
        scoreTrs = soup.select('tr')
        thead = scoreTrs[0]
        state = thead.select('td')[0].text.strip().split("\xa0")
        matchState = scrawler_config.lq_matchState[state[0]]
        # 比赛未开场，不需更新比分
        if matchState != 0:
            scoreData = {}
            home_tr = scoreTrs[1]
            away_tr = scoreTrs[2]
            home_tds = home_tr.select('td')
            away_tds = away_tr.select('td')
            span_homeScore = home_tr.find(class_='zbf')
            span_awayScore = away_tr.find(class_='zbf')
            number = len(home_tds)
            if number > 5:
                # homeName = home_tds[0].text
                # awayName = away_tds[0].text
                if span_homeScore is not None and span_homeScore.text != '':
                    scoreData['homeScore'] = span_homeScore.text
                if span_awayScore is not None and span_awayScore.text != '':
                    scoreData['awayScore'] = span_awayScore.text
                homeOne = home_tds[1].text
                if homeOne != '':
                    scoreData['homeScore1'] = homeOne
                homeTwo = home_tds[2].text
                if homeTwo != '':
                    scoreData['homeScore2'] = homeTwo
                homeThree = home_tds[3].text
                if homeThree != '':
                    scoreData['homeScore3'] = homeThree
                homeFour = home_tds[4].text
                if homeFour != '':
                    scoreData['homeScore4'] = homeFour
                awayOne = away_tds[1].text
                if awayOne != '':
                    scoreData['awayScore1'] = awayOne
                awayTwo = away_tds[2].text
                if awayTwo != '':
                    scoreData['awayScore2'] = awayTwo
                awayThree = away_tds[3].text
                if awayThree != '':
                    scoreData['awayScore3'] = awayThree
                awayFour = away_tds[4].text
                if awayFour != '':
                    scoreData['awayScore4'] = awayFour
            if number > 6:
                for i in range(number - 6):
                    AddTime = AddTimes[i]
                    homeAddTimeScore = home_tds[5 + i].text
                    if homeAddTimeScore != '':
                        scoreData['home' + AddTime] = homeAddTimeScore
                    awayAddTimeScore = away_tds[5 + i].text
                    if awayAddTimeScore != '':
                        scoreData['away' + AddTime] = awayAddTimeScore
            scoreData['matchState'] = matchState
            # 更新本节或加时剩余时间
            if len(state) > 1:
                scoreData['remainTime'] = state[1]
            else:
                scoreData['remainTime'] = ''
            # 如比赛已完场、中场、下半场或者加时，更新半场比分
            if matchState == -1 or matchState > 2:
                if ('homeScore1' in scoreData) and ('homeScore2' in scoreData) and \
                        ('awayScore1' in scoreData) and ('awayScore2' in scoreData):
                    scoreData['homeHalf'] = int(scoreData['homeScore1']) + int(scoreData['homeScore2'])
                    scoreData['awayHalf'] = int(scoreData['awayScore1']) + int(scoreData['awayScore2'])
            # 如比赛已完场，本次采集后，未来不再采集本场比赛比分
            if matchState in (-1, -4):
                scoreData['partScore_f'] = 2
            else:
                scoreData['partScore_f'] = 1
            partScore['data'] = scoreData
        partScore['state'] = 1
    except Exception as e:
        print(e)
    return partScore


def mobile_get_partScore(script_tag, matchId, scheduleId):
    partScore = {'state': 0, 'matchId': matchId, 'scheduleId': scheduleId, 'data': {}}
    if script_tag is not None:
        script = str(script_tag).replace('<script type="text/javascript">', '').replace('</script>', '').strip()
        parse_result = js2pyUtil.js2c(
            script,
            source="lq_zhibo_mobile_part_score:{0}".format(scheduleId),
            required_names=("techData",),
        )
        if parse_result[0] != 1:
            return partScore
        context = parse_result[1]
        techData = context.techData.to_dict()
        if "generalInfo" in techData.keys():
            if 'stateCode' in techData['generalInfo'].keys():
                partScore['data']['matchState'] = techData['generalInfo']['stateCode']
            if 'remainTime' in techData['generalInfo'].keys():
                partScore['data']['remainTime'] = techData['generalInfo']['remainTime']
            if 'home' in techData['generalInfo']:
                homeData = techData['generalInfo']['home']
                if 'score' in homeData.keys():
                    partScore['data']['homeScore'] = homeData['score']
                if 'score1' in homeData.keys():
                    partScore['data']['homeScore1'] = homeData['score1']
                    homeOne = homeData['score1']
                else:
                    homeOne = 0

                if 'score2' in homeData.keys():
                    partScore['data']['homeScore2'] = homeData['score2']
                    homeTwo = homeData['score2']
                else:
                    homeTwo = 0

                if 'score3' in homeData.keys():
                    partScore['data']['homeScore3'] = homeData['score3']
                if 'score4' in homeData.keys():
                    partScore['data']['homeScore4'] = homeData['score4']
                if 'overtimeScore' in homeData.keys():
                    partScore['data']['homeAdd'] = homeData['overtimeScore']
                partScore['data']['homeHalf'] = homeOne + homeTwo
            if 'away' in techData['generalInfo']:
                awayData = techData['generalInfo']['away']
                if 'score' in awayData.keys():
                    partScore['data']['awayScore'] = awayData['score']
                if 'score1' in awayData.keys():
                    partScore['data']['awayScore1'] = awayData['score1']
                    awayOne = awayData['score1']
                else:
                    awayOne = 0
                if 'score2' in awayData.keys():
                    partScore['data']['awayScore2'] = awayData['score2']
                    awayTwo = awayData['score2']
                else:
                    awayTwo = 0
                if 'score3' in awayData.keys():
                    partScore['data']['awayScor3'] = awayData['score3']
                if 'score4' in awayData.keys():
                    partScore['data']['awayScor4'] = awayData['score4']
                if 'overtimeScore' in awayData.keys():
                    partScore['data']['awayAdd'] = awayData['overtimeScore']
                partScore['data']['awayHalf'] = awayOne + awayTwo

            if 'homeScore'in partScore['data'].keys() and 'awayScore' in partScore['data'].keys():
                partScore['state'] = 1
    return partScore


# if __name__ == '__main__':
#     zhiBoCrawler = ZhiBoCrawler(211899, 391791)
#     zhiBoData = zhiBoCrawler.qt_web_get()
#     print(zhiBoData)
