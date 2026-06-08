import os
import utils.fileUtil
import utils.js2pyUtil
from lq.formate import model


# 按照【文件列表】解析赛程JS文件获取 【获取赛事信息列表】，单场比赛基本信息以字典保存
def getMatchFromFile(filePath):
    matchList = []
    # 获取JS文件名
    filename = os.path.basename(filePath)
    # 联赛分类：l联赛或c杯赛
    kindType = filename[0]
    if kindType == 'l':
        data = filename.split('_')
        matchkind = data[1][0]
        # 联赛季前赛或常规赛赛程信息
        if matchkind == '3' or matchkind == '1':
            matchList = getMatchByjs(filePath)
        # 联赛季后赛赛程信息
        elif matchkind == '2':
            matchList = getOffMatchByjs(filePath)
        else:
            print("联赛比赛类型解析异常：" + filePath)
    # 当前文件是杯赛赛程文件
    elif kindType == 'c':
        matchList = getCupMatchByjs(filePath)
    else:
        print('异常赛程JS文件：' + filePath)
    return matchList


# 解析联赛【常规赛和季前赛】本地赛程JS文件，返回比赛列表，单场比赛基本信息以字典保存
def getMatchByjs(filePath):
    context = utils.js2pyUtil.jsLocjs(filePath)
    matchlist = []
    if context == '':
        print("联赛JS文件为空：" + filePath)
    else:
        leagueInfo = context.arrLeague
        teamlist = context.arrTeam
        # 获取team字典
        teamdict = model.teamDict(teamlist)
        # 获取JS文件赛程信息
        schedule = context.arrData
        for match in schedule:
            matseason = model.changeSeason(leagueInfo[4].replace(' ', ''))
            matchdict = model.match(match, teamdict)
            if matchdict == {}:
                pass
                # print("比赛基本信息不完整：" + filePath)
                # print(match)
            else:
                matchdict['leagueID'] = leagueInfo[0]
                matchdict['leagueName'] = leagueInfo[7]
                matchdict['matchSeason'] = matseason
                matchlist.append(matchdict)
    return matchlist


# 解析联赛【季后赛】本地赛程JS文件，返回比赛列表，单场比赛基本信息以字典保存
def getOffMatchByjs(filePath):
    matchlist = []
    context = utils.js2pyUtil.jsLocjs(filePath)
    if context == '':
        print("联赛季后赛JS文件为空：" + filePath)
    else:
        leagueInfo = context.arrLeague
        matseason = model.changeSeason(leagueInfo[4].replace(' ', ''))
        teamlist = context.arrTeam
        # 获取team字典
        teamdict = model.teamDict(teamlist)
        # 获取季后赛列表
        playoffs = context.playoffsList
        for playoff in playoffs:
            # 局数
            countround = playoff[5]
            pfkey = 'P' + str(playoff[0])
            if context.pfData[pfkey] is None:
                pass
            else:
                matchsData = context.pfData[pfkey]
                # 多局分胜负
                if countround > 0:
                    for data in matchsData:
                        matchs = data[4]
                        for match in matchs:
                            matchdict = model.match(match, teamdict)
                            if matchdict == {}:
                                pass
                                # print("比赛基本信息不完整:" + filePath)
                                # print(match)
                            else:
                                matchdict['leagueID'] = leagueInfo[0]
                                matchdict['leagueName'] = leagueInfo[7]
                                matchdict['matchSeason'] = matseason
                                matchdict['playoffsID'] = playoff[0]
                                matchlist.append(matchdict)
                # 单局分胜负
                else:
                    for match in matchsData:
                        matchdict = model.match(match, teamdict)
                        if matchdict == {}:
                            pass
                            # print("比赛基本信息不完整 " + filePath)
                            # print(match)
                        else:
                            matchdict['leagueID'] = leagueInfo[0]
                            matchdict['leagueName'] = leagueInfo[7]
                            matchdict['matchSeason'] = matseason
                            matchdict['playoffsID'] = playoff[0]
                            matchlist.append(matchdict)

    return matchlist


# 解析【杯赛】赛程JS文件，返回比赛列表，单场比赛基本信息以字典保存
def getCupMatchByjs(filePath):
    matchlist = []
    context = utils.js2pyUtil.jsLocjs(filePath)
    if context == '':
        print("杯赛JS文件为空：" + filePath)
    else:
        leagueInfo = context.arrLeague
        teamlist = context.arrTeam
        # 获取team字典
        teamdict = model.teamDict(teamlist)
        # 获取杯赛分类列表
        qualifylist = context.arrQualify
        for qualify in qualifylist:
            countround = -1
            cupqualifyid = qualify[0]
            # 局数
            while len(qualify) > 6:
                countround = qualify[6]
                break
            isGroup = qualify[4]
            matseason = model.changeSeason(leagueInfo[4].replace(' ', ''))
            # 赛程分类有分小组（一级 + 二级）
            if isGroup == True:
                qualifykey = 'GH' + str(cupqualifyid)
                if context.jh[qualifykey] is None:
                    pass
                    # print("分组无二级分组信息")
                else:
                    grouplist = context.jh[qualifykey]
                    for group in grouplist:
                        groupkey = 'G' + str(cupqualifyid) + '_' + str(group[1])
                        groupmatchs = context.jh[groupkey]
                        for match in groupmatchs:
                            matchdict = model.match(match, teamdict)
                            # 关键信息缺少返回空字典
                            if matchdict != {}:
                                matchdict['leagueID'] = leagueInfo[0]
                                matchdict['leagueName'] = leagueInfo[7]
                                matchdict['matchSeason'] = matseason
                                matchdict['cupqualifyID'] = cupqualifyid
                                matchdict['groupID'] = group[1]
                                matchlist.append(matchdict)
            # 无分组（一级）
            else:
                qualifykey = 'Q' + str(cupqualifyid)
                matchsData = context.jh[qualifykey]
                # 多局分胜负
                if countround > 0:
                    for data in matchsData:
                        matchs = data[4]
                        for match in matchs:
                            matchdict = model.match(match, teamdict)
                            if matchdict == {}:
                                pass
                                # print("比赛基本信息不完整 "+ filePath)
                                # print(match)
                            else:
                                matchdict['leagueID'] = leagueInfo[0]
                                matchdict['leagueName'] = leagueInfo[7]
                                matchdict['matchSeason'] = matseason
                                matchdict['cupqualifyID'] = cupqualifyid
                                matchlist.append(matchdict)
                # 一局定胜负
                else:
                    for match in matchsData:
                        matchdict = model.match(match, teamdict)
                        if matchdict != {}:
                            matchdict['leagueID'] = leagueInfo[0]
                            matchdict['leagueName'] = leagueInfo[7]
                            matchdict['matchSeason'] = matseason
                            matchdict['cupqualifyID'] = cupqualifyid
                            matchlist.append(matchdict)
    return matchlist
