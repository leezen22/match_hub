import threading
import time
from multiprocessing import Queue

from utils import sql_util
from utils.dateUtil import getNowTime
from zq.service.asian_odds import AsianOddsZq

asian_queue = Queue()
oddsID_queue = Queue()
product_alive = 0
detail_alive = 0


def task_up_detail():
    global product_alive
    global detail_alive

    querySql = """ SELECT 
                      asian.oddsID, asian.scheduleID, asian.companyID, 
                      asian.finished_pre, asian.finished_gun, 
                      sche.matchState 
                   FROM
                      zq_AsianOdds asian 
                      LEFT JOIN zq_schedule sche 
                      ON sche.scheduleID =asian.scheduleID 
                   WHERE asian.companyID = {0}
                      AND asian.finished_gun = 0 
                      AND sche.matchTime >= '{1}'
                      AND sche.matchTime < '{2}'
                      AND sche.matchState = - 1 """.format(3, '2018-01-01 00:00', '2019-01-01 00:00')
    result = sql_util.select_rows(querySql)
    count = len(result)
    print('任务数量：', count)

    product_alive = 1
    detail_alive = 1
    threads = []

    # 采集变化记录
    thread_name = "detail_product_local"
    detail_product = threading.Thread(target=detailProduct, args=(result, thread_name, False))
    threads.append(detail_product)

    # # 更新变化记录和采集状态
    # for i in range(0, 5):
    #     thread_name = 'consumer'+str(i)
    #     detail_consumer = threading.Thread(target=detailConsumer, args=(thread_name,))
    #     threads.append(detail_consumer)

    # 更新变化记录
    detail_consumer = threading.Thread(target=detailConsumer2, args=())
    threads.append(detail_consumer)

    # 更新采集状态
    oddsID_consumer = threading.Thread(target=oddsIDConsumer, args=())
    threads.append(oddsID_consumer)

    for t in threads:
        t.start()
    for t in threads:
        t.join()


def detailProduct(oddsDataList, name, isProxy=True, isDriver=False, proxy=None):
    global asian_queue
    global product_alive

    count = len(oddsDataList)
    for item in oddsDataList:
        # print(gettime(), "数据待采集：", count)
        finished_gun = item[4]
        data = AsianOddsZq.get_deail(item[0], item[1], item[2], item[3], item[4], isproxy=isProxy)
        detail_count = len(data['detail'])
        print([getNowTime(), name, count, '让分变化记录', item[0], item[1], item[2], data['state'], detail_count])
        if data['state'] == 1:
            if finished_gun == 0 and detail_count > 0:
                data['matchState'] = item[5]
                asian_queue.put(data)
        count = count - 1
    product_alive = product_alive - 1
    print(name, "完成任务推出")


def detailConsumer(thread_name):
    global asian_queue
    global product_alive
    global detail_alive
    count = 5
    while count > 0:
        print("采集数据待更新(份)：", asian_queue.qsize())
        if not asian_queue.empty():
            data = asian_queue.get()
            AsianOddsZq.up_asian_detail(data, 2)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    detail_alive = detail_alive - 1


def detailConsumer2():
    global asian_queue
    global product_alive
    global detail_alive
    global oddsID_queue
    count = 5
    while count > 0:
        print(getNowTime(), "采集数据待更新(份)：", asian_queue.qsize())
        data = {'detail': [], 'oddsIDList': []}
        count_detail = 0
        while not asian_queue.empty() and count_detail < 10000:
            item = asian_queue.get()
            detail = item['detail']
            data['detail'] = data['detail'] + detail
            count_detail = count_detail + len(detail)

            oddsID = item['oddsID']
            matchState = item['matchState']
            finished_gun = item['finished_gun']
            finished_pre = item['finished_pre']
            oddsID_data = {'oddsID': oddsID, 'matchState': matchState, 'finished_gun': finished_gun,
                           'finished_pre': finished_pre}
            data['oddsIDList'].append(oddsID_data)
            # print("本次已接收", len(data['detail']), len(data['oddsIDList']))
        if len(data['oddsIDList']) > 0:
            result = AsianOddsZq.up_asian_details(data, 2)
            if result['isUP']:
                oddsID_queue.put(result['oddsIDList'])
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    detail_alive = detail_alive - 1


def oddsIDConsumer():
    global oddsID_queue
    global detail_alive
    count = 5
    while count > 0:
        print("采集状态待更新，剩余：", oddsID_queue.qsize())
        if not oddsID_queue.empty():
            data = oddsID_queue.get()
            for item in data:
                oddsID = item['oddsID']
                if item['matchState'] == -1 or item['matchState'] == -10:
                    sql_util.upData('zq_AsianOdds', {'finished_pre': 2, 'finished_gun': 2}, {'oddsID': oddsID})
                else:
                    sql_util.upData('zq_AsianOdds', {'finished_pre': 1, 'finished_gun': 1}, {'oddsID': oddsID})
        elif detail_alive == 0:
            count = count - 1
        else:
            time.sleep(5)
    print(getNowTime(), "oddsIDConsumer 完成任务退出")

    # cell = count//4
    # local = result[cell:count]
    # print(thread_name, cell, count)
    # cell = half // number_http
    # for i in range(0, number_http):
    #     start = i * cell
    #     if i < number_http - 1:
    #         end = (i + 1) * cell
    #     else:
    #         end = half
    #     matchs_cell = result[start:end]
    #     thread_name = "http" + str(i)
    #     detail_product = threading.Thread(target=detailProduct, args=(matchs_cell, thread_name, True))
    #     print(thread_name, start, end)
    #     threads.append(detail_product)
