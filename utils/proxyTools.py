import json
import random
import threading
import time
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.chrome import webdriver

from config import common_config
from utils import sql_util
from utils.proxyCheck import ProxyCheck


class ProxyTools(object):

    @staticmethod
    def task_proxy():
        threads = []
        jxl_thread = threading.Thread(target=ProxyTools.task_proxy_jxl, args=())
        threads.append(jxl_thread)
        interval_thread = threading.Thread(target=ProxyTools.task_proxy_interval, args=())
        threads.append(interval_thread)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    @staticmethod
    def task_proxy_interval():
        while True:
            ip_local = ProxyTools.get_localip()
            # sql_driver = 'SELECT ip,port,id FROM proxyip WHERE availableDriver in(3) and abandon_driver =0 order By ID DESC '
            # proxy_driver_local = sql_util_zq.select(sql_driver)
            # sql_http = ' SELECT ip,port,type,id FROM proxyip where http_state in(3) and abandon_http=0 order by  http_state ASC '
            # proxy_http_local = sql_util_zq.select(sql_http)
            proxys_ipku = ProxyTools.collect_proxy_ipku()
            proxys_gn = ProxyTools.collect_proxy_gn()
            proxy_kdl= ProxyTools.colllect_proxy_kdl()
            # proxy_drvier = proxys_ipku + proxys_gn
            # proxy_http = proxys_ipku + proxys_gn
            proxys = proxys_ipku + proxys_gn + proxy_kdl
            threads = []
            http_thread = threading.Thread(target=ProxyCheck.checkup_ips_http, args=(proxys, ip_local))
            threads.append(http_thread)
            driver_thread = threading.Thread(target=ProxyCheck.checkup_ips_driver, args=(proxys, ip_local,))
            threads.append(driver_thread)
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            # for data in proxy_drvier:
            #     time.sleep(2)
            #     ProxyCheck.checkup_ip_http(data, ip_local)
            # for data in proxy_http:
            #     time.sleep(3)
            #     ProxyCheck.checkup_ip_driver(data, ip_local=ip_local, headless=True)
            time.sleep(10)

    @staticmethod
    def task_proxy_free():
        ip_local = ProxyTools.get_localip()
        # prox = testGetFreeProxy()
        while True:
            print("开始采集并验证代理")
            proxys_ipku = ProxyTools.collect_proxy_ipku()
            proxys_gn = ProxyTools.collect_proxy_gn()
            proxy_kdl = ProxyTools.colllect_proxy_kdl()
            # proxy_drvier = proxys_ipku + proxys_gn
            # proxy_http = proxys_ipku + proxys_gn
            proxys = proxys_ipku + proxys_gn + proxy_kdl
            count = len(proxys)
            print('代理IP数量:', count)
            print(ip_local)
            threads= []
            http_thread = threading.Thread(target=ProxyCheck.checkup_ips_http, args=(proxys, ip_local))
            threads.append(http_thread)
            driver_thread = threading.Thread(target=ProxyCheck.checkup_ips_driver, args=(proxys, ip_local,))
            threads.append(driver_thread)
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            print("本轮结束")

    @staticmethod
    def get_localip():
        ip_local = None
        while ip_local is None:
            try:
                url = 'http://icanhazip.com/'
                html = requests.get(url, timeout=5)
                ip_local = html.text.replace("\n", '')
            except Exception as e:
                print(e)
                time.sleep(5)
        return ip_local

    @staticmethod
    def task_proxy_jxl():
        target_url = "https://ip.jiangxianli.com/api/proxy_ip"
        ip_local = ProxyTools.get_localip()
        print(['jxl更新本地IP：', ip_local])
        while True:
            try:
                response = requests.get(target_url)
                proxydata = json.loads(response.text)['data']
                proxy = [proxydata['ip'], proxydata['port']]
                ProxyCheck.checkup_ip_http(proxy, ip_local)
                time.sleep(2)
                ProxyCheck.checkup_ip_driver(proxy, ip_local)
                sql_driver = 'SELECT ip,port,id,http_state, abandon_http, availableDriver,abandon_driver ' \
                             'FROM proxyip WHERE availableDriver in(3) and abandon_driver =0 ' \
                             'order By ID ASC '
                proxy_driver_local = sql_util.select(sql_driver)
                sql_http = ' SELECT ip,port,id,http_state, abandon_http, availableDriver,abandon_driver ' \
                           'FROM proxyip where http_state in(3) and abandon_http=0 ' \
                           'order by ID ASC '
                proxy_http_local = sql_util.select(sql_http)
                for data in proxy_driver_local:
                    time.sleep(2)
                    ProxyCheck.checkup_ip_driver(data, ip_local=ip_local, headless=True)
                for data in proxy_http_local:
                    time.sleep(2)
                    ProxyCheck.checkup_ip_http(data, ip_local)
            except Exception as e:
                print(e)
            else:
                pass

            time.sleep(15)

    @staticmethod
    def get_http_proxy():
        proxy = None
        sql = "SELECT ip,port,type,id FROM proxyip " \
              "WHERE http_state in(1,2) and abandon_http =0 " \
              "ORDER BY RAND() LIMIT 1"
        items = list(sql_util.select(sql))
        while len(items) > 0:
            number = len(items)
            # i = random.randint(0, number - 1)
            item = items[0]
            proxy = item[0] + ":" + item[1]
            break
        return proxy

    @staticmethod
    def get_driver_proxy():
        sql = "SELECT ip,port FROM proxyip " \
              "WHERE availableDriver=1 and used_driver =0 and abandon_driver=0 " \
              "ORDER BY RAND() LIMIT 1 "
        items = sql_util.select(sql)
        for item in items:
            sql_util.upData('proxyip', {'used_driver': 1}, {'ip': item[0]})
        if len(items) > 0:
            item = items[0]
            proxy = item[0] + ":" + item[1]
        else:
            proxy = None
        return proxy

    @staticmethod
    def get_driver_proxys(count):
        proxys = []
        sql = "SELECT ip,port FROM proxyip WHERE http_state in(1,2,3,4) and availableDriver=1 " \
              " and used_driver =0 and abandon_driver=0 ORDER BY RAND() LIMIT " + str(count)
        items = sql_util.select(sql)
        # for item in items:
        #     sql_util_zq.updateData('proxyip', {'used_driver': 1}, {'ip': item[0]})
        if len(items) > 0:
            for item in items:
                proxy = item[0] + ":" + item[1]
                proxys.append(proxy)
                sql_util.upData('proxyip', {'used_driver': 1}, {'ip': item[0]})
        return proxys

    # jiangxianli
    # github:https://github.com/jiangxianli/ProxyIpLib
    # URL: https://ip.jiangxianli.com/api/proxy_ip

    # 快代理
    @staticmethod
    def colllect_proxy_kdl():
        # url = common_config.website_kd
        proxys = []
        headers = common_config.headers_kd
        headers['User-Agent'] = random.choice(common_config.web_agents)
        # proxy = {'https': "https://" + item[0] + ":" + str(item[1])}
        for i in range(1, 2):
            url = common_config.website_kd + "/inha/" + str(i) + "/"
            try:
                response = requests.get(url, headers=headers, timeout=5)
            except Exception as e:
                print(e)
            else:
                soup = BeautifulSoup(response.text, 'html.parser')
                soup.prettify()
                trs = soup.select('body table tbody tr')
                for tr in trs:
                    data = {}
                    tds = tr.selectData('td')
                    data['ip'] = tds[0].text
                    data['port'] = tds[1].text
                    data['hide'] = 1
                    data['responsetime'] = float(tds[5].text.split('秒')[0])
                    data['source'] = 'kuaidaili'
                    proxys.append((data['ip'], data['port']))
        return proxys

    # 高匿网
    @staticmethod
    def collect_proxy_gn():
        proxys = []
        headers = common_config.headers_gn
        headers['User-Agent'] = random.choice(common_config.web_agents)
        # proxy = {'https': "https://" + item[0] + ":" + str(item[1])}
        for i in range(1, 2):
            url = common_config.website_gn + str(i)
            try:
                response = requests.get(url, headers=headers, timeout=5)
            except Exception as e:
                print(e)
            else:
                soup = BeautifulSoup(response.text, 'html.parser')
                soup.prettify()
                # print(soup)
                trs = soup.select('body table#ip_list tr')
                count = len(trs)
                for i in range(1, count):
                    tr = trs[i]
                    data = {}
                    tds = tr.selectData('td')
                    data['responsetime'] = float(tds[6].selectData('div')[0].get('title').split('秒')[0])
                    if data['responsetime'] <= 1.5:
                        data['type'] = tds[5].text.lower()
                        data['ip'] = tds[1].text
                        data['port'] = tds[2].text
                        data['hide'] = 1
                        data['source'] = 'gaoni'
                        proxys.append((data['ip'], data['port']))
        return proxys

    # 免费IP代理库
    @staticmethod
    def collect_proxy_ipku():
        proxys = []
        for i in range(1, 2):
            url = "https://ip.jiangxianli.com/?page=" + str(i) + "&country=中国"
            response = requests.get(url, timeout=3)
            soup = BeautifulSoup(response.text, 'html.parser')
            soup.prettify()
            buttons = soup.find_all('button', {'class': 'layui-btn layui-btn-sm btn-copy'})
            for button in buttons:
                # print(button.get('data-url'))
                proxy = button.get('data-url')
                proxy_dict = {
                    'ip': proxy.split("//")[-1].split(":")[0],
                    'port': proxy.split("//")[-1].split(":")[1],
                    'type': proxy.split(':')[0],
                    'hide': 1,
                    'country': 'China'
                }
                proxys.append((proxy_dict['ip'], proxy_dict['port']))
        return proxys

    @staticmethod
    def generateCookie(count):
        for i in range(0, count):
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')
            driver = webdriver.Chrome(chrome_options=chrome_options)
            # driver = webdriver.Chrome()
            url = "http://zq.win007.com/cn/League/36.html"
            driver.get(url)
            cookie_list = driver.get_cookies()
            # for cookie in cookie_list:
            #     cookies = cookie['name'] + "=" + cookie['value'] + ";"+cookies
            # print(cookie_list)
            if len(cookie_list) > 1:
                cookie = cookie_list[1]['name'] + "=" + cookie_list[1]['value'] + ";" + cookie_list[0]['name'] + "=" + \
                         cookie_list[0]['value']
                sql_util.insertData('cookie', {'cookie': cookie})
            driver.close()
        # return cookies

    @staticmethod
    def getCookie(count):
        sql = "select cookie from cookie ORDER BY createTime DESC LIMIT 100 "
        result = sql_util.select(sql)
        cookielist = []
        for data in result:
            cookielist.append(data[0])
        sample = random.sample(cookielist, count)
        return sample

