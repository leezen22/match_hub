import threading
from lq.service.europe_odds import EuropeOddsLq
from lq.service.partscore import upPartscore
from lq.service.rank import upRank
from lq.service.schedule import upSchedule
from lq.service.schedulejs import upScheJs
from lq.service.lqodds import LqOddsService

if __name__ == '__main__':
    task = ["任务：0 全部更新不包含变化记录", "1 更新赛程 ", "2 更新比分+亚指大小",
            "3 更新比分 ", "4 更新初盘即时盘 ", "5 更新变化记录", "6 下载欧赔JS文件", "7 本地欧赔JS文件提取赔率"]
    print(task)
    task_code = input("请输入任务编号： ")
    threads = []
    threads_used = False
    score_thread = threading.Thread(target=upPartscore, args=())
    odds_thread = threading.Thread(target=LqOddsService.upOdds, args=())
    rank_thread = threading.Thread(target=upRank, args=())
    if task_code == '0':
        upScheJs()
        upSchedule()
        threads.append(score_thread)
        threads.append(odds_thread)
        threads.append(rank_thread)
        threads_used = True
    elif task_code == '1':
        upScheJs()
        upSchedule()
    elif task_code == '2':
        threads.append(score_thread)
        threads.append(odds_thread)
        threads_used = True
    elif task_code == '3':
        threads.append(score_thread)
        threads_used = True
    elif task_code == '4':
        threads.append(odds_thread)
        threads_used = True
    # elif task_code == '5':
    #     LqOddsService.upOddsDetail()
    elif task_code == '6':
        EuropeOddsLq.loadjs_europe()
    elif task_code == '7':
        EuropeOddsLq.upodds_byfile()
    else:
        pass
    if threads_used:
        for t in threads:
            t.start()
        for t in threads:
            t.join()


