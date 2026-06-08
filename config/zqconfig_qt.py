from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "zuqiu"
LOG_DIR = PROJECT_ROOT / "logs" / "zuqiu"

host_zuqiu = "http://zq.titan007.com"
ziliao = "http://zq.titan007.com/info/index_cn.htm"

sclass_path_local = str(DATA_DIR / "pending" / "league" / "seague.js")
team_path_local = str(DATA_DIR / "pending" / "team" / "team.js")
cupQualify_path_local = str(DATA_DIR / "pending" / "cupQualify" / "cupQualify.js")
referee_path_local = str(DATA_DIR / "pending" / "referee" / "referee.js")
subLeage_path_local = str(DATA_DIR / "pending" / "subLeague" / "subleague.js")
fifa_path_local = str(DATA_DIR / "pending" / "fifa" / "fifa.js")

seajslocaldir = str(DATA_DIR / "jsData" / "LeagueSeason") + "/"
schelocaldir = str(DATA_DIR / "jsData" / "matchResult") + "/"
ranklocaldir = str(DATA_DIR / "jsData" / "rank") + "/"
schejs_pending = str(DATA_DIR / "pending" / "matchResult") + "/"
schedule_js_work_dir = str(DATA_DIR / "work" / "matchResult")
schedule_js_legacy_pending_dirs = ["new", "exist"]
keep_schedule_js_cache = False
enable_finished_season_backfill = False

europjs_dir = str(DATA_DIR / "1x2") + "/"
europjs_pending_dir = str(DATA_DIR / "pending" / "1x2") + "/"

seajsWebdir = "http://zq.titan007.com/jsData/LeagueSeason/"
scheWebdir = "http://zq.titan007.com/jsData/matchResult/"
rankWebdir = "http://zq.titan007.com/jsData/rank/"

cup_web_schedir = "http://zq.titan007.com/cn/CupMatch/"
sub_web_schedir = "http://zq.titan007.com/cn/SubLeague/"
league_web_schedir = "http://zq.titan007.com/cn/League/"

asianscore_url = "http://vip.titan007.com/AsianOdds_n.aspx"
totalscore_url = "http://vip.titan007.com/OverDown_n.aspx"
europe_url = "http://op1.titan007.com/oddslist/"
europejs_url = "http://1x2d.titan007.com/"

fileload_none = str(LOG_DIR / "fileload_none.txt")
fileload_e = str(LOG_DIR / "fileload_e.txt")
exception = str(LOG_DIR / "exception.txt")

ziliao_jsurl = "http://zq.titan007.com/jsData/infoHeader.js"
ziliao_jspath = str(DATA_DIR / "jsData" / "LeagueInfo" / "infoHeader.js")

ch_score_xml = "http://lq3.titan007.com/NBA/change.xml"
m_aisan = "http://m.titan007.com/asian/"
m_total = "http://m.titan007.com/overunder/"
m_detail_headers = {
    "Host": "m.titan007.com",
}
masiandetail_url = "http://m.titan007.com/HandicapDataInterface.ashx?type=3&oddskind=0"
mtotaldetail_url = "http://m.titan007.com/HandicapDataInterface.ashx?type=3&oddskind=1"

headers_score = {
    "Host": "lq3.titan007.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36",
    "Sec-Fetch-Mode": "navigate",
    "Referer": "http://lq3.titan007.com/nba.htm",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
}
headers_odds = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "Host": "vip.titan007.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36",
}
headers_europe = {
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Host": "1x2d.titan007.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36",
}
headers = {
    "Host": "zq.titan007.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36",
}
