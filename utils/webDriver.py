import time
from selenium import webdriver
from utils import sql_util


class WebDriver(object):
    @staticmethod
    def get_proxy_driver(proxy=None, headless=True, timeout=8, incognito=True):
        driver = None
        if proxy is None:
            sql = 'SELECT ip,port FROM proxyip WHERE availableDriver in(1) ORDER BY RAND() LIMIT ' + str(1)
            result = sql_util.select_rows(sql)
            if len(result) > 0:
                data = result[0]
                proxy = data[0]+":"+data[1]
            else:
                return driver
        chrome_options = webdriver.ChromeOptions()
        if proxy:
            chrome_options.add_argument('--proxy-server={0}'.format(proxy))
        if headless:
            chrome_options.add_argument('--headless')
        if incognito:
            chrome_options.add_argument('--incognito')
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(timeout)
        return driver

    @staticmethod
    def get_driver(proxy=None, headless=True, timeout=8, incognito=True, disable_js=False):
        chrome_options = webdriver.ChromeOptions()
        if proxy:
            chrome_options.add_argument('--proxy-server={0}'.format(proxy))
        if headless:
            chrome_options.add_argument('--headless')
        if incognito:
            chrome_options.add_argument('--incognito')
        if disable_js:
            chrome_options.add_argument('–disable-javascript')
        # # 谷歌文档提到需要加上这个属性来规避bug
        # chrome_options.add_argument('--disable-gpu')
        # # 禁止策略化，自动化提示
        # chrome_options.add_argument('--disable-infobars')
        # # 不加载图片, 提升速度
        # chrome_options.add_argument('blink-settings=imagesEnabled=false')
        chrome_options.add_argument('log-level=3')
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        browser = webdriver.Chrome(options=chrome_options)
        browser.set_page_load_timeout(timeout)
        # self.driver.get(url)
        return browser

    @staticmethod
    def driver_get(url, driver):
        content = ''
        state = 0
        count = 1
        while state != 1 and count < 4:
            try:
                driver.get(url)
            except Exception as e:
                time.sleep(1)
                count = count+1
                if count == 4:
                    state = 404
            else:
                state = 1
                driver_state = 1
                content = driver.page_source
        return [state, content]
