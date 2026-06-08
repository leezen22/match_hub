import threading
import time
from multiprocessing import Queue

from config import common_config
from utils import sql_util
from utils.dateUtil import getNowTime
from utils.js2pyUtil import logLine
from zq.service.europe_odds import EuropeOddsZq
from zq.service.asian_odds import AsianOddsZq
from zq.service.total_odds import TotalOddsZq
from zq.service.zq_odds_detail import OddsDetailZq

product_alive = 0
asian_detail_queue = Queue()
asian_oddsID_queue = Queue()
asian_detail_alive = 0
asian_detail_count = 0

total_detail_queue = Queue()
total_oddsID_queue = Queue()
total_detail_alive = 0
total_detail_count = 0

europe_detail_queue = Queue()
europe_detail_alive = 0
europe_oddsID_queue = Queue()
europe_detail_count = 0


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
    WHERE euro.companyID=545 and euro.finished_gun=0  and euro.finished_pre=0 
    and sche.matchState=-1 and sche.matchTime>='{0}' and sche.matchTime <'{1}'
    ORDER BY sche.matchTime desc
    """.format('2019-06-01 00:00', '2020-01-01 00:00')
    result = sql_util.select_Execute(querySql)
    companyID = 3

    product_alive = 2
    asian_detail_alive = 1
    total_detail_alive = 1
    europe_detail_alive = 1

    threads = []

    count = len(result)
    part = count // 4

    # 采集变化记录
    # thread_name = "detail_product_local"
    # detail_product = threading.Thread(target=detailProduct_byEuro, args=(result, companyID, thread_name, False))
    # threads.append(detail_product)
    thread_name = "DetailProduct 1"
    detail_product1 = threading.Thread(target=detailProduct_byEuro, args=(result[0:part], companyID, thread_name, True))
    threads.append(detail_product1)
    thread_name = "DetailProduct 2"
    detail_product2 = threading.Thread(target=detailProduct_byEuro,
                                       args=(result[part:part * 2], companyID, thread_name, True))
    threads.append(detail_product2)
    thread_name = "DetailProduct 3"
    detail_product3 = threading.Thread(target=detailProduct_byEuro,
                                       args=(result[part * 2:part * 3], companyID, thread_name, True))
    threads.append(detail_product3)
    thread_name = "DetailProduct 4"
    detail_product4 = threading.Thread(target=detailProduct_byEuro,
                                       args=(result[part * 3:], companyID, thread_name, True))
    threads.append(detail_product4)

    # 让分变化记录
    asian_thread_name = 'asianConsumer'
    asian_detail_consumer = threading.Thread(target=AsianDetailConsumer, args=(asian_thread_name,))
    threads.append(asian_detail_consumer)
    # 大小变化记录
    total_thread_name = "totConsumer"
    tot_detail_consumer = threading.Thread(target=TotalDetailConsumer, args=(total_thread_name,))
    threads.append(tot_detail_consumer)
    # 欧指变化记录
    europe_thread_name = "eurConsumer"
    europe_detail_consumer = threading.Thread(target=EuropeDetailConsumer, args=(europe_thread_name,))
    threads.append(europe_detail_consumer)

    # 让分变化记录
    asian_oddsID_consumer = threading.Thread(target=AsianOddsIDConsumer, args=())
    threads.append(asian_oddsID_consumer)
    # 大小变化记录
    tot_oddsID_consumer = threading.Thread(target=TotalOddsIDConsumer, args=())
    threads.append(tot_oddsID_consumer)
    # 欧指变化记录
    europe_oddsID_consumer = threading.Thread(target=EuropeOddsIDConsumer, args=())
    threads.append(europe_oddsID_consumer)

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
        log = "{0}, {1}, {2}, {3}, {4}, {5}, {6}".format(threadName, count, getNowTime(), companyID,
                                                         scheduleID, matchState, matchTime)
        print(log)
        collect = OddsDetailZq.get_detail_byEurope(companyID, europe, isProxy)
        if 'asian' in collect:
            asian = collect['asian']
            finished_gun = asian['finished_gun']
            finished_pre = asian['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and asian['state'] == 1:
                data = ['asian生产完成', asian['scheduleID'], asian['companyID'], asian['oddsID'], finished_pre, finished_gun,
                        matchState,
                        '采集结果:',
                        asian['state'], "---", asian['hasPre'], asian['hasIn'], asian['hasFirst'], asian['hasSecond']]
                asian_detail_queue.put(asian)
                print(threadName, data)
            else:
                data = ['asian放弃生产', scheduleID, companyID, finished_pre, finished_gun, asian['state']]
            # print(data)

        if 'total' in collect:
            total = collect['total']
            finished_gun = total['finished_gun']
            finished_pre = total['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and total['state'] == 1:
                data = ['tot生产完成', total['scheduleID'], total['companyID'], total['oddsID'], finished_pre, finished_gun,
                        matchState,
                        '采集结果:',
                        total['state'], "---", total['hasPre'], total['hasIn'], total['hasFirst'], total['hasSecond']]
                total_detail_queue.put(total)
                print(threadName, data)
            else:
                data = ['tot放弃生产', scheduleID, companyID, finished_pre, finished_gun, total['state']]
            # print(data)

        if 'europe' in collect:
            europe = collect['europe']
            finished_gun = europe['finished_gun']
            finished_pre = europe['finished_pre']
            if (finished_gun is not None) and (finished_gun in [0, 1]) and europe['state'] == 1:
                data = ['eur生产完成', europe['scheduleID'], europe['companyID'], europe['oddsID'], finished_pre,
                        finished_gun, matchState,
                        '采集结果:', europe['state'], "---", europe['hasPre'], europe['hasIn'], europe['hasFirst'],
                        europe['hasSecond']]
                europe_detail_queue.put(europe)
                print(threadName, data)
            else:
                data = ['eur放弃生产', scheduleID, companyID, finished_pre, finished_gun, europe['state']]
            # print(data)
        count = count - 1
    product_alive = product_alive - 1
    print(threadName, "完成任务推出")


def AsianDetailConsumer(thread_name):
    global asian_detail_queue
    global product_alive
    global asian_detail_alive
    global asian_oddsID_queue

    count = 5
    while count > 0:
        batch_data = {'detail': [], 'oddsIDS': []}
        count_detail_batch = 0
        while not asian_detail_queue.empty() and count_detail_batch < 5000:
            data = asian_detail_queue.get()
            log = [getNowTime(), ' asian消费', data['scheduleID'], data['oddsID'], data['companyID'], data['state'],
                   data['finished_pre'], data['finished_gun'], '剩余', asian_detail_queue.qsize(),
                   len(batch_data['detail'])]
            print(log)
            finished_pre = data['finished_pre']
            finished_gun = data['finished_gun']
            if finished_pre == 0 and finished_gun == 0:
                matchState = data['matchState']
                scheduleID = data['scheduleID']
                companyID = data['companyID']
                oddsID = data['oddsID']
                hasPre = data['hasPre']
                hasIn = data['hasIn']
                hasFirst = data['hasFirst']
                hasHalf = data['hasHalf']
                hasSecond = data['hasSecond']
                oddsID_data = [scheduleID, matchState, companyID, oddsID, finished_pre, finished_gun,
                               hasPre, hasIn, hasFirst, hasHalf, hasSecond]
                details = data['detail']['pre'] + data['detail']['in']
                batch_data['detail'] = batch_data['detail'] + details
                batch_data['oddsIDS'].append(oddsID_data)
            else:
                print("让分单场更新")
                AsianOddsZq.up_AsianDetail(data, 2)
        if len(batch_data['oddsIDS']) > 0:
            # print("让分本轮结束,开始批量插入更新")
            # isUP = True
            logLine(common_config.zq_oddsdetail_asian, batch_data['oddsIDS'])
            isUP = AsianOddsZq.insert_asianDetail_batch(batch_data['detail'], 2)
            if isUP:
                for item in batch_data['oddsIDS']:
                    asian_oddsID_queue.put(item)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    asian_detail_alive = asian_detail_alive - 1


def TotalDetailConsumer(thread_name):
    global total_detail_queue
    global product_alive
    global total_detail_alive
    global total_oddsID_queue

    count = 5
    while count > 0:
        batch_data = {'detail': [], 'oddsIDS': []}
        count_detail_batch = 0
        while not total_detail_queue.empty() and count_detail_batch < 5000:
            data = total_detail_queue.get()
            log = [getNowTime(), ' tot消费', data['scheduleID'], data['oddsID'], data['companyID'], data['state'],
                   data['finished_pre'],
                   data['finished_gun'], '剩余：', total_detail_queue.qsize(), len(batch_data['detail'])]
            print(log)
            finished_pre = data['finished_pre']
            finished_gun = data['finished_gun']
            if finished_pre == 0 and finished_gun == 0:
                matchState = data['matchState']
                scheduleID = data['scheduleID']
                companyID = data['companyID']
                oddsID = data['oddsID']
                hasPre = data['hasPre']
                hasIn = data['hasIn']
                hasFirst = data['hasFirst']
                hasHalf = data['hasHalf']
                hasSecond = data['hasSecond']
                oddsID_data = [scheduleID, matchState, companyID, oddsID, finished_pre, finished_gun,
                               hasPre, hasIn, hasFirst, hasHalf, hasSecond]
                details = data['detail']['pre'] + data['detail']['in']
                batch_data['detail'] = batch_data['detail'] + details
                batch_data['oddsIDS'].append(oddsID_data)
            else:
                print("大小单场更新")
                TotalOddsZq.up_totalDetail(data, 2)
        if len(batch_data['oddsIDS']) > 0:
            # print("大小本轮结束,开始批量插入更新")
            # isUP = True
            logLine(common_config.zq_oddsdetail_total, batch_data['oddsIDS'])
            isUP = TotalOddsZq.insert_totalDetail_batch(batch_data['detail'], 2)
            if isUP:
                for item in batch_data['oddsIDS']:
                    total_oddsID_queue.put(item)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    total_detail_alive = total_detail_alive - 1


def EuropeDetailConsumer(thread_name):
    global europe_detail_queue
    global product_alive
    global europe_detail_alive
    global europe_oddsID_queue

    count = 5
    while count > 0:
        batch_data = {'detail': [], 'oddsIDS': []}
        count_detail_batch = 0
        while not europe_detail_queue.empty() and count_detail_batch < 5000:
            data = europe_detail_queue.get()
            log = [getNowTime(), ' eur消费', data['scheduleID'], data['oddsID'], data['companyID'], data['state'],
                   data['finished_pre'],
                   data['finished_gun'], '剩余：', europe_detail_queue.qsize(), len(batch_data['detail'])]
            print(log)
            finished_pre = data['finished_pre']
            finished_gun = data['finished_gun']
            if finished_pre == 0 and finished_gun == 0:
                matchState = data['matchState']
                scheduleID = data['scheduleID']
                companyID = data['companyID']
                oddsID = data['oddsID']
                hasPre = data['hasPre']
                hasIn = data['hasIn']
                hasFirst = data['hasFirst']
                hasHalf = data['hasHalf']
                hasSecond = data['hasSecond']
                oddsID_data = [scheduleID, matchState, companyID, oddsID, finished_pre, finished_gun,
                               hasPre, hasIn, hasFirst, hasHalf, hasSecond]
                details = data['detail']['pre'] + data['detail']['in']
                batch_data['detail'] = batch_data['detail'] + details
                batch_data['oddsIDS'].append(oddsID_data)
            else:
                print("欧指单场更新")
                EuropeOddsZq.up_europeDetail(data, 2)
        if len(batch_data['oddsIDS']) > 0:
            # print("欧指本轮结束,开始批量插入更新")
            # isUP = True
            logLine(common_config.zq_oddsdetail_europe, batch_data['oddsIDS'])
            isUP = EuropeOddsZq.insert_europeDetail_batch(batch_data['detail'], 2)
            if isUP:
                for item in batch_data['oddsIDS']:
                    europe_oddsID_queue.put(item)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    europe_detail_alive = europe_detail_alive - 1


def AsianOddsIDConsumer():
    global asian_oddsID_queue
    global asian_detail_alive

    count = 5
    while count > 0:
        if not asian_oddsID_queue.empty():
            item = asian_oddsID_queue.get()
            scheduleID = item[0]
            matchState = item[1]
            oddsID = item[3]
            finished_pre = item[4]
            finished_gun = item[5]
            hasPre = item[6]
            hasIn = item[7]
            hasFirst = item[8]
            hasHalf = item[9]
            hasSecond = item[10]
            if matchState == -1 or matchState == -10:
                if hasIn == 0:
                    finished_gun = 3
                else:
                    finished_gun = 2
                if hasPre == 1:
                    finished_pre = 2
                sql_util.upData('zq_AsianOdds',
                                {'finished_pre': finished_pre, 'finished_gun': finished_gun, 'hasPre': hasPre,
                                 'hasIn': hasIn, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})
                print("让分完场",
                      [scheduleID, oddsID, finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond])
            else:

                sql_util.upData('zq_AsianOdds',
                                {'finished_pre': 1, 'finished_gun': 1, 'hasPre': hasPre,
                                 'hasIn': hasIn, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})
                print("让分未完场",
                      [scheduleID, oddsID, finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond])

        elif asian_detail_alive == 0:
            count = count - 1
        else:
            time.sleep(5)
    print(getNowTime(), "AsianOddsIDConsumer 完成任务退出")


def TotalOddsIDConsumer():
    global total_oddsID_queue
    global total_detail_alive
    count = 5
    while count > 0:
        if not total_oddsID_queue.empty():
            item = total_oddsID_queue.get()
            scheduleID = item[0]
            matchState = item[1]
            oddsID = item[3]
            finished_pre = item[4]
            finished_gun = item[5]
            hasPre = item[6]
            hasIn = item[7]
            hasFirst = item[8]
            hasHalf = item[9]
            hasSecond = item[10]
            if matchState == -1 or matchState == -10:
                if hasIn == 0:
                    finished_gun = 3
                else:
                    finished_gun = 2
                if hasPre == 1:
                    finished_pre = 2
                sql_util.upData('zq_TotalScore',
                                {'finished_pre': finished_pre, 'finished_gun': finished_gun, 'hasPre': hasPre,
                                 'hasIn': hasIn, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})
                print("大小完场",
                      [scheduleID, oddsID, finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond])
            else:
                print("大小未完场",
                      [scheduleID, oddsID, finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond])
                sql_util.upData('zq_TotalScore',
                                {'finished_pre': 1, 'finished_gun': 1, 'hasPre': hasPre,
                                 'hasIn': hasIn, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})

        elif total_detail_alive == 0:
            count = count - 1
        else:
            time.sleep(5)
    print(getNowTime(), "TotalOddsIDConsumer 完成任务退出")


def EuropeOddsIDConsumer():
    global europe_oddsID_queue
    global europe_detail_alive

    count = 5
    while count > 0:
        if not europe_oddsID_queue.empty():
            item = europe_oddsID_queue.get()
            scheduleID = item[0]
            matchState = item[1]
            oddsID = item[3]
            finished_pre = item[4]
            finished_gun = item[5]
            hasPre = item[6]
            hasIn = item[7]
            hasFirst = item[8]
            hasHalf = item[9]
            hasSecond = item[10]
            if matchState == -1 or matchState == -10:
                if hasIn == 0:
                    finished_gun = 3
                else:
                    finished_gun = 2
                if hasPre == 1:
                    finished_pre = 2
                sql_util.upData('zq_europe',
                                {'finished_pre': finished_pre, 'finished_gun': finished_gun, 'hasPre': hasPre,
                                 'hasIn': hasIn, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})
                print("欧指完场",
                      [scheduleID, oddsID, finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond])

            else:
                sql_util.upData('zq_europe',
                                {'finished_pre': 1, 'finished_gun': 1, 'hasPre': hasPre,
                                 'hasIn': hasIn, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})
                print("欧指未完场",
                      [scheduleID, oddsID, finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond])

        elif europe_detail_alive == 0:
            count = count - 1
        else:
            time.sleep(5)
    print(getNowTime(), "EuropeOddsIDConsumer 完成任务退出")


# if __name__ == '__main__':
    # task_upDetail_zq()
