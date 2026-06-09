from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"

# Text logs are diagnostic files, not long-term storage. Rotate them before
# each append so request/parse failures cannot grow without bound.
LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUP_COUNT = 3

fileread_e = str(LOG_DIR / 'fileread_e.txt')
js2pylocal_e = str(LOG_DIR / 'js2pylocal_e.txt')
js2pyweb_e = str(LOG_DIR / 'js2pyweb_e.txt')
zq_extract_fail = str(LOG_DIR / 'zq_extract_fail.txt')
zq_extract_e = str(LOG_DIR / 'zq_extract_e.txt')
zq_update_log = str(LOG_DIR / 'zq_update_log.txt')
zq_oddsdetail_asian = str(LOG_DIR / "zq_oddsdetail_asian.txt")
zq_oddsdetail_total = str(LOG_DIR / "zq_oddsdetail_total.txt")
zq_oddsdetail_europe = str(LOG_DIR / "zq_oddsdetail_europe.txt")
httpRequest_fail = str(LOG_DIR / 'httpRequest_fail.txt')
exception = str(LOG_DIR / 'exception.txt')
lq_rank_fail = str(LOG_DIR / 'lq_rank_fail.txt')
lq_oddsdetail_fail = str(LOG_DIR / 'lq_oddsdetail_fail.txt')
lq_asianodds_fail = str(LOG_DIR / 'lq_asianodds_fail.txt')
lq_totalodds_fail = str(LOG_DIR / 'lq_totalodds_fail.txt')
webcontent = str(LOG_DIR / 'webcontent.txt')
webresponse = str(LOG_DIR / 'webresponse.txt')
matchs = str(LOG_DIR / 'matchs.txt')
exit = str(LOG_DIR / 'exit.txt')
record = str(LOG_DIR / 'record.txt')
collect = str(LOG_DIR / 'collect.txt')
collect_asian = str(LOG_DIR / 'collect_asian.txt')
collect_total = str(LOG_DIR / 'collect_total.txt')

check_asian = str(LOG_DIR / 'check_asian.txt')
check_total = str(LOG_DIR / 'check_total.txt')
headers_kd = {
    'Host': 'www.kuaidaili.com',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
}
website_kd = 'https://www.kuaidaili.com/free'

headers_gn = {
    'Host': 'www.xicidaili.com',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
}
website_gn = 'https://www.xicidaili.com/nn/'

web_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/61.0",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
                "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
                "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
                "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
            ]

mobile_agents = ["Mozilla/5.0 (Linux; U; Android 4.4.2; zh-CN; NX505J Build/KVT49L) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 UCBrowser/10.5.2.598 U3/0.8.0 Mobile Safari/534.30",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X; zh-CN) AppleWebKit/537.51.1 (KHTML, like Gecko) Mobile/13G34 UCBrowser/10.9.19.815 Mobile",
"Mozilla/5.0 (Linux; Android 4.4.2; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/35.0.1916.138 Mobile Safari/537.36 T7/7.1baiduboxapp/7.5.1 (Baidu; P1 4.4.2)",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko)", "Mobile/13G34baiduboxapp/0_7.0.5.7_enohpi_4331_057/3.3.9_1C2%258enohPi/1099a/B80ADBCDA918AA94450DE8767C97BC446249D6087FCLPRHEEPF/1",
"Mozilla/5.0 (Linux; Android 4.4.2; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/35.0.1916.138 Mobile Safari/537.36 T7/7.2baidubrowser/7.3.14.0 (Baidu; P1 4.4.2)",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.3 Mobile/13G34 Safari/600.1.4baidubrowser/4.2.0.324 (Baidu; P2 9.3.3)",
"Mozilla/5.0 (Linux; Android 4.4.2; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/37.0.0.0 Mobile MQQBrowser/6.2 TBS/036555 Safari/537.36 V1_AND_SQ_6.3.7_374_YYB_D PA QQ/6.3.7.2795 NetType/WIFI WebP/0.3.0 Pixel/1080",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13G34 QQ/6.5.0.443 V1_IPH_SQ_6.5.0_1_APP_A Pixel/750 Core/UIWebView NetType/WIFI Mem/41",
"Mozilla/5.0 (Linux; Android 4.4.2; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/37.0.0.0 Mobile MQQBrowser/6.2 TBS/036555 Safari/537.36 V1_AND_SQ_6.3.7_374_YYB_D QQ/6.3.7.2795 NetType/WIFI WebP/0.3.0 Pixel/1080",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13G34 QQ/6.5.0.443 V1_IPH_SQ_6.5.0_1_APP_A Pixel/750 Core/UIWebView NetType/WIFI Mem/169",
"Mozilla/5.0 (Linux; U; Android 4.4.2; zh-cn; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko)Version/4.0 Chrome/37.0.0.0MQQBrowser/6.8 Mobile Safari/537.36",
"Mozilla/5.0 (iPhone 6s; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/6.0 MQQBrowser/6.8.1 Mobile/13G34 Safari/8536.25 MttCustomUA/2",
"Mozilla/5.0 (Linux; Android 4.4.2; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/37.0.0.0 Mobile MQQBrowser/6.2 TBS/036548 Safari/537.36 MicroMessenger/6.3.18.800 NetType/WIFI Language/zh_CN",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13G34 MicroMessenger/6.3.23 NetType/WIFI Language/zh_CN",
"Mozilla/5.0 (Linux; Android 4.4.2; NX505J Build/KVT49L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 Weibo (nubia-NX505J__weibo__6.8.0__android__android4.4.2) tae_sdk_a_2.0.0 AliApp(BC/2.0.0)",
"Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_3 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13G34 Weibo(iPhone8,1__weibo__6.8.1__iphone__os9.3.3) AliApp(BC/2.1) tae_sdk_ios_2.1 havana"]
