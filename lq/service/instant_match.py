import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pymemcache.client.base import Client

import utils.dateUtil
from lq.dao import AsianOddsDao
from lq.dao import TotalScoreDao
from lq.parshtml import part_score
from utils import sql_util, js2pyUtil
from utils.webUtil import WebUtil


# 解析字符串转比赛字典数据
def formatScore(matchdata):
    matchfiled = ['scheduleID', 'MatchState', 'remainTime', 'HomeScore', 'AwayScore', 'HomeOne', 'AwayOne',
                  'HomeTwo', 'AwayTwo', 'HomeThree', 'AwayThree', 'HomeFour', 'AwayFour',
                  'AddTime', 'LiveContent', 'PartNumer',
                  'HomeAddTime1', 'AwayAddTime1', 'HomeAddTime2', 'AwayAddTime2', 'HomeAddTime3', 'AwayAddTime3',
                  'OddsContent', 'Technique', 'VictoryOdds']
    mdict = {}
    datalist = matchdata.split('^')
    for i in range(0, len(datalist)):
        if datalist[i] != '':
            mdict[matchfiled[i]] = datalist[i]
    return mdict


# 更新比赛信息
def upMatchdata(begintime, endtime):
    sql = "SELECT scheduleID,leagueID,MatchState,MatchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule` " \
          "WHERE MatchTime <= " + "'" + endtime + "'" + " and MatchTime >=" + "'" + begintime + "' order by MatchState ASC "
    matchs = sql_util.select(sql)
    for match in matchs:
        # 更新比分
        matchstate = match[2]
        if match[4] != 2 and match[3] <= datetime.now():
            condition = {'ID': match[0]}
            partdict = part_score.get_PartScore(match[0])
            if len(partdict) > 0:
                sql_util.upData('lq_schedule', partdict, condition)
        # 更新让分指数
        if match[5] != 2:
            AsianOddsDao.upAsianOddsBymid(match[0], match[5])
        # 更新大小指数
        if match[6] != 2:
            TotalScoreDao.upTotalOddsBymid(match[0], match[6])


# 内存初始化数据
def initialMatchcache(begintime, endtime):
    client = Client(('localhost', 11211))
    if client.get('cacheMatchs') is None:
        cachematch = []
    else:
        cachematch = json.loads(client.get('cacheMatchs').decode())
    upMatchdata(begintime, endtime)
    matchfiled = ['scheduleID', 'leagueID', 'MatchState', 'MatchTime', 'HomeTeamID', 'AwayTeamID', 'HomeTeam',
                  'AwayTeam',
                  'HomeScore', 'AwayScore', 'HomeHalf', 'AwayHalf', 'remainTime', 'AddTime',
                  'HomeOne', 'AwayOne', 'HomeTwo', 'AwayTwo', 'HomeThree', 'AwayThree', 'HomeFour', 'AwayFour',
                  'HomeAddTime1', 'AwayAddTime1', 'HomeAddTime2', 'AwayAddTime2', 'HomeAddTime3', 'AwayAddTime3',
                  'partscore_f', 'asianodds_f', 'totalodds_f',
                  'CompanyID', 'CompanyName', 'HomeOdds_F', 'AsianOdds_F', 'AwayOdds_F', 'HomeOdds', 'AsianOdds',
                  'AwayOdds',
                  'finished', 'updateTime']
    sql = """SELECT scheduleID,leagueID,MatchState,MatchTime,HomeTeamID,AwayTeamID,HomeTeam,AwayTeam,
        HomeScore,AwayScore,HomeHalf,AwayHalf,remainTime,AddTime,
        HomeOne,AwayOne,HomeTwo,AwayTwo,HomeThree,AwayThree,HomeFour,AwayFour,
        HomeAddTime1,AwayAddTime1,HomeAddTime2,AwayAddTime2,HomeAddTime3,AwayAddTime3,
        partscore_f,asianodds_f,totalodds_f,
        asian.CompanyID,asian.CompanyName,asian.HomeOdds_F,asian.AsianOdds_F,asian.AwayOdds_F,asian.HomeOdds,asian.AsianOdds,asian.AwayOdds,asian.finished,updateTime
        FROM `lq_schedule` as sche left join lq_AsianOdds as asian on sche.scheduleID = asian.ScheduleID
        """
    # ---------------- 正在进行的比赛 ------------------
    ongoing = sql + "WHERE MatchTime <=" + "'" + endtime + "'" + " and MatchTime >=" + "'" + begintime + "'" + \
              " and MatchState>0 and asian.CompanyID= 8  ORDER BY MatchTime ASC"
    # ---------- 未开比赛 ---------
    notstarted = sql + "WHERE MatchTime <=" + "'" + endtime + "'" + " and MatchTime >=" + "'" + begintime + "'" + \
                 " and MatchState = 0 and asian.CompanyID= 8  ORDER BY MatchTime ASC"
    # ---------------- 完场或异常比赛 ------------------
    finished = sql + "WHERE MatchTime <=" + "'" + endtime + "'" + " and MatchTime >=" + "'" + begintime + "'" + \
               " and MatchState <= -1 and asian.CompanyID= 8  ORDER BY MatchTime ASC"
    matchs = {}
    # 进行中比赛
    ongoing_result = sql_util.select(ongoing)
    ongoing_matchs = {}
    for match in ongoing_result:
        matchdict = {}
        length = len(match)
        for i in range(0, length):
            matchdict[matchfiled[i]] = match[i]
        matchdict['stateType'] = 1
        matchstr = json.dumps(matchdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
        client.set(str(match[0]), matchstr.encode())
        # print(client.get(str(match[0])).decode())
        ongoing_matchs[str(match[0])] = matchdict
        cachematch.append(match[0])
    matchs['ongoing'] = ongoing_matchs

    # 未开比赛
    notstarted_result = sql_util.select(notstarted)
    notstarted_matchs = {}
    for match in notstarted_result:
        matchdict = {}
        length = len(match)
        for i in range(0, length):
            matchdict[matchfiled[i]] = match[i]
        matchdict['stateType'] = 0
        matchstr = json.dumps(matchdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
        client.set(str(match[0]), matchstr.encode())
        # print(client.get(str(match[0])).decode())
        notstarted_matchs[str(match[0])] = matchdict
        cachematch.append(match[0])
    matchs['notstarted'] = notstarted_matchs

    # 完场或异常比赛#
    finished_result = sql_util.select(finished)
    finished_matchs = {}
    for match in finished_result:
        matchdict = {}
        length = len(match)
        for i in range(0, length):
            matchdict[matchfiled[i]] = match[i]
        matchdict['stateType'] = -1
        matchstr = json.dumps(matchdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
        client.set(str(match[0]), matchstr.encode())
        # print(client.get(str(match[0])).decode())
        finished_matchs[str(match[0])] = matchdict
        cachematch.append(match[0])
    matchs['finished'] = finished_matchs
    # 初始化比赛列表
    insjson = json.dumps(matchs, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
    client.set('insmatch', insjson.encode())
    cachejson = json.dumps(cachematch, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
    client.set('cachematch', cachejson.encode())


# 实时更新缓存中比赛信息
def upInsMatch():
    client = Client(('localhost', 11211))
    while 1:
        matchsjson = client.get('insmatch').decode()
        matchsdict = json.loads(matchsjson)
        try:
            score_r = WebUtil.requests_get(
                ch_score_xml,
                headers=headers_score,
                timeout=5,
                encoding='gb2312',
                sourceName="lq_instant_score",
            )
        except Exception as e:
            print(e)
        else:
            if score_r[0] != 1:
                score_data = ''
            else:
                score_data = score_r[1]
            #   ---------------- 更新即时比分----------------
            if not score_data:
                pass
            elif client.get('ch_score') is not None and client.get('ch_score').decode() == score_data:
                # print("比分变化：本次接收与上次接收 相同")
                pass
            else:
                print("比分变化：本次接收与上次接收 不同")
                tree = ET.fromstring(score_data)
                for element in tree:
                    matchdata = element.text
                    matchid = matchdata.split('^')[0]
                    print("比赛ID：" + matchid)
                    print("最新接收比分信息：")
                    print(matchdata)
                    ch_mdict = formatScore(matchdata)
                    ch_mdict['updateTime'] = js2pyUtil.getNowTime()
                    print(ch_mdict)
                    if client.get(matchid) is None:
                        print("比赛未入库")
                    else:
                        matchold_str = client.get(matchid).decode()
                        match_key = str(matchid) + "_score"
                        if client.get(match_key) is not None and client.get(match_key).decode() == matchdata:
                            pass
                        else:
                            matchdict = json.loads(matchold_str)
                            matchdict.update(ch_mdict)
                            if matchdict['stateType'] == 1:
                                if int(ch_mdict['MatchState']) < 0:
                                    matchdict['stateType'] = -1
                                    matchsdict['finished'][matchid] = matchdict
                                    matchsnew = json.dumps(matchsdict, ensure_ascii=False,
                                                           cls=utils.dateUtil.DateEncoder)
                                    client.set('insmatch', matchsnew.encode())
                                    matchnew_str = json.dumps(matchdict, ensure_ascii=False,
                                                              cls=utils.dateUtil.DateEncoder)
                                    client.set(matchid, matchnew_str.encode())
                                    del matchsdict['ongoing'][matchid]
                                    matchsnew = json.dumps(matchsdict, ensure_ascii=False,
                                                           cls=utils.dateUtil.DateEncoder)
                                    client.set('insmatch', matchsnew.encode())
                                else:
                                    matchsdict['ongoing'][matchid] = matchdict
                                    matchsnew = json.dumps(matchsdict, ensure_ascii=False,
                                                           cls=utils.dateUtil.DateEncoder)
                                    client.set('insmatch', matchsnew.encode())
                                    matchnew_str = json.dumps(matchdict, ensure_ascii=False,
                                                              cls=utils.dateUtil.DateEncoder)
                                    client.set(matchid, matchnew_str.encode())
                            elif matchdict['stateType'] == 0:
                                if int(ch_mdict['MatchState']) > 0:
                                    matchdict['stateType'] = 1
                                    matchsdict['ongoing'][matchid] = matchdict
                                    matchsnew = json.dumps(matchsdict, ensure_ascii=False,
                                                           cls=utils.dateUtil.DateEncoder)
                                    client.set('insmatch', matchsnew.encode())
                                    matchnew_str = json.dumps(matchdict, ensure_ascii=False,
                                                              cls=utils.dateUtil.DateEncoder)
                                    client.set(matchid, matchnew_str.encode())
                                    del matchsdict['notstarted'][matchid]
                                    matchsnew = json.dumps(matchsdict, ensure_ascii=False,
                                                           cls=utils.dateUtil.DateEncoder)
                                    client.set('insmatch', matchsnew.encode())
                                else:
                                    matchsdict['notstarted'][matchid] = matchdict
                                    matchsnew = json.dumps(matchsdict, ensure_ascii=False,
                                                           cls=utils.dateUtil.DateEncoder)
                                    client.set('insmatch', matchsnew.encode())
                                    matchnew_str = json.dumps(matchdict, ensure_ascii=False,
                                                              cls=utils.dateUtil.DateEncoder)
                                    client.set(matchid, matchnew_str.encode())
                            else:
                                matchsdict['finished'][matchid].update(ch_mdict)
                                matchsnew = json.dumps(matchsdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
                                client.set('insmatch', matchsnew.encode())
                                matchnew_str = json.dumps(matchdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
                                client.set(matchid, matchnew_str.encode())
                            client.set(match_key, matchdata.encode())
                        print("最新比赛信息：")
                        print(client.get(matchid).decode())
                client.set('ch_score', score_data.encode())
        #   ---------------- 更新即时赔率 ----------------
        try:
            odds365_r = WebUtil.requests_get(
                ch_odds_bet365_url,
                headers=headers_score,
                timeout=5,
                encoding='utf-8',
                sourceName="lq_instant_odds365",
            )
        except Exception as e:
            print(e)
        else:
            if odds365_r[0] != 1:
                odds8 = ''
            else:
                odds8 = odds365_r[1]
            if not odds8:
                pass
            elif client.get("ch_odds8") is not None and client.get("ch_odds8").decode() == odds8:
                pass
            else:
                print("最新赔率数据：")
                print(odds8)
                tree = ET.fromstring(odds8)
                for element in tree[0]:
                    oddsdata = element.text
                    matchid = oddsdata.split(',')[0]
                    odds_key = str(matchid) + "_odds8"
                    if client.get(matchid) is None:
                        print("比赛未入库")
                    else:
                        matchold_str = client.get(matchid).decode()
                        if client.get(odds_key) is not None and client.get(odds_key).decode() == oddsdata:
                            pass
                        else:
                            matchdict = json.loads(matchold_str)
                            matchdict['AsianOdds'] = oddsdata.split(',')[1]
                            matchdict['HomeOdds'] = oddsdata.split(',')[2]
                            matchdict['AwayOdds'] = oddsdata.split(',')[3]
                            ch_mdict['updateTime'] = js2pyUtil.getNowTime()
                            if matchdict['stateType'] == 1:
                                matchsdict['ongoing'][matchid] = matchdict
                            elif matchdict['stateType'] == 0:
                                matchsdict['notstarted'][matchid] = matchdict
                            else:
                                matchsdict['finished'][matchid] = matchdict
                            matchnew_str = json.dumps(matchdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
                            client.set(matchid, matchnew_str.encode())
                            matchsnew = json.dumps(matchsdict, ensure_ascii=False, cls=utils.dateUtil.DateEncoder)
                            client.set('insmatch', matchsnew.encode())
                            client.set(odds_key, oddsdata.encode())
                        print("最新比赛信息：")
                        print(client.get(matchid).decode())
                client.set("ch_odds8", odds8.encode())
        # time.sleep(5)


# 获取实时比赛列表
def getInsMatch():
    client = Client(('localhost', 11211))
    matchsdict = json.loads(client.get('insmatch').decode())
    # for item in list(matchsdict['ongoing'].items()):
    #     while int(item[1]['MatchState']) < 0:
    #         # print(item[1])
    #         item[1]['stateType'] = -1
    #         matchsdict['finished'][item[0]] = item[1]
    #         del matchsdict['ongoing'][item[0]]
    #         break
    # for item in list(matchsdict['notstarted'].items()):
    #     while int(item[1]['MatchState']) > 0:
    #         # print(item[1])
    #         item[1]['stateType'] = 1
    #         matchsdict['ongoing'][item[0]] = item[1]
    #         del matchsdict['notstarted'][item[0]]
    #         break
    # # 初始化比赛列表
    # matchsjson = json.dumps(matchsdict, ensure_ascii=False, cls=CommonUtil.DateEncoder)
    # client.set('insmatch', matchsjson.encode())
    return matchsdict


ch_score_xml = 'http://lq3.titian007.com/NBA/change.xml'
ch_odds_bet365_url = 'http://lq3.titian007.com/NBA/ch_nbaGoal8.xml'
ch_odds_sb_url = 'http://lq3.titian007.com/NBA/ch_nbaGoal3.xml'

headers_score = {"Host": "lq3.titian007.com",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36",
                 'Sec-Fetch-Mode': 'navigate',
                 'Referer': 'http://lq3.titian007.com/nba.htm',
                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
                 }
ch_score_xml = 'http://lq3.titian007.com/NBA/change.xml'
beginTime = '2019-11-08 20:00:00'
endTime = '2019-11-09 20:00:00'
initialMatchcache(beginTime, endTime)
upInsMatch()
