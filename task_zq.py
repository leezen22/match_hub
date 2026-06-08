from zq.service.europe_odds import EuropeOddsZq
from utils.proxyCheck import ProxyCheck
from utils.proxyTools import ProxyTools
from zq.service.zq_up_asiandetail import task_up_detail
from zq.service.zq_up_odds import task_upodds
from zq.service.zq_up_totaldetail import task_up_totalDetail

if __name__ == '__main__':
    # task = ["任务：1 更新足球赔率 让分和大小", "2 验证driver现在是否有效 ", "3 采集并验证jxl代理",
    #         "4 验证已入库有效IP ", "5 采集并验证免费IP ", "6 代理IP管理维护", "7 更新欧赔",
    #         "8 下载欧赔js", "9 更新让分变化记录", "10 更新大小变化记录"]
    task = "任务：1 更新足球赔率 让分和大小, 2 验证driver现在是否有效 , 3 采集并验证jxl代理,\n 4 验证已入库有效IP , " \
           "5 采集并验证免费IP , 6 代理IP管理维护, 7 更新欧赔,\n " \
           "8 下载欧赔js, 9 更新让分变化记录, 10 更新大小变化记录 11 本地更新欧赔变化记录"

    print(task)
    task_code = input("请输入任务编号： ")
    threads = []
    if task_code == '1':
        task_upodds()
    elif task_code == '2':
        ProxyCheck.task_checkip_driver()
    elif task_code == '3':
        ProxyTools.task_proxy_jxl()
    elif task_code == '4':
        ProxyCheck.task_checkip_http()
    elif task_code == '5':
        ProxyTools.task_proxy_free()
    elif task_code == '6':
        ProxyTools.task_proxy()
    elif task_code == '7':
        EuropeOddsZq.task_upodds_byfile()
    elif task_code == '8':
        EuropeOddsZq.task_loadjs_europe()
    elif task_code == '9':
        task_up_detail()
    elif task_code == '10':
        task_up_totalDetail()
    elif task_code == '11':
        EuropeOddsZq.local_detail_byFile()
    else:
        pass