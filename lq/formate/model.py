# 比赛列表消息转字典
def match(matchData, teamDict):
    matchDict = {'scheduleID': matchData[0], 'matchKind': matchData[1], 'matchTime': matchData[2],
                 'homeTeamID': matchData[3], 'awayTeamID': matchData[4]}
    if matchData[3] in teamDict:
        matchDict['homeTeam'] = teamDict[matchData[3]]
    else:
        # print("主队名称不存在")
        return {}
    if matchData[4] in teamDict:
        matchDict['awayTeam'] = teamDict[matchData[4]]
    else:
        # print("客队名称不存在")
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
def teamDict(teamlist):
    team_dict = {}
    for team in teamlist:
        team_dict[team[0]] = team[4]
    return team_dict
