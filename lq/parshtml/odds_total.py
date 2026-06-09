import traceback
from bs4 import BeautifulSoup
from config import lqconfig_qt, common_config
from lq.dao.MatchDao import selectMatch
from utils.fileUtil import logLine
from utils.webUtil import get_random_user_agent, get_with_retry


# 获取比赛大小初盘和终盘
def get_overdown(scheduleID):
    oddsdata = {"odds": [], 'state': 0}
    matchs = selectMatch({'scheduleID': scheduleID})
    if len(matchs) > 0:
        matchstate = matchs[0][3]
        matchID = matchs[0][7]
        oddsdata['matchstate'] = matchstate
        url = lqconfig_qt.TotalScore_n + '?' + 'id=' + str(scheduleID)
        try:
            # 访问篮球指数页面，response返回页面HTML内容
            # webresponse = requests.get(url, headers=lqconfig_qt.headers)
            headers=lqconfig_qt.headers
            headers={**headers, "User-Agent": get_random_user_agent()}
            webresponse,error = get_with_retry(url, headers=headers, timeout=10, max_retries=3)
            # webresponse = requests.get(url, headers=headers,timeout=10)
            if webresponse is not None:
                content = webresponse.text.strip()
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    # 赔率table tr 标签
                    odds_tr = soup.select('body table#odds tr')
                    counts = len(odds_tr)
                    # 判断指数公司列表是否为空，大于2不为空
                    if counts > 2:
                        for i in range(2, counts):
                            tds = odds_tr[i].select('td')
                            # 多盘口指数，tr标签有classs属性
                            if odds_tr[i].has_attr('optimize') or tds[1].find('span') is None:
                                pass
                            # 无class属性，tr则为主盘口
                            else:
                                totaldict = {'ScheduleID': scheduleID, 'MatchID': matchID}
                                CompanyName = tds[0].get_text().replace("\r\n", "").strip()
                                if len(CompanyName) > 0:
                                    totaldict['CompanyName'] = CompanyName
                                # QT让分和大小分同公司ID不一致
                                if CompanyName in lqconfig_qt.companys.keys():
                                    companyid = lqconfig_qt.companys[CompanyName]
                                else:
                                    companyid = 0
                                # companyid = tds[1].find('span').get('companyid')
                                totaldict['CompanyID'] = companyid
                                HighOdds_F = odds_tr[i].select('#td_11')[0].get_text().replace("\r\n", "").strip()
                                if len(HighOdds_F) > 0:
                                    totaldict['HighOdds_F'] = HighOdds_F
                                totalScore_F = odds_tr[i].select('#td_12')[0].get_text().replace("\r\n", "").strip()
                                if len(totalScore_F) > 0:
                                    totaldict['Goal_F'] = totalScore_F
                                LowOdds_F = odds_tr[i].select('#td_13')[0].get_text().replace("\r\n", "").strip()
                                if len(LowOdds_F) > 0:
                                    totaldict['LowOdds_F'] = LowOdds_F
                                HighOdds = odds_tr[i].select('#td1')[0].get_text().replace("\r\n", "").strip()
                                if len(HighOdds) > 0:
                                    totaldict['HighOdds'] = HighOdds
                                totalScore = odds_tr[i].select('#td2')[0].get_text().replace("\r\n", "").strip()
                                if len(totalScore) > 0:
                                    totaldict['Goal'] = totalScore
                                LowOdds = odds_tr[i].select('#td3')[0].get_text().replace("\r\n", "").strip()
                                if len(LowOdds) > 0:
                                    totaldict['LowOdds'] = LowOdds
                                # html标签提取数据正常，将公司开盘信息插入赔率列表
                                oddsdata['odds'].append(totaldict)
                except Exception as e:
                    print(e)
                    excepstr = traceback.format_exc()
                    logLine(lqconfig_qt.exception, excepstr)
                    # 本地记录失败记录
                    logLine(common_config.lq_totalodds_fail, [webresponse[0], scheduleID])
                else:
                    oddsdata['state'] = 1
        
        except requests.RequestException as e:
            return {"success": False, "error": f"请求失败: {e}", "match_id": str(scheduleID)}
        except Exception as e:
            return {"success": False, "error": f"解析失败: {e}", "match_id": str(scheduleID)}
    return oddsdata



# if __name__ == '__main__':
#     OddsList = get_overdown(544813)
#     print(OddsList)
