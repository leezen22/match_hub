import threading
import time
from multiprocessing import Queue
from utils import sql_util
from utils.dateUtil import getNowTime
from zq.service.europe_odds import EuropeOddsZq
from zq.service.asian_odds import AsianOddsZq
from zq.service.total_odds import TotalOddsZq
from zq.service.zq_odds_detail import OddsDetailZq

total_detail_queue = Queue()
asian_detail_queue = Queue()
europe_detail_queue = Queue()

asian_oddsID_queue = Queue()
total_oddsID_queue = Queue()
europe_oddsID_queue = Queue()

product_alive = 0
asian_detail_alive = 0
total_detail_alive = 0
europe_detail_alive = 0


def task_upDetail_zq():
    global product_alive
    global asian_detail_alive
    global total_detail_alive
    global europe_detail_alive

    querySql = """SELECT euro.scheduleID, sche.matchTime, sche.matchState, 
    euro.companyID, euro.oddsID, euro.oddsID_Q, euro.finished_pre,euro.finished_gun,
    euro.hasPre, euro.hasIn, euro.hasFirst, euro.hasHalf, euro.hasSecond
    FROM zq_europe as euro LEFT JOIN zq_schedule as sche
    on euro.scheduleID = sche.scheduleID
    WHERE euro.companyID=545 and euro.finished_gun=0 
    and sche.matchState=-1 and sche.matchTime>='{0}' and sche.matchTime>='{1}'
    ORDER BY sche.matchTime desc
    """.format('2020-01-01 00:00', '2020-03-07 23:01')
    result = sql_util.select_Execute(querySql)
    companyID = 3

    product_alive = 1
    asian_detail_alive = 1
    total_detail_alive = 1
    europe_detail_alive = 1

    threads = []

    # 采集变化记录
    thread_name = "detail_product_local"
    # detail_product = threading.Thread(target=detailProduct, args=(result, companyID, thread_name, True))
    detail_product = threading.Thread(target=detailProduct_byEuro, args=(result, companyID, thread_name, True))
    threads.append(detail_product)

    # 让分变化记录
    asian_thread_name = 'asianConsumer'
    asian_detail_consumer = threading.Thread(target=AsianDetailConsumer, args=(asian_thread_name,))
    threads.append(asian_detail_consumer)
    # 大小变化记录
    total_thread_name = "totalConsumer"
    tot_detail_consumer = threading.Thread(target=TotalDetailConsumer, args=(total_thread_name,))
    threads.append(tot_detail_consumer)
    # 欧指变化记录
    europe_thread_name = "eurConsumer"
    europe_detail_consumer = threading.Thread(target=EuropeDetailConsumer, args=(europe_thread_name,))
    threads.append(europe_detail_consumer)

    #
    # # 更新采集状态
    # oddsID_consumer = threading.Thread(target=oddsIDConsumer, args=())
    # threads.append(oddsID_consumer)

    for t in threads:
        t.start()
    for t in threads:
        t.join()


def detailProduct_byEuro(europeList, companyID, threadName, isProxy=True, isDriver=False, proxy=None):
    global product_alive
    global total_detail_queue
    global asian_detail_queue
    global europe_detail_queue
    count = len(europeList)
    for europe in europeList:
        scheduleID = europe[0]
        matchTime = europe[1]
        matchState = europe[2]
        log = "{0}, {1}, {2}, {3}, {4}, {5}".format(count, getNowTime(), companyID, scheduleID, matchState, matchTime)
        print(log)
        collect = OddsDetailZq.get_detail_byEurope(companyID, europe)
        if 'asian' in collect:
            asian = collect['asian']
            finished_gun = asian['finished_gun']
            finished_pre = asian['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and asian['state'] == 1:
                data = ['asian生产完成', asian['scheduleID'], asian['companyID'], finished_pre, finished_gun, matchState,
                        '采集结果:',
                        asian['state'], "---", asian['hasPre'], asian['hasIn'], asian['hasFirst'], asian['hasSecond']]
                asian_detail_queue.put(asian)
            else:
                data = ['asian放弃生产', scheduleID, companyID, finished_pre, finished_gun, asian['state']]
            print(data)

        if 'total' in collect:
            total = collect['total']
            finished_gun = total['finished_gun']
            finished_pre = total['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and total['state'] == 1:
                data = ['total生产完成', total['scheduleID'], total['companyID'], finished_pre, finished_gun, matchState,
                        '采集结果:',
                        total['state'], "---", total['hasPre'], total['hasIn'], total['hasFirst'], total['hasSecond']]
                total_detail_queue.put(total)
            else:
                data = ['total放弃生产', scheduleID, companyID, finished_pre, finished_gun, total['state']]
            print(data)

        if 'europe' in collect:
            europe = collect['europe']
            finished_gun = europe['finished_gun']
            finished_pre = europe['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and europe['state'] == 1:
                data = ['eur生产完成', europe['scheduleID'], europe['companyID'], finished_pre, finished_gun, matchState,
                        '采集结果:', europe['state'], "---", europe['hasPre'], europe['hasIn'], europe['hasFirst'],
                        europe['hasSecond']]
                europe_detail_queue.put(europe)
            else:
                data = ['eur放弃生产', scheduleID, companyID, finished_pre, finished_gun, europe['state']]
            print(data)
        count = count - 1
        if europe_detail_queue.qsize() > 10:
            print("休息50秒")
            time.sleep(50)
    product_alive = product_alive - 1
    print(threadName, "完成任务推出")


def detailProduct(matchs, companyID, threadName, isProxy=True, isDriver=False, proxy=None):
    global product_alive
    global total_detail_queue
    global asian_detail_queue
    global europe_detail_queue

    count = len(matchs)

    for match in matchs:
        scheduleID = match[0]
        matchTime = match[1]
        matchState = match[2]
        log = "{0}, {1}, {2}, {3}, {4}, {5}".format(count, getNowTime(), companyID, scheduleID, matchState, matchTime)
        print(log)
        collect = OddsDetailZq.get_detail(scheduleID, companyID, matchTime, matchState)
        if 'asian' in collect:
            asian = collect['asian']
            finished_gun = asian['finished_gun']
            finished_pre = asian['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and asian['state'] == 1:
                data = ['asian生产完成', asian['scheduleID'], asian['companyID'], finished_pre, finished_gun, matchState,
                        '采集结果:',
                        asian['state'], "---", asian['hasPre'], asian['hasIn'], asian['hasFirst'], asian['hasSecond']]
                asian_detail_queue.put(asian)
            else:
                data = ['asian放弃生产', scheduleID, companyID, finished_pre, finished_gun, asian['state']]
            print(data)

        if 'total' in collect:
            total = collect['total']
            finished_gun = total['finished_gun']
            finished_pre = total['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and total['state'] == 1:
                data = ['total生产完成', total['scheduleID'], total['companyID'], finished_pre, finished_gun, matchState,
                        '采集结果:',
                        total['state'], "---", total['hasPre'], total['hasIn'], total['hasFirst'], total['hasSecond']]
                total_detail_queue.put(total)
            else:
                data = ['total放弃生产', scheduleID, companyID, finished_pre, finished_gun, total['state']]
            print(data)

        if 'europe' in collect:
            europe = collect['europe']
            finished_gun = europe['finished_gun']
            finished_pre = europe['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and europe['state'] == 1:
                data = ['eur生产完成', europe['scheduleID'], europe['companyID'], finished_pre, finished_gun, matchState,
                        '采集结果:', europe['state'], "---", europe['hasPre'], europe['hasIn'], europe['hasFirst'],
                        europe['hasSecond']]
                europe_detail_queue.put(europe)
            else:
                data = ['eur放弃生产', scheduleID, companyID, finished_pre, finished_gun, europe['state']]
            print(data)
        count = count - 1
        if europe_detail_queue.qsize() > 10:
            print("休息50秒")
            time.sleep(50)
    product_alive = product_alive - 1
    print(threadName, "完成任务推出")


def AsianDetailConsumer(thread_name):
    global asian_detail_queue
    global product_alive
    global asian_detail_alive
    count = 5
    while count > 0:
        if not asian_detail_queue.empty():
            data = asian_detail_queue.get()
            log = [' asian消费', data['scheduleID'], data['companyID'], data['state'],
                   '剩余：', asian_detail_queue.qsize()]
            print(log)
            AsianOddsZq.up_AsianDetail(data, 2)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    asian_detail_alive = asian_detail_alive - 1


def TotalDetailConsumer(thread_name):
    global total_detail_queue
    global product_alive
    global total_detail_alive
    count = 5
    while count > 0:
        if not total_detail_queue.empty():
            data = total_detail_queue.get()
            log = [' total消费', data['scheduleID'], data['companyID'], data['state'],
                   '剩余：', asian_detail_queue.qsize()]
            print(log)
            TotalOddsZq.up_totalDetail(data, 2)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    total_detail_alive = total_detail_alive - 1


def EuropeDetailConsumer(thread_name):
    global europe_detail_queue
    global product_alive
    global europe_detail_alive
    count = 5
    while count > 0:
        if not europe_detail_queue.empty():
            data = europe_detail_queue.get()
            log = [' eur消费', data['scheduleID'], data['companyID'], data['state'],
                   '剩余：', europe_detail_queue.qsize()]
            print(log)
            EuropeOddsZq.up_europeDetail(data, 2)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    europe_detail_alive = europe_detail_alive - 1

    # querySql = "SELECT scheduleID,matchTime,matchState FROM zq_schedule " \
    #            "WHERE " \
    #            "matchTime >= '{0}' and matchTime<'{1}' and matchState=-1 " \
    #            "and (asianOdds_f in(1,2) or totalOdds_f in(1,2) and eurOdds_f in(1,2)) " \
    #            "order by matchTime DESC".format('2020-01-01 00:00', '2020-03-07 23:01')


# if __name__ == '__main__':
#     task_upDetail_zq()
