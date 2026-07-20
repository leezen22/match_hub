from bs4 import BeautifulSoup

from config import lqconfig_qt
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil


def get_part_score(match_id):
    """Fetch and parse basketball quarter scores."""
    match_dict = {}
    add_times = ['Add1', 'Add2', 'Add3', 'Add4', 'Add5']
    url = f"{lqconfig_qt.techtxtlive}?matchid={match_id}"

    try:
        web_response = WebUtil.requests_get(
            url,
            headers=lqconfig_qt.headers,
            timeout=10,
            sourceName="lq_score_part_score",
        )
        if web_response[0] != 1:
            return {"success": False, "error": "request failed", "match_id": str(match_id)}

        content = web_response[1].strip()
        if not content:
            return match_dict

        soup = BeautifulSoup(content, 'html.parser')
        score_tr = soup.select('body div table.t_bf tr')
        if not score_tr:
            return match_dict

        ths = score_tr[0].select('th')
        state_data = ths[0].text.strip().split("\xa0")
        sign = lqconfig_qt.matchstate.get(state_data[0], 0)
        if sign == 0:
            return match_dict

        _parse_total_scores(soup, match_dict)

        home_tr = score_tr[1]
        away_tr = score_tr[2]
        home_tds = home_tr.select('td')
        away_tds = away_tr.select('td')
        td_count = len(home_tds)

        if td_count > 5:
            _parse_quarter_scores(home_tds, away_tds, match_dict)

        if td_count > 6:
            _parse_overtime_scores(home_tds, away_tds, td_count, add_times, match_dict)

        _update_match_state(match_dict, state_data, sign)
        print(f"{match_id}: {match_dict}")
    except Exception as e:
        return {"success": False, "error": f"parse failed: {e}", "match_id": str(match_id)}

    return match_dict


def _parse_total_scores(soup, match_dict):
    home_score = soup.find(id='homeHeadScore')
    away_score = soup.find(id='guestHeadScore')

    if home_score and home_score.text:
        match_dict['homeScore'] = home_score.text
    if away_score and away_score.text:
        match_dict['awayScore'] = away_score.text


def _parse_quarter_scores(home_tds, away_tds, match_dict):
    quarter_mapping = [
        (1, 0),
        (2, 1),
        (3, 2),
        (4, 3),
    ]

    for quarter, index in quarter_mapping:
        if home_tds[index].text:
            match_dict[f'homeScore{quarter}'] = home_tds[index].text
        if away_tds[index].text:
            match_dict[f'awayScore{quarter}'] = away_tds[index].text


def _parse_overtime_scores(home_tds, away_tds, td_count, add_times, match_dict):
    overtime_count = td_count - 6

    for i in range(overtime_count):
        if i >= len(add_times):
            break

        add_time = add_times[i]
        home_value = home_tds[6 + i].text
        away_value = away_tds[6 + i].text

        if home_value and home_value != '-':
            match_dict[f'home{add_time}'] = home_value
        if away_value and away_value != '-':
            match_dict[f'away{add_time}'] = away_value


def _update_match_state(match_dict, state_data, sign):
    match_dict['matchState'] = sign
    match_dict['remainTime'] = state_data[1] if len(state_data) > 1 else ''

    if sign == -1 or sign > 2:
        _calculate_half_score(match_dict)

    match_dict['partscore_f'] = 2 if sign == -1 else 1
    match_dict['updateTime'] = getNowTime()


def _calculate_half_score(match_dict):
    required_keys = ['homeScore1', 'homeScore2', 'awayScore1', 'awayScore2']

    if all(key in match_dict for key in required_keys):
        try:
            match_dict['homeHalf'] = int(match_dict['homeScore1']) + int(match_dict['homeScore2'])
            match_dict['awayHalf'] = int(match_dict['awayScore1']) + int(match_dict['awayScore2'])
        except (ValueError, TypeError):
            pass
