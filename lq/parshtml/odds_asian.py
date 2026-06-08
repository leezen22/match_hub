import traceback
from bs4 import BeautifulSoup
from config import lqconfig_qt
from lq.dao.MatchDao import selectMatch
from utils.webUtil import get_random_user_agent, get_with_retry


# 获取比赛亚指初盘和终盘
def get_asianodds2(scheduleID):
    oddsdata = {"odds": [], 'state': 0}
    matchs = selectMatch({'scheduleID': scheduleID})
    if len(matchs) > 0:
        matchID = matchs[0][7]
        matchstate = matchs[0][3]
        oddsdata['matchstate'] = matchstate
        url = lqconfig_qt.AsianOdds_n + '?' + 'id=' + str(scheduleID)
        try:
            # 访问篮球亚指页面，response返回页面HTML内容
            # webresponse = requests.get(url, headers=lqconfig_qt.headers)

            headers=lqconfig_qt.headers
            headers={**headers, "User-Agent": get_random_user_agent()}

            # webresponse = requests.get(url, headers=headers, timeout=10)

            webresponse,error = get_with_retry(url, headers=headers, timeout=10, max_retries=3)
            if webresponse:
                content = webresponse.text.strip()
                if webresponse.status_code == 200 and content != '':
                    # 获取页面成功
                    try:
                        soup = BeautifulSoup(content, 'html.parser')
                        # 赔率table tr 标签
                        odds_trs = soup.select('body table#odds tr')
                        counts = len(odds_trs)
                        # 判断让分指数公司列表是否为空，大于2不为空
                        if counts > 2:
                            for i in range(2, counts):
                                tds = odds_trs[i].select('td')
                                # 多盘口让分指数，tr标签有classs属性
                                if odds_trs[i].has_attr('optimize') or tds[1].find('span') is None:
                                    pass
                                # 无class属性，tr则为主盘口
                                else:
                                    asiandict = {'ScheduleID': scheduleID, 'MatchID': matchID}
                                    CompanyName = tds[0].get_text().replace("\r\n", "").strip()
                                    if len(CompanyName) > 0:
                                        asiandict['CompanyName'] = CompanyName
                                    companyid = tds[1].find('span').get('companyid')
                                    if companyid is not None:
                                        asiandict['CompanyID'] = companyid
                                    HomeOdds_F = odds_trs[i].select('#td_11')[0].get_text().replace("\r\n", "").strip()
                                    if len(HomeOdds_F) > 0:
                                        asiandict['HomeOdds_F'] = HomeOdds_F
                                    Goal_F = odds_trs[i].select('#td_12')[0].get_text().replace("\r\n", "").strip()
                                    if len(Goal_F) > 0:
                                        asiandict['Goal_F'] = Goal_F
                                    AwayOdds_F = odds_trs[i].select('#td_13')[0].get_text().replace("\r\n", "").strip()
                                    if len(AwayOdds_F) > 0:
                                        asiandict['AwayOdds_F'] = AwayOdds_F
                                    HomeOdds = odds_trs[i].select('#td2')[0].get_text().replace("\r\n", "").strip()
                                    if len(HomeOdds) > 0:
                                        asiandict['HomeOdds'] = HomeOdds
                                    Goal = odds_trs[i].select('#td3')[0].get_text().replace("\r\n", "").strip()
                                    if len(Goal) > 0:
                                        asiandict['Goal'] = Goal
                                AwayOdds = odds_trs[i].select('#td4')[0].get_text().replace("\r\n", "").strip()
                                if len(AwayOdds) > 0:
                                    asiandict['AwayOdds'] = AwayOdds
                                    # html标签提取数据正常，将公司开盘信息插入赔率列表
                                oddsdata['odds'].append(asiandict)
                    except Exception as e:
                        excepstr = traceback.format_exc()
                        # 获取页面成功
                    else:
                        oddsdata['state'] = 1
            
        except Exception as e:
            excepstr = traceback.format_exc()
        else:
            oddsdata['state'] = 1
    # 返回亚指开盘公司初盘和终盘盘口
    return oddsdata

def get_asianodds(scheduleID):
    oddsdata = {"odds": [], 'state': 0}
    matchs = selectMatch({'scheduleID': scheduleID})
    
    if len(matchs) > 0:
        matchID = matchs[0][7]
        matchstate = matchs[0][3]
        oddsdata['matchstate'] = matchstate
        url = lqconfig_qt.AsianOdds_n + '?' + 'id=' + str(scheduleID)
        
        try:
            headers = lqconfig_qt.headers
            headers = {**headers, "User-Agent": get_random_user_agent()}
            
            webresponse, error = get_with_retry(url, headers=headers, timeout=10, max_retries=3)
            
            if webresponse:
                content = webresponse.text.strip()
                if webresponse.status_code == 200 and content != '':
                    try:
                        soup = BeautifulSoup(content, 'html.parser')
                        odds_trs = soup.select('body table#odds tr')
                        counts = len(odds_trs)
                        
                        if counts > 2:
                            for i in range(2, counts):
                                tr_element = odds_trs[i]
                                tds = tr_element.select('td')
                                
                                # 检查是否为有效的赔率行
                                if not is_valid_odds_row(tr_element, tds):
                                    continue
                                
                                # 提取赔率数据
                                odds_dict = extract_odds_data(tr_element, tds, scheduleID, matchID)
                                if odds_dict:
                                    oddsdata['odds'].append(odds_dict)
                        
                        oddsdata['state'] = 1
                        
                    except Exception as e:
                        excepstr = traceback.format_exc()
                        # 保持 oddsdata['state'] = 0，表示解析失败
                        
        except Exception as e:
            excepstr = traceback.format_exc()
            # 保持 oddsdata['state'] = 0，表示请求失败
    
    return oddsdata


def is_valid_odds_row(tr_element, tds):
    """
    检查是否为有效的赔率行
    返回 True 表示该行是有效的主盘口赔率行
    """
    # 安全检查：确保有足够的td元素
    if len(tds) < 4:
        return False
    
    # 获取tr的class属性
    tr_class = tr_element.get('class', [])
    
    # 过滤多盘口行（hui_txt类）
    if 'hui_txt' in tr_class:
        return False
    
    # 过滤汇总行（最大值/最小值）
    if 'yellow_bg' in tr_class:
        return False
    
    # 过滤标题行
    if 'title' in tr_class:
        return False
    
    # 检查第二个td是否包含span标签（主盘口的标志）
    if tds[1].find('span') is None:
        return False
    
    # 检查公司名称是否为空（多盘口行的公司名称为空）
    company_name = tds[0].get_text().strip()
    if not company_name:
        return False
    
    return True


def extract_odds_data(tr_element, tds, scheduleID, matchID):
    """
    从有效的赔率行提取数据
    返回字典或None
    """
    try:
        asiandict = {'ScheduleID': scheduleID, 'MatchID': matchID}
        
        # 提取公司名称
        CompanyName = tds[0].get_text().replace("\r\n", "").strip()
        if CompanyName:
            asiandict['CompanyName'] = CompanyName
        
        # 提取公司ID
        span_elem = tds[1].find('span')
        if span_elem:
            companyid = span_elem.get('companyid')
            if companyid:
                asiandict['CompanyID'] = companyid
        
        # 提取初盘数据（td_11, td_12, td_13）
        home_odds_f = extract_td_text(tr_element, '#td_11')
        if home_odds_f:
            asiandict['HomeOdds_F'] = home_odds_f
        
        goal_f = extract_td_text(tr_element, '#td_12')
        if goal_f:
            asiandict['Goal_F'] = goal_f
        
        away_odds_f = extract_td_text(tr_element, '#td_13')
        if away_odds_f:
            asiandict['AwayOdds_F'] = away_odds_f
        
        # 提取终盘数据（td2, td3, td4）
        home_odds = extract_td_text(tr_element, '#td2')
        if home_odds:
            asiandict['HomeOdds'] = home_odds
        
        goal = extract_td_text(tr_element, '#td3')
        if goal:
            asiandict['Goal'] = goal
        
        away_odds = extract_td_text(tr_element, '#td4')
        if away_odds:
            asiandict['AwayOdds'] = away_odds
        
        return asiandict
        
    except Exception as e:
        # 单行数据提取失败，返回None跳过该行
        return None


def extract_td_text(tr_element, selector):
    """
    安全地从tr元素中提取指定选择器的文本
    """
    try:
        elements = tr_element.select(selector)
        if elements:
            text = elements[0].get_text().replace("\r\n", "").strip()
            return text
    except Exception:
        pass
    return None

# if __name__ == '__main__':
#     scheduleID = '717756'
#     odds=get_asianodds(scheduleID)
    # print(odds)
#     url = lqconfig_qt.AsianOdds_n + '?' + 'id=' + str(scheduleID)
#     webresponse = WebUtil.requests_get(url, headers=lqconfig_qt.headers)
#     content = webresponse[1]
#     if webresponse[0] != 1:
#         logLine(common_config.lq_asianodds_fail, [webresponse[0], scheduleID])
#     if webresponse[0] == 1 and content != '':
#         # 获取页面成功
#         try:
#             soup = BeautifulSoup(content, 'html.parser')
#             tables = soup.select('table.font13')
#             trs = tables[1].select('tr')
#         except Exception as e:
#             print(e)

#     OddsList = get_asianodds(544813)
#     print(OddsList)