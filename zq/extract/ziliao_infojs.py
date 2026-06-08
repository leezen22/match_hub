import os
import time
from datetime import datetime

import utils.fileUtil
import utils.js2pyUtil
from config import zqconfig_qt
from utils.webUtil import WebUtil


def up_ziliaoJS():
    headers = zqconfig_qt.headers
    headers['Referer'] = zqconfig_qt.ziliao
    if os.path.exists(zqconfig_qt.ziliao_jspath):
        # 如果本地文件存在
        mTime = time.localtime(os.path.getmtime(zqconfig_qt.ziliao_jspath))
        lastTime = time.strftime("%Y-%m-%d", mTime)
        now = datetime.now()
        nowTime = now.strftime("%Y-%m-%d")
        if lastTime != nowTime:
            WebUtil.loadFileByName(zqconfig_qt.ziliao_jsurl, zqconfig_qt.ziliao_jspath, headers)
    else:
        WebUtil.loadFileByName(zqconfig_qt.ziliao_jsurl, zqconfig_qt.ziliao_jspath, headers)


def up_scheJS():
    context = utils.js2pyUtil.jsLocjs(zqconfig_qt.ziliao_jspath)
    # 国家或地区列表
    for i in range(0, len(context.arr)):
        sclassList = context.arr[i][4]
        for sclass in sclassList:
            # 更新联赛JS文件，杯赛+无子联赛联赛
            sclassinfo = sclass.split(",")
            print(sclassinfo)
            leagueId = sclassinfo[0]
            sclassName = sclassinfo[1]
            type = sclassinfo[2]
            ifHaveSub = sclassinfo[3]
            for i in range(4, len(sclassinfo)):
                scheinfo = get_scheJS([leagueId, sclassName, type, ifHaveSub, sclassinfo[i]])
                sche_headers = zqconfig_qt.headers
                sche_headers['Referer'] = scheinfo[2]
                try:
                    if len(scheinfo) > 0:
                        WebUtil.loadFileByName(scheinfo[0], scheinfo[1], sche_headers)
                except Exception as e:
                    print("更新失败：")
                    print([scheinfo[0], scheinfo[1]])


def get_scheJS(sclassinfo):
    schejsList = []
    # 足球杯赛
    if str(sclassinfo[2]) == '2':
        weburl = zqconfig_qt.cup_web_schedir + sclassinfo[4] + "/" + str(sclassinfo[0]) + ".html"
        schejs_url = zqconfig_qt.scheWebdir + sclassinfo[4] + "/c" + str(sclassinfo[0]) + ".js"
        schejs_path = zqconfig_qt.scheWebdir + sclassinfo[4] + "/c" + str(sclassinfo[0]) + ".js"
        schejsList = [schejs_url, schejs_path, weburl]
    # 足球联赛但无子联赛
    elif str(sclassinfo[2]) == '1' and str(sclassinfo[3]) == '0':
        weburl = zqconfig_qt.league_web_schedir + sclassinfo[4] + "/" + str(sclassinfo[0]) + ".html"
        schejs_url = zqconfig_qt.scheWebdir + sclassinfo[4] + "/s" + str(sclassinfo[0]) + ".js"
        schejs_path = zqconfig_qt.schelocaldir + sclassinfo[4] + "/s" + str(sclassinfo[0]) + ".js"
        schejsList = [schejs_url, schejs_path, weburl]
    # 足球联赛有子联赛
    else:
        pass
    return schejsList

# if __name__ == '__main__':
    # up_ziliaoJS()
    # up_scheJS()