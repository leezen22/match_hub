import datetime
import random
import threading
import time

from crawler.qt.zq_3in1_detail_crawler import DetailCrawler
from multiprocessing import Queue
from config import zqconfig_qt
from utils import sql_util
from utils.dateUtil import getNowTime
from utils.js2pyUtil import jsLocjs
from utils.proxyTools import ProxyTools
from utils.webDriver import WebDriver
from zq.oddsUtil_zq import OddsUtil
from zq.service.asian_odds import AsianOddsZq
from zq.service.total_odds import TotalOddsZq

number_alive = 0
asia_queue = Queue()
total_queue = Queue()


def task_upodds():
    global number_alive
    count_http = sql_util.select('SELECT COUNT(*) FROM proxyip WHERE http_state IN(1,2) and abandon_http=0 ')
    count_driver = sql_util.select('SELECT COUNT(*) FROM proxyip WHERE availableDriver IN(1) and used_driver=0 ')
    print({'Http代理IP': count_http[0][0], 'Driver代理IP': count_driver[0][0]})
    task_type = input("请输入采集方式：1 Http采集赔率 , 2 driver采集赔率 3 两者并行 ")
    if task_type == '1':
        Http_count = input("请输入Http采集器数量：")
    elif task_type == '2':
        driver_count = input("请输入浏览器采集器数量：")
    elif task_type == '3':
        Http_count = input("请输入Http采集器数量：")
        driver_count = input("请输入浏览器采集器数量：")
        factor_input = input("请输入浏览器加倍因子：")
    else:
        pass
    leagues = [{"leagueID": "67", "nameChsShort": "欧洲杯"}, {"leagueID": "10", "nameChsShort": "俄超"}]
    print(str(leagues))
    leagueid = input("请输入采集联赛ID：")
    if leagueid != '0':
        filepath = zqconfig_qt.seajslocaldir + "sea" + str(leagueid) + ".js"
        context = jsLocjs(filepath)
        seasons = list(context.arrSeason)
        print([len(seasons), seasons])
        number_input = input("请输入联赛赛季采集数量：")
        number_season = int(number_input)
        if len(seasons) > number_season:
            target = seasons[0:number_season]
        else:
            target = seasons[0:len(seasons)]
        if len(target) == 1:
            target_str = "('" + target[0] + "')"
        else:
            target_str = str(tuple(target))
        print(target_str)
        sql = " SELECT sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.leagueId,sche.subLeagueID," \
              "lea.type,sche.partscore_f,sche.asianOdds_f,sche.totalodds_f,sche.HomeTeam,sche.AwayTeam FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea " \
              "ON sche.LeagueID =lea.LeagueID WHERE sche.LeagueID={0} AND MatchSeason in {1}  AND sche.MatchState=-1 AND (sche.asianodds_f IN(0,1) " \
              "OR sche.totalodds_f IN(0,1)) ORDER BY sche.MatchTime ASC ".format(leagueid, target_str)
    else:
        sql = " SELECT sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.leagueId,sche.subLeagueID," \
              "lea.type,sche.partscore_f,sche.asianOdds_f,sche.totalodds_f,sche.HomeTeam,sche.AwayTeam " \
              "FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID =lea.LeagueID " \
              "WHERE MatchTime>='2024-01-01 00:00:00' and sche.MatchState=-1 " \
              "and (sche.asianOdds_f IN(0,1) OR sche.totalodds_f IN(0,1)) " \
              "ORDER BY sche.MatchTime DESC "

    matchs = sql_util.select(sql)
    count = len(matchs)
    print(len(matchs), sql)

    threads = []
    if task_type == '1':
        number_http = int(Http_count)
        cell = count // number_http
        for i in range(0, number_http):
            start = i * cell
            if i < number_http - 1:
                end = (i + 1) * cell
            else:
                end = count
            matchs_cell = matchs[start:end]
            thread_name = "http" + str(i)
            odds_thread = threading.Thread(target=OddsProduct, args=(matchs_cell, thread_name))
            threads.append(odds_thread)
    elif task_type == '2':
        number_driver = int(driver_count)
        sql_util.upData('proxyip', {'used_driver': 0}, {'used_driver': 1})
        proxys = ProxyTools.get_driver_proxys(number_driver)
        if len(proxys) < number_driver:
            number_driver = len(proxys)
        number_alive = number_driver
        # 份数
        parts = number_driver
        cell = count // parts
        for i in range(0, number_driver):
            start = i * cell
            if i < number_driver - 1:
                end = start + cell
            else:
                end = count
            proxy = proxys[i]
            matchs_cell = matchs[start:end]
            thread_name = "driver" + str(i)
            print(thread_name, start, end)
            odds_thread = threading.Thread(target=OddsProduct, args=(matchs_cell, thread_name, True, True, proxy,))
            threads.append(odds_thread)
    elif task_type == '3':
        factor = int(factor_input)
        number_http = int(Http_count)
        number_driver = int(driver_count)
        sql_util.upData('proxyip', {'used_driver': 0}, {'used_driver': 1})
        proxys = ProxyTools.get_driver_proxys(number_driver)
        if len(proxys) < number_driver:
            number_driver = len(proxys)
        number = number_driver + number_http
        number_alive = number_driver + number_http + 1
        # 份数
        parts = (number_driver + 1) * factor + number_http
        cell = count // parts
        start_local = number_driver * cell * factor + number_http * cell
        end_local = count
        matchs_local = matchs[start_local:end_local]
        print(['本地', start_local, end_local])
        odds_thread = threading.Thread(target=OddsProduct, args=(matchs_local, 'localdriver', True, False,))
        threads.append(odds_thread)

        for i in range(0, number_driver):
            start = i * cell * factor
            end = start + cell * factor
            proxy = proxys[i]
            matchs_cell = matchs[start:end]
            thread_name = "driver" + str(i)
            print(thread_name, start, end)
            odds_thread = threading.Thread(target=OddsProduct, args=(matchs_cell, thread_name, True, True, proxy,))
            threads.append(odds_thread)

        for i in range(0, number_http):
            start = number_driver * cell * factor + i * cell
            end = start + cell
            # if i < number_http-1:
            #     end = start + cell
            # else:
            #     end = count
            matchs_cell = matchs[start:end]
            thread_name = "http" + str(i)
            print(thread_name, start, end)
            odds_thread = threading.Thread(target=OddsProduct, args=(matchs_cell, thread_name))
            threads.append(odds_thread)
    odds_asian_conssumer = threading.Thread(target=asia_odds_consumer, args=('casian',))
    threads.append(odds_asian_conssumer)
    odds_total_conssumer = threading.Thread(target=total_odds_consumer, args=('ctotal',))
    threads.append(odds_total_conssumer)
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def OddsProduct(matchs, name, isdriver=False, isproxy=True, proxy=None):
    global asia_queue
    global total_queue
    global number_alive
    count_match = len(matchs)
    if isdriver and (proxy is None or isproxy is False):
        driver = WebDriver.get_driver(timeout=20)
    elif isdriver and proxy:
        driver = WebDriver.get_driver(proxy, timeout=20)
    else:
        driver = None
    for match in matchs:
        if driver:
            seconds = random.randint(2, 4)
        else:
            seconds = random.randint(2, 3)
        time.sleep(seconds)
        # print([gettime(), i, count, asia_queue.qsize(), total_queue.qsize(), match])
        matchid = match[0]
        finished_asian = match[8]
        finished_total = match[9]
        matchstate = match[2]
        # state_code 2 不处理
        result_asian = {'state_asian': 2, 'matchid': matchid, 'match_state': matchstate, 'asian_f': finished_asian,
                      'odds_asian': []}
        result_total = {'state_total': 2, 'matchid': matchid, 'match_state': matchstate, 'total_f': finished_total,
                        'odds_total': []}

        data_asian = AsianOddsZq.get_asian_odds(match, driver, isproxy=isproxy, proxy=proxy)
        print([getNowTime(), name, count_match, asia_queue.qsize(), total_queue.qsize(), '让分', matchid,
               data_asian['state']])
        time.sleep(seconds)
        data_total = TotalOddsZq.get_total_odds(match, driver, isproxy=isproxy, proxy=proxy)
        print(
            [getNowTime(), name, count_match, asia_queue.qsize(), total_queue.qsize(), '大小', matchid,
             data_total['state']])
        if data_asian['state'] == 1:
            result_asian['state_asian'] = data_asian['state']
            result_asian['odds_asian'] = data_asian['odds']
            asia_queue.put(result_asian)
            # print("{0} 生产者{1}生产亚指：{2}".format(gettime(),i, result_asian))
        if data_total['state'] == 1:
            result_total['state_total'] = data_total['state']
            result_total['odds_total'] = data_total['odds']
            total_queue.put(result_total)
            # print("{0} 生产者{1}生产大小：{2}".format(gettime(),i, result_total))
        if data_total['state'] == 0 and isdriver and isproxy is True:
            if proxy:
                ip = proxy.split(":")[0]
                sql_util.upData('proxyip', {'availableDriver': 3, 'used_driver': 0}, {'ip': ip})
            if driver:
                driver.quit()
            driver = None
            # retry = 60
            while isdriver is True and driver is None:
                proxy = ProxyTools.get_driver_proxy()
                if proxy:
                    driver = WebDriver.get_driver(proxy, timeout=6)
                else:
                    sql = "UPDATE proxyip SET availableDriver=1,abandon_driver=0 WHERE id in(85,86,1498, 1627, 1680,3865,3878,3938,3994,3996,3999,4009,4042,4400,4679,4775,4874, 4990, 5021, 5197,5338,5446,5605, 5838, 6108,6224,6437,6511,7436,7447,7449,7475,7482)"
                    sql_util.sqlExecute(sql)
                    # print("driver无可用代理")
                    # retry = retry-1
                    # if retry == 0:
                    #     number_alive = number_alive - 1
                    #     return
                    # time.sleep(60)
        count_match = count_match - 1
    if driver:
        driver.quit()
    number_alive = number_alive - 1
    print(name, "完成任务推出")


def asia_odds_consumer(i):
    global asia_queue
    global number_alive
    count = 5
    time.sleep(10)
    while count > 0:
        # print(i,'asian', count, number_alive)
        if not asia_queue.empty():
            res = asia_queue.get()
            # print('{0} 消费者{3}亚指剩余{1}：{2}'.format(gettime(), asia_queue.qsize(), len(res['odds_asian']), i))
            matchid = res['matchid']
            matchstate = res['match_state']
            if res['state_asian'] == 1:
                OddsUtil.up_asia_odds(matchid, res['asian_f'], matchstate, res['odds_asian'])
        # time.sleep(random.randint(1, 3))
        elif number_alive == 0:
            count = count - 1
        else:
            time.sleep(20)
        # time.sleep(1)


def total_odds_consumer(i):
    global total_queue
    global number_alive
    count = 5
    time.sleep(10)
    while count > 0:
        # print(i,'total',count,number_alive)
        if not total_queue.empty():
            res = total_queue.get()
            # print('{0} 消费者{3}大小分剩余{1}：{2}'.format(gettime(), total_queue.qsize(), len(res['odds_total']),i))
            matchid = res['matchid']
            matchstate = res['match_state']
            if res['state_total'] == 1:
                OddsUtil.up_total_dds(matchid, res['total_f'], matchstate, res['odds_total'])
        # time.sleep(random.randint(1, 3))
        elif number_alive == 0:
            count = count - 1
        else:
            time.sleep(20)
        # time.sleep(1)


def upAsianTotalDetails(companyID, startTime):

    start_str = "AND zc.matchTime>='{0}'".format(startTime)
    sql = "SELECT zt.matchID,zt.scheduleID,zc.matchState,zc.matchTime,zt.companyID," \
          "zt.oddsID as ztoddsID,zt.finished_pre as zt_pre,zt.finished_gun as zt_gun," \
          "za.oddsID as zaoddsID,za.finished_pre as za_pre,za.finished_gun as za_gun " \
          "FROM zq_totalscore as zt " \
          "LEFT JOIN zq_schedule as zc on zt.scheduleID = zc.scheduleID " \
          "LEFT JOIN zq_asianodds as za on za.scheduleID = zt.scheduleID and zt.companyID = za.companyID " \
          "WHERE zt.companyID={0} {1} and matchState =-1 "\
          "AND (zt.finished_pre in (0,1) or zt.finished_gun in (0,1) or za.finished_pre in (0,1) or za.finished_gun in (0,1)) " \
          "ORDER BY zc.matchTime ASC".format(companyID, start_str)

    results = sql_util.select(sql)
    print("开始更新变化记录：{0}".format(len(results)))
    for item in results:
        print(item)
        detailCrawler = DetailCrawler(item[4], item[0], item[1], matchState=item[2], matchTime=item[3],
                                      total_oddsId=item[5], total_finished_pre=item[6], total_finished_gun=item[7],
                                      asian_oddsId=item[8], asian_finished_pre=item[9], asian_finished_gun=item[10])
        data = detailCrawler.qt_web_get(3, True, True, False)
        if data['state'] == 1:
            if detailCrawler.asian_oddsId and (detailCrawler.asian_finished_pre in [0,1] or detailCrawler.asian_finished_gun in [0,1]):
                AsianOddsZq.up_AsianDetail(data['asian'], 2)
            if detailCrawler.total_oddsId and (detailCrawler.total_finished_pre in [0,1] or detailCrawler.total_finished_gun in [0,1]):
                TotalOddsZq.up_totalDetail(data['total'], 2)
        # time.sleep(1)


# if __name__ == '__main__':
#     upAsianTotalDetails('2023-06-01 00:00:00')
#     item = [1665552, 2394361, -1, datetime.datetime(2023, 6, 1, 0, 45), 3, 5550324, 1, 2, 5448345, 2, 2]
#     detailCrawler = DetailCrawler(item[4], item[0], item[1], matchState=item[2], matchTime=item[3],
#                                   total_oddsId=item[5], total_finished_pre=item[6], total_finished_gun=item[7],
#                                   asian_oddsId=item[8], asian_finished_pre=item[9], asian_finished_gun=item[10])
#     data = detailCrawler.qt_web_get(3, True, True, False)
#     AsianOddsZq.up_totalDetail(data['asian'], 2)