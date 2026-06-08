import traceback

import requests

from config import lqconfig_qt
from utils import sql_util
from utils.js2pyUtil import logLine


class Technical(object):
    @staticmethod
    def upTeamtech():
        matchs = sql_util.select("SELECT scheduleID,HomeTeamID,AwayTeamID,MatchSeason,MatchTime FROM `lq_schedule` "
                                 "where sclassID =1 and MatchState=-1 and teamTech=0 order by MatchTime ASC")
        for match in matchs:
            teamtech = Technical.technical_team(match)
            if len(teamtech[0]) > 0 and len(teamtech[1]) > 0:
                sql_util.insertData('lq_teamtechnic', teamtech[0])
                sql_util.insertData('lq_teamtechnic', teamtech[1])
                sql_util.upData('lq_schedule', {'teamTech': 1}, {'scheduleID': match[0]})

    @staticmethod
    def technical_team(matchdata):
        tech_home = {}
        tech_away = {}
        matchid = matchdata[0]
        url = "http://nba.titian007.com/jsData/tech/" + str(matchid)[0:1] + "/" + str(matchid)[1:3] + "/" + str(
            matchid) + ".js"
        # print(url)
        try:
            page = requests.get(url, headers=lqconfig_qt.headers, timeout=5)
        except Exception as e:
            print(e)
            excepstr = traceback.format_exc()
            logLine(lqconfig_qt.exception, excepstr)
            logLine(lqconfig_qt.quarterscore_e, str(matchid))
        else:
            page.encoding = 'utf-8'
            technicals = page.text
            tech_data = technicals.split('$')
            # print(tech_data)
            if len(tech_data) > 2:
                data_match = tech_data[0].split('^')
                # print(data_match)
                tech_home['scheduleID'] = matchdata[0]
                tech_away['scheduleID'] = matchdata[0]
                tech_home['teamID'] = matchdata[1]
                tech_away['teamID'] = matchdata[2]
                tech_home['matchSeason'] = matchdata[3]
                tech_away['matchSeason'] = matchdata[3]
                tech_home['fast'] = data_match[4]
                tech_home['inside'] = data_match[6]
                tech_home['exceed'] = data_match[8]
                tech_away['fast'] = data_match[5]
                tech_away['inside'] = data_match[7]
                tech_away['exceed'] = data_match[9]
                data_home = tech_data[1].split('!')[-2].split('^')
                data_away = tech_data[2].split('!')[-2].split('^')
                # soup = BeautifulSoup(page.content, 'html.parser', from_encoding="gb18030")
                # trs = soup.find_all('tr', bgcolor="#E6E9FF")
                field = ['playTime', 'shoot', 'shoot_hit', 'threeMin_hit', 'threeMin', 'punishBall_Hit', 'punishBall',
                         'attack', 'defend', 'rebound', 'helpAttack', 'foul', 'rob', 'misplay', 'cover', 'score']
                for i in range(0, len(data_home)):
                    tech_home[field[i]] = data_home[i]
                    tech_away[field[i]] = data_away[i]
                tech_home['isHome'] = 1
                tech_home['loseScore'] = tech_away['score']
                tech_away['isHome'] = 0
                tech_away['loseScore'] = tech_home['score']
        return [tech_home, tech_away]
