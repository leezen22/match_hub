import sys
import types

import pytest

if 'js2py' not in sys.modules:
    stub = types.ModuleType('js2py')
    stub.EvalJs = object
    sys.modules['js2py'] = stub

from scripts.repair_lq_team_shooting import plan_repairs, plan_player_repairs, write_repairs


@pytest.fixture
def evidence():
    total = '240^20^40^4^12^8^12^4^8^12^4^4^4^4^4^52'
    periods = '!!'.join(str(p) + '!0^5^10^5^10,1^1^3^1^3,2^2^3^2^3' for p in range(1, 5))
    source = {'ID': 1, 'matchID': 10, 'scheduleID': 100, 'homeTeamID': 1, 'awayTeamID': 2,
              'homeScore': 52, 'awayScore': 52, 'matchSeason': '26-27', 'captureID': 'capture',
              'rawTech': 'header$' + total + '!rates$' + total + '!rates$$' + periods}
    stored = [{'ID': tid, 'matchID': 10, 'scheduleID': 100, 'teamID': tid, 'period': 0,
               'rawCaptureID': 'capture', 'score': 52, 'shoot_Hit': 4, 'shoot': 12,
               'threeMin_Hit': 4, 'threeMin': 12, 'punishBall_Hit': 8, 'punishBall': 12}
              for tid in (1, 2)]
    return source, stored


def test_only_verified_existing_fg_conflicts_are_planned(evidence):
    source, stored = evidence
    changes, reason = plan_repairs(source, stored)
    assert reason is None and len(changes) == 2
    assert all(c['before'] == [4, 12] and c['after'] == [20, 40] for c in changes)
    assert stored[0]['shoot_Hit'] == 4


def test_updated_values_are_idempotent(evidence):
    source, stored = evidence
    for row in stored:
        row.update(shoot_Hit=20, shoot=40)
    assert plan_repairs(source, stored) == ([], None)


@pytest.mark.parametrize('change', ['capture', 'missing', 'score', 'period', 'raw_missing', 'duplicate'])
def test_missing_or_unverified_evidence_is_not_written(evidence, change):
    source, stored = evidence
    if change == 'capture':
        source['captureID'] = 'different'
    elif change == 'missing':
        for row in stored:
            row['shoot'] = None
    elif change == 'score':
        source['rawTech'] = source['rawTech'].replace('^4^12^8^12', '^5^12^8^12')
    elif change == 'period':
        source['rawTech'] = source['rawTech'].replace('240^20^40', '240^20^10')
    elif change == 'raw_missing':
        source['rawTech'] = ''
    else:
        stored.append(dict(stored[0]))
    assert plan_repairs(source, stored)[0] == []


class Connection:
    def __init__(self, source, *, stale=False):
        self.source = source
        self.stale = stale
        self.committed = False
        self.rolled_back = False
        self.rowcount = 0
        self.result = None
        self.updates = []

    def cursor(self, *_): return self
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
    def fetchone(self): return self.result

    def execute(self, sql, params):
        if 'FROM lq_matchtechnic_raw' in sql:
            self.result = {k: self.source[k] for k in ('captureID', 'rawTech')}
        elif 'FROM lq_schedule' in sql:
            self.result = {k: self.source[k] for k in ('homeTeamID', 'awayTeamID', 'homeScore', 'awayScore')}
        elif sql.startswith('UPDATE'):
            self.rowcount = 0 if self.stale else 1
            self.updates.append((sql, params))
            self.result = {'shoot_Hit': params[0], 'shoot': params[1]}


def test_writer_changes_only_fg_and_checks_old_values(evidence):
    source, stored = evidence
    connection = Connection(source)
    changes, _ = plan_repairs(source, stored)
    write_repairs(connection, source, changes)
    assert connection.committed and not connection.rolled_back
    assert len(connection.updates) == 2
    assert all(sql.split(' WHERE')[0] == 'UPDATE lq_teamtechnic_period SET shoot_Hit=%s,shoot=%s'
               and params[-2:] == (4, 12) for sql, params in connection.updates)


def test_concurrent_change_rolls_back_match(evidence):
    source, stored = evidence
    connection = Connection(source, stale=True)
    changes, _ = plan_repairs(source, stored)
    with pytest.raises(RuntimeError, match='stored_row_changed'):
        write_repairs(connection, source, changes)
    assert connection.rolled_back and not connection.committed


@pytest.fixture
def player_evidence(evidence):
    source, stored = evidence
    source.pop('rawTech')
    source.pop('captureID')
    for row in stored:
        row['rawCaptureID'] = None
    players = [dict(ID=tid*10+i, scheduleID=100, teamID=tid, playerID=tid*10+i,
                    shoot_Hit=5, shoot=10, threeMin_Hit=1, threeMin=3,
                    punishBall_Hit=2, punishBall=3, score=13)
               for tid in (1, 2) for i in range(4)]
    return source, stored, players


def test_player_sum_repairs_without_any_raw_capture(player_evidence):
    source, stored, players = player_evidence
    changes, _ = plan_player_repairs(source, stored, players)
    assert len(changes) == 2
    assert all(c['after'] == [20, 40] and c['raw_capture_id'] is None for c in changes)


@pytest.mark.parametrize('issue', ['duplicate', 'missing', 'conflicting', 'incomplete', 'wrong_three_points', 'all_zero'])
def test_player_sum_does_not_overwrite_missing_or_unmatched_stats(player_evidence, issue):
    source, stored, players = player_evidence
    if issue == 'duplicate':
        players.extend([dict(p) for p in players])
    elif issue == 'missing':
        for p in players:
            p['shoot'] = None
    elif issue == 'conflicting':
        for p in players:
            p['threeMin'] = 20
    elif issue == 'incomplete':
        players = players[1:4] + players[5:]
    elif issue == 'wrong_three_points':
        for row in stored:
            row.update(shoot=13, threeMin=13)
    else:
        for row in stored:
            row.update(shoot_Hit=0, shoot=0)
    assert plan_player_repairs(source, stored, players)[0] == []


def test_unrelated_small_conflicts_do_not_block_fg_repair(player_evidence):
    source, stored, players = player_evidence
    players[0]['punishBall'] = None
    players[0]['score'] = 14
    source['homeScore'] = 53
    changes, _ = plan_player_repairs(source, stored, players)
    assert len(changes) == 2
    assert all(c['after'] == [20, 40] for c in changes)


def test_player_evidence_change_blocks_write(player_evidence):
    source, stored, players = player_evidence
    connection = Connection(source)
    connection.fetchall = lambda: []
    changes, _ = plan_player_repairs(source, stored, players)
    with pytest.raises(RuntimeError, match='player_evidence_changed'):
        write_repairs(connection, source, changes, player_evidence=players)
    assert connection.rolled_back and not connection.committed


def test_player_based_writer_accepts_null_capture_and_checks_rows(player_evidence):
    source, stored, players = player_evidence
    connection = Connection(source)
    connection.fetchall = lambda: players
    changes, _ = plan_player_repairs(source, stored, players)
    write_repairs(connection, source, changes, player_evidence=players)
    assert connection.committed
    assert len(connection.updates) == 2
    assert all('rawCaptureID <=> %s' in sql and params[-3] is None for sql, params in connection.updates)
