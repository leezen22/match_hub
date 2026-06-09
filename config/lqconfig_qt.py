from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "lanqiu"
LOG_DIR = PROJECT_ROOT / "logs" / "lanqiu"


# 篮球联赛/赛季列表源数据JS采集地址
lqcountryJS = 'http://nba.titan007.com/jsData/infoHeader_cn.js'
# 篮球赛季JS文件网站访问目录
seajsWebdir = 'http://nba.titan007.com/jsData/LeagueSeason/'
# 篮球赛程JS文件网站访问目录
scheWebdir = 'http://nba.titan007.com/jsData/matchResult/'
# 篮球积分JS文件网站访问目录
rankWebdir = 'http://nba.titan007.com/jsData/rank/'

# 篮球欧赔JS文件网站访问目录
# europwebdir = 'http://nba.titan007.com/1x2/data1x2/'

europe_url = "http://nba.titan007.com/1x2/oddslist/"
europejs_url = "http://nba.titan007.com/1x2/data1x2/"
europjs_dir = str(DATA_DIR / 'work' / '1x2') + '/'

# 篮球小节比分页面地址
techtxtlive = 'http://nba.titan007.com/cn/Tech/TechTxtLive.aspx'
# 篮球让分指数页面地址
AsianOdds_n = 'http://nba.titan007.com/odds/AsianOdds_n.aspx'
# 篮球大小分指数页面地址
TotalScore_n = 'http://nba.titan007.com/odds/OverDown_n.aspx'
# 篮球亚指变化记录页面地址
AsianOddsDetail ='http://nba.titan007.com/odds/2in1Odds.aspx'

# 篮球赛季JS文件本地存储目录
seajslocaldir = str(DATA_DIR / 'jsData' / 'LeagueSeason') + '/'
# 篮球赛程JS文件本地存储目录
schelocaldir = str(DATA_DIR / 'jsData' / 'matchResult') + '/'
# 篮球积分榜JS文件本地存储目录（联赛）
ranklocaldir = str(DATA_DIR / 'jsData' / 'rank') + '/'
# 篮球欧赔JS文件本地存储目录
europlocaldir = str(DATA_DIR / '1x2' / 'data1x2') + '/'

# 篮球资料入口网站地址
lanqurl= 'http://nba.titan007.com'
# 机会提醒声音地址
chance_sound = str(LOG_DIR / "chance.mp3")
# 任务待处理目录
seajslocaldir_p = str(DATA_DIR / 'pending' / 'LeagueSeason') + '/'
schejslocaldir_p = str(DATA_DIR / 'pending' / 'matchResult') + '/'
rankdir_p = str(DATA_DIR / 'pending' / 'rank') + '/'

# Schedule JS files are working artifacts. Keep this off so another device can
# run from shared DB state without depending on stale local cache.
keep_schedule_js_cache = False

# Current schedule update only uses temporary files. They are deleted after
# parsing, so a new device can run without historical local JS cache.
schedule_js_work_dir = str(DATA_DIR / 'work' / 'matchResult')

# Set this to True only for explicit historical repair/backfill jobs.
enable_finished_season_backfill = False
# 篮球联赛 赛季js文件 读取失败记录
seajs_loadfail = str(LOG_DIR / 'seajs_loadfail.txt')
# 篮球联赛 赛季js文件 本地查找失败
seajs_local_nonexist = str(LOG_DIR / 'seajs_local_nonexistent.txt')
# 篮球联赛 赛程js文件 读取失败记录
schejs_loadfail = str(LOG_DIR / 'schejs_loadfail.txt')
# 篮球联赛 赛程js文件 本地查找失败
schejs_local_nonexist = str(LOG_DIR / 'schejs_local_nonexistent.txt')
# 篮球联赛 赛季js文件 读取失败记录
quarterscore_e = str(LOG_DIR / 'quarterscore_e.txt')
# 篮球让分指数访问页面失败记录
asianodds_e = str(LOG_DIR / 'asianodds_e.txt')
# 篮球让分指数解析页面标签失败记录
asianodds_parse_e = str(LOG_DIR / 'asianodds_parse_e.txt')
# 篮球大小分分指数访问页面失败记录
overdown_e = str(LOG_DIR / 'overdown_e.txt')
# 篮球让分指数解析页面标签失败记录
overdown_parse_e = str(LOG_DIR / 'overdown_parse_e.txt')
# 篮球欧指文件为空
euro_none = str(LOG_DIR / 'eurojs_none.txt')
# 篮球欧指文件超时读取失败
euro_e = str(LOG_DIR / 'eurojs_e.txt')
# 篮球赔率全场变化超时读取失败
update_log = str(LOG_DIR / 'lq_update_log.txt')

# 文件不存在
fileload_none = str(LOG_DIR / 'fileload_none.txt')
fileload_fail = str(LOG_DIR / 'fileload_fail.txt')
# 文件下载异常
fileload_e = str(LOG_DIR / 'fileload_e.txt')
exception = str(LOG_DIR / 'exception.txt')
# Js解析失败下载异常
js2pyweb_e = str(LOG_DIR / 'js2pyweb_e.txt')
js2pylocal_e = str(LOG_DIR / 'js2pylocal_e.txt')

# 篮球公司字典-与让分指数公司ID保持一致
companys = {'澳门': 1, '皇冠': 3, 'SB': 3, '立博': 4, 'bet365': 8, '易胜博': 2, '韦德': 9, '伟德': 9, '威廉希尔': 10,
            '利记': 31, 'Interwetten': 19, '12Bet':24,'竞彩官方': 30, '澳*': 1, 'Crow*': 3, 'S*': 3, '立*': 4, '36*': 8,
            '365*': 8, '易*': 2, '易胜*': 2,'伟*': 9, '韦*': 9, '威*': 10, '利*': 31, 'Interwet*': 19, '12*': 24,
            '竞彩官*': 30, '竞彩*': 30
            }

# 篮球比赛状态
matchstate = {'未开场': 0, '完场': -1, '完': -1, '待定': -2, '中断': -3, '取消': -4, '推迟': -5, '中场': 50, '加时': 10,
              "第1'OT": 5, "第2'OT": 6, "第3'OT": 7, "第4'OT": 8,"第5'OT":9,
              "1'OT": 5, "2'OT": 6, "3'OT": 7, "4'OT": 8, "5'OT":9,
              '第一节': 1, '第二节': 2, '第三节': 3, '第四节': 4,
              '第1节': 1, '第2节': 2, '中场': 50, '第3节': 3, '第4节': 4}

matchkind ={'3':'季前赛','2':'季后赛','1':'常规赛'}

# requests header 信息
headers = {"Host": "nba.titan007.com",
           "Referer": "http://nba.titian007.com/",
         "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
}

headers_europe = {
         "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
}

headers_365 = {"Host": "www.365365068.com",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36",
               'Sec-Fetch-Mode': 'navigate',
               'Referer': 'https://www.365365868.com/#/AS/B18/K^2/',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3'}



# 欧冠 bet365与库球队比对表
teamEurop= {"奇美基 莫斯科":{"TeamID":"1703","TeamName":"其姆奇"},
            "拜仁慕尼黑":{"TeamID":"3891","TeamName":"拜仁"},
            "艾斯维尔 里昂 维勒班":{"TeamID":"901","TeamName":"艾斯维尔"},
            "皇家马德里":{"TeamID":"835","TeamName":"皇马"},
            "萨拉基利斯":{"TeamID":"1300","TeamName":"萨拉基利斯"},
            "安纳托利亚艾菲斯":{"TeamID":"1126","TeamName":"阿纳多卢艾菲斯"},
            "艾巴柏林":{"TeamID":"978","TeamName":"柏林"},
            "帕纳辛奈科斯":{"TeamID":"829","TeamName":"帕纳辛"},
            "瓦伦西亚":{"TeamID":"894","TeamName":"华伦西亚"},
            "贝尔格莱德红星":{"TeamID":"785","TeamName":"红星"},
            "圣彼得堡泽尼特":{"TeamID":"982","TeamName":"圣彼得堡泽尼特"},
            "CSKA莫斯科":{"TeamID":"1006","TeamName":"中央陆军"},
            "奥林匹亚科斯":{"TeamID":"828","TeamName":"亚高斯"},
            "米兰":{"TeamID":"813","TeamName":"米兰阿马尼"},
            "费内巴切":{"TeamID":"145","TeamName":"费内巴切"},
            "特拉维夫马卡比":{"TeamID":"1022","TeamName":"TA马卡比"},
            "巴塞罗那":{"TeamID":"898","TeamName":"巴塞罗那"},
            "巴斯科尼亚":{"TeamID":"869","TeamName":"沙萨基"}
            }

teamAus= {"SE Melbourne Phoenix":{"TeamID":"8545","TeamName":"东南墨尔本"},
            "珀斯野猫":{"TeamID":"903","TeamName":"野猫"},
            "悉尼国王":{"TeamID":"1813","TeamName":"悉尼国王"},
            "墨尔本联":{"TeamID":"852","TeamName":"墨尔本联"},
            "布里斯班子弹":{"TeamID":"853","TeamName":"布里斯班"},
            "伊拉瓦拉老鹰":{"TeamID":"5376","TeamName":"伊拉瓦拉老鹰"},
            "阿德莱德36人":{"TeamID":"910","TeamName":"36人"},
            "新西兰破坏者":{"TeamID":"937","TeamName":"破坏者"},
            "坎斯大班":{"TeamID":"816","TeamName":"大班"}
            }
