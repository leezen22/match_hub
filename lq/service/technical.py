import traceback
import uuid
from datetime import datetime, timezone
from config import lqconfig_qt
from utils import sql_util
from utils.js2pyUtil import logLine
from utils.webUtil import WebUtil


class Technical(object):
    TEAM_FIELD = [
        'playTime', 'shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin', 'punishBall_Hit', 'punishBall',
        'attack', 'defend', 'rebound', 'helpAttack', 'foul', 'rob', 'misplay', 'cover', 'score'
    ]
    PLAYER_FIELD = [
        'playerID', 'playerName', 'playerNameTrad', 'playerNameEn', 'isUnknown', 'position', 'playTime',
        'shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin', 'punishBall_Hit', 'punishBall', 'attack',
        'defend', 'rebound', 'helpAttack', 'foul', 'rob', 'misplay', 'cover', 'score', 'isFirst',
        'shortName', 'plusMinus', 'shirtNumber', 'playerPic'
    ]
    TEAM_NUMERIC_FIELDS = {
        'playTime', 'shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin', 'punishBall_Hit', 'punishBall',
        'attack', 'defend', 'rebound', 'helpAttack', 'foul', 'rob', 'misplay', 'cover', 'score',
        'loseScore', 'fast', 'inside', 'exceed', 'quarterFoul', 'remainingPause', 'twoPointScore',
        'threePointScore'
    }
    PLAYER_NUMERIC_FIELDS = {
        'playerID', 'isUnknown', 'playTime', 'shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin',
        'punishBall_Hit', 'punishBall', 'attack', 'defend', 'rebound', 'helpAttack', 'foul',
        'rob', 'misplay', 'cover', 'score', 'isFirst', 'plusMinus'
    }
    PLAYER_SUM_FIELDS = {
        'playTime', 'shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin', 'punishBall_Hit', 'punishBall',
        'attack', 'defend', 'rebound', 'helpAttack', 'foul', 'rob', 'misplay', 'cover', 'score',
        'plusMinus'
    }

    @staticmethod
    def upTeamtech():
        matchs = sql_util.select("SELECT scheduleID,matchID,homeTeamID,awayTeamID,matchSeason,matchTime FROM `lq_schedule` "
                                 "where matchState=-1 and teamTech=0 order by matchTime ASC")
        for match in matchs:
            result = Technical.technical_match(match, include_players=False)
            if result.get('rawTech') != '':
                sql_util.replace_table_row('lq_matchtechnic_raw', {'scheduleID': match[0]}, {
                    'scheduleID': match[0],
                    'matchID': result['matchID'],
                    'rawTech': result['rawTech'],
                    'sourceUrl': result['sourceUrl'],
                    'sourceOperation': result['sourceOperation'],
                    'captureID': result['captureID'],
                    'capturedAt': result['capturedAt'],
                })
            if len(result['teamPeriodRows']) > 0:
                sql_util.delData('lq_teamtechnic_period', {'scheduleID': match[0]})
                sql_util.insertDatas('lq_teamtechnic_period', result['teamPeriodRows'])
                sql_util.upData('lq_schedule', {'teamTech': 1}, {'scheduleID': match[0]})

    @staticmethod
    def upMatchTechnical(scheduleID):
        matchs = sql_util.select(
            "SELECT scheduleID,matchID,homeTeamID,awayTeamID,matchSeason,matchTime FROM `lq_schedule` "
            "where scheduleID={0}".format(int(scheduleID))
        )
        if len(matchs) == 0:
            print("technical match not found: {0}".format(scheduleID))
            return {'state': 0, 'request_ok': False, 'teams': 0, 'players': 0}

        result = Technical.technical_match(matchs[0], include_players=True)
        persist_ok = True
        if result.get('rawTech') != '':
            persist_ok = sql_util.replace_table_row('lq_matchtechnic_raw', {'scheduleID': scheduleID}, {
                'scheduleID': scheduleID,
                'matchID': result['matchID'],
                'rawTech': result['rawTech'],
                'sourceUrl': result['sourceUrl'],
                'sourceOperation': result['sourceOperation'],
                'captureID': result['captureID'],
                'capturedAt': result['capturedAt'],
            }) and persist_ok
        if len(result['teamPeriodRows']) > 0:
            if sql_util.replace_table_rows('lq_teamtechnic_period', {'scheduleID': scheduleID}, result['teamPeriodRows']):
                sql_util.upData('lq_schedule', {'teamTech': 1}, {'scheduleID': scheduleID})
            else:
                persist_ok = False
                result['teamPeriodRows'] = []
        if len(result['players']) > 0:
            if not sql_util.replace_table_rows('lq_playertechnic', {'scheduleID': scheduleID}, result['players']):
                persist_ok = False
                result['players'] = []
        return {'state': 1 if result['requestOk'] and persist_ok else 0,
                'request_ok': result['requestOk'] and persist_ok,
                'teams': len(result['teams']), 'players': len(result['players']), 'periods': len(result['teamPeriodRows'])}

    @staticmethod
    def upMatchTextLive(scheduleID):
        text_live = Technical.text_live(scheduleID)
        rows = text_live.get('events', [])
        persist_ok = True
        if text_live.get('rawTextLive') != '':
            persist_ok = sql_util.replace_table_row('lq_textlive_raw', {'scheduleID': scheduleID}, {
                'scheduleID': scheduleID,
                'matchID': text_live['matchID'],
                'rawTextLive': text_live['rawTextLive'],
                'sourceUrl': text_live['sourceUrl'],
                'sourceOperation': text_live['sourceOperation'],
                'captureID': text_live['captureID'],
                'capturedAt': text_live['capturedAt'],
            }) and persist_ok
        if len(rows) > 0:
            if not sql_util.replace_table_rows('lq_textlive', {'scheduleID': scheduleID}, rows):
                persist_ok = False
                rows = []
        return {'state': 1 if text_live['requestOk'] and persist_ok else 0, 'request_ok': text_live['requestOk'] and persist_ok, 'events': len(rows)}

    @staticmethod
    def technical_match(matchdata, include_players=True):
        result = {
            'teams': [], 'players': [], 'teamPeriodRows': [], 'rawTech': '', 'sourceUrl': '',
            'sourceOperation': 'lq_technical_team', 'captureID': None, 'capturedAt': None,
            'requestOk': False,
        }
        result['matchID'] = matchdata[1]
        schedule_id = matchdata[0]
        source_url, content, request_ok = Technical._fetch_technical_js(schedule_id)
        result['rawTech'] = content
        result['sourceUrl'] = source_url
        result['requestOk'] = request_ok
        capture = _new_capture_metadata(request_ok)
        result.update(capture)
        if content == '':
            return result

        tech_data = content.split('$')
        if len(tech_data) <= 2:
            return result

        data_match = tech_data[0].split('^')
        home_team = Technical._parse_team_technical(matchdata, data_match, tech_data[1], is_home=1)
        away_team = Technical._parse_team_technical(matchdata, data_match, tech_data[2], is_home=0)
        if home_team and away_team:
            home_team['loseScore'] = _to_int(away_team.get('score'))
            away_team['loseScore'] = _to_int(home_team.get('score'))
            result['teams'] = [home_team, away_team]

        if include_players:
            result['players'].extend(Technical._parse_player_technical(matchdata, tech_data[1], is_home=1))
            result['players'].extend(Technical._parse_player_technical(matchdata, tech_data[2], is_home=0))
        if len(tech_data) > 4:
            result['teamPeriodRows'] = Technical._parse_period_technical(matchdata, tech_data[4])
            result['teamPeriodRows'] = Technical._merge_full_team_rows(result['teamPeriodRows'], result['teams'])
        if len(tech_data) > 3 and result['teamPeriodRows']:
            result['teamPeriodRows'] = Technical._merge_supplemental_team_tech(result['teamPeriodRows'], tech_data[3])
        if len(result['teamPeriodRows']) == 0 and len(result['teams']) == 2:
            result['teamPeriodRows'] = Technical._team_rows_to_period_rows(result['teams'])
        for row in result['teamPeriodRows'] + result['players']:
            row['rawCaptureID'] = result['captureID']
        return result

    @staticmethod
    def technical_team(matchdata):
        result = Technical.technical_match(matchdata, include_players=False)
        if len(result['teams']) == 2:
            return result['teams']
        return [{}, {}]

    @staticmethod
    def _fetch_technical_js(matchid):
        url = "https://nba.titan007.com/jsdata/tech/" + str(matchid)[0:1] + "/" + str(matchid)[1:3] + "/" + str(
            matchid) + ".js"
        content, request_ok = Technical._fetch_url(url, "lq_technical_team", matchid)
        return url, content, request_ok

    @staticmethod
    def _fetch_url(url, source_name, matchid):
        try:
            response = WebUtil.requests_get(
                url,
                headers=lqconfig_qt.headers,
                timeout=5,
                sourceName=source_name,
            )
            if response[0] != 1:
                logLine(lqconfig_qt.quarterscore_e, str(matchid))
                return '', False
            return response[1] or '', True
        except Exception as e:
            print(e)
            excepstr = traceback.format_exc()
            logLine(lqconfig_qt.exception, excepstr)
            logLine(lqconfig_qt.quarterscore_e, str(matchid))
        return '', False

    @staticmethod
    def _parse_team_technical(matchdata, data_match, team_data, is_home):
        items = team_data.split('!')
        if len(items) < 2:
            return {}
        total_values = items[-2].split('^')
        if len(total_values) < len(Technical.TEAM_FIELD):
            return {}

        team = {
            'scheduleID': matchdata[0],
            'matchID': matchdata[1],
            'teamID': matchdata[2] if is_home == 1 else matchdata[3],
            'matchSeason': matchdata[4],
            'isHome': is_home,
        }
        for i, field in enumerate(Technical.TEAM_FIELD):
            team[field] = _clean_field_value(field, total_values[i], Technical.TEAM_NUMERIC_FIELDS)

        if len(data_match) > 9:
            team['fast'] = _clean_field_value('fast', data_match[4] if is_home == 1 else data_match[5], Technical.TEAM_NUMERIC_FIELDS)
            team['inside'] = _clean_field_value('inside', data_match[6] if is_home == 1 else data_match[7], Technical.TEAM_NUMERIC_FIELDS)
            team['exceed'] = _clean_field_value('exceed', data_match[8] if is_home == 1 else data_match[9], Technical.TEAM_NUMERIC_FIELDS)
        return team

    @staticmethod
    def _parse_player_technical(matchdata, team_data, is_home):
        rows = []
        items = team_data.split('!')
        for item in items[:-2]:
            values = item.split('^')
            if len(values) < 24:
                continue
            player = {
                'scheduleID': matchdata[0],
                'matchID': matchdata[1],
                'teamID': matchdata[2] if is_home == 1 else matchdata[3],
                'matchSeason': matchdata[4],
                'isHome': is_home,
                'rawData': item,
            }
            for i, field in enumerate(Technical.PLAYER_FIELD):
                player[field] = _clean_field_value(
                    field,
                    values[i] if i < len(values) else '',
                    Technical.PLAYER_NUMERIC_FIELDS,
                )
            rows.append(player)
        return Technical._merge_duplicate_player_rows(rows)

    @staticmethod
    def _merge_duplicate_player_rows(rows):
        merged = []
        by_key = {}
        for row in rows:
            key = (row.get('scheduleID'), row.get('teamID'), row.get('playerID'))
            if key not in by_key or row.get('playerID') is None:
                by_key[key] = row
                merged.append(row)
                continue

            existing = by_key[key]
            for field in Technical.PLAYER_SUM_FIELDS:
                existing[field] = _sum_optional_int(existing.get(field), row.get(field))
            existing['isFirst'] = max(_to_int(existing.get('isFirst'), 0) or 0, _to_int(row.get('isFirst'), 0) or 0)
            existing['rawData'] = "{}||{}".format(existing.get('rawData') or '', row.get('rawData') or '')
        return merged

    @staticmethod
    def _parse_period_technical(matchdata, period_data):
        by_period = {}
        for section in (period_data or '').split('!!'):
            if '!' not in section:
                continue
            section_values = section.split('!', 1)
            period = _to_int(section_values[0], 0)
            home = Technical._new_team_period_row(matchdata, period, is_home=1)
            away = Technical._new_team_period_row(matchdata, period, is_home=0)
            home['rawData'] = section
            away['rawData'] = section
            for item in section_values[1].split(','):
                values = item.split('^')
                if len(values) < 2:
                    continue
                stat_index = _to_int(values[0])
                Technical._apply_period_stat(home, away, stat_index, values)
            by_period[period] = [home, away]
        rows = []
        for period in sorted(by_period.keys()):
            rows.extend(by_period[period])
        return rows

    @staticmethod
    def _new_team_period_row(matchdata, period, is_home):
        return {
            'scheduleID': matchdata[0],
            'matchID': matchdata[1],
            'teamID': matchdata[2] if is_home == 1 else matchdata[3],
            'matchSeason': matchdata[4],
            'isHome': is_home,
            'period': period,
        }

    @staticmethod
    def _apply_period_stat(home, away, stat_index, values):
        if stat_index == 0:
            home['shoot_Hit'] = _to_int(values[1], 0)
            home['shoot'] = _to_int(values[2] if len(values) > 2 else None, 0)
            away['shoot_Hit'] = _to_int(values[3] if len(values) > 3 else None, 0)
            away['shoot'] = _to_int(values[4] if len(values) > 4 else None, 0)
        elif stat_index == 1:
            home['threeMin_Hit'] = _to_int(values[1], 0)
            home['threeMin'] = _to_int(values[2] if len(values) > 2 else None, 0)
            away['threeMin_Hit'] = _to_int(values[3] if len(values) > 3 else None, 0)
            away['threeMin'] = _to_int(values[4] if len(values) > 4 else None, 0)
        elif stat_index == 2:
            home['punishBall_Hit'] = _to_int(values[1], 0)
            home['punishBall'] = _to_int(values[2] if len(values) > 2 else None, 0)
            away['punishBall_Hit'] = _to_int(values[3] if len(values) > 3 else None, 0)
            away['punishBall'] = _to_int(values[4] if len(values) > 4 else None, 0)
        elif stat_index == 3:
            home['rebound'] = _to_int(values[1], 0)
            away['rebound'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 4:
            home['helpAttack'] = _to_int(values[1], 0)
            away['helpAttack'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 5:
            home['rob'] = _to_int(values[1], 0)
            away['rob'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 6:
            home['cover'] = _to_int(values[1], 0)
            away['cover'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 7:
            home['foul'] = _to_int(values[1], 0)
            away['foul'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 8:
            home['misplay'] = _to_int(values[1], 0)
            away['misplay'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 9:
            home['fast'] = _to_int(values[1], 0)
            away['fast'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 10:
            home['inside'] = _to_int(values[1], 0)
            away['inside'] = _to_int(values[3] if len(values) > 3 else None, 0)
        elif stat_index == 11:
            home['exceed'] = _to_int(values[1], 0)
            away['exceed'] = _to_int(values[3] if len(values) > 3 else None, 0)

    @staticmethod
    def _team_rows_to_period_rows(team_rows):
        rows = []
        for team in team_rows:
            row = dict(team)
            row['period'] = 0
            rows.append(row)
        return rows

    @staticmethod
    def _merge_full_team_rows(period_rows, team_rows):
        if len(team_rows) != 2:
            return period_rows
        team_by_home = {team.get('isHome'): team for team in team_rows}
        merged = []
        has_full_home = False
        has_full_away = False
        for row in period_rows:
            if row.get('period') == 0 and row.get('isHome') in team_by_home:
                full_row = dict(team_by_home[row.get('isHome')])
                full_row.update({key: value for key, value in row.items() if value is not None})
                row = full_row
                if row.get('isHome') == 1:
                    has_full_home = True
                else:
                    has_full_away = True
            merged.append(row)
        if not has_full_home or not has_full_away:
            existing = {(row.get('period'), row.get('isHome')) for row in merged}
            for full_row in Technical._team_rows_to_period_rows(team_rows):
                key = (full_row.get('period'), full_row.get('isHome'))
                if key not in existing:
                    merged.append(full_row)
        return merged

    @staticmethod
    def _merge_supplemental_team_tech(period_rows, supplemental_data):
        extras = Technical._parse_supplemental_team_tech(supplemental_data)
        if not extras:
            return period_rows
        merged = []
        for row in period_rows:
            if row.get('period') == 0 and row.get('teamID') in extras:
                updated = dict(row)
                updated.update(extras[row.get('teamID')])
                merged.append(updated)
            else:
                merged.append(row)
        return merged

    @staticmethod
    def _parse_supplemental_team_tech(supplemental_data):
        rows = {}
        for item in (supplemental_data or '').split('!'):
            values = item.split('^')
            if len(values) < 5:
                continue
            team_id = _to_int(values[0])
            if team_id is None:
                continue
            rows[team_id] = {
                'quarterFoul': _to_int(values[1], 0),
                'remainingPause': _to_int(values[2], 0),
                'twoPointScore': _to_int(values[3], 0),
                'threePointScore': _to_int(values[4], 0),
            }
        return rows

    @staticmethod
    def text_live(scheduleID):
        matchs = sql_util.select(
            "SELECT scheduleID,matchID FROM `lq_schedule` where scheduleID={0}".format(int(scheduleID))
        )
        if len(matchs) == 0:
            return {
                'state': 0, 'requestOk': False, 'events': [], 'rawTextLive': '', 'sourceUrl': '',
                'sourceOperation': 'lq_text_live', 'captureID': None, 'capturedAt': None, 'matchID': None,
            }
        match_id = matchs[0][1]
        url, content, request_ok = Technical._fetch_txt_live_js(scheduleID)
        events = Technical._parse_txt_live_events(scheduleID, match_id, content)
        capture = _new_capture_metadata(request_ok)
        for row in events:
            row['rawCaptureID'] = capture['captureID']
        return {
            'state': 1 if request_ok else 0, 'requestOk': request_ok, 'events': events,
            'rawTextLive': content, 'sourceUrl': url, 'sourceOperation': 'lq_text_live',
            'captureID': capture['captureID'], 'capturedAt': capture['capturedAt'], 'matchID': match_id,
        }

    @staticmethod
    def _fetch_txt_live_js(matchid):
        url = "https://nba.titan007.com/jsdata/txtLive/" + str(matchid)[0:1] + "/" + str(matchid)[1:3] + "/" + str(
            matchid) + ".js"
        content, request_ok = Technical._fetch_url(url, "lq_text_live", matchid)
        return url, content, request_ok

    @staticmethod
    def _parse_txt_live_events(scheduleID, matchID, content):
        rows = []
        event_index = 0
        for period_index, period_text in enumerate((content or '').split('$'), start=1):
            for group in period_text.split('!'):
                for event_text in group.split(','):
                    event_text = event_text.strip()
                    if event_text == '':
                        continue
                    parts = event_text.split('^')
                    if len(parts) < 7:
                        continue
                    rows.append({
                        'scheduleID': scheduleID,
                        'matchID': matchID,
                        'period': _to_int(parts[6], period_index),
                        'clock': parts[0],
                        'eventType': _to_int(parts[1], 0),
                        'homeScore': _to_int(parts[2], 0),
                        'awayScore': _to_int(parts[3], 0),
                        'content': parts[4],
                        'liveID': _to_int(parts[5], event_index),
                        'eventIndex': event_index,
                        'sequence': _to_int(parts[7], event_index) if len(parts) > 7 else event_index,
                        'rawData': event_text,
                    })
                    event_index += 1
        return rows


def _to_int(value, default=None):
    try:
        if value is None or value == '':
            return default
        return int(value)
    except Exception:
        return default


def _clean_field_value(field, value, numeric_fields):
    if field in numeric_fields:
        return _to_int(value)
    if value == '':
        return None
    return value


def _sum_optional_int(left, right):
    left_value = _to_int(left)
    right_value = _to_int(right)
    if left_value is None and right_value is None:
        return None
    return (left_value or 0) + (right_value or 0)


def _new_capture_metadata(request_ok):
    if not request_ok:
        return {'captureID': None, 'capturedAt': None}
    return {
        'captureID': str(uuid.uuid4()),
        # MySQL DATETIME is timezone-naive; this column is explicitly defined as UTC.
        'capturedAt': datetime.now(timezone.utc).replace(tzinfo=None),
    }
