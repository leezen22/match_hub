import os
from datetime import datetime
import utils.fileUtil
import utils.js2pyUtil
from config import lqconfig_qt
from lq.formate import model
from utils import js2pyUtil, sql_util, fileUtil
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil


def upRank():
    fileUtil.logLine(lqconfig_qt.update_log, "开始更新积分文件")
    print(getNowTime() + ' 开始更新积分文件')
    Rank.upRankJS()
    rankfiles = []
    if os.path.isdir(lqconfig_qt.rankdir_p):
        rankfiles = utils.fileUtil.dirFiles(lqconfig_qt.rankdir_p, [])
    for file in rankfiles:
        try:
            Rank.upRankByfile(file)
        except Exception as e:
            print(e)
        else:
            os.remove(file)
    print(getNowTime() + ' 篮球积分更新结束')
    sql_util.upData('lq_note', {'lastUpdateTime': getNowTime()}, {'task': 'rank'})


class Rank(object):

    @staticmethod
    def upRankJS():
        result = sql_util.select_table_rows(
            'lq_note',
            ['ID', 'task', 'lastUpdateTime'],
            {'task': 'rank'},
            isDis=True,
        )
        if not result:
            return
        lastUpdate_local = result[0][2]
        select_Sql = "select leagueId FROM lq_league where leagueKind=1 order by leagueId ASC"
        leagues = sql_util.select(select_Sql)
        for league in leagues:
            leagueId = str(league[0])
            seaFileName = 'sea' + leagueId + '.js'
            # seajsUrl = lanqiu_config_qt.seajsWebdir + seafilename
            seaJSPath = lqconfig_qt.seajslocaldir + seaFileName
            # 赛季文件存在(更新积分信息前，会优先更新本地联赛赛季信息)
            if os.path.exists(seaJSPath):
                localContex = js2pyUtil.jsLocjs(seaJSPath)
                if not localContex or not hasattr(localContex, 'arrSeason'):
                    continue
                seasons = localContex.arrSeason
                # 日常更新，只判断更新最新赛季
                season_latest = model.changeSeason(seasons[0][0])
                rankFileName = 's' + leagueId + '.js'
                rankLocalPath = lqconfig_qt.ranklocaldir + season_latest + '/' + rankFileName
                rankPendPath = lqconfig_qt.rankdir_p + season_latest + '/' + rankFileName
                rankJSurl = lqconfig_qt.rankWebdir + season_latest + '/' + rankFileName
                if os.path.exists(rankLocalPath):
                    webResponse = WebUtil.requests_get(rankJSurl, headers=lqconfig_qt.headers,
                                                       sourceName='collect web_Rankjs');
                    state = webResponse[0]
                    webContent = webResponse[1]
                    if state == 1 and webContent != '':
                        parse_result = js2pyUtil.js2c(
                            webContent,
                            source=rankJSurl,
                            required_names=("lastUpdateTime", "arrLeague"),
                        )
                        if parse_result[0] != 1:
                            continue
                        webContext = parse_result[1]
                        updateTime_web = webContext.lastUpdateTime
                        lastUpdate_web = datetime.strptime(updateTime_web, "%Y-%m-%d %H:%M:%S")
                        # 网站更新时间大于本次更新时间
                        if lastUpdate_web > lastUpdate_local:
                            fileUtil.fileWrite(rankPendPath, "w", webContent)
                            # 待更新文件下载成功
                            if os.path.exists(rankPendPath):
                                utils.fileUtil.copyfile(rankPendPath, rankLocalPath)
                else:
                    WebUtil.loadFileByName(rankJSurl, rankPendPath, lqconfig_qt.headers)
                    if os.path.exists(rankPendPath):
                        utils.fileUtil.copyfile(rankPendPath, rankLocalPath)

    # 下载联赛JS文件到本地
    @staticmethod
    def loadRankJS():
        select_sql = "select leagueId FROM lq_league where leagueKind=1 order by leagueId ASC"
        leagues = sql_util.select(select_sql)
        # print(sclasslist)
        for league in leagues:
            leagueId = str(league[0])
            seaFileName = 'sea' + leagueId + '.js'
            seaJS_path = lqconfig_qt.seajslocaldir + seaFileName
            if os.path.exists(seaJS_path):
                context = utils.js2pyUtil.jsLocjs(seaJS_path)
                if not context or not hasattr(context, 'arrSeason'):
                    continue
                seasons = context.arrSeason
                for season in seasons:
                    season2 = model.changeSeason(season[0])
                    filename = 's' + leagueId + '.js'
                    rankLocalDir = lqconfig_qt.ranklocaldir + season2 + '/'
                    rankJSurl = lqconfig_qt.rankWebdir + season2 + '/' + filename
                    rankJSpath = rankLocalDir + filename
                    # common_util.loadWebFile(rankJSurl, rankJSpath, lqconfig_qt.headers)
                    WebUtil.loadFileByName(rankJSurl, rankJSpath, lqconfig_qt.headers)
            else:
                print("联赛：" + leagueId + " 赛季列表不存在")

    @staticmethod
    # 根据本地文件路径更新 积分
    def upRankByfile(filePath):
        context = utils.js2pyUtil.jsLocjs(filePath)
        if not context:
            return
        teams = {}
        rankings = []
        leagueId = context.arrLeague[0]
        leagueName = context.arrLeague[7]
        MatchSeason = model.changeSeason(context.arrLeague[4])
        for team in context.arrTeam:
            teams[str(team[0])] = team[4]
        try:
            # context.westData is not None:
            for i in range(0, len(context.westData)):
                data = context.westData[i]
                rank = {}
                rank['leagueID'] = leagueId
                rank['leagueName'] = leagueName
                rank['matchSeason'] = MatchSeason
                rank['modifyTime'] = context.lastUpdateTime
                rank['teamID'] = data[0]
                rank['teamName'] = teams[str(data[0])]
                rank['score'] = data[6]
                rank['lossScore'] = data[7]
                rank['homeWin'] = data[12]
                rank['homeLoss'] = data[13]
                rank['awayWin'] = data[14]
                rank['awayLoss'] = data[15]
                rank['winScale'] = data[3]
                rank['totalOrder'] = i + 1
                rank['near10Win'] = data[16]
                rank['near10Loss'] = data[17]
                rank['state'] = data[18]
                rankings.append(rank)
                # rank['HomeOrder'] =
                # rank['AwayOrder'] =
        except Exception as e:
            print(e)
        try:
            # if context.eastData is not None:
            for i in range(0, len(context.eastData)):
                data = context.eastData[i]
                rank = {}
                rank['leagueID'] = leagueId
                rank['leagueName'] = leagueName
                rank['matchSeason'] = MatchSeason
                rank['modifyTime'] = context.lastUpdateTime
                rank['teamID'] = data[0]
                rank['teamName'] = teams[str(data[0])]
                rank['score'] = data[6]
                rank['lossScore'] = data[7]
                rank['homeWin'] = data[12]
                rank['homeLoss'] = data[13]
                rank['awayWin'] = data[14]
                rank['awayLoss'] = data[15]
                rank['winScale'] = data[3]
                rank['totalOrder'] = i + 1
                rank['near10Win'] = data[16]
                rank['near10Loss'] = data[17]
                rank['state'] = data[18]
                rankings.append(rank)
                # rank['HomeOrder'] =
                # rank['AwayOrder'] =
        except Exception as e:
            print(e)
        for ranking in rankings:
            search_sql = "SELECT * FROM lq_rank where LeagueID=" + str(ranking['leagueID']) + " and TeamID=" + str(
                ranking['teamID']) + \
                         " AND MatchSeason= '" + ranking['matchSeason'] + "'"
            results = sql_util.select_Execute(search_sql)
            if len(results) == 0:
                sql_util.insertData('lq_rank', ranking)
            else:
                sql_util.upData('lq_rank', ranking, {'LeagueID': ranking['leagueID'], 'TeamID': ranking['teamID'],
                                                     'MatchSeason': ranking['matchSeason']})
