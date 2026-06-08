import random
import threading
import time
import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from utils import sql_util
from utils.dateUtil import getNowTime
from utils.webDriver import WebDriver


class ProxyCheck(object):

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
    # 验证有效Http代理driver是否有效
    @staticmethod
    def task_checkip_driver():
        ip_local = ProxyCheck.get_localip()
        number_input = input("请输入线程数量：")
        isheadless = input("是否静默执行：1 是 0 否 ")
        if isheadless == '1':
            headless = True
        else:
            headless = False
        print('本地IP', ip_local)
        sql = 'SELECT ip,port,id FROM proxyip WHERE availableDriver in(1,3) and abandon_driver =0 order By ID ASC '
        items = sql_util.select(sql)
        count = len(items)
        print(count)
        number = int(number_input)
        cell = count//number
        threads = []
        for i in range(0, number):
            start = i*cell
            if i == number-1:
                end = count
            else:
                end = start+cell
            datas= items[start:end]
            check_thread = threading.Thread(target=ProxyCheck.checkup_ips_driver, args=(datas, ip_local, headless,))
            # check_thread = threading.Thread(target=ProxyCheck.check_proxydriver_asia, args=(datas, headless,))
            threads.append(check_thread)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # 验证非有效HTTP代理
    @staticmethod
    def task_checkip_http():
        ip_local = ProxyCheck.get_localip()
        print('本地IP', ip_local)
        sql = ' SELECT ip,port,type,id FROM proxyip where http_state in(1,2) and abandon_http=0 order by id ASC '
        result = sql_util.select(sql)
        count = len(result)
        print(count)
        for data in result:
            time.sleep(2)
            ProxyCheck.checkup_ip_http(data, ip_local)

    @staticmethod
    def checkup_ips_driver(datas, ip_local, headless=True, interval=3):
        print("批量检查driver 代理IP")
        for data in datas:
            time.sleep(interval)
            ProxyCheck.checkup_ip_driver(data, ip_local=ip_local, headless=headless)

    @staticmethod
    def checkup_ips_http(datas, ip_local, interval=3):
        print("批量检查Http 代理IP")
        for data in datas:
            time.sleep(interval)
            ProxyCheck.checkup_ip_http(data, ip_local=ip_local)


    @staticmethod
    def checkup_ip_driver(proxy, ip_local=None, headless=True):
        if ip_local is None:
            url = 'http://icanhazip.com/'
            html = requests.get(url, timeout=4)
            ip_local = html.text.replace("\n", '')
        ip_proxy = ProxyCheck.get_ip_drivercheck(proxy, headless)
        print(proxy)
        print([getNowTime(), 'driver验证', ip_proxy, ip_local])
        result = sql_util.select_table_rows('proxyip', ['ip', 'port', 'type', 'id'], {'ip': proxy[0]})
        if ip_proxy is None or ip_proxy == ip_local:
            if len(result) > 0:
                sql_util.upData('proxyip', {'availableDriver': 5, 'abandon_driver': 1, 'used_driver':0}, {'ip': proxy[0]})
            else:
                sql_util.insertData('proxyip', {'ip': proxy[0], 'port': proxy[1], 'availableDriver': 5, 'abandon_driver': 1, 'used_driver':0})
        else:
            if len(result) > 0:
                sql_util.upData('proxyip', {'availableDriver': 1, 'abandon_driver': 0, 'used_driver':0}, {'ip': proxy[0]})
            else:
                sql_util.insertData(
                    'proxyip',
                    {'ip': proxy[0], 'port': proxy[1], 'availableDriver': 1,'abandon_driver': 0,'used_driver':0}
                )

    @staticmethod
    def checkup_ip_http(proxy, ip_local=None):
        print(proxy)
        if ip_local is None:
            url = 'http://icanhazip.com/'
            html = requests.get(url, timeout=4)
            ip_local = html.text.replace("\n", '')
        ip_proxy = ProxyCheck.get_ip_httpcheck(proxy)
        print([getNowTime(), 'http验证', ip_proxy, ip_local])
        result = sql_util.select_table_rows('proxyip', ['ip', 'port', 'type', 'id'], {'ip': proxy[0]})
        if ip_proxy is None or ip_proxy == ip_local:
            if len(result) > 0:
                sql_util.upData('proxyip', {'http_state': 5, 'abandon_http': 1}, {'ip': proxy[0]})
            else:
                sql_util.insertData('proxyip', {'ip': proxy[0], 'port': proxy[1], 'http_state': 5, 'abandon_http': 1})
        else:
            if len(result) > 0:
                sql_util.upData('proxyip', {'http_state': 1, 'abandon_http': 0}, {'ip': proxy[0]})
            else:
                sql_util.insertData('proxyip', {'ip': proxy[0], 'port': proxy[1], 'http_state': 1, 'abandon_http': 0})

    @staticmethod
    def get_ip_httpcheck(data):
        proxy = {"http": "http" + "://" + data[0] + ":" + data[1]}
        ip_proxy = None
        sites = [
            # 'http://ip.chinaz.com/',
            'http://icanhazip.com/',
            # 'http://coolaf.com/',
            # 'https://tool.lu/ip/'
        ]
        url = random.choice(sites)
        try:
            reponse = requests.get(url, timeout=10, proxies=proxy)
            html = reponse.text
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title
            # if title and title.string == '违法违规网站':
            if '违法违规网站' in html or '404 not found' in html or 'File not found' in html or "Too Many Requests" in html:
                print("响应内容异常：", data)
                return ip_proxy
            if url == 'http://icanhazip.com/' and len(html) < 25 and len(html)>5:
                ip_proxy = html.replace("\n", '')
            elif url == 'http://ip.chinaz.com/':
                dd_ip = soup.find('dd', attrs={'class': 'fz24'})
                ip_proxy = dd_ip.text
            elif url == 'http://coolaf.com/':
                a_ip = soup.find(id='getip')
                ip_proxy = a_ip.text

            elif url == 'https://tool.lu/ip/':
                input_ip = soup.find('input', attrs={'name': 'ip'})
                ip_proxy = input_ip.get("value")
            else:
                pass
        except Exception as e:
            print(e)
            # print(traceback.format_exc())
        else:
            pass
        return ip_proxy

    @staticmethod
    def get_ip_drivercheck(data, headless=True):
        proxy = data[0] + ":" + data[1]
        browser = WebDriver.get_driver(proxy, timeout=10, headless=headless)
        # url = 'http://icanhazip.com/'
        ip_proxy = None
        sites = [
            # 'http://ip.chinaz.com/',
            'http://icanhazip.com/',
            # 'http://coolaf.com/',
            # 'https://tool.lu/ip/',
            # 'http://www.baidu.com/'
        ]
        url = random.choice(sites)

        try:
            # print([data, url])
            browser.get(url)
            html = browser.page_source
            title = browser.title
            if '违法违规网站' in html or '404 not found' in html or 'File not found' in html \
                    or "Too Many Requests" in html:
                print("响应内容异常：", data)
                return ip_proxy
                # sql_util_zq.upData('proxyip', {'availableDriver': 5, 'abandon': 1}, {'ip': data[0]})
            if url == 'http://icanhazip.com/':
                pre = browser.find_element_by_css_selector('body pre')
                info = pre.text.replace("\n", '')
                if len(info) < 20 and len(info)> 10:
                    ip_proxy = pre.text.replace("\n", '')
                # ip_proxy = html.replace("\n", '')
            elif url == 'http://ip.chinaz.com/':
                soup = BeautifulSoup(html, 'html.parser')
                dd_ip = soup.find('dd', attrs={'class': 'fz24'})
                ip_proxy = dd_ip.text
            elif url == 'http://coolaf.com/':
                soup = BeautifulSoup(html, 'html.parser')
                a_ip = soup.find(id='getip')
                ip_proxy = a_ip.text

            elif url == 'https://tool.lu/ip/':
                soup = BeautifulSoup(html, 'html.parser')
                input_ip = soup.find('input', attrs={'name': 'ip'})
                ip_proxy = input_ip.get("value")
            else:
                pass
        except TimeoutException as e:
            # print(e)
            pass
        except Exception as e:
            pass
            # print(traceback.format_exc())
            # print(e)
        else:
            pass
        time.sleep(5)
        browser.quit()
        return ip_proxy

