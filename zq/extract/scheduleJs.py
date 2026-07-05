import os
import traceback
from pathlib import Path

import utils.fileUtil
import utils.js2pyUtil
from config import common_config, zqconfig_qt
from utils import fileUtil


def getSche(filePath):
    mdictList = []
    # 获取JS文件名
    filename = os.path.basename(filePath)
    # 联赛分类：l联赛或c杯赛
    kindType = filename[0]
    # 联赛赛程文件
    if os.path.exists(filePath):
        if kindType == 's':
            data = filename.split(('_'))
            if len(data) > 1:
                mdictList = getSubsche(filePath)
            # 联赛无子联赛
            else:
                mdictList = getleagsche(filePath)
        # 杯赛赛程文件
        elif kindType == 'c':
            mdictList = getCupsche(filePath)
        else:
            mdictList = ['fail', []]
    else:
        mdictList = ['fail', []]
    return mdictList


def getleagsche(filePath):
    mdictList = []
    # flag = 'fail'
    try:
        context = utils.js2pyUtil.jsLocjs(filePath)
        teamdict = dict_teaminfo(context.arrTeam)
        matchSeason = _match_season_from_path(filePath)
        arrLeague = context.arrLeague
        totalRound = arrLeague[7]
        for i in range(1, totalRound + 1):
            key = "R_" + str(i)
            matchlist = context.jh[key]
            for match in matchlist:
                matchdict = dict_matchinfo(match, teamdict)
                matchdict['matchSeason'] = matchSeason
                matchdict['Round'] = i
                mdictList.append(matchdict)
        flag = 'suc'
    except Exception as e:
        print(e)
        detail = traceback.format_exc()
        fileUtil.logLine(common_config.exception, ['schejs.getLeagesche()', [filePath], detail])
        fileUtil.logLine(common_config.zq_extract_e, ['schejs.getleagsche', filePath, str(e)])
        # print(filePath)
        # print(detail)
        flag = 'fail'
    # else:
    #     flag = 'suc'
    return [flag, mdictList]


def getSubsche(filePath):
    mdicList = []
    filename = os.path.basename(filePath)
    # flag = 'fail'
    try:
        context = utils.js2pyUtil.jsLocjs(filePath)
        teamdict = dict_teaminfo(context.arrTeam)
        matchSeason = _match_season_from_path(filePath)
        subdict = {}
        subLeagueID = filename.split(".")[-2].split('_')[-1]
        subs = context.arrSubLeague
        for sub in subs:
            subdict[str(sub[0])] = sub
        round = subdict[str(subLeagueID)][5]
        if(len(subdict[str(subLeagueID)])) > 7:
            multiRound = subdict[str(subLeagueID)][7]
        else:
            multiRound = 0
        if round > 0:
            for i in range(1, round + 1):
                key = "R_" + str(i)
                # 子联赛：分组多场决胜负，即2队至少打2场比赛
                if multiRound == 1:
                    # multiRound = subdict[str(subLeagueID)][7]
                    matchArr = context.jh[key]
                    for item in matchArr:
                        for j in range(4, len(item)):
                            match = item[j]
                            matchdict = dict_matchinfo(match, teamdict)
                            matchdict['matchSeason'] = matchSeason
                            matchdict['Round'] = i
                            matchdict['subLeagueID'] = subLeagueID
                            mdicList.append(matchdict)
                # 常规子联赛
                else:
                    matchlist = context.jh[key]
                    for match in matchlist:
                        matchdict = {}
                        matchdict = dict_matchinfo(match, teamdict)
                        matchdict['matchSeason'] = matchSeason
                        matchdict['Round'] = i
                        matchdict['subLeagueID'] = subLeagueID
                        mdicList.append(matchdict)
        flag = 'suc'
    except Exception as e:
        print(filePath)
        print(e)
        detail = traceback.format_exc()
        # print(detail)
        fileUtil.logLine(common_config.exception, ['schejs.getSubsche()', [filePath], detail])
        flag = 'fail'
        fileUtil.logLine(common_config.zq_extract_e, ['schejs.getSubsche', filePath, str(e)])
    # else:
    #     flag = 'suc'
    return [flag, mdicList]


def getCupsche(filePath):
    mdicList = []
    # flag = 'fail'
    try:
        context = utils.js2pyUtil.jsLocjs(filePath)
        teamdict = dict_teaminfo(context.arrTeam)
        matchSeason = _match_season_from_path(filePath)
        groupdict = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E', '6': 'F', '7': 'G', '8': 'H', '9': 'I',
                     '10': 'J',
                     '11': 'K',
                     '12': 'L', '13': 'M', '14': 'N', '15': 'O', '16': 'P', '17': 'Q', '18': 'R', '19': 'S', '20': 'T',
                     '21': 'U',
                     '22': 'V', '23': 'W', '24': 'X', '25': 'Y', '26': 'Z'}

        if context.arrCupKind:
            for cupkind in context.arrCupKind:
                cupkindId = cupkind[0]
                groupnum = cupkind[5]
                if groupnum == 0:
                    key = "G" + str(cupkindId)
                    # 无分组非多场决胜负
                    # print(matchdict)
                    # 无分组 多场决胜负
                    if len(cupkind) == 8 and cupkind[7] == 1:
                        for i in range(0, len(context.jh[key])):
                            for j in range(4, len(context.jh[key][i])):
                                match = context.jh[key][i][j]
                                matchdict = dict_matchinfo(match, teamdict)
                                matchdict['matchSeason'] = matchSeason
                                matchdict['Grouping'] = cupkind[2]
                                matchdict['groupingId'] = cupkind[0]
                                mdicList.append(matchdict)
                    else:
                        matchlist = context.jh[key]
                        if matchlist is None:
                            print(key)
                        for match in matchlist:
                            matchdict = dict_matchinfo(match, teamdict)
                            matchdict['matchSeason'] = matchSeason
                            matchdict['Grouping'] = cupkind[2]
                            matchdict['groupingId'] = cupkind[0]
                            mdicList.append(matchdict)
                else:
                    for i in range(1, groupnum + 1):
                        key = "G" + str(cupkindId) + groupdict[str(i)]
                        matchlist = context.jh[key]
                        if matchlist is None:
                            matchlist = []
                        for match in matchlist:
                            matchdict = dict_matchinfo(match, teamdict)
                            matchdict['matchSeason'] = matchSeason
                            matchdict['Grouping'] = cupkind[2]
                            matchdict['groupingId'] = cupkind[0]
                            matchdict['grouping2'] = groupdict[str(i)]
                            mdicList.append(matchdict)
        flag = 'suc'
    except Exception as e:
        print(e)
        detail = traceback.format_exc()
        # print(detail)
        fileUtil.logLine(common_config.exception, ['schejs.getCupsche()', [filePath], detail])
        fileUtil.logLine(common_config.zq_extract_e, ['schejs.getCupsche', filePath, str(e)])
        flag = 'fail'
    # else:
    #     flag = 'suc'
    return [flag, mdicList]


def dict_matchinfo(datalist, teamdict):
    matchdict = {}
    # [1720912,36,-1,'2019-08-10 03:00',25,34,'4-1','4-0','2','英冠1',2.25,1,'3/3.5','1/1.5',1,1,1,1,0,0,'','2','ENG LCH-1'],
    # ['ScheduleID','LeagueID','MatchState','MatchTime','HomeTeamID','AwayTeamID','全场比分','半场比分',
    #  'Home_order','Away_order','让分全场初盘','让分半场初盘','大小全场初盘','大小半场输盘','析','欧','亚','大',
    #  'Home_Red','Away_Red','','主队排名','客队排名']
    try:
        matchdict['ScheduleID'] = datalist[0]
        matchdict['LeagueID'] = datalist[1]
        matchdict['MatchState'] = datalist[2]
        matchdict['MatchTime'] = datalist[3]
        matchdict['HomeTeamID'] = datalist[4]
        matchdict['AwayTeamID'] = datalist[5]
        matchdict['HomeTeam'] = teamdict[str(datalist[4])]
        matchdict['AwayTeam'] = teamdict[str(datalist[5])]
        if datalist[6] != '' and len(datalist[6].split('-')) > 1:
            if datalist[6].split('-')[0] != '':
                matchdict['HomeScore'] = datalist[6].split('-')[0]
            if datalist[6].split('-')[1] != '':
                matchdict['AwayScore'] = datalist[6].split('-')[1]
        if datalist[7] != '' and len(datalist[7].split('-')) > 1:
            if datalist[7].split('-')[0] != '':
                matchdict['HomeHalf'] = datalist[7].split('-')[0]
            if datalist[7].split('-')[1] != '':
                matchdict['AwayHalf'] = datalist[7].split('-')[1]
        if datalist[8] != "":
            matchdict['Home_order'] = datalist[8]
        if datalist[9] != "" and datalist[9] is not None:
            matchdict['Away_order'] = datalist[9]
        if datalist[10] != "" and datalist[10] is not None:
            matchdict['goal'] = datalist[10]
        if datalist[11] != "" and datalist[11] is not None:
            matchdict['goalhalf'] = datalist[11]
        if datalist[12] != "" and datalist[12] is not None:
            matchdict['total'] = form_total_handicap(datalist[12])
        if datalist[13] != "" and datalist[13] is not None:
            matchdict['totalhalf'] = form_total_handicap(datalist[13])
        matchdict['Home_Red'] = datalist[18]
        matchdict['Away_Red'] = datalist[19]
        if datalist[20] != '' and len(datalist[20]) < 100:
            matchdict['remark'] = datalist[20]
    except Exception as e:
        print(e)
        # print(traceback.format_exc())
    return matchdict


def dict_teaminfo(teamlist):
    dict = {}
    for team in teamlist:
        dict[str(team[0])] = team[1]
    return dict


def _match_season_from_path(filePath):
    return Path(filePath).parent.name


def amend_schejs():
    filepathList = utils.fileUtil.dirFiles(zqconfig_qt.schelocaldir, [])
    content = "var jh = new Object();" + "\n"
    if len(filepathList) > 0:
        for filepath in filepathList:
            try:
                with open(filepath, 'r+', encoding="utf-8") as fo:
                    old = fo.read()
                    fo.seek(0)
                    fo.write(content)
                    fo.write(old)
                    fo.close()
            except Exception as e:
                # print(e)
                detail = traceback.format_exc()
                fileUtil.logLine(common_config.exception, ['schejs.amend_schejs', [], detail])
                fileUtil.logLine(common_config.fileread_e, [filepath])


def del_errorschejs():
    filepathList = fileUtil.dirFiles(zqconfig_qt.schelocaldir, [])
    for filepath in filepathList:
        fileUtil.del_error_file(filepath)


def form_total_handicap(hcap):
    if len(hcap.split('/')) < 2:
        hcap2 = float(hcap)
    else:
        hcap2 = float(hcap.split('/')[0]) + 0.25
    return hcap2


def amend_schejs_byfile(filepath):
    content = "var jh = new Object();" + "\n"
    try:
        with open(filepath, 'r+', encoding="utf-8") as fo:
            old = fo.read()
            fo.seek(0)
            fo.write(content)
            fo.write(old)
            fo.close()
    except Exception as e:
        detail = traceback.format_exc()
        fileUtil.logLine(common_config.exception, ['schejs.amend_schejs_byfile', [filepath], detail])
        fileUtil.logLine(common_config.fileread_e, [filepath])



# if __name__ == '__main__':
#
#     # datalist = [49467, 12807, 2, 3, [2500129, 847, -1, '2023-11-16 09:05', 49467, 12807, '2-1', '2-1', '7', '2', 0.5, 0.25, '2.5/3', '1', 1, 1, 1, 1, 0, 0, '', '7', '2'], [2500133, 847, -1, '2023-11-19 09:05', 12807, 49467, '2-0', '2-0', '2', '7', 0.25, 0.25, '2.5/3', '1/1.5', 1, 1, 1, 1, 0, 0, '', '2', '7']]
#     # teamdict = {'10078': 'FC美利达', '12807': '哥达拿查拉大学', '1337': '亚特兰特', '23242': '扎卡特卡斯', '25079': '西玛罗雷斯索诺拉', '29865': '坎昆FC', '30569': '帕蒂特兰德莫雷洛斯', '49467': '莫雷利亚'}
#     # dict_matchinfo(datalist,teamdict)
#
#     matchArr = [[49467, 12807, 2, 3, [2500129, 847, -1, '2023-11-16 09:05', 49467, 12807, '2-1', '2-1', '7', '2', 0.5, 0.25, '2.5/3', '1', 1, 1, 1, 1, 0, 0, '', '7', '2'], [2500133, 847, -1, '2023-11-19 09:05', 12807, 49467, '2-0', '2-0', '2', '7', 0.25, 0.25, '2.5/3', '1/1.5', 1, 1, 1, 1, 0, 0, '', '2', '7']], [25079, 1337, 4, 4, [2500130, 847, -1, '2023-11-16 11:05', 25079, 1337, '2-0', '1-0', '6', '3', 0, 0, '2/2.5', '1', 1, 1, 1, 1, 0, 0, '', '6', '3'], [2500134, 847, -1, '2023-11-19 07:05', 1337, 25079, '4-2', '1-1', '3', '6', 0.75, 0.25, '2.5', '1', 1, 1, 1, 1, 0, 1, '', '3', '6']], [30569, 23242, 2, 7, [2500131, 847, -1, '2023-11-17 09:05', 30569, 23242, '0-2', '0-1', '5', '4', 0.25, 0, '2.5/3', '1', 1, 1, 1, 1, 0, 0, '', '5', '4'], [2500135, 847, -1, '2023-11-20 09:05', 23242, 30569, '5-2', '2-0', '4', '5', 0.75, 0.25, '3', '1/1.5', 1, 1, 1, 1, 0, 0, '', '4', '5']], [10078, 29865, 2, 2, [2500128, 847, -1, '2023-11-17 11:05', 10078, 29865, '1-0', '0-0', '8', '1', 0.25, 0.25, '2.5', '1', 1, 1, 1, 1, 0, 0, '', '8', '1'], [2500132, 847, -1, '2023-11-20 07:05', 29865, 10078, '2-1', '0-0', '1', '8', 0.5, 0.25, '2.5/3', '1/1.5', 1, 1, 1, 1, 0, 0, '', '1', '8']]]
#     for item in matchArr:
#         for i in range(4,len(item)):
#             print(item[i])
