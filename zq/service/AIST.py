# 导入必要的库
import numpy as np

from utils import sql_util


def predict_first_half_goals_probability(companyID,homeWin_F,standOff_F,awayWin_F,homeWin,standOff,awayWin,earlyGoal,earlyGoal2,judgeGoals=False):
    """
    预测本场比赛上半场进球数 > 0 的概率。

    参数:
        current_match (dict): 当前比赛的初盘和临场赔率，格式如下：
            {
                "homeWin_F": 初盘主胜,
                "standOff_F": 初盘平局,
                "awayWin_F": 初盘客胜,
                "homeWin": 临场主胜,
                "standOff": 临场平局,
                "awayWin": 临场客胜
            }
        historical_data (list): 历史比赛数据，每场比赛为一个元组，格式如下：
            (初盘主胜, 初盘平局, 初盘客胜, 临场主胜, 临场平局, 临场客胜, 主队上半场进球, 客队上半场进球)

    返回:
        float: 本场比赛上半场进球数 > 0 的概率（0 到 1 之间）。
    """

    current_match={
        "homeWin_F": homeWin_F,
        "standOff_F": standOff_F,
        "awayWin_F": awayWin_F,
        "homeWin": homeWin,
        "standOff": standOff,
        "awayWin": awayWin
    }

    if homeWin > homeWin_F:
        mc = "homeWin>homeWin_F"
    elif homeWin < homeWin_F:
        mc = "homeWin<homeWin_F"
    else:
        mc = "homeWin=homeWin_F"

    if standOff > standOff_F:
        mc = "{0} and standoff>standoff_F".format(mc)
    elif standOff < standOff_F:
        mc = "{0} and standoff<standoff_F".format(mc)
    else:
        mc = "{0} and standoff=standoff_F".format(mc)

    c_g = " ep.goal_F={0} and ep.goal={1} ".format(earlyGoal, earlyGoal2)

    s1 = "SELECT ep.homeWin_F,ep.standOff_F,ep.awayWin_F,ep.homeWin,ep.standOff,ep.awayWin,sc.homeHalf,sc.awayHalf " \
         "FROM zq_europe_{0} as ep LEFT JOIN zq_schedule as sc ON sc.scheduleID=ep.scheduleID " \
         "WHERE ep.homeWin_F={1} and ep.standOff_F={2} and ep.awayWin_F={3} and homeWin>0 and {4} " \
         "ORDER BY OddsID desc".format(companyID,homeWin_F,standOff_F,awayWin_F,mc)
    s2 = "SELECT ep.homeWin_F,ep.standOff_F,ep.awayWin_F,ep.homeWin,ep.standOff,ep.awayWin,sc.homeHalf,sc.awayHalf " \
         "FROM zq_europe_{0} as ep LEFT JOIN zq_schedule as sc ON sc.scheduleID=ep.scheduleID " \
         "WHERE ep.homeWin_F={1} and ep.standOff_F={2} and ep.awayWin_F={3} and ep.goal>0 and {4} and {5} " \
         "ORDER BY OddsID desc".format(companyID,homeWin_F,standOff_F,awayWin_F,mc,c_g)
    if judgeGoals:
        historical_data = sql_util.select(s2)
    else:
        historical_data = sql_util.select(s1)

    # 计算赔率变化幅度
    def calculate_odds_change(match):
        delta_home = abs(match["homeWin_F"] - match["homeWin"])
        delta_draw = abs(match["standOff_F"] - match["standOff"])
        delta_away = abs(match["awayWin_F"] - match["awayWin"])
        return delta_home, delta_draw, delta_away

    # 统计历史数据中上半场进球分布
    def calculate_historical_distribution(data):
        total_matches = len(data)
        zero_goals = sum(1 for match in data if match[6] + match[7] == 0)
        one_goal = sum(1 for match in data if match[6] + match[7] == 1)
        two_or_more_goals = sum(1 for match in data if match[6] + match[7] >= 2)

        p_zero = zero_goals / total_matches
        p_one = one_goal / total_matches
        p_two_plus = two_or_more_goals / total_matches

        return p_zero, p_one, p_two_plus

    # 筛选符合当前赔率变化模式的历史比赛
    def filter_by_odds_change(data, current_match, current_delta_home, current_delta_draw, current_delta_away):
        filtered_data = []
        for match in data:
            # 提取当前比赛的初盘和临场赔率
            homeWin_F, standOff_F, awayWin_F, homeWin, standOff, awayWin = match[:6]

            # 计算当前比赛的赔率变化幅度
            delta_home = abs(homeWin_F - homeWin)
            delta_draw = abs(standOff_F - standOff)
            delta_away = abs(awayWin_F - awayWin)

            # 筛选条件：初盘和临场赔率接近，且赔率变化幅度接近
            if (
                    abs(homeWin_F - current_match["homeWin_F"]) < 0.1 and
                    abs(homeWin - current_match["homeWin"]) < 0.1 and
                    abs(delta_home - current_delta_home) < 0.1 and
                    abs(delta_draw - current_delta_draw) < 0.2 and
                    abs(delta_away - current_delta_away) < 0.2
            ):
                filtered_data.append(match)
        return filtered_data

    # 计算综合概率
    def calculate_combined_probability(data, current_match, current_delta_home, current_delta_draw, current_delta_away):
        # 统计整体历史分布
        p_zero_hist, p_one_hist, p_two_plus_hist = calculate_historical_distribution(data)
        p_goals_hist = 1 - p_zero_hist  # 上半场有进球的概率

        # 筛选符合赔率变化模式的比赛
        filtered_data = filter_by_odds_change(data, current_match, current_delta_home, current_delta_draw,current_delta_away)
        if not filtered_data:
            # 如果没有符合条件的比赛，直接使用历史数据
            return p_goals_hist

        # 统计筛选后比赛的进球分布
        p_zero_filtered = sum(1 for match in filtered_data if match[6] + match[7] == 0) / len(filtered_data)
        p_goals_filtered = 1 - p_zero_filtered  # 上半场有进球的概率

        # 加权平均计算综合概率
        weight_hist = 0.6
        weight_filtered = 0.4
        p_goals_combined = weight_hist * p_goals_hist + weight_filtered * p_goals_filtered

        return p_goals_combined

    # 当前比赛的赔率变化幅度
    current_delta_home, current_delta_draw, current_delta_away = calculate_odds_change(current_match)

    # 调用核心逻辑计算概率
    probability = calculate_combined_probability(historical_data, current_match, current_delta_home, current_delta_draw, current_delta_away)
    return probability


# def calculate_probability_2x1_half_goals(homeWin_F,standOff_F,awayWin_F,homeWin,awayWin,awayHalf,goal_F,goal):
#     s1 = "SELECT ep.homeWin_F,ep.standOff_F,ep.awayWin_F,ep.homeWin,ep.standOff,ep.awayWin,sc.homeHalf,sc.awayHalf " \
#          "FROM zq_europe_281 as ep LEFT JOIN zq_schedule as sc ON sc.scheduleID=ep.scheduleID " \
#          "WHERE ep.homeWin_F={0} and ep.standOff_F={1} and ep.awayWin_F={2} ORDER BY OddsID desc".format(homeWin_F,standOff_F,awayWin_F)
#     s2 = "SELECT ep.homeWin_F,ep.standOff_F,ep.awayWin_F,ep.homeWin,ep.standOff,ep.awayWin,sc.homeHalf,sc.awayHalf " \
#          "FROM zq_europe_281 as ep LEFT JOIN zq_schedule as sc ON sc.scheduleID=ep.scheduleID " \
#          "WHERE ep.homeWin_F={0} and ep.standOff_F={1} and ep.awayWin_F={2} and goal_F={3} and goal={4} and ep.goal>0  ORDER BY OddsID desc".format(homeWin_F,standOff_F,awayWin_F,homeWin,awayWin,awayHalf,goal_F,goal)
#     data1 = sql_util.select(s1)
#     data2 = sql_util.select(s2)
#     # p1 =



# 主函数
if __name__ == "__main__":
    homeWin_F=1.9
    standOff_F=3.5
    awayWin_F=3.3
    homeWin=1.53
    standOff=4.33
    awayWin=4.5
    earlyGoal=2.5
    earlyGoal2=2.25
    companyID=281
    probability = predict_first_half_goals_probability(companyID,homeWin_F,standOff_F,awayWin_F,homeWin,standOff,awayWin,earlyGoal,earlyGoal2,False)
    print(probability)
#     # 计算综合概率
#     probability = calculate_combined_probability(
#         data, current_match, current_delta_home, current_delta_draw, current_delta_away
#     )
#     print(f"本场比赛上半场进球数 > 0 的概率为: {probability:.2%}")