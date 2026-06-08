import datetime
import time

from selenium import webdriver

from config import lqconfig_qt
from utils import sql_util

nba_url = 'https://www.365212365.com/#/AC/B18/C20651951/D1/'
champurl_europ = 'https://www.365212365.com/#/AC/B18/C20653915/D1/E42401559/F2/'
champurl_Aus = 'https://www.365212365.com/#/AC/B18/C20637360/D1/E41042171/F2/'
default_url = 'https://www.365212365.com/zh-CHS/'
nba_types = {'获得总冠军': 'E42216247/F2/', '联盟冠军': 'E42216316/F2/', '区赛冠军': 'E42751986/F2/',
             '晋级季后赛': 'E43263793/F2/', '获胜场数': 'E43292204/F2/'}


def earlyOdds_NBA():
    Oddslist = []
    earlydict = {}
    driver = webdriver.Chrome()
    # 第一次访问365默认页面
    driver.get(default_url)
    chines = driver.find_element_by_class_name('lpdgl')
    chines.click()
    time.sleep(10)
    # 获取365 NBA总冠军赔率
    driver.get(nba_url + nba_types['获得总冠军'])
    time.sleep(12)
    champ_teams = driver.find_elements_by_class_name('gll-Participant_General.gll-Participant.gll-Market_CN-2 ')
    # ClosingtimeChamp = driver.find_elements_by_class_name('cm-MarketSubGroup_BookCloses ')
    for team in champ_teams:
        # print("总冠军："+team.text)
        teamname = team.find_element_by_class_name('gll-Participant_Name').text
        champOdds = team.find_element_by_class_name('gll-Participant_Odds').text
        earlydict[teamname] = {'TeamName': teamname, 'ChampOdds': champOdds}
        # earlydict[teamname]['ClosingtimeChamp'] = ClosingtimeChamp
    # 获取365 联盟冠军赔率
    driver.get(nba_url + nba_types['联盟冠军'])
    time.sleep(10)
    League_teams = driver.find_elements_by_class_name('gll-Participant_General.gll-Participant.gll-Market_CN-2 ')
    for team in League_teams:
        # print("联赛冠军："+team.text)
        teamname = team.find_element_by_class_name('gll-Participant_Name').text
        LeagueOdds = team.find_element_by_class_name('gll-Participant_Odds').text
        earlydict[teamname]['LeagueOdds'] = LeagueOdds
    # 区赛冠军
    driver.get(nba_url + nba_types['区赛冠军'])
    time.sleep(12)
    Zone_teams = driver.find_elements_by_class_name('gll-Participant_General.gll-Participant.gll-Market_CN-2 ')
    # closingtimeZone = driver.find_elements_by_class_name('cm-MarketSubGroup_BookCloses ')
    for team in Zone_teams:
        teamname = team.find_element_by_class_name('gll-Participant_Name').text
        ZoneOdds = team.find_element_by_class_name('gll-Participant_Odds').text
        earlydict[teamname]['ZoneOdds'] = ZoneOdds
        # earlydict[teamname]['closingtimeZone'] = closingtimeZone
    # # 晋级季后赛
    # driver.get(nba_url + nba_types['晋级季后赛'])
    # time.sleep(10)
    # Playoffs_teams = driver.find_elements_by_class_name('cm-MarketSubGroup_Label ')
    # teamlist = []
    # oddslist = []
    # for team in Playoffs_teams:
    #     teamname = team.text.replace(' 参加NBA季后赛', '')
    #     teamlist.append(teamname)
    # OptionDivs = driver.find_elements_by_class_name(
    #     'gll-MarketExtraData.gll-Market_General.gll-Market_PWidth-100.gll-Market_LastInRow ')
    # for OptionDiv in OptionDivs:
    #     oddsdict = {}
    #     options = OptionDiv.find_elements_by_class_name('gll-Participant_General.gll-Participant.gll-Market_CN-2 ')
    #     for option in options:
    #         name = option.find_element_by_class_name('gll-Participant_Name').text
    #         odds = option.find_element_by_class_name('gll-Participant_Odds').text
    #         oddsdict[name] = odds
    #     oddslist.append(oddsdict)
    # count = len(teamlist)
    # for i in range(0, count):
    #     earlydict[teamlist[i]]['InPlayoffsOdds'] = oddslist[i]['是']
    #     earlydict[teamlist[i]]['OutPlayoffsOdds'] = oddslist[i]['否']
    # # NBA常规赛获胜场数
    # driver.get(nba_url + nba_types['获胜场数'])
    # time.sleep(12)
    # teamtags = driver.find_elements_by_class_name('sl-CouponParticipantWithBookCloses_Name ')
    # teamlist = []
    # highlist = []
    # lowlist = []
    # for team in teamtags:
    #     teamname = team.text
    #     teamlist.append(teamname)
    # OptionDivs = driver.find_elements_by_class_name('sl-MarketCouponValuesExplicit40.gll-Market_General.'
    #                                                 'gll-Market_PWidth-20.gll-Market_AdditionalRowHeight ')
    # for OptionDiv in OptionDivs:
    #     typediv = OptionDiv.find_element_by_class_name('gll-MarketColumnHeader ')
    #     options = OptionDiv.find_elements_by_class_name('sl-CouponParticipantCenteredAsianDarker.'
    #                                                     'sl-CouponParticipantCenteredAsian.gll-Participant_General.'
    #                                                     'gll-ParticipantCentered.gll-ParticipantCentered_NoHandicap ')
    #     for option in options:
    #         oddsdict = {}
    #         name = option.find_element_by_class_name('gll-ParticipantCentered_Name').text
    #         odds = option.find_element_by_class_name('gll-ParticipantCentered_Odds').text
    #         oddsdict['Wins'] = name
    #         if typediv.text == '高于':
    #             oddsdict['HighOdds'] = odds
    #             highlist.append(oddsdict)
    #         elif typediv.text == '低于':
    #             oddsdict['LowOdds'] = odds
    #             lowlist.append(oddsdict)
    #         else:
    #             pass
    # count = len(teamlist)
    # for i in range(0, count):
    #     earlydict[teamlist[i]]['Wins'] = highlist[i]['Wins']
    #     earlydict[teamlist[i]]['HighOdds'] = highlist[i]['HighOdds']
    #     earlydict[teamlist[i]]['LowOdds'] = lowlist[i]['LowOdds']
    teamInfo = sql_util.selectData('lq_team', ['ID', 'Name_J', 'leagueID', 'LocationID', 'MatchAddrID', 'Drillmaster'],
                                   {'leagueID': 1}, 1)
    for team in teamInfo:
        if team[1] == '亚特兰大老鹰':
            teamname = '亚特兰大鹰'
        elif team[1] == '休斯顿火箭':
            teamname = '休斯敦火箭'
        elif team[1] == '洛杉矶快船':
            teamname = '洛杉矶快艇'
        elif team[1] == '萨克拉门托国王':
            teamname = '萨卡拉门托国王'
        elif team[1] == '夏洛特黄蜂':
            teamname = '夏洛特黃蜂'
        else:
            teamname = team[1]
        TeamOdds = earlydict[teamname]
        TeamOdds['TeamName'] = team[1]
        TeamOdds['TeamID'] = team[0]
        TeamOdds['leagueID'] = 1
        TeamOdds['LocationID'] = team[3]
        TeamOdds['ZoneID'] = team[4]
        TeamOdds['Drillmaster'] = team[5]
        TeamOdds['MatchSeason'] = '19-20'
        TeamOdds['UpdateTime'] = datetime.datetime.now()
        Oddslist.append(TeamOdds)
    sql_util.insertDatas('lq_earlyOdds', Oddslist)
    driver.close()
    # print(teamInfo)


# 采集欧冠，2019-20赛季 冠军赔率
def earlyOdds_Europ():
    Oddslist = []
    driver = webdriver.Chrome()
    # 首次访问默认页面
    driver.get(default_url)
    chines = driver.find_element_by_class_name('lpdgl')
    chines.click()
    time.sleep(10)
    # 获取总冠军赔率
    driver.get(champurl_europ)
    time.sleep(12)
    champ_teams = driver.find_elements_by_class_name('gll-Participant_General.gll-Participant.gll-Market_CN-2 ')
    for team in champ_teams:
        TeamOdds = {}
        # print("总冠军："+team.text)
        teamname = team.find_element_by_class_name('gll-Participant_Name').text
        champOdds = team.find_element_by_class_name('gll-Participant_Odds').text
        TeamOdds['TeamID'] = lqconfig_qt.teamEurop[teamname]['TeamID']
        TeamOdds['TeamName'] = lqconfig_qt.teamEurop[teamname]['TeamName']
        TeamOdds['leagueID'] = 7
        TeamOdds['ChampOdds'] = champOdds
        TeamOdds['MatchSeason'] = '19-20'
        TeamOdds['UpdateTime'] = datetime.datetime.now()
        Oddslist.append(TeamOdds)
    sql_util.insertDatas('lq_earlyOdds', Oddslist)
    driver.close()


# 采集澳大利亚甲级联赛-男，2019-20赛季 冠军赔率
def earlyOdds_Aus():
    Oddslist = []
    driver = webdriver.Chrome()
    # 首次访问默认页面
    driver.get(default_url)
    chines = driver.find_element_by_class_name('lpdgl')
    chines.click()
    time.sleep(10)
    # 获取总冠军赔率
    driver.get(champurl_Aus)
    time.sleep(12)
    champ_teams = driver.find_elements_by_class_name('gll-Participant_General.gll-Participant.gll-Market_CN-2 ')
    for team in champ_teams:
        TeamOdds = {}
        # print("总冠军："+team.text)
        teamname = team.find_element_by_class_name('gll-Participant_Name').text
        champOdds = team.find_element_by_class_name('gll-Participant_Odds').text
        TeamOdds['TeamID'] = lqconfig_qt.teamAus[teamname]['TeamID']
        TeamOdds['TeamName'] = lqconfig_qt.teamAus[teamname]['TeamName']
        TeamOdds['leagueID'] = 14
        TeamOdds['ChampOdds'] = champOdds
        TeamOdds['MatchSeason'] = '19-20'
        TeamOdds['UpdateTime'] = datetime.datetime.now()
        Oddslist.append(TeamOdds)
    # print(Oddslist)
    sql_util.insertDatas('lq_earlyOdds', Oddslist)
    driver.close()
