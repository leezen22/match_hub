import traceback

from config import zqconfig_qt, common_config
from utils import sql_util
from utils.fileUtil import logLine


class OddsUtil(object):
    @staticmethod
    def getRefer(leagueID, leagueType, season, sublegueID=None):
        host = zqconfig_qt.host_zuqiu
        if leagueType == 2:
            referer = host + '/cn/CupMatch/' + season + "/" + str(leagueID) + ".html"
        elif leagueType == 1 and sublegueID is not None:
            referer = host + '/cn/SubLeague/' + season + "/" + str(leagueID) + '_' + str(sublegueID) + ".html"
        else:
            referer = host + '/cn/League/' + season + "/" + str(leagueID) + ".html"
        return referer

    #  亚指和大小解析通用
    @staticmethod
    def collect_odds(scheduleID, soup):
        oddsresult = {'state': 0, "odds": []}
        try:
            # soup = BeautifulSoup(content, 'html.parser')
            # odds_trs = soup.select("tbody tr")
            # print(odds_trs)
            odds_trs = soup.select('table#odds tr')
            # print(odds_trs)
            count_tr = len(odds_trs)
            if count_tr < 3:
                pass
            elif count_tr == 3:
                oddsresult['state'] = 1
            elif count_tr > 4:
                oddsresult['state'] = 1
                for i in range(2, count_tr - 2):
                    tds = odds_trs[i].find_all('td')
                    print(tds)
                    oddsdata = {}
                    oddsdata['scheduleid'] = scheduleID
                    if odds_trs[i].has_attr('companyid'):
                        oddsdata['companyid'] = odds_trs[i].get('companyid')
                    else:
                        oddsdata['companyid'] = tds[1].find('span').get('companyid')

                    if tds[1].get_text().strip() == '':
                        oddsdata['num'] = 1
                    else:
                        num = tds[1].get_text().strip().split('盘口')[-1]
                        oddsdata['num'] = int(num)

                    if tds[2].get_text().strip() != '':
                        oddsdata['FirstUpOdds'] = tds[2].get_text()
                    if tds[3].get('goals') is not None and tds[3].get('goals').strip() != '':
                        oddsdata['FirstGoal'] = tds[3].get('goals')
                    if tds[4].get_text().strip() != '':
                        oddsdata['FirstDownOdds'] = tds[4].get_text()
                    if tds[5].get_text().strip() != '':
                        oddsdata['UpOdds_R'] = tds[5].get_text()
                    if tds[6].get('goals') is not None and tds[6].get('goals').strip() != '':
                        oddsdata['Goal_R'] = tds[6].get('goals')
                    if tds[7].get_text().strip() != '':
                        oddsdata['DownOdds_R'] = tds[7].get_text()
                    if tds[8].get_text().strip() != '':
                        oddsdata['UpOdds'] = tds[8].get_text()
                    if tds[9].get('goals') is not None and tds[9].get_text().strip() != '':
                        oddsdata['Goal'] = tds[9].get('goals')
                    if tds[10].get_text().strip() != '':
                        oddsdata['DownOdds'] = tds[10].get_text()
                    if len(oddsdata) > 3:
                        oddsresult['odds'].append(oddsdata)
            else:
                pass
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            # common_util.logline(common_config.soup_e, ['zq.getAsianOdds', url, e])
            oddsresult['state'] = 0
        return oddsresult

    @staticmethod
    def up_asia_odds(scheduleID, finished, matchState, oddsList):
        sql_util.upData('zq_schedule', {'asianodds_f': 1}, {'ScheduleID': scheduleID})
        if finished == 0:
            datas = []
            multi_datas = []
            for data in oddsList:
                while data['num'] == 1:
                    data2 = data.copy()
                    del data2['num']
                    datas.append(data2)
                    break
                multi_datas.append(data)
            sql_util.insertDatas('zq_AsianOdds', datas)
            sql_util.insertDatas('zq_multiAsianOdds', multi_datas)
        elif finished == 1:
            for data in oddsList:
                if data['num'] == 1:
                    data2 = data.copy()
                    condition = {'ScheduleID': scheduleID, 'CompanyID': data['companyid']}
                    del data2['num']
                    results = sql_util.select_table_rows('zq_AsianOdds', ['OddsID'], condition, isDis=True)
                    if len(results) > 0:
                        sql_util.upData('zq_AsianOdds', data2, condition)
                    else:
                        sql_util.insertData('zq_AsianOdds', data2)
                condition2 = {'ScheduleID': scheduleID, 'CompanyID': data['companyid'], 'num': data['num']}
                results2 = sql_util.select_table_rows('zq_multiAsianOdds', ['OddsID'], condition2, isDis=True)
                if len(results2) > 0:
                    sql_util.upData('zq_multiAsianOdds', data, condition2)
                else:
                    sql_util.insertData('zq_multiAsianOdds', data)
        else:
            pass
        if matchState in (-1, -10):
            sql_util.upData('zq_schedule', {'asianOdds_f': 2}, {'ScheduleID': scheduleID})

    @staticmethod
    def up_total_dds(scheduleID, finished, matchState, oddsList):
        sql_util.upData('zq_schedule', {'totalodds_f': 1}, {'ScheduleID': scheduleID})
        if finished == 0:
            datas = []
            multi_datas = []
            for data in oddsList:
                if data['num'] == 1:
                    data2 = data.copy()
                    del data2['num']
                    datas.append(data2)
                multi_datas.append(data)
            sql_util.insertDatas('zq_totalscore', datas)
            sql_util.insertDatas('zq_multitotalscore', multi_datas)
        elif finished == 1:
            for data in oddsList:
                if data['num'] == 1:
                    data2 = data.copy()
                    condition = {'ScheduleID': scheduleID, 'CompanyID': data['companyid']}
                    del data2['num']
                    results = sql_util.select_table_rows('zq_totalscore', ['OddsID'], condition, isDis=True)
                    if len(results) > 0:
                        sql_util.upData('zq_totalscore', data2, condition)
                    else:
                        sql_util.insertData('zq_totalscore', data2)
                condition2 = {'ScheduleID': scheduleID, 'CompanyID': data['companyid'], 'num': data['num']}
                results2 = sql_util.select_table_rows('zq_multitotalscore', ['OddsID'], condition2, isDis=True)
                if len(results2) > 0:
                    sql_util.upData('zq_multitotalscore', data, condition2)
                else:
                    sql_util.insertData('zq_multitotalscore', data)
        else:
            pass
        if matchState in (-1, -10):
            sql_util.upData('zq_schedule', {'totalodds_f': 2}, {'ScheduleID': scheduleID})

    @staticmethod
    def AsiaOddsCheck(scheduleID, homeName, awayName, soup):
        try:
            soup.prettify()
            h2_ip = soup.select('body h2')
            if h2_ip:
                print(scheduleID, soup)
            home_div = soup.find('div', attrs={'class': 'home'})
            home_a = home_div.find('a')
            away_div = soup.find('div', attrs={'class': 'away'})
            away_a = away_div.find('a')
            home_name = home_a.text.replace(" ", "")
            away_name = away_a.text.replace(" ", "")
            ontab_li = soup.find('li', attrs={'class': 'ontab'})
            ontab = ontab_li.text
        except Exception as e:
            # print(soup)
            print(e)
            print(traceback.format_exc())
            print([scheduleID, "亚指内容 解析出错 ×××", e])
            return False
        else:
            if (homeName in home_name or awayName in away_name) and ontab == '让球':
                # print("亚指内容检查 验证通过 √√√")
                return True
            else:
                print(scheduleID, "亚指内容检查 验证不通过 ×××")
                print([scheduleID, homeName, home_name, awayName, away_name, '让球', ontab])
                logLine(common_config.check_asian, [scheduleID, homeName, home_name, awayName, away_name, '让球', ontab])
                return False

    @staticmethod
    def TotalOddsCheck(scheduleID, homeName, awayName, soup):
        # anomalyresult = OddsUtil.anomaly_common_detect(content)
        # if anomalyresult is False:
        #     print("大小请求 响应异常 ×××")
        #     return False
        try:
            soup.prettify()
            h2_ip = soup.select('body h2')
            if h2_ip:
                print(scheduleID, soup)
            home_div = soup.find('div', attrs={'class': 'home'})
            home_a = home_div.find('a')
            away_div = soup.find('div', attrs={'class': 'away'})
            away_a = away_div.find('a')
            home_name = home_a.text.replace(" ", "")
            away_name = away_a.text.replace(" ", "")
            ontab_li = soup.find('li', attrs={'class': 'ontab'})
            ontab = ontab_li.text
        except Exception as e:
            # print(soup)
            print([scheduleID, "亚指内容 解析出错 ×××", e])
            # print(content)
            # print(traceback.format_exc())
            # print(content)
            return False
        else:
            if (homeName in home_name or awayName in away_name) and ontab == '进球数':
                # print("大小内容检查验证通过")
                return True
            else:
                print(scheduleID, "大小内容检查验证不通过：")
                print([scheduleID, homeName, home_name, awayName, away_name, '进球数', ontab])
                logLine(common_config.check_total,
                        [scheduleID, homeName, home_name, awayName, away_name, '进球数', ontab])
                return False

    @staticmethod
    def EuropeOddsCheck(scheduleID, context):
        ScheduleID = context.ScheduleID
        if ScheduleID and ScheduleID == scheduleID:
            return True
        else:
            return False

    @staticmethod
    def get_oddshtml_driver(browser):
        html = None
        try:
            odds_tbody = browser.find_element_by_id("odds").get_attribute('innerHTML')
            odds_html = '<table class="font13" id="odds">{0}</table>'.format(odds_tbody)
            header_html = browser.find_element_by_class_name("header").get_attribute('innerHTML')
            # response = requests.get(url)
            # html = response.text
            html = header_html + odds_html
        except Exception as e:
            print(e)
        return html

    @staticmethod
    def anomaly_common_detect(content):
        result = True
        if ("对不起" in content) or ("频繁" in content):
            result = False
        return result
