from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

qt_mobile_host = "m.titan007.com"
qt_lq_web_host = "nba.titan007.com"
qt_lq_bf_host = "bf.titan007.com"
qt_lq_live_host = "lq3.titan007.com"
qt_zq_web_host = "vip.titan007.com"
qt_zq_1X2_host = "1x2d.titan007.com"
qt_zq_live_host = "live.titan007.com"
qt_zq_static_host = "livestatic.titan007.com"

qt_lq_league_js = "http://nba.titan007.com/jsData/infoHeader_cn.js"
qt_lq_left_data_js = "https://nba.titan007.com/jsData/leftData/leftData.js"
qt_lq_league_referer = "https://nba.titan007.com/index_cn.htm"
qt_lq_web_sc_home = "http://bf.titan007.com/NBA_SC.aspx"
qt_lq_web_sc_date = "http://bf.titan007.com/nba_date.aspx"
qt_lq_mobile_ji = "http://m.titan007.com/basketball.shtml"
qt_lq_mobile_ji_score = "http://m.titan007.com/txt/Schedule_0_0.txt"
qt_lq_mobile_odds_home = "http://m.titan007.com/lq/Odds.htm"
qt_lq_mobile_odds = "http://m.titan007.com/Lq/OddsDataFilter.aspx"
qt_lq_mobile_asianOdds_url = "http://m.titan007.com/lq/handicap"
qt_lq_mobile_asianDetail_url = "http://m.titan007.com/lq/asianDetail"
qt_lq_mobile_totalOdds_url = "http://m.titan007.com/lq/overunder"
qt_lq_mobile_totalDetail_url = "http://m.titan007.com/lq/oudetail"
qt_lq_mobile_europeOdds_url = "http://m.titan007.com/lq/Compensate"
qt_lq_mobile_europeDetail_url = "http://m.titan007.com/lq/CompensateDetail"
qt_lq_mobile_zhiBo_url = "http://m.titan007.com/AnalyLq/Shijian"
qt_lq_web_ji_url = "http://lq3.titan007.com/nba.htm"
qt_lq_web_ji_score_url = "http://lq3.titan007.com/NBA/today2.xml"
qt_lq_web_ji_odds_url = "http://lq3.titan007.com/NBA/nbaGoal"
qt_lq_web_home = "http://nba.titan007.com"
qt_lq_web_asianOdds_url = "http://nba.titan007.com/odds/AsianOdds_n.aspx"
qt_lq_web_totalOdds_url = "http://nba.titan007.com/odds/OverDown_n.aspx"
qt_lq_web_europeOddsJs_url = "http://nba.titan007.com/1x2/data1x2"
qt_lq_web_europeOdds_url = "http://nba.titan007.com/1x2/oddslist"
qt_lq_web_2in1_url = "http://nba.titan007.com/odds/2in1Odds.aspx"
qt_lq_web_zhiBo_url = "http://nba.titan007.com/cn/Tech/TechTxtLive.aspx"
qt_lq_web_scheJS_dir = "http://nba.titan007.com/jsData/matchResult"
qt_lq_web_seasonJS_bdir = 'http://nba.titan007.com/jsData/LeagueSeason/'
qt_lq_web_normal = "http://nba.titan007.com//cn/normal.aspx"

lq_matchState = {'未开场': 0, '中场': 50, '加时': 10, '完场': -1,
                 '第一节': 1, '第二节': 2, '第三节': 3, '第四节': 4,
                 '第1节': 1, '第2节': 2, '中场': 50, '第3节': 3, '第4节': 4,
                 '待定': -2, '中断': -3, '取消': -4, '推迟': -5
                 }


qt_zq_mobile_ji = "http://m.titan007.com/index.shtml"
qt_zq_mobile_sc = "http://m.titan007.com/Schedule.htm"
qt_zq_mobile_sc_bf = "http://m.titan007.com/ChangeDate.ashx"
qt_zq_mobile_ji_bf = "http://m.titan007.com/phone/Schedule_0_0.txt"
qt_zq_mobile_ji_0dds = "http://m.titan007.com/txt/goalBf3.xml"
qt_zq_mobile_odds_3 = "http://m.titan007.com/txt/goalBf3.xml"
qt_zq_mobile_asianOdds_url = "http://m.titan007.com/HandicapDataInterface.ashx?type=1&oddskind=0"
qt_zq_mobile_asianDetail_url = "http://m.titan007.com/HandicapDataInterface.ashx?type=3&oddskind=0"
qt_zq_mobile_totalOdds_url = "http://m.titan007.com/HandicapDataInterface.ashx?type=1&oddskind=1"
qt_zq_mobile_totalDetail_url = "http://m.titan007.com/HandicapDataInterface.ashx?type=3&oddskind=1"
qt_zq_mobile_europeOdds_url = "http://m.titan007.com/compensate"
qt_zq_mobile_europeDetail_url = "http://m.titan007.com/CompensateDetail"
qt_zq_mobile_oddsDetail = "https://m.titan007.com/Analy/OddsDetail.aspx"
qt_zq_mobile_live = "https://m.titan007.com/Analy/ShiJian"
qt_zq_mobile_flash = "https://m.titan007.com/flashdata"

qt_zq_web_ji = "http://live.titan007.com/"
qt_zq_web_ji_bf = "http://live.titan007.com/vbsxml/bfdata_ut.js"
qt_zq_web_ji_0dds = "http://live.titan007.com//vbsxml"
qt_zq_web_asianOdds_url = "http://vip.titan007.com/AsianOdds_n.aspx"
qt_zq_web_totalOdds_url = "http://vip.titan007.com/OverDown_n.aspx"
qt_zq_web_europeOdds_url = "http://op1.titan007.com/oddslist"
qt_zq_web_europeOddsJs_url = "http://1x2d.titan007.com/"
qt_zq_web_3in1_url = "http://vip.titan007.com/changeDetail/3in1Odds.aspx"
qt_zq_web_toalDetails_url = "https://vip.titan007.com/changeDetail/overunder.aspx"
qt_zq_web_livestatic = "https://livestatic.titan007.com"
qt_zq_web_livedetail = "https://live.titan007.com/detail"

zq_matchState = {'-14': '推迟', '-13': '中断', '-12': '腰斩', '-11': '待定', '-10': '取消', '-1': '完',
                 '0': '未开', '1': '上', '2': '中', '3': '下', '4': '加', '5': '点'}
zq_new_season = ['2023-2024','2024','2024-2025']

# state_ch.append("推迟,推遲,Defer")
# state_ch[1] = "中断,中斷,Halt"
# state_ch[2] = "腰斩,腰斬,Halt"
# state_ch[3] = "<font color=green>待定</font>,<font color=green>待定</font>,<font color=green>Wait</font>"
# state_ch[4] = "取消,取消,Cancel"
# state_ch[13] = "<b>完</b>,<b>完</b>,<b>Ft</b>"
# state_ch[14] = ",,"
# state_ch[15] = "上,上,Part1"
# state_ch[16] = "<font color=blue>中</font>,<font color=blue>中</font>,<font color=blue>Half</font>"
# state_ch[17] = "下,下,Part2"
# state_ch[18] = "加,加,Ot"
# state_ch[19] = "点,點,"

zq_europJS_dir = str(DATA_DIR / 'zuqiu' / 'work' / '1x2')

lq_europJS_dir = str(DATA_DIR / 'lanqiu' / 'work' / '1x2')
lq_scheJS_local_dir = str(DATA_DIR / 'lanqiu' / 'jsData' / 'matchResult')
scheJs_localPend_dir = str(DATA_DIR / 'lanqiu' / 'pending' / 'matchResult')
lq_seasonJS_local_dir = str(DATA_DIR / 'lanqiu' / 'jsData' / 'LeagueSeason')
