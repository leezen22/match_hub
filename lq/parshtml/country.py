from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait


# 获取国家信息列表，国际元数据以字典结构封装
def getCountrylist(lanqmdataurl):
    # 打开chrome浏览器（需提前安装好chromedriver）
    browser = webdriver.Chrome()
    browser.get(lanqmdataurl)
    # 需要等一下，直到页面加载完成
    wait = WebDriverWait(browser, 10)
    soup = BeautifulSoup(browser.page_source, 'html.parser', from_encoding="gb18030")
    browser.close()
    countryList = []
    countrys = soup.find_all("div", "divList")
    for country in countrys:
        countrydict = {}
        infoID = country.get('id')
        imgID = infoID + 'img'
        nameID = infoID + 'bottomSpan'
        imgs = soup.find_all(id=imgID)
        img = imgs[0]
        names = soup.find_all(id=nameID)
        name = names[0]
        infoType = country.get('infotype')
        countryID = infoID.replace('InfoID_', '')
        countrydict['InfoID'] = countryID
        countrydict['NameCN'] = name.text
        countrydict['FlagPic'] = img.get('src')
        countrydict['InfoType'] = infoType
        countrydict['IfShow'] = '1'
        countryList.append(countrydict)
    return countryList
