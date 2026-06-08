import os
import random
import requests
import time
from pathlib import Path

from config import common_config
from utils import sql_util
from utils.fileUtil import logLine
from utils.proxyTools import ProxyTools

USER_AGENTS = [
    # Chrome Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    # Chrome Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    # Firefox Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
    # Firefox Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    # Safari Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    # Edge Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
]

def get_with_retry(url, headers=None, timeout=10, max_retries=3):
    """
    返回: (Response, None) 或 (None, Error)
    不返回None导致调用方困惑
    """
    for i in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response, None  # 成功
        except requests.HTTPError as e:
            if i == max_retries:
                return e.response, e  # 返回错误响应+异常
            time.sleep(2 ** i)
        except requests.RequestException as e:
            if i == max_retries:
                return None, e  # 网络错误，无响应
            time.sleep(2 ** i)

def get_random_user_agent() -> str:
    """获取随机 User-Agent"""
    return random.choice(USER_AGENTS)

class WebUtil(object):
    @staticmethod
    def requests_get(url, headers=None, timeout=5, isProxy=False, proxy=None,
                     retry_time=2, sleep=True, retry_interval=2,
                     isMobile=False, sourceName=None, encoding=None):
        state = 0
        content = ''
        ip = ''
        headers = dict(headers or {})
        if isProxy and proxy is None:
            proxy = ProxyTools.get_http_proxy()
        if proxy:
            ip = proxy.split(":")[0]
            port = proxy.split(":")[1]
            proxy_format = {"http": "http://" + ip + ":" + port}
        else:
            proxy_format = None
        count = 0
        info = ''
        while state != 1 and count < retry_time and state != 4:
            if isMobile:
                headers['User-Agent'] = random.choice(common_config.mobile_agents)
            else:
                headers['User-Agent'] = random.choice(common_config.web_agents)
            try:
                if proxy_format:
                    filePage = requests.get(url, headers=headers, proxies=proxy_format, timeout=timeout)
                elif isProxy is False:
                    filePage = requests.get(url, headers=headers, timeout=timeout)
                # 使用代理但无代理IP可用
                else:
                    return [state, content]
            except Exception as e:
                count = count + 1
                if count == retry_time:
                    state = 4
                if proxy_format and count == retry_time:
                    sql_util.upData('proxyip', {'http_state': 3}, {'ip': ip})
                if sleep:
                    time.sleep(retry_interval)
                info = "{0},{1} 请求异常 {2}, {3}".format(sourceName, ip, url, e)
            else:
                if filePage.status_code == 200 and filePage.text != '':
                    state = 1
                    if encoding is not None:
                        filePage.encoding = encoding
                    # content = filePage.text
                    content = filePage.text
                else:
                    state = 4
                info = "{0},{1}, 请求无异常：{2}, {3}".format(sourceName, ip, filePage.status_code, url)
        if state == 0 or state == 4:
            info = "HTTP_GET_FAILED source={0} url={1} proxy_ip={2} detail={3}".format(
                sourceName, url, ip, info
            )
            logLine(common_config.httpRequest_fail, info)
        return [state, content]

    @staticmethod
    def requests_post(url, headers=None, data=None, timeout=5, isProxy=False, proxy=None,
                      retry_time=2, sleep=True, retry_interval=2, isMobile=False,
                      sourceName=None, encoding=None):
        state = 0
        content = ''
        ip = ''
        info = ''
        count = 0
        headers = dict(headers or {})
        data = data or {}
        if isProxy and proxy is None:
            proxy = ProxyTools.get_http_proxy()
        if proxy:
            ip = proxy.split(":")[0]
            port = proxy.split(":")[1]
            proxy_format = {"http": "http://" + ip + ":" + port}
        else:
            proxy_format = None

        while state != 1 and count < retry_time and state != 4:
            if isMobile:
                headers['User-Agent'] = random.choice(common_config.mobile_agents)
            else:
                headers['User-Agent'] = random.choice(common_config.web_agents)
            try:
                if proxy_format:
                    r = requests.post(url, headers=headers, data=data,
                                      proxies=proxy_format, timeout=timeout)
                elif isProxy is False:
                    r = requests.post(url, headers=headers, data=data, timeout=timeout)
                # 使用代理但无代理IP可用
                else:
                    return [state, content]
            except Exception as e:
                count = count + 1
                if count == retry_time:
                    state = 4
                if proxy_format and count == retry_time:
                    sql_util.upData('proxyIP', {'http_state': 3}, {'ip': ip})
                if sleep:
                    time.sleep(retry_interval)
                info = "{0},{1} 请求异常 {2}, {3}".format(sourceName, ip, url, e)
            else:
                if r.status_code == 200 and r.text != '':
                    # html = filePage.content
                    # html_doc = str(html, 'gbk')
                    state = 1
                    if encoding is not None:
                        r.encoding = encoding
                    content = r.text
                else:
                    state = 4
                info = "{0},{1}, 请求无异常：{2}, {3}".format(sourceName, ip, r.status_code, url)
        if state == 0 or state == 4:
            logLine(common_config.httpRequest_fail, info)
        return [state, content]

    @staticmethod
    def loadfile(file_url, file_dir, headers=None, isProxy=False, proxy=None, retry_time=4, sleep=False):
        result = 0
        file_name = file_url.split('?')[0].split('/')[-1]
        filePath = file_dir + file_name
        response = WebUtil.requests_get(file_url, headers, isProxy=isProxy, proxy=proxy, retry_time=retry_time,
                                        sleep=sleep)
        if response[0] != 1:
            result = response[0]
        else:
            if not Path(file_dir).exists():
                os.makedirs(file_dir)
            with open(filePath, "w", encoding="utf-8") as file:
                file.write(response[1])
                file.close()
            result = 1
        return result

    @staticmethod
    def loadFileByName(file_url, file_path, headers=None, isProxy=False, proxy=None, retry_time=4, sleep=False):
        result = 0
        file_dir = os.path.dirname(file_path)
        response = WebUtil.requests_get(file_url, headers, isProxy=isProxy, proxy=proxy, retry_time=retry_time,
                                        sleep=sleep)
        if response[0] != 1:
            result = response[0]
        else:
            if not Path(file_dir).exists():
                os.makedirs(file_dir)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(response[1])
                file.close()
            result = 1
        return result

    @staticmethod
    def user_agent():
        ua_list = [
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
            'Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
        ]
        return random.choice(ua_list)

    @staticmethod
    def header():
        return {'User-Agent': WebUtil.user_agent(),
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Accept-Language': 'zh-CN,zh;q=0.8'}
# if not proxy:
#     proxyip_id = '(85,86,1404,3814,3852,3878,3938,3994,4009, 4775, 4990,5021,5197,5838,6108,6216,6224,' \
#                  '6290,6448,6511,7447,7473,7475,7449,74882)'
#     sql = " UPDATE proxyip SET http_state=1,abandon_http=0 WHERE id in {0}".format(proxyip_id)
#     sql_util.sqlExecute(sql)
