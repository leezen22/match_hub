import threading
import time
from multiprocessing import Queue

from utils import sql_util
from utils.dateUtil import getNowTime
from zq.service.total_odds import TotalOddsZq

total_queue = Queue()
oddsID_queue = Queue()

product_alive = 0
detail_alive = 0


def task_up_totalDetail():
    global product_alive
    global detail_alive

    querySql = """ SELECT
                      tot.oddsID,
                      tot.scheduleID,
                      tot.companyID,
                      tot.finished_pre,
                      tot.finished_gun,
                      sche.matchState
                   FROM
                      zq_TotalScore tot
                      LEFT JOIN zq_schedule sche
                      ON sche.scheduleID = tot.scheduleID
                   WHERE tot.companyID = {0}
                      AND tot.finished_gun = 0
                      AND sche.matchTime >= '{1}'
                      AND sche.matchTime < '{2}'
                      AND sche.matchState = - 1 """.format(3, '2018-01-01 00:00', '2019-01-01 00:00')
    result = sql_util.select_Execute(querySql)
    count = len(result)
    print("任务数量：", count)

    product_alive = 1
    detail_alive = 1
    threads = []

    # 采集变化记录
    thread_name = "detail_product_local"
    detail_product = threading.Thread(target=detailProduct, args=(result, thread_name, True))
    threads.append(detail_product)

    # # 更新变化记录
    # detail_consumer = threading.Thread(target=detailConsumer2, args=())
    # threads.append(detail_consumer)
    #
    # # 更新采集状态
    # oddsID_consumer = threading.Thread(target=oddsIDConsumer, args=())
    # threads.append(oddsID_consumer)

    for t in threads:
        t.start()
    for t in threads:
        t.join()


def detailProduct(oddsDataList, threadName, isProxy=True, isDriver=False, proxy=None):
    global total_queue
    global product_alive

    count = len(oddsDataList)
    for item in oddsDataList:
        print(getNowTime(), "数据待采集：", count)
        data = TotalOddsZq.get_deail(item[0], item[1], item[2], item[3], item[4], isproxy=isProxy)
        detail_count = len(data['detail'])
        print([getNowTime(), threadName, count, '变化记录',
               item[0], item[1], item[2], data['state'], detail_count])
        # if data['state'] == 1:
        #     if finished_gun == 0 and detail_count > 0:
        #         data['matchState'] = item[5]
        #         total_queue.put(data)
        count = count - 1
    product_alive = product_alive - 1
    print(threadName, "完成任务推出")


def detailConsumer(thread_name):
    global total_queue
    global product_alive
    global detail_alive
    count = 5
    while count > 0:
        if not total_queue.empty():
            print(getNowTime(), "采集数据待更新(份)：", total_queue.qsize())
            data = total_queue.get()
            TotalOddsZq.up_total_detail(data, 2)
        elif product_alive == 0:
            count = count - 1
        else:
            time.sleep(10)
    detail_alive = detail_alive - 1


def detailConsumer2():
    global total_queue
    global product_alive
    global detail_alive
    global oddsID_queue
    count = 5
    while count > 0:

        data = {'detail': [], 'oddsIDList': []}
        count_detail = 0
        while not total_queue.empty() and count_detail < 10000:
            print(getNowTime(), "采集数据待更新(份)：", total_queue.qsize())
            item = total_queue.get()
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
            result = TotalOddsZq.up_total_details(data, 2)
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
        print("采集状态待更新：", oddsID_queue.qsize())
        if not oddsID_queue.empty():
            data = oddsID_queue.get()
            for item in data:
                oddsID = item['oddsID']
                if item['matchState'] == -1 or item['matchState'] == -10:
                    sql_util.upData('zq_TotalScore', {'finished_pre': 2, 'finished_gun': 2}, {'oddsID': oddsID})
                else:
                    sql_util.upData('zq_TotalScore', {'finished_pre': 1, 'finished_gun': 1}, {'oddsID': oddsID})
        elif detail_alive == 0:
            count = count - 1
        else:
            time.sleep(5)
    print(getNowTime(), "oddsIDConsumer 完成任务退出")

    # for item in oddsDataList:
    #     print(gettime(), "数据待采集：", count)
    #     finished_gun = item[4]
    #     data = TotalOddsZq.get_deail(item[0], item[1], item[2], item[3], item[4], isproxy=isProxy)
    #     detail_count = len(data['detail'])
    #     print([gettime(), name, count, '让分变化记录', item[0], item[1], item[2], data['state'], detail_count])
    #     # if data['state'] == 1:
    #     #     if finished_gun == 0 and detail_count > 0:
    #     #         data['matchState'] = item[5]
    #     #         total_queue.put(data)
    #     count = count - 1
    # product_alive = product_alive - 1
    # print(name, "完成任务推出")

    # querySql = "SELECT scheduleID,matchState FROM zq_schedule WHERE matchTime<'2020-01-01 00:00' " \
    #            "and matchTime>='2019-06-01 00:00' and matchState=-1 and totalOdds_f=2"

    # count = len(result)
    # for match in result:
    #     scheduleID = match[0]
    #     matchState = match[1]
    #     sql = "SELECT oddsID,scheduleID,finished_pre,finished_gun FROM zq_totalscore " \
    #           "WHERE scheduleID = {0} and companyID in(3,8) and finished_gun=0".format(scheduleID)
    #     result = sql_util.select_Execute(sql)
    #     if len(result) > 0:
    #         for item in result:
    #             data = TotalOddsZq.get_deail(item[0], item[1], item[2], item[3], matchState, isproxy=isProxy)
    #             detail_count = len(data['detail'])
    #             print([gettime(), name, count, '让分变化记录', item[0], item[1], item[2], data['state'], detail_count])
    #     count = count - 1
    # product_alive = product_alive - 1
    # print(name, "完成任务推出")
