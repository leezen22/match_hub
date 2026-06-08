import threading
from typing import Any, Tuple, cast

from crawler.qt.lq_2in1_detail_crawler import Lq2in1Crawler
from lq.dao.AsianOddsDao import upAsianOddsBymid
from lq.dao.TotalScoreDao import upTotalOddsBymid
from lq.parshtml import part_score
from lq.service.league import LQleague
from lq.service.lqodds import LqOddsService
from lq.service.partscore import upPartscore
from lq.service.schedule import upSchedule
from lq.service.schedulejs import upScheJs, upScheJsLocal
from utils import sql_util


# ------------------------------------------实时维护联赛范围-------------------------------------

# 根据联赛ID和赛季更新小节比分
def up_score_batch(scheduleIdArr):
    for matchID in scheduleIdArr:
        partdDct = part_score.get_PartScore(matchID)
        sql_util.upData('lq_schedule', partdDct, {'scheduleID': matchID})
    print("小节比分更新成功: " + str(scheduleIdArr))


def up_2in1Details_by_match(scheduleId,companyId, scope):
    # scope = 3
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
            WHERE tot.companyId={1} and (tot.finished_gun in(0,1) or asian.finished_gun in(0,1)) 
            and sche.scheduleId={0}
            and sche.matchState >=-1 order by sche.matchtime ASC
        """.format(scheduleId, companyId)
    results = cast(Tuple[Tuple[Any, ...], ...], sql_util.select(sql,isDict=False))
    size = len(results)
    for item in results:
        print(str(companyId) + "变化记录剩余比赛：" + str(size) + ",最新 ：" + str(item))
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
        collectData = crawler.qt_web_get(scope=scope)
        threads = []
        if scope != 2:
            if 'asian' in collectData.keys() and collectData['asian']['state'] == 1 and \
                    collectData['asian']['finished_pre'] in (0, 1):
                asian_pre_thread = threading.Thread(target=LqOddsService.up_asianPre_details,
                                                    args=(collectData['asian'],))
                threads.append(asian_pre_thread)
            if 'total' in collectData.keys() and collectData['total']['state'] == 1 and \
                    collectData['total']['finished_pre'] in (0, 1):
                total_pre_thread = threading.Thread(target=LqOddsService.up_totalPre_details,
                                                    args=(collectData['total'],))
                threads.append(total_pre_thread)

        if scope != 1:
            if 'asian' in collectData.keys() and collectData['asian']['state'] == 1 and \
                    collectData['asian']['finished_gun'] in (0, 1):
                asian_gun_thread = threading.Thread(target=LqOddsService.up_asianGun_details,
                                                    args=(collectData['asian'],))
                threads.append(asian_gun_thread)
            if 'total' in collectData.keys() and collectData['total']['state'] == 1 and \
                    collectData['total']['finished_gun'] in (0, 1):
                total_gun_thread = threading.Thread(target=LqOddsService.up_totalGun_details,
                                                    args=(collectData['total'],))
                threads.append(total_gun_thread)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        size = size - 1


def up_match_data(scheduleIdArr):
    # scheduleIdArr= ['1716532','1756832']
    # now = datetime.now()
    # time = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
    # time1 = "'" + (now + timedelta(hours=-4)).strftime("%Y-%m-%d %H:%M:%S") + "'"
    # time2 = "'" + (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S") + "'"
    # and leagueID in (1, 2, 5, 7, 14, 15, 19, 25, 20, 28, 22)
    for matchId in scheduleIdArr:
        up_score_batch([matchId])
        asiansql = "SELECT scheduleID, leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                   " WHERE asianodds_f in(0,1) and matchState>=-1 and scheduleId = {0} order by matchTime ASC ".format(matchId)
        totalsql = "SELECT scheduleID,leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                   " WHERE totalodds_f in(0,1) and matchState>=-1 and scheduleId = {0} order by matchTime ASC ".format(matchId)
        # totalsql= {}
        asianMatchList = sql_util.select(asiansql)
        print(asianMatchList)
        totalMatchList = sql_util.select(totalsql)
        print(totalMatchList)
        if len(asianMatchList)>0:
            match=asianMatchList[0]
            if match[5] != 2:
                upAsianOddsBymid(match[0], match[5])
        if len(totalMatchList)>0:
            match=totalMatchList[0]
            if match[6] != 2:
                # 比赛ID，更新状态
                upTotalOddsBymid(match[0], match[6])

        up_2in1Details_by_match(matchId, 8, 3)
        up_2in1Details_by_match(matchId, 3, 3)

if __name__ == '__main__':
    # upScheJsLocal()
    upScheJs()
    upSchedule()
    upPartscore()
    LqOddsService.upOdds()
    LqOddsService.up_2in1Details_byCid(8, 3)
    LqOddsService.up_2in1Details_byCid(3, 3)
    # LQleague.getSchejsPending([1,'NBA',1])

    # scheduleIdArr=['716461','716852','716893','716682','704952','704953','716927','704954','714911','716514','716933','716934','667640']
    # up_match_data(scheduleIdArr)
