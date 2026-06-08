import utils.fileUtil
import utils.js2pyUtil
from config import zqconfig_qt
from utils import sql_util


def update_sclass():
    filepath = zqconfig_qt.sclass_path_local
    context = utils.js2pyUtil.jsLocjs(filepath)
    leagueList = context.league['leagueList']
    for league in leagueList:
        while 'sumRound' in league.keys():
            while league['sumRound'] is None or league['sumRound'] == '':
                del league['sumRound']
                break
            break
        while 'currRound' in league.keys():
            while league['currRound'] is None or league['currRound'] == '':
                del league['currRound']
                break
            break

        # print(sclass)
        sql = "select * from zq_sclass where leagueId=" + str(league['leagueId'])
        result = sql_util.select_rows(sql)
        try:
            if len(result) > 0:
                sql_util.upData('zq_league', league, {'leagueID': league['leagueId']})
            else:
                sql_util.insertData('zq_league', league)
        except Exception as e:
            print(e)


# 更新球队基本信息
def update_team():
    filepath = zqconfig_qt.team_path_local
    context = utils.js2pyUtil.jsLocjs(filepath)
    teamList = context.team['teamList']
    for team in teamList:
        # print(sclass)
        if 'capacity' in team.keys():
            if team['capacity'] is None or team['capacity'] == '':
                del team['capacity']
        sql = "select * from zq_team where teamId=" + str(team['teamId'])
        result = sql_util.select_rows(sql)
        try:
            if len(result) > 0:
                sql_util.upData('zq_team', team, {'teamId': team['teamId']})
            else:
                sql_util.insertData('zq_team', team)
        except Exception as e:
            print(e)


# 更新杯赛信息
def update_cupQualify():
    filepath = zqconfig_qt.cupQualify_path_local
    context = utils.js2pyUtil.jsLocjs(filepath)
    cuplist = context.cupQualify['list']
    for cup in cuplist:
        # while 'capacity' in cup.keys():
        #     while cup['capacity'] is None or cup['capacity'] == '':
        #         del cup['capacity']
        #         break
        #     break
        if 'groupNum' in cup.keys():
            if cup['groupNum'] is None or cup['groupNum'] == '':
                del cup['groupNum']

        if 'lineCount' in cup.keys():
            if cup['lineCount'] is None or cup['lineCount'] == '':
                del cup['lineCount']

        condition = {'leagueId': cup['leagueId'], 'groupId': cup['groupId'], 'season': cup['season']}
        result = sql_util.select_table_rows('zq_cupQualify', list(cup.keys()), condition)
        try:
            if len(result) > 0:
                sql_util.upData('zq_cupQualify', cup, condition)
            else:
                sql_util.insertData('zq_cupQualify', cup)
        except Exception as e:
            print(e)


# 更新裁判信息
def update_referee():
    filepath = zqconfig_qt.referee_path_local
    context = utils.js2pyUtil.jsLocjs(filepath)
    refList = context.referee['list']
    for ref in refList:
        condition = {'refereeId': ref['refereeId'], 'matchId': ref['matchId']}
        result = sql_util.select_table_rows('zq_referee', list(ref.keys()), condition)
        try:
            if len(result) > 0:
                sql_util.upData('zq_referee', ref, condition)
            else:
                sql_util.insertData('zq_referee', ref)
        except Exception as e:
            print(e)


# 更新子联赛信息
def update_subLeague():
    filepath = zqconfig_qt.subLeage_path_local
    context = utils.js2pyUtil.jsLocjs(filepath)
    sublist = context.subleague['list']
    for sub in sublist:
        if 'totalRound' in sub.keys():
            if sub['totalRound'] is None or sub['totalRound'] == '':
                del sub['totalRound']

        if 'currentRound' in sub.keys():
            if sub['currentRound'] is None or sub['currentRound'] == '':
                del sub['currentRound']
        condition = {'subId': sub['subId'], 'leagueId': sub['leagueId']}
        result = sql_util.select_table_rows('zq_subLeague', list(sub.keys()), condition)
        try:
            if len(result) > 0:
                sql_util.upData('zq_subLeague', sub, condition)
            else:
                sql_util.insertData('zq_subLeague', sub)
        except Exception as e:
            print(e)


# 更新
def update_fifa():
    filepath = zqconfig_qt.fifa_path_local
    context = utils.js2pyUtil.jsLocjs(filepath)
    teamlist = context.fifa['list']
    for team in teamlist:
        # print(sclass)
        # while 'capacity' in team.keys():
        #     while team['capacity'] is None or team['capacity'] == '':
        #         del team['capacity']
        #         break
        #     break
        team['updateTime'] = team['update']
        del team['update']
        sql = "select * from zq_fifa where teamId=" + str(team['teamId'])
        result = sql_util.select_rows(sql)
        try:
            if len(result) > 0:
                sql_util.upData('zq_fifa', team, {'teamId': team['teamId']})
            else:
                sql_util.insertData('zq_fifa', team)
        except Exception as e:
            print(e)
