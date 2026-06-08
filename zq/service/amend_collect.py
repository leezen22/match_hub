import threading

from utils import sql_util


def amend_AsianOdds(datas):
    count = len(datas)
    for data in datas:
        oddsID = data[0]
        sql = "SELECT DISTINCT matchState FROM zq_AsianOddsDetail WHERE oddsID={0}".format(oddsID)
        result = sql_util.select(sql)
        matchStates = []
        for item in result:
            matchStates.append(item[0])
        finished_pre = data[1]
        finished_gun = data[2]
        hasPre = data[3]
        hasIn = data[4]
        hasFirst = data[5]
        hasHalf = data[6]
        hasSecond = data[7]

        if finished_pre != 0 or finished_gun != 0:
            if 0 in matchStates:
                hasPre = 1
            else:
                hasPre = 0

        if finished_gun != 0:
            if 1 in matchStates:
                hasFirst = 1
            else:
                hasFirst = 0
            if 2 in matchStates:
                hasHalf = 1
            else:
                hasHalf = 0
            if 3 in matchStates:
                hasSecond = 1
            else:
                hasSecond = 0
            if hasFirst == 1 or hasHalf == 1 or hasSecond == 1:
                hasIn = 1
            else:
                hasIn = 0

        if finished_pre == 2 and hasPre == 0:
            finished_pre = 3
        if finished_gun == 2 and hasIn == 0:
            finished_gun = 3

        print([finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond, oddsID], 'asian剩余：', count)
        sql3 = "UPDATE zq_AsianOdds SET finished_pre= {0},finished_gun={1},hasPre={2},hasIn={3},hasFirst={4}, " \
               "hasHalf={5},hasSecond={6} WHERE oddsID= {7}".format(finished_pre, finished_gun, hasPre, hasIn,
                                                                    hasFirst, hasHalf, hasSecond, oddsID)
        sql_util.sqlExecute(sql3)
        count = count - 1


def amend_totalScore(datas):
    count = len(datas)
    for data in datas:
        oddsID = data[0]
        sql = "SELECT DISTINCT matchState FROM zq_totalScoreDetail WHERE oddsID={0}".format(oddsID)
        result = sql_util.select(sql)
        matchStates = []
        for item in result:
            matchStates.append(item[0])

        finished_pre = data[1]
        finished_gun = data[2]
        hasPre = data[3]
        hasIn = data[4]
        hasFirst = data[5]
        hasHalf = data[6]
        hasSecond = data[7]

        if finished_pre != 0 or finished_gun != 0:
            if 0 in matchStates:
                hasPre = 1
            else:
                hasPre = 0

        if finished_gun != 0:
            if 1 in matchStates:
                hasFirst = 1
            else:
                hasFirst = 0
            if 2 in matchStates:
                hasHalf = 1
            else:
                hasHalf = 0
            if 3 in matchStates:
                hasSecond = 1
            else:
                hasSecond = 0
            if hasFirst == 1 or hasHalf == 1 or hasSecond == 1:
                hasIn = 1
            else:
                hasIn = 0

        if finished_pre == 2 and hasPre == 0:
            finished_pre = 3
        if finished_gun == 2 and hasIn == 0:
            finished_gun = 3

        print([finished_pre, finished_gun, hasPre, hasIn, hasFirst, hasHalf, hasSecond, oddsID], 'asian剩余：', count)
        sql3 = "UPDATE zq_totalScore SET finished_pre= {0},finished_gun={1},hasPre={2},hasIn={3},hasFirst={4}, " \
               "hasHalf={5},hasSecond={6} WHERE oddsID= {7}".format(finished_pre, finished_gun, hasPre, hasIn,
                                                                    hasFirst, hasHalf, hasSecond, oddsID)
        sql_util.sqlExecute(sql3)
        count = count - 1


if __name__ == '__main__':
    sql1 = "SELECT oddsID,finished_pre,finished_gun,hasPre,hasIn,hasFirst,hasHalf,hasSecond " \
           "FROM zq_AsianOdds WHERE finished_gun=2 and hasIn=-1 "
    result1 = list(sql_util.select(sql1))
    half1 = len(result1) // 2
    asian1 = result1[0:half1]
    asian2 = result1[half1:]

    sql2 = "SELECT oddsID,finished_pre,finished_gun,hasPre,hasIn,hasFirst,hasHalf,hasSecond " \
           "FROM zq_totalScore WHERE finished_gun=2 and hasIn=-1 "
    result2 = list(sql_util.select(sql2))
    half2 = len(result2) // 2
    tot1 = result2[0:half2]
    tot2 = result2[half2:]

    threads = []
    thread1 = threading.Thread(target=amend_AsianOdds, args=(asian1,))
    thread2 = threading.Thread(target=amend_AsianOdds, args=(asian2,))
    thread3 = threading.Thread(target=amend_totalScore, args=(tot1,))
    thread4 = threading.Thread(target=amend_totalScore, args=(tot2,))
    threads.append(thread1)
    threads.append(thread2)
    threads.append(thread3)
    threads.append(thread4)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # asian = [969, 971, 1003, 1004, 1052, 1054, 1078, 1079, 5508, 5510, 5543, 5544, 5594, 5595, 5632, 5634, 5681, 5684,
    #        5709, 5710, 5747, 5748, 5788, 5790, 5839, 5904, 5906, 5948, 5950, 5988, 6025, 6027, 6068, 6070, 6114, 6115,
    #        6152, 6154, 6206, 6209, 6245, 6292, 6330, 6368, 6406, 6450]
    # total = [950,2943, 2985,3040, 3085,3118, 3182,3222,3262,3306,3347,3376, 3435,3475, 3515,3555,3595,3661,3701,3741,
    #          3781,3841,3887,3927,3970,4012,4050, 4091,4131,4171, 4225,4274, 4320, 4358,4396,4441,4477, 4539, 4592,4632,
    #          4695,4738,4775,4808]
    # for oddsID in asian:
    #     sql1 = "UPDATE zq_AsianOdds SET finished_pre= 2,finished_gun=2 where oddsID={0}".format(oddsID)
    #     sql_util.sqlExecute(sql1)
    # for oddsID in total:
    #     sql2 = "UPDATE zq_totalScore SET finished_pre= 2,finished_gun=2 where oddsID={0}".format(oddsID)
    #     sql_util.sqlExecute(sql2)
