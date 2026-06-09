import os
from datetime import datetime
from config import scrawler_config
from crawler.qt.lq_league_crawler import LeagueCrawler
from crawler.qt.lq_schedule_js_crawler import ScheduleJSCrawler
from crawler.qt.lq_zhibo_crawler import ZhiBoCrawler
from dao.lq_cup_group_dao import LqCupGroupDao
from dao.lq_match_dao import LqMatchDao
from dao.lq_note_dao import LqNoteDao
from dao.lq_playoffs_dao import LqPlayoffsDao
from dao.lq_schedule_craw_dao import ScheduleCrawDao
from utils import fileUtil, js2pyUtil
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil


class LqService(object):

    def __init__(self):
        pass

    # 赛程JS文件本地存储目录
    @property
    def scheJs_local_dir(self):
        return scrawler_config.lq_scheJS_local_dir

    # 赛程JS待更新文件，本地暂存目录
    @property
    def scheJs_localPend_dir(self):
        return scrawler_config.scheJs_localPend_dir

    # 下载待更新文件至本地: 总库和暂存目录
    def up_scheduleJs(self):
        print(getNowTime() + "开始更新篮球赛程JS文件")
        headers = {'Host': scrawler_config.qt_lq_web_host}
        result_lqNote = LqNoteDao.select_rows(['ID', 'task', 'lastUpdateTime'], {'task': 'scheduleJs'}, isDis=True)
        lastUpdate_local = result_lqNote[0][2]
        crawler = LeagueCrawler()
        leagues = crawler.get_leagues_web()
        for league in leagues:
            crawler = ScheduleJSCrawler(league[0], league[2])
            items = crawler.getScheJSPend()['data']
            for item in items:
                scheJsUrl = item[0]
                scheJsPath = item[1]
                filename = os.path.basename(scheJsUrl)
                season = scheJsUrl.split('/')[-2]
                pendingPath_new = self.scheJs_localPend_dir + '/new/' + str(season) + '/' + filename
                pendingPath_exist = self.scheJs_localPend_dir + '/exist/' + str(season) + '/' + filename

                # 赛程文件已存在
                if os.path.exists((scheJsPath)):
                    webResponse = WebUtil.requests_get(scheJsUrl, headers=headers)
                    state = webResponse[0]
                    webContent = webResponse[1]
                    if state == 0:
                        print("赛程文件爬取失败：{0}".format(scheJsUrl))
                    if state == 1 and webContent != '':
                        parse_result = js2pyUtil.js2c(
                            webContent,
                            source=scheJsUrl,
                            required_names=("lastUpdateTime",),
                        )
                        if parse_result[0] != 1:
                            continue
                        try:
                            webContext = parse_result[1]
                            updateTime_web = webContext.lastUpdateTime
                            lastUpdate_web = datetime.strptime(updateTime_web, "%Y-%m-%d %H:%M:%S")
                            # 网站更新时间大于本次更新时间
                            if lastUpdate_web > lastUpdate_local:
                                fileUtil.fileWrite(pendingPath_exist, "w", webContent)
                                # 待更新文件下载成功
                                if os.path.exists(pendingPath_exist):
                                    fileUtil.copyfile(pendingPath_exist, scheJsPath)
                        except Exception as e:
                            print("赛程JS文件解析异常：{0} ".format(e))
                # 赛程文件不存在
                else:
                    WebUtil.loadFileByName(scheJsUrl, pendingPath_new, headers)
                    if os.path.exists(pendingPath_new):
                        fileUtil.copyfile(pendingPath_new, scheJsPath)
        LqNoteDao.update({'lastUpdateTime': getNowTime()}, {'task': 'scheduleJs'})

    def up_schedule(self):
        print(getNowTime() + ' 开始解析JS文件并更新赛程')
        result = LqNoteDao.select_rows(['ID', 'task', 'lastUpdateTime'], {'task': 'schedule'}, isDis=True)
        updateTime_local = result[0][2]
        files_new = []
        new_dir = self.scheJs_localPend_dir + '/new/'
        if os.path.isdir(new_dir):
            files_new = fileUtil.dirFiles(new_dir, [])

        for file in files_new:
            self.upScheduleByFile(file, 0, updateTime_local)
            os.remove(file)
        print(getNowTime() + ' 新增赛程文件解析更新结束')
        # 已存在赛程文件
        files_exist = []
        exist_dir = self.scheJs_localPend_dir + '/exist/'
        if os.path.isdir(exist_dir):
            files_exist = fileUtil.dirFiles(exist_dir, [])
        for file in files_exist:
            print(file)
            self.upScheduleByFile(file, 1, updateTime_local)
            os.remove(file)
        print(getNowTime() + ' 已有赛程文件解析更新结束')
        LqNoteDao.update({'lastUpdateTime': getNowTime()}, {'task': 'schedule'})

    def up_partScore(self):
        print(getNowTime() + " 开始更新比分")
        now = datetime.now()
        time0 = now.strftime("%Y-%m-%d %H:%M:%S")
        # time1 = "'" + (now + timedelta(hours=-4)).strftime("%Y-%m-%d %H:%M:%S") + "'"

        # 采集任务未完成，且比赛状态完场或进行中，且比赛日期小于当前时间
        sql = " SELECT matchId, scheduleId, leagueId, matchState, matchTime FROM `lq_schedule` " \
              "WHERE  matchState >= -1 AND partscore_f in(0,1) AND matchTime <='{0}' " \
              "ORDER BY matchTime DESC".format(time0)
        matches = LqMatchDao.select(sql)
        print("采集比分比赛数量：{0}".format(len(matches)))
        for match in matches:
            matchState = match[3]
            condition = {'matchId': match[0]}
            zhiBoCrawler = ZhiBoCrawler(match[0], match[1])
            collect = zhiBoCrawler.qt_web_get()
            print(collect)
            if collect['state'] == 1:
                partScore = collect['partScore']['data']
                if matchState in (-1, -4):
                    partScore['partscore_f'] = 2
                if len(partScore) > 0:
                    # sql_util.upData('lq_schedule', partdict, condition)
                    LqMatchDao.update(partScore, condition)
        print(getNowTime() + " 比分更新成功")

    def upScheduleByFile(self, file, flag, updateTime_local):
        matchInfo = self.getMatchByJs(file)
        matchs = matchInfo['match']
        isFinished = 2
        for match in matchs:
            matchTime = datetime.strptime(match['matchTime'], "%Y-%m-%d %H:%M")
            between = (updateTime_local - matchTime).days
            if flag == 1 and between >= 4 and (match['matchState'] == -1 or match['matchState'] == -4):
                pass
            else:
                LqMatchDao.update(match, {'scheduleId': match['scheduleId']}, judge=True)
            if match['matchState'] not in [-1, -4]:
                isFinished = 1
        if isFinished == 2:
            ScheduleCrawDao.upScheCrawByFlag(file, isFinished)
        if 'playoffs' in matchInfo.keys():
            for item in matchInfo['playoffs']:
                LqPlayoffsDao.update(item, {'playoffsId': item['playoffsId']}, judge=True)
            print("季后赛信息更新结束")
        if 'cupGroup' in matchInfo.keys():
            for item in matchInfo['cupGroup']:
                LqCupGroupDao.update(item, {'cupQualifyId': item['cupQualifyId']}, judge=True)
            print("杯赛信息更新结束")

    def getMatchByJs(self, filePath):
        # matchList = []
        # 获取JS文件名
        filename = os.path.basename(filePath)
        # 联赛分类：l联赛或c杯赛
        kindType = filename[0]
        if kindType == 'l':
            arr = filename.split('_')
            matchKind = arr[1][0]
            # 联赛季前赛或常规赛赛程信息
            if matchKind == '3' or matchKind == '1':
                matchInfo = self.getNormMatchByJs(filePath)
            # 联赛季后赛赛程信息
            else:
                matchInfo = self.getOffMatchByJs(filePath)
        # 当前文件是杯赛赛程文件
        else:
            matchInfo = self.getCupMatchByJs(filePath)
        return matchInfo

    # 解析联赛【常规赛和季前赛】本地赛程JS文件，返回比赛列表，单场比赛基本信息以字典保存
    @staticmethod
    def getNormMatchByJs(filePath):
        context = js2pyUtil.jsLocjs(filePath)
        matchList = []
        if context == '':
            print("联赛JS文件为空：" + filePath)
        else:
            leagueInfo = context.arrLeague
            legueId = leagueInfo[0]
            leagueName = leagueInfo[7]
            teams = context.arrTeam
            # 获取team字典
            teamDict = team2dict(teams)
            # 获取JS文件赛程信息
            schedule = context.arrData
            matSeason = changeSeason(leagueInfo[4].replace(' ', ''))
            for match in schedule:
                matchDict = match2dict(match, teamDict)
                if matchDict != {}:
                    matchDict['leagueId'] = legueId
                    matchDict['leagueName'] = leagueName
                    matchDict['matchSeason'] = matSeason
                    matchList.append(matchDict)
        matchInfo = {'match': matchList}
        return matchInfo

    # 解析联赛【季后赛】本地赛程JS文件，返回比赛列表，单场比赛基本信息以字典保存
    @staticmethod
    def getOffMatchByJs(filePath):
        matchList = []
        groupArr = []
        context = js2pyUtil.jsLocjs(filePath)
        if context != '':
            leagueInfo = context.arrLeague
            leagueId = leagueInfo[0]
            leagueName = leagueInfo[7]
            matchSeason = changeSeason(leagueInfo[4].replace(' ', ''))
            teamList = context.arrTeam
            # 获取team字典
            teamDict = team2dict(teamList)
            # 获取季后赛列表
            playoffs = context.playoffsList
            if playoffs is not None:
                for i in range(0, len(playoffs)):
                    playoff = list(playoffs[i])
                    countRound = playoff[5]
                    if playoff[4] is False:
                        playoff[4] = 0
                    else:
                        playoff[4] = 1
                    pfKey = 'P' + str(playoff[0])
                    if context.pfData[pfKey] is not None:
                        items = context.pfData[pfKey]
                        # 多局分胜负
                        if countRound > 0:
                            for item in items:
                                matchs = item[4]
                                for match in matchs:
                                    matchDict = match2dict(match, teamDict)
                                    if matchDict != {}:
                                        matchDict['leagueId'] = leagueId
                                        matchDict['leagueName'] = leagueName
                                        matchDict['matchSeason'] = matchSeason
                                        matchDict['playoffsId'] = playoff[0]
                                        matchList.append(matchDict)
                        # 单局分胜负
                        else:
                            for item in items:
                                matchDict = match2dict(item, teamDict)
                                if matchDict != {}:
                                    matchDict['leagueId'] = leagueId
                                    matchDict['leagueName'] = leagueName
                                    matchDict['matchSeason'] = matchSeason
                                    matchDict['playoffsId'] = playoff[0]
                                    matchList.append(matchDict)

                    groupDict = {'playoffsId': playoff[0], 'name_J': playoff[1], 'name_F': playoff[2],
                                 'name_E': playoff[3], 'isCurrGroup': playoff[4], 'countRound': playoff[5],
                                 'leagueId': leagueId, 'season': matchSeason, 'numberSort': i+1}
                    groupArr.append(groupDict)
        matchInfo = {'match': matchList}
        if len(groupArr) > 0:
            matchInfo['playoffs'] = groupArr
        return matchInfo

    # 解析【杯赛】赛程JS文件，返回比赛列表，单场比赛基本信息以字典保存
    @staticmethod
    def getCupMatchByJs(filePath):
        matchList = []
        cupArr = []
        context = js2pyUtil.jsLocjs(filePath)
        if context != '':
            leagueInfo = context.arrLeague
            teamlist = context.arrTeam
            # 获取team字典
            teamdict = team2dict(teamlist)
            # 获取杯赛分类列表
            arrQualify = context.arrQualify
            for i in range(len(arrQualify)):
                qualify = list(arrQualify[i])
                groupNum = 0
                cupqualifyid = qualify[0]
                leagueId = leagueInfo[0]
                leagueName = leagueInfo[7]
                isGroup = qualify[4]
                season = changeSeason(leagueInfo[4].replace(' ', ''))
                # 局数
                if len(qualify) > 6:
                    countround = qualify[6]
                else:
                    qualify.append(0)
                    countround = 0
                # 赛程分类有分小组（一级 + 二级）
                if isGroup:
                    qualifyKey = 'GH' + str(cupqualifyid)
                    if context.jh[qualifyKey] is not None:
                        groups = context.jh[qualifyKey]
                        groupNum = len(groups)
                        for group in groups:
                            groupKey = 'G' + str(cupqualifyid) + '_' + str(group[1])
                            groupMatchs = context.jh[groupKey]
                            for match in groupMatchs:
                                matchdict = match2dict(match, teamdict)
                                # 关键信息缺少返回空字典
                                if matchdict != {}:
                                    matchdict['leagueId'] = leagueId
                                    matchdict['leagueName'] = leagueName
                                    matchdict['matchSeason'] = season
                                    matchdict['cupqualifyId'] = cupqualifyid
                                    matchdict['groupId'] = group[1]
                                    matchList.append(matchdict)
                # 无分组（一级）
                else:
                    qualifyKey = 'Q' + str(cupqualifyid)
                    matchsData = context.jh[qualifyKey]
                    # 多局分胜负
                    if countround > 0:
                        for data in matchsData:
                            matchs = data[4]
                            for match in matchs:
                                matchdict = match2dict(match, teamdict)
                                if matchdict != {}:
                                    matchdict['leagueId'] = leagueId
                                    matchdict['leagueName'] = leagueName
                                    matchdict['matchSeason'] = season
                                    matchdict['cupqualifyId'] = cupqualifyid
                                    matchList.append(matchdict)
                    # 一局定胜负
                    else:
                        for match in matchsData:
                            matchdict = match2dict(match, teamdict)
                            if matchdict != {}:
                                matchdict['leagueId'] = leagueId
                                matchdict['leagueName'] = leagueName
                                matchdict['matchSeason'] = season
                                matchdict['cupqualifyId'] = cupqualifyid
                                matchList.append(matchdict)

                if qualify[4] is False:
                    qualify[4] = 0
                else:
                    qualify[4] = 1

                if qualify[5] is False:
                    qualify[5] = 0
                else:
                    qualify[5] = 1
                if len(qualify) == 7:
                    groupDict = {'cupQualifyId': qualify[0], 'name_J': qualify[1], 'name_F': qualify[2],
                                 'name_E': qualify[3], 'isGroup': qualify[4], 'isCurrGroup': qualify[5],
                                 'countRound': qualify[6], 'leagueId': leagueId, 'season': season,
                                 'numberSort': i+1, 'groupNum': groupNum}
                    cupArr.append(groupDict)
        matchInfo = {'match': matchList}
        if len(cupArr) > 0:
            matchInfo['cupGroup'] = cupArr
        return matchInfo


# 比赛列表消息转字典
def match2dict(matchData, teamDict):
    matchDict = {'scheduleId': matchData[0], 'matchKind': matchData[1], 'matchTime': matchData[2],
                 'homeTeamId': matchData[3], 'awayTeamId': matchData[4]}
    if matchData[3] in teamDict:
        matchDict['homeTeam'] = teamDict[matchData[3]]
    else:
        # print("主队名称不存在")
        return {}
    if matchData[4] in teamDict:
        matchDict['awayTeam'] = teamDict[matchData[4]]
    else:
        return {}
    matchDict['matchState'] = matchData[9]
    if matchData[5] is not None and matchData[5] != '':
        matchDict['homeScore'] = matchData[5]
    if matchData[6] is not None and matchData[6] != '':
        matchDict['awayScore'] = matchData[6]
    if matchData[7] is not None and matchData[7] != '':
        matchDict['homeHalf'] = matchData[7]
    if matchData[8] is not None and matchData[8] != '':
        matchDict['awayHalf'] = matchData[8]
    if matchData[10] is not None and matchData[10] != '':
        matchDict['goal'] = matchData[10]
    if matchData[11] is not None and matchData[11] != '':
        matchDict['total'] = matchData[11]
    # 比赛已完场获取小节和加时比分
    # if matchdata[9] == -1:
    #     quarterdict = collect.parshtml.PartScore.get_PartScore(matchdata[0])
    #     matchdict = formate(matchdict, **quarterdict)
    # else:
    #     pass
    return matchDict


# 赛季格式转换 2019-2020 调整为 19-20
def changeSeason(season):
    if len(season) == 9:
        years = season.split('-')
        newSeason = years[0][2:] + '-' + years[1][2:]
    elif len(season) == 4:
        newSeason = season[2:]
    else:
        newSeason = season
    return newSeason


# 球队列表信息转为字典：球队Id/球队简称
def team2dict(teams):
    team_dict = {}
    for team in teams:
        team_dict[team[0]] = team[4]
    return team_dict

