import json

from pymemcache.client.base import Client

from utils import sql_util

matchvalue = ['scheduleID', 'leagueID', 'MatchSeason', 'MatchKind', 'HomeTeam', 'GuestTeam', 'MatchTime', 'MatchState',
              'HomeScore', 'GuestScore', 'HomeHalf', 'GuestHalf']
asianvalue = ['ScheduleID', 'CompanyID', 'HomeOdds_F', 'AsianOdds_F', 'GuestOdds_F',
            'HomeOdds', 'AsianOdds', 'GuestOdds', 'ModifyTime']
totalvalue = ['ScheduleID', 'CompanyID', 'HighOdds_F', 'totalscore_F', 'LowOdds_F',
              'HighOdds', 'totalscore', 'LowOdds', 'ModifyTime']


def collectChance():
    client = Client(('localhost', 11211))
    matchsdict = json.loads(client.get('insmatch').decode())
    for match in matchsdict['ongoing'].items:
        print("符合条件")
        # while evaluateChance1(match):
        #     recom = {}
        #     # 比赛ID
        #     recom['ScheduleID'] =match[1]['ID']
        #     # 运动种类
        #     recom['Kind'] = 2
        #     # 玩法
        #     recom['Tricks'] = 4
        #     # 推荐项
        #     recom['Option'] =
        #     # 赔率
        #     recom['Odds'] =
        #     # 让分
        #     recom['AsianOdds'] = match[1]['AsianOdds']
        #     # 声音提示
        #     playsound(config.chance_sound)
        #     break

    # 查看即时比分和即时赔率

    # 判断是否符合入场条件

    # 如符合记录即时比分和推荐内容

    # 发出机会通知

    # 比赛结束，判断结果


def evalPrechance(homeid, awayid):
    # 总冠军，联盟冠军
    early_homesql = "select TeamID,leagueID,LeagueOdds,ZoneOdds,UpdateTime FROM lq_earlyodds " \
                    "WHERE TeamID=" + str(homeid) + " ORDER BY ID DESC LIMIT 1"
    early_awaysql = "select TeamID,leagueID,LeagueOdds,ZoneOdds,UpdateTime FROM lq_earlyodds " \
                     "WHERE TeamID=" + str(awayid) + " ORDER BY ID DESC LIMIT 1"
    earlyodds_home = sql_util.select(early_homesql)
    earlyodds_away = sql_util.select(early_awaysql)
    info_home = sql_util.select("select ID,Name_JS,LocationID,MatchAddrID FROM lq_team where ID=" + str(homeid))
    info_away = sql_util.select("select ID,Name_JS,LocationID,MatchAddrID FROM lq_team where ID=" + str(awayid))
    print(earlyodds_home)
    print(earlyodds_away)
    print(info_home)
    print(info_away)

    # 最近15场比赛
    base_sql = "SELECT scheduleID,leagueID,MatchSeason,MatchKind,MatchTime,MatchState,HomeTeamID,GuestTeamID,HomeTeam,GuestTeam," \
               "HomeScore,GuestScore,HomeHalf,GuestHalf," \
               "asian.HomeOdds_F,asian.Goal_F,asian.GuestOdds_F,asian.HomeOdds,asian.Goal,asian.GuestOdds," \
               "tot.HighOdds_F,tot.totalscore_F,tot.LowOdds_F,tot.HighOdds,tot.totalscore,tot.LowOdds," \
               "HomeOne,GuestOne,HomeTwo,GuestTwo,HomeThree,GuestThree,HomeFour,GuestFour " \
               "FROM `lq_schedule` as sche " \
               "left join lq_AsianOdds as asian on sche.ID = asian.ScheduleID left join lq_totalodds as tot on sche.scheduleID = tot.ScheduleID " \
               "WHERE leagueID=1 and MatchSeason='19-20' and MatchState=-1 and asian.CompanyID=8 "
    recent_homesql = base_sql + "and (HomeTeamID= " + str(homeid) + " or GuestTeamID=" + str(
        homeid) + ") ORDER BY MatchTime DESC LIMIT 15"
    recent_awaysql = base_sql + "and (HomeTeamID= " + str(homeid) + " or GuestTeamID=" + str(
        homeid) + ") ORDER BY MatchTime DESC LIMIT 15"
    recent_home = sql_util.select(recent_homesql)
    recent_away = sql_util.select(recent_awaysql)

    print(recent_home)
    print(recent_away)


def evalPerform(matchid):
    # 22项
    mfield = ['scheduleID', 'leagueID', 'MatchSeason', 'MatchKind', 'MatchTime', 'MatchState', 'HomeTeamID',
              'GuestTeamID',
              'HomeTeam', 'GuestTeam', 'HomeScore', 'GuestScore', 'HomeHalf', 'GuestHalf', 'HomeOne', 'GuestOne',
              'HomeTwo', 'GuestTwo', 'HomeThree', 'GuestThree', 'HomeFour', 'GuestFour',
              'asian.HomeOdds_F', 'asian.AsianOdds_F', 'asian.GuestOdds_F', 'asian.HomeOdds', 'asian.AsianOdds', 'asian.GuestOdds',
              'tot.HighOdds_F', 'tot.totalscore_F', 'tot.LowOdds_F', ' tot.HighOdds', 'tot.totalscore', 'tot.LowOdds'
              ]
    ldfield = ['ld.HomeScore', 'ld.GuestScore', 'ld.HomeOdds', 'ld.AsianOdds', 'ld.GuestOdds', 'ld.IsBet', 'ld.OddsType',
               'ld.ModifyTime', 'ld.State', 'ld.RemainTime']
    # matchfield = "scheduleID,leagueID,MatchSeason,MatchKind,MatchTime,MatchState,HomeTeamID,GuestTeamID,HomeTeam,GuestTeam," \
    #              "HomeScore,GuestScore,HomeHalf,GuestHalf,HomeOne,GuestOne,HomeTwo,GuestTwo,HomeThree,GuestThree,HomeFour,GuestFour"
    # 6项
    # asianfield = "asian.HomeOdds_F,asian.AsianOdds_F,asian.GuestOdds_F,asian.HomeOdds,asian.AsianOdds,asian.GuestOdds"
    # totalfield = "tot.HighOdds_F,tot.totalscore_F,tot.LowOdds_F, tot.HighOdds,tot.totalscore,tot.LowOdds"
    # ldfield = "ld.HomeScore,ld.GuestScore,ld.HomeOdds,ld.AsianOdds,ld.GuestOdds,ld.IsBet,ld.OddsType,ld.ModifyTime,ld.State,ld.RemainTime"
    # ------------------比赛信息------------------
    match_sql = "SELECT " + ",".join(mfield) + \
                " FROM `lq_schedule` as sche left join lq_AsianOdds as asian on sche.scheduleID = asian.ScheduleID" \
                " left join lq_totalodds as tot on asian.ScheduleID = tot.ScheduleID" \
                " WHERE scheduleID=" + str(matchid) + " and asian.CompanyID=8 and tot.CompanyID=8"
    asian_sql = "SELECT asian.ScheduleID," + ",".join(ldfield) + \
              " FROM `lq_AsianOdds` as asian left join lq_AsianOddsdetail as ld on asian.OddsID= ld.OddsID " \
              " WHERE asian.ScheduleID=" + str(matchid) + " and asian.CompanyID=8 and OddsType=2 ORDER BY ld.ID ASC"
    # 比赛基本数据
    match_info = sql_util.select(match_sql)
    # 滚球让分变化记录
    match_asian = sql_util.select(asian_sql)
    # 主队ID
    homeid = match_info[0][6]
    hometeam = match_info[0][8]
    # 客队ID
    awayid = match_info[0][7]
    awayteam = match_info[0][9]
    # print(match_info[0][4])
    matchtime = match_info[0][4]
    # 主队基本信息
    info_home = sql_util.select("select ID,Name_JS,LocationID,MatchAddrID FROM lq_team where ID=" + str(homeid))
    print(hometeam + " 主队基本信息：")
    print(info_home)
    # 客队基本信息
    info_away = sql_util.select("select ID,Name_JS,LocationID,MatchAddrID FROM lq_team where ID=" + str(awayid))
    print(awayteam + " 客队基本信息：")
    print(info_away)

    # ------------- 早期投注 --------------
    early_homesql = "select TeamID,leagueID,ChampOdds,LeagueOdds,ZoneOdds,UpdateTime FROM lq_earlyodds " \
                    "WHERE TeamID=" + str(homeid) + " ORDER BY ID DESC LIMIT 1"
    early_awaysql = "select TeamID,leagueID,ChampOdds,LeagueOdds,ZoneOdds,UpdateTime FROM lq_earlyodds " \
                     "WHERE TeamID=" + str(awayid) + " ORDER BY ID DESC LIMIT 1"
    # 主队早期投注赔率
    earlyodds_home = sql_util.select(early_homesql)
    print(hometeam + " 主队早期赔率：")
    print(earlyodds_home)
    # 客队早期投注赔率
    earlyodds_away = sql_util.select(early_awaysql)
    print(awayteam + " 客队早期赔率：")
    print(earlyodds_away)

    # -------------- 球队过去15场比赛 --------------
    print("主队：" + hometeam + " 过去15场比赛：")
    print(matchtime)
    homematchs = recentMatch(homeid, matchtime)
    print(homematchs)
    print("客队：" + awayteam + " 过去15场比赛：")
    awaymatchs = recentMatch(awayid, matchtime)
    print(awaymatchs)
    # ----------------- 主队每场比赛对手信息--------------
    print("\n主队：" + hometeam + " 每场比赛赛前信息")
    for match in homematchs:
        print(match)
        print("--------------双方近期比赛------------")
        print("球队：")
        print(recentMatch(match[13], match[1]))
        print("对手：")
        print(recentMatch(match[14], match[1]))
        print(" -------------------------- \n")
    print("\n客队：" + awayteam + " 每场比赛赛前信息")
    for match in awaymatchs:
        print(match)
        print("------------双方近期比赛--------------")
        print("球队：")
        print(recentMatch(match[13], match[1]))
        print("对手：")
        print(recentMatch(match[14], match[1]))
        print("---------------------------------------\n")


def recentMatch(teamid, matchtime):
    matchs = []
    mfield = ['scheduleID', 'leagueID', 'MatchSeason', 'MatchKind', 'MatchTime', 'MatchState', 'HomeTeamID',
              'GuestTeamID',
              'HomeTeam', 'GuestTeam', 'HomeScore', 'GuestScore', 'HomeHalf', 'GuestHalf', 'HomeOne', 'GuestOne',
              'HomeTwo', 'GuestTwo', 'HomeThree', 'GuestThree', 'HomeFour', 'GuestFour',
              'asian.HomeOdds_F', 'asian.AsianOdds_F', 'asian.GuestOdds_F', 'asian.HomeOdds', 'asian.AsianOdds', 'asian.GuestOdds',
              'tot.HighOdds_F', 'tot.totalscore_F', 'tot.LowOdds_F', ' tot.HighOdds', 'tot.totalscore', 'tot.LowOdds'
              ]
    base_sql = "SELECT " + ",".join(mfield) + \
               " FROM `lq_schedule` as sche" \
               " left join lq_AsianOdds as asian on sche.ID = asian.ScheduleID left join lq_totalodds as tot on sche.scheduleID = tot.ScheduleID" \
               " WHERE leagueID=1 and MatchSeason='19-20' and MatchKind=1 and MatchState=-1 and asian.CompanyID=8 and tot.CompanyID=8"
    recent_sql = base_sql + " and matchtime<'" + str(matchtime) + "'" + " and (HomeTeamID= " + str(
        teamid) + " or GuestTeamID=" + str(teamid) + ") ORDER BY MatchTime DESC LIMIT 15"
    result = sql_util.select(recent_sql)
    for match in result:
        if match[6] == teamid:
            # 比赛时间 # 球队 # 球队得分 # 对手得分 # 对手
            info = ['主场', match[4].strftime("%Y-%m-%d %H:%M"), match[8], match[10], match[11], match[9]]
            if match[10] - match[11] > 0:
                info.append('胜')
            elif match[10] - match[11] < 0:
                info.append('负')
            else:
                info.append('平')
            # 盘果
            if match[10] - match[23] - match[11] > 0:
                info.append('赢')
            elif match[10] - match[23] - match[11] == 0:
                info.append('走')
            else:
                info.append('输')
            # 让分初盘
            info.append(numformer(-match[23]))
            # 让分即时
            info.append(numformer(-match[26]))
            # 大小初盘
            info.append(match[29])
            # 大小即时
            info.append(match[32])
            info.append(match[0])
            info.append(match[6])
            info.append(match[7])
        else:
            info = ['客场', match[4].strftime("%Y-%m-%d %H:%M"), match[9], match[11], match[10], match[8]]
            if match[11] - int(match[10]) > 0:
                info.append('胜')
            elif int(match[11]) - int(match[10]) < 0:
                info.append('负')
            else:
                info.append('平')
            # 盘果
            if int(match[11]) + int(match[23]) - int(match[10]) > 0:
                info.append('赢')
            elif int(match[11]) + int(match[23]) - int(match[10]) == 0:
                info.append('走')
            else:
                info.append('输')
            # 让分初盘
            info.append(numformer(int(match[23])))
            # 让分即时
            info.append(numformer(int(match[26])))
            # 大小初盘
            info.append(match[29])
            # 大小即时
            info.append(match[32])
            info.append(match[0])
            info.append(match[7])
            info.append(match[6])
        matchs.append(info)
    return matchs
    # 评估客队表现


def numformer(num):
    if num > 0:
        return "+" + str(num)
    else:
        return str(num)


# evalPrechance(24, 25)
evalPerform(362455)
