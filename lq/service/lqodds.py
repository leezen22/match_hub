import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple, cast

from config import lqconfig_qt
from crawler.qt.lq_2in1_detail_crawler import Lq2in1Crawler
from crawler.qt.lq_asian_detail_crawler import AsianDetailCrawler
from crawler.qt.lq_asian_odds_crawler import AsianOddsCrawler
from crawler.qt.lq_europe_odds_crawler import EuropeOddsCrawler
from crawler.qt.lq_total_detail_crawler import TotalDetailCrawler
from crawler.qt.lq_total_odds_crawler import TotalScoreCrawler
from dao.lq_asianDetail_dao import LqAsianDetailDao
from dao.lq_asianOdds_dao import LqAsianOddsDao
from dao.lq_eurDetail_dao import LqEurDetailDao
from dao.lq_europeOdds_dao import LqEuropeOddsDao
from dao.lq_match_dao import LqMatchDao
from dao.lq_totalDetail_dao import LqTotalDetailDao
from dao.lq_totalOdss_dao import LqTotalOddsDao
from lq.dao import AsianOddsDao, TotalScoreDao
from utils import fileUtil, sql_util
from utils.dateUtil import getNowTime

DictRow = Dict[str, Any]


def _schedule_id_sql_filter(schedule_ids, column):
    if schedule_ids is None:
        return ""
    normalized = sorted({int(schedule_id) for schedule_id in schedule_ids})
    if not normalized or any(schedule_id <= 0 for schedule_id in normalized):
        raise ValueError("schedule_ids must contain positive integers")
    return " and {0} in ({1})".format(
        column,
        ",".join(str(schedule_id) for schedule_id in normalized),
    )


class LqOddsService(object):

    def __init__(self):
        pass

    @staticmethod
    def upOdds(lookback_days=14, until_days=1, schedule_ids=None):
        fileUtil.logLine(lqconfig_qt.update_log, ['开始更新篮球初盘/即时盘'])
        print(getNowTime() + " 开始更新篮球初盘/即时盘")
        now = datetime.now()
        time1 = "'" + (now + timedelta(days=-int(lookback_days))).strftime("%Y-%m-%d %H:%M:%S") + "'"
        time2 = "'" + (now + timedelta(days=int(until_days))).strftime("%Y-%m-%d %H:%M:%S") + "'"
        # and leagueID in (1, 2, 5, 7, 14, 15, 19, 25, 20, 28, 22)
        schedule_filter = _schedule_id_sql_filter(schedule_ids, "scheduleID")
        asiansql = "SELECT scheduleID, leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                   " WHERE asianodds_f in(0,1,4) and matchState>=-1 and MatchTime >= {0} and MatchTime < {1}{2} order by matchTime ASC ".format(time1, time2, schedule_filter)
        totalsql = "SELECT scheduleID,leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                   " WHERE totalodds_f in(0,1,4) and matchState>=-1 and matchTime >= {0} and matchTime < {1}{2} order by matchTime ASC ".format(time1, time2, schedule_filter)

        # totalsql= {}
        asianMatchList = sql_util.select(asiansql)
        # print(asianMatchList)
        totalMatchList = sql_util.select(totalsql)
        # print(totalMatchList)
        threads = []
        # 更新让分赔率线程
        if len(asianMatchList) > 0:
            asian_thread = threading.Thread(target=AsianOddsDao.upAsianOddsByMatchs, args=([asianMatchList]))
            threads.append(asian_thread)
        # 更新大小赔率线程
        if len(totalMatchList) > 0:
            total_thread = threading.Thread(target=TotalScoreDao.upTotalOddsBymatchs, args=([totalMatchList]))
            threads.append(total_thread)
        # 启动线程
        for t in threads:
            t.start()
        # 等待所有线程完成
        for t in threads:
            t.join()
        print(getNowTime() + " 初盘/即时盘更新成功, lookback_days={0}, until_days={1}".format(
            lookback_days,
            until_days,
        ))

    @staticmethod
    def up_total_Odds():
        print(getNowTime() + " 开始更新篮球大小 初盘/即时盘")
        now = datetime.now()
        # time = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
        # time1 = "'" + (now + timedelta(hours=-4)).strftime("%Y-%m-%d %H:%M:%S") + "'"
        time2 = (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        totalSql = "SELECT matchId,scheduleId,leagueId,matchState,matchTime,totalOdds_f " \
                   "FROM `lq_schedule` " \
                   "WHERE totalOdds_f in(0,1) and matchState>=-1 and matchTime<'{0}' order by sche.matchTime ASC".format(
            time2)

        matchList = cast(Tuple[DictRow, ...], LqMatchDao.select(totalSql, isdict=True))

        for match in matchList:
            print(getNowTime(), match)
            crawler = TotalScoreCrawler(match['matchId'], match['scheduleId'],
                                        match['matchState'], match['totalOdds_f'])
            oddsData = cast(DictRow, crawler.qt_web_get())
            if oddsData['state'] == 1:
                if len(oddsData['odds']) > 0:
                    LqMatchDao.update({'totalOdds_f': 1}, {'matchId': match['matchId']})
                    if match['totalOdds_f'] == 0:
                        for item in oddsData['odds']:
                            LqTotalOddsDao.insert(cast(DictRow, item))
                    elif match['totalOdds_f'] == 1:
                        for item in oddsData['odds']:
                            item = cast(DictRow, item)
                            LqTotalOddsDao.update(item, {'matchId': match['matchId'], 'companyId': item['companyId']},
                                                  judge=True)
                if oddsData['matchState'] in (-1, -4):
                    LqMatchDao.update({'totalOdds_f': 2}, {'matchId': match['matchId']})
            elif oddsData['state'] == 4 and oddsData['matchState'] in (-1, -4):
                LqMatchDao.update({'totalOdds_f': 4}, {'matchId': match['matchId']})
        print(getNowTime() + "更新结束 篮球大小 初盘/即时盘")

    @staticmethod
    def up_asian_Odds():
        print(getNowTime() + " 开始更新篮球让分 初盘/即时盘")
        now = datetime.now()
        time2 = (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

        asianSql = "SELECT matchId,scheduleId,leagueId,matchState,matchTime,asianOdds_f " \
                   "FROM `lq_schedule` " \
                   "WHERE AsianOdds_f in(0,1) and matchState>=-1 and matchTime<'{0}' order by sche.matchTime ASC".format(
            time2)

        matchList = cast(Tuple[DictRow, ...], LqMatchDao.select(asianSql, isdict=True))

        for match in matchList:
            print(getNowTime(), match)
            crawler = AsianOddsCrawler(match['matchId'], match['scheduleId'],
                                       match['matchState'], match['asianOdds_f'])
            oddsData = cast(DictRow, crawler.qt_web_get())
            print("采集结束")
            if oddsData['state'] == 1:
                if len(oddsData['odds']) > 0:
                    LqMatchDao.update({'asianOdds_f': 1}, {'matchId': match['matchId']})
                    if match['asianOdds_f'] == 0:
                        for item in oddsData['odds']:
                            LqAsianOddsDao.insert(cast(DictRow, item))
                    elif match['asianOdds_f'] == 1:
                        for item in oddsData['odds']:
                            item = cast(DictRow, item)
                            LqAsianOddsDao.update(item, {'matchId': match['matchId'], 'companyId': item['companyId']},
                                                  judge=True)
                if oddsData['matchState'] in (-1, -4):
                    LqMatchDao.update({'asianOdds_f': 2}, {'matchId': match['matchId']})
                print("单场比赛更新完成")
            elif oddsData['state'] == 4 and oddsData['matchState'] in (-1, -4):
                LqMatchDao.update({'asianOdds_f': 4}, {'matchId': match['matchId']})

        print(getNowTime() + "更新结束 篮球让分 初盘/即时盘")

    @staticmethod
    def up_europe_odds(scope=3):
        print(getNowTime() + " 开始更新篮球欧赔")
        now = datetime.now()
        time2 = (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        selectSql = """
        SELECT matchId,scheduleId,matchState,eurOdds_f,matchTime
        FROM lq_schedule
        WHERE matchTime>='2015-01-01 00:00' and eurOdds_f in(0,1) and 
        matchState >=-1 and matchTime<'{0}'
        """.format(time2)
        matchList = cast(Tuple[DictRow, ...], LqMatchDao.select(selectSql, isdict=True))
        count = len(matchList)
        for match in matchList:
            print(count)
            LqOddsService.up_europe_byMatch(match['matchId'], match['scheduleId'], match['matchState'],
                                            match['eurOdds_f'], scope)
            count = count - 1
        print(getNowTime() + " 结束更新篮球欧赔")

    @staticmethod
    def up_asianPre_batch(companyArr):
        threads = []
        for cid in companyArr:
            threadTask = threading.Thread(target=LqOddsService.up_asianPre_mobile, args=(cid,))
            threads.append(threadTask)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    @staticmethod
    def up_totalPre_batch(companyArr):
        threads = []
        for cid in companyArr:
            threadTask = threading.Thread(target=LqOddsService.up_totalPre_mobile, args=(cid,))
            threads.append(threadTask)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    @staticmethod
    def up_2in1Details(scope):
        companyArr = [3, 8]
        threads = []
        for cid in companyArr:
            threadTask = threading.Thread(target=LqOddsService.up_2in1Details_byCid, args=(cid, scope,))
            threads.append(threadTask)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # scope 1 赛前 2赛中 3赛前+赛中
    @staticmethod
    def up_2in1Details_byCid(companyId, scope, lookback_days=14, until_days=1, schedule_ids=None):
        # scope = 3
        now = datetime.now()
        time1 = (now + timedelta(days=-int(lookback_days))).strftime("%Y-%m-%d %H:%M:%S")
        time2 = (now + timedelta(days=int(until_days))).strftime("%Y-%m-%d %H:%M:%S")
        schedule_filter = _schedule_id_sql_filter(schedule_ids, "sche.scheduleID")
        sql = """SELECT sche.matchId,sche.scheduleId,sche.matchState,sche.matchTime,
            tot.companyId,
            tot.oddsId as total_oddsId ,
            tot.finished_pre as total_finished_pre,
            tot.finished_gun as total_finished_gun,
            asian.oddsId as asian_oddsId,
            asian.finished_pre as asian_finished_pre,
            asian.finished_gun as asian_finished_gun
            FROM lq_totalodds as tot 
            LEFT JOIN lq_AsianOdds as asian
            on asian.companyId = tot.companyId and asian.matchId = tot.matchId
            left JOIN `lq_schedule` as sche 
            on sche.matchId = tot.matchId
            WHERE tot.companyId={0}
            and (
                tot.finished_pre in(0,1,4) or tot.finished_gun in(0,1,4)
                or asian.finished_pre in(0,1,4) or asian.finished_gun in(0,1,4)
            )
            and sche.matchTime>='{1}'
            and sche.matchTime<'{2}'{3}
            and sche.matchState >=-1 order by sche.matchtime ASC
        """.format(companyId, time1, time2, schedule_filter)
        results = cast(Tuple[Tuple[Any, ...], ...], LqAsianOddsDao.select(sql))
        size = len(results)
        print("开始更新篮球2合1赔率变化: companyId={0}, count={1}, lookback_days={2}, until_days={3}".format(
            companyId,
            size,
            lookback_days,
            until_days,
        ))
        for item in results:
            print(str(companyId)+"变化记录剩余比赛：" + str(size) + ",最新 ：" + str(item))
            matchId = item[0]
            scheduleId = item[1]
            matchState = item[2]
            matchTime = item[3]
            companyId = item[4]
            total_oddsId = item[5]
            total_finished_pre = item[6]
            total_finished_gun = item[7]
            asian_oddsId = item[8]
            asian_finished_pre = item[9]
            asian_finished_gun = item[10]
            crawler = Lq2in1Crawler(matchId, companyId, scheduleId, asian_oddsId, total_oddsId, matchState, matchTime,
                                    asian_finished_pre=asian_finished_pre, asian_finished_gun=asian_finished_gun,
                                    total_finished_pre=total_finished_pre, total_finished_gun=total_finished_gun)
            collectData = cast(DictRow, crawler.qt_web_get(scope=scope))
            threads = []
            if scope != 2:
                if 'asian' in collectData.keys():
                    asian = cast(DictRow, collectData['asian'])
                    if asian['state'] == 1 and asian['finished_pre'] in (0, 1):
                        asian_pre_thread = threading.Thread(target=LqOddsService.up_asianPre_details,
                                                            args=(asian,))
                        threads.append(asian_pre_thread)
                if 'total' in collectData.keys():
                    total = cast(DictRow, collectData['total'])
                    if total['state'] == 1 and total['finished_pre'] in (0, 1):
                        total_pre_thread = threading.Thread(target=LqOddsService.up_totalPre_details,
                                                            args=(total,))
                        threads.append(total_pre_thread)

            if scope != 1:
                if 'asian' in collectData.keys():
                    asian = cast(DictRow, collectData['asian'])
                    if asian['state'] == 1 and asian['finished_gun'] in (0, 1):
                        asian_gun_thread = threading.Thread(target=LqOddsService.up_asianGun_details,
                                                            args=(asian,))
                        threads.append(asian_gun_thread)
                if 'total' in collectData.keys():
                    total = cast(DictRow, collectData['total'])
                    if total['state'] == 1 and total['finished_gun'] in (0, 1):
                        total_gun_thread = threading.Thread(target=LqOddsService.up_totalGun_details,
                                                            args=(total,))
                        threads.append(total_gun_thread)
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            size = size - 1
    @staticmethod
    def up_europe_byMatch(matchId, scheduleId, matchState, eurOdds_f, scope):
        crawler = EuropeOddsCrawler(matchId, scheduleId, matchState, eurOdds_f)
        collect = cast(DictRow, crawler.qt_web_get(hasDetail=True))
        print(collect['state'], matchId, scheduleId, matchState, eurOdds_f, scope)
        if collect['state'] == 1 and scope in (1, 3):
            # 更新初盘即时指数
            if collect['eurOdds_f'] == 0:
                LqMatchDao.update({'eurOdds_f': 1}, {'matchId': matchId})
                for item in collect['odds']:
                    LqEuropeOddsDao.insert(cast(DictRow, item))
            elif collect['eurOdds_f'] == 1:
                for item in collect['odds']:
                    item = cast(DictRow, item)
                    LqEuropeOddsDao.update(item, {'matchId': matchId, 'companyId': item['companyId']}, judge=True)
            if (collect['matchState'] in (-1, -4)) and (collect['eurOdds_f'] != 2):
                LqMatchDao.update({'eurOdds_f': 2}, {'matchId': matchId})
        elif collect['state'] == 4 and collect['matchState'] in (-1, -4):
            LqMatchDao.update({'eurOdds_f': 4}, {'matchId': matchId})

        # 更新变化记录
        if collect['state'] == 1 and scope in (2, 3):
            querySql = "select oddsId,matchId,companyId,finished_pre,companyName " \
                       "from lq_europe " \
                       "where matchId={0} and finished_pre in(0,1)".format(matchId)
            results2 = cast(Tuple[DictRow, ...], LqEuropeOddsDao.select(querySql, isDict=True))

            LqEuropeOddsDao.update({'finished_pre': 1}, {'matchId': matchId})
            data: DictRow | None = None
            count = 0
            for data in results2:
                cid = data['companyId']
                keys_pre = collect['keys_pre']
                oddsId = data['oddsId']
                details = collect['pre'][str(cid)]
                count = len(details)
                if data['finished_pre'] == 0:
                    LqEurDetailDao.insertMany(cid, details, keys_pre)
                    # 新增记录无OddsId
                    LqEurDetailDao.update(cid, {'oddsId': oddsId}, {'matchId': matchId})
                elif data['finished_pre'] == 1:
                    # LqEuropeOddsDao.update({'finished_pre': 1}, {'matchId': matchId, 'companyId': cid})
                    querySql = "SELECT COUNT(*) FROM lq_europe_pre_{0} WHERE matchId={1}".format(cid, matchId)
                    count_local = cast(Tuple[Tuple[Any, ...], ...], LqEurDetailDao.select(querySql))[0][0]

                    if count > int(count_local):
                        details_new = details[count_local:]
                        LqEurDetailDao.insertMany(cid, details_new, keys=keys_pre)
                        # 新增记录无OddsId
                        LqEurDetailDao.update(cid, {'oddsId': oddsId}, {'matchId': matchId})
            if data is not None and collect['matchState'] in [-1, -4] and data['finished_pre'] in (0, 1) and count > 0:
                LqEuropeOddsDao.update({'finished_pre': 2}, {'matchId': matchId})
            elif data is not None and collect['matchState'] in [-1, -4] and data['finished_pre'] in (0, 1) and count == 0:
                LqEuropeOddsDao.update({'finished_pre': 3}, {'matchId': matchId})
        print(getNowTime(), '欧赔更新完成')

    @staticmethod
    def up_asianPre_mobile(companyId, matchId=None):
        sql = """
        SELECT asian.matchId,asian.companyId,asian.scheduleId,asian.oddsId,
        sche.matchState,sche.matchTime,asian.finished_pre,asian.finished_gun
        FROM lq_AsianOdds as asian 
        left JOIN `lq_schedule` as sche 
        on sche.matchId = asian.matchId
        WHERE asian.companyId={0} and asian.finished_pre in(0,1) and sche.matchTime>='2020-01-01 00:00' 
        and sche.matchState >=-1
        """.format(companyId)
        if matchId:
            sql = sql + " and sche.matchId={0}".format(matchId)
        sql = sql + " order by sche.matchTime ASC"
        print(sql)
        results = cast(Tuple[DictRow, ...], LqAsianOddsDao.select(sql, isDict=True))
        # print("让分赛前比赛数量：{0}".format(len(results)))
        for item in results:
            crawler = AsianDetailCrawler(item['matchId'], item['companyId'], scheduleId=item['scheduleId'],
                                         oddsId=item['oddsId'], matchState=item['matchState'],
                                         matchTime=item['matchTime'], finished_pre=item['finished_pre'],
                                         finished_gun=item['finished_gun'])
            collect = cast(DictRow, crawler.qt_mobile_pre_detail())
            print(collect['state'], item['matchId'], item['scheduleId'], item['companyId'])
            LqOddsService.up_asianPre_details(collect)

    @staticmethod
    def up_totalPre_mobile(companyId, matchId=None):
        sql = """
        SELECT odds.matchId,odds.companyId,odds.scheduleId,odds.oddsId,
        sche.matchState,sche.matchTime,odds.finished_pre,odds.finished_gun
        FROM lq_totalodds as odds 
        left JOIN `lq_schedule` as sche 
        on sche.matchId = odds.matchId
        WHERE odds.companyId={0} and odds.finished_pre in(0,1) and sche.matchTime>='2020-01-01 00:00' 
        and sche.matchState >=-1
        """.format(companyId)
        if matchId:
            sql = sql + " and sche.matchId={0}".format(matchId)
        sql = sql + " order by sche.matchTime ASC"
        print(sql)
        results = cast(Tuple[DictRow, ...], LqTotalOddsDao.select(sql, isDict=True))
        # print("大小赛前比赛数量：{0}".format(len(results)))
        for item in results:
            crawler = TotalDetailCrawler(item['matchId'], item['companyId'], scheduleId=item['scheduleId'],
                                         oddsId=item['oddsId'], matchState=item['matchState'],
                                         matchTime=item['matchTime'], finished_pre=item['finished_pre'],
                                         finished_gun=item['finished_gun'])
            collect = cast(DictRow, crawler.qt_mobile_pre_detail())
            print(collect['state'], item['matchId'], item['scheduleId'], item['companyId'])
            LqOddsService.up_totalPre_details(collect)

    # scope: 1 赛前, 2 赛中, 3 赛前+赛中
    @staticmethod
    def up_2in1_byMatch(scope, matchId, companyId, scheduleId, matchState, matchTime):
        asian_results = cast(Tuple[Dict[str, Any], ...],
                             LqAsianOddsDao.select_dicts(['oddsId', 'finished_pre', 'finished_gun'],
                                                         {'matchId': matchId, 'companyId': companyId}))
        total_results = cast(Tuple[Dict[str, Any], ...],
                             LqTotalOddsDao.select_dicts(['oddsId', 'finished_pre', 'finished_gun'],
                                                         {'matchId': matchId, 'companyId': companyId}))
        asian_oddsId = None
        asian_finished_pre = None
        asian_finished_gun = None
        total_oddsId = None
        total_finished_pre = None
        total_finished_gun = None
        if len(asian_results):
            asian_oddsId = asian_results[0]['oddsId']
            asian_finished_pre = asian_results[0]['finished_pre']
            asian_finished_gun = asian_results[0]['finished_gun']
        if len(total_results):
            total_oddsId = total_results[0]['oddsId']
            total_finished_pre = total_results[0]['finished_pre']
            total_finished_gun = total_results[0]['finished_gun']
        crawler = Lq2in1Crawler(matchId, companyId, scheduleId, asian_oddsId, total_oddsId, matchState, matchTime,
                                asian_finished_pre=asian_finished_pre, asian_finished_gun=asian_finished_gun,
                                total_finished_pre=total_finished_pre, total_finished_gun=total_finished_gun)
        collectData = cast(DictRow, crawler.qt_web_get(scope=scope))
        threads = []
        if scope != 2:
            if collectData['asian']['state'] == 1 and collectData['asian']['finished_pre'] in (0, 1):
                asian_pre_thread = threading.Thread(target=LqOddsService.up_asianPre_details,
                                                    args=(collectData['asian'],))
                threads.append(asian_pre_thread)
            if collectData['total']['state'] == 1 and collectData['total']['finished_pre'] in (0, 1):
                total_pre_thread = threading.Thread(target=LqOddsService.up_totalPre_details,
                                                    args=(collectData['total'],))
                threads.append(total_pre_thread)

        if scope != 1:
            if collectData['asian']['state'] == 1 and collectData['asian']['finished_gun'] in (0, 1):
                asian_gun_thread = threading.Thread(target=LqOddsService.up_asianGun_details,
                                                    args=(collectData['asian'],))
                threads.append(asian_gun_thread)
            if collectData['total']['state'] == 1 and collectData['total']['finished_gun'] in (0, 1):
                total_gun_thread = threading.Thread(target=LqOddsService.up_totalGun_details,
                                                    args=(collectData['total'],))
                threads.append(total_gun_thread)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    @staticmethod
    def up_asianPre_details(collect: DictRow):
        details = collect['pre']
        if collect['state'] == 1:
            count = len(details)
            if collect['finished_pre'] == 0 and count > 0:
                LqAsianOddsDao.update({'finished_pre': 1, 'hasPre': 1},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})
                LqAsianDetailDao.insertMany(collect['companyId'], details, keys=collect['keys_pre'])
            elif collect['finished_pre'] == 1 and count > 0:
                querySql = "SELECT COUNT(*) FROM lq_AsianOdds_pre_{0} WHERE oddsID={1}" \
                    .format(collect['companyId'], collect['oddsId'])
                count_local = cast(Tuple[Tuple[Any, ...], ...], LqAsianDetailDao.select(querySql))[0][0]

                if count > int(count_local):
                    details_new = details[count_local:]
                    LqAsianDetailDao.insertMany(collect['companyId'], details_new, keys=collect['keys_pre'])
            else:
                pass

            if collect['matchState'] in [-1, -4] and count > 0:
                LqAsianOddsDao.update({'finished_pre': 2},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})
            elif collect['matchState'] in [-1, -4] and count == 0:
                LqAsianOddsDao.update({'finished_pre': 3},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})

    @staticmethod
    def up_asianGun_details(collect: DictRow):
        print('让分', collect['state'], collect['matchId'], collect['scheduleId'], collect['companyId'])
        details = collect['gun']
        if collect['state'] == 1:
            if collect['finished_gun'] == 0 and len(details) > 0:
                LqAsianOddsDao.update({'finished_gun': 1, 'hasGun': 1},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})
                LqAsianDetailDao.insertMany(collect['companyId'], details, keys=collect['keys_gun'], isPre=False)
            elif collect['finished_gun'] == 1 and len(details) > 0:
                querySql = "SELECT COUNT(*) FROM lq_AsianOdds_gun_{0} WHERE oddsID={1}" \
                    .format(collect['companyId'], collect['oddsId'])
                count_local = cast(Tuple[Tuple[Any, ...], ...], LqAsianDetailDao.select(querySql))[0][0]
                count = len(details)
                if count > int(count_local):
                    details_new = details[count_local:]
                    LqAsianDetailDao.insertMany(collect['companyId'], details_new, keys=collect['keys_gun'],
                                                isPre=False)
            else:
                pass

            data = {'hasGun': collect['hasGun'], 'hasFirst': collect['hasFirst'], 'hasSecond': collect['hasSecond'],
                    'hasHalf': collect['hasHalf'], 'hasThird': collect['hasThird'], 'hasFour': collect['hasFour']}
            if collect['matchState'] in [-1, -4] and len(details) > 0:
                data['finished_gun'] = 2
            elif collect['matchState'] in [-1, -4] and len(details) == 0:
                data['finished_gun'] = 3
            LqAsianOddsDao.update(data, {'matchId': collect['matchId'], 'companyId': collect['companyId']})

    @staticmethod
    def up_totalPre_details(collect: DictRow):
        details = collect['pre']
        if collect['state'] == 1:
            count = len(details)
            if collect['finished_pre'] == 0 and count > 0:
                LqTotalOddsDao.update({'finished_pre': 1, 'hasPre': 1},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})
                LqTotalDetailDao.insertMany(collect['companyId'], details, keys=collect['keys_pre'])
            elif collect['finished_pre'] == 1 and count > 0:
                querySql = "SELECT COUNT(*) FROM lq_totalodds_pre_{0} WHERE oddsID={1}" \
                    .format(collect['companyId'], collect['oddsId'])
                count_local = cast(Tuple[Tuple[Any, ...], ...], LqTotalDetailDao.select(querySql))[0][0]

                if count > int(count_local):
                    details_new = details[count_local:]
                    LqTotalDetailDao.insertMany(collect['companyId'], details_new, keys=collect['keys_pre'])
            else:
                pass

            if collect['matchState'] in [-1, -4] and count > 0:
                LqTotalOddsDao.update({'finished_pre': 2},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})
            elif collect['matchState'] in [-1, -4] and count == 0:
                LqTotalOddsDao.update({'finished_pre': 3},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})

    @staticmethod
    def up_totalGun_details(collect: DictRow):
        # print('大小', collect['state'], collect['matchId'], collect['scheduleId'], collect['companyId'])
        details = collect['gun']
        # print(collect)
        if collect['state'] == 1:
            count = len(details)
            if collect['finished_gun'] == 0 and count > 0:
                LqTotalOddsDao.update({'finished_gun': 1, 'hasGun': 1},
                                      {'matchId': collect['matchId'], 'companyId': collect['companyId']})
                LqTotalDetailDao.insertMany(collect['companyId'], details, keys=collect['keys_gun'], isPre=False)
            elif collect['finished_gun'] == 1 and count > 0:
                querySql = "SELECT COUNT(*) FROM lq_totalodds_gun_{0} WHERE oddsID={1}" \
                    .format(collect['companyId'], collect['oddsId'])
                count_local = cast(Tuple[Tuple[Any, ...], ...], LqTotalDetailDao.select(querySql))[0][0]
                if count > int(count_local):
                    details_new = details[count_local:]
                    LqTotalDetailDao.insertMany(collect['companyId'], details_new, keys=collect['keys_gun'],
                                                isPre=False)
            else:
                pass
            data = {'hasGun': collect['hasGun'], 'hasFirst': collect['hasFirst'], 'hasSecond': collect['hasSecond'],
                    'hasHalf': collect['hasHalf'], 'hasThird': collect['hasThird'], 'hasFour': collect['hasFour']}

            if collect['matchState'] in [-1, -4] and count > 0:
                data['finished_gun'] = 2
            elif collect['matchState'] in [-1, -4] and count == 0:
                data['finished_gun'] = 3
            LqTotalOddsDao.update(data, {'matchId': collect['matchId'], 'companyId': collect['companyId']})


# if __name__ == '__main__':
#     LqOddsService.upOdds()
#     matchTime = datetime.strptime('2025-08-09 07:30:00', "%Y-%m-%d %H:%M:%S")
#     crawler = Lq2in1Crawler(645719, 8, 645719, 0, 0, 4, matchTime,
#                             asian_finished_pre=0, asian_finished_gun=0,
#                             total_finished_pre=0, total_finished_gun=0)
#     collectData = crawler.qt_web_get(scope=2)
#     # print(collectData)
#     if 'total' in collectData.keys():
#         if 'gun' in collectData['total'].keys() and len(collectData['total']['gun'])>0:
#             scoreData = []
#             print(collectData['total']['gun'])
#             for item in collectData['total']['gun']:
#                 scoreData.append([])
#     # ['highOdds', 'goal', 'lowOdds', 'modifyTime', 'oddsType', 'isBet', 'matchState', 'happenTime', 'homeScore',
#     #  'awayScore', 'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind']
#     6,7,8,9,4
