"""Stable source identities; technical observations are not current profiles."""
from datetime import datetime, timezone
import re

from utils import sql_util
from pymysql import OperationalError

SOURCE_NAMESPACE = "titan_basketball"


class PlayerIdentityError(RuntimeError):
    pass


def identity_transaction(work):
    """Retry MySQL deadlocks/lock timeouts without hiding persistence failures."""
    for attempt in range(3):
        connection = sql_util._connect()
        try:
            result = work(connection.cursor())
            connection.commit()
            return result
        except BaseException as error:
            connection.rollback()
            if not (isinstance(error, OperationalError) and error.args[0] in (1205, 1213) and attempt < 2):
                raise
        finally:
            connection.close()


def source_player_id(value):
    text = str(value or "")
    if not re.fullmatch(r"[1-9][0-9]*", text) or int(text) > 2147483647:
        raise PlayerIdentityError("invalid_source_player_id: {!r}".format(value))
    return int(text)


def ensure_player_identity(cursor, player_id, evidence=None, namespace=SOURCE_NAMESPACE):
    """Caller owns transaction. Never update an existing public ID or its profile."""
    player_id = source_player_id(player_id)
    if namespace != SOURCE_NAMESPACE:
        raise PlayerIdentityError("unsupported_source_namespace: {}".format(namespace))
    evidence = evidence or {}
    condition = (namespace, str(player_id))
    cursor.execute(
        "SELECT id,playerID FROM lq_player_profile "
        "WHERE source_namespace=%s AND source_entity_id=%s", condition)
    existing = cursor.fetchone()
    if existing and existing[1] != player_id:
        raise PlayerIdentityError("source_identity_conflict: {}:{}".format(*condition))
    cursor.execute(
        "SELECT id,source_entity_id FROM lq_player_profile "
        "WHERE playerID=%s AND source_namespace=%s", (player_id, namespace))
    if any(row[1] != str(player_id) for row in cursor.fetchall()):
        raise PlayerIdentityError("source_alias_conflict: {}:{}".format(*condition))
    if existing:
        return existing[0]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Only source identity and names are registered. Team, position, shirt number,
    # roster/availability and physical attributes remain unknown.
    cursor.execute(
        "INSERT INTO lq_player_profile "
        "(playerID,source_namespace,source_entity_id,playerName,playerNameTrad,playerNameEn,"
        "collection_status,has_data,recorded_at,updated_at,source_url_or_operation) "
        "VALUES (%s,%s,%s,%s,%s,%s,'identity_only',0,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
        (player_id, namespace, str(player_id), evidence.get('playerName'),
         evidence.get('playerNameTrad'), evidence.get('playerNameEn'), now, now,
         evidence.get('source_url_or_operation') or 'lq_technical_player_identity'))
    cursor.execute(
        "SELECT id,playerID FROM lq_player_profile "
        "WHERE source_namespace=%s AND source_entity_id=%s FOR UPDATE", condition)
    registered = cursor.fetchone()
    if not registered or registered[1] != player_id:
        raise PlayerIdentityError("identity_registration_failed: {}:{}".format(*condition))
    return registered[0]


def register_technical_identities(rows, source_url=None):
    """Commit identities before technical facts; DB errors propagate for retry.

    Invalid/conflicting identities remain unmerged. Their original technical
    facts can still be stored, with explicit diagnostics returned to the caller.
    """
    def register(cursor):
        diagnostics = []
        seen = set()
        for row in sorted(rows, key=lambda row: str(row.get('playerID'))):
            try:
                player_id = source_player_id(row.get('playerID'))
                if row.get('isUnknown'):
                    raise PlayerIdentityError('source_player_marked_unknown')
                if player_id in seen:
                    continue
                evidence = dict(row, source_url_or_operation=source_url)
                ensure_player_identity(cursor, player_id, evidence)
                seen.add(player_id)
            except PlayerIdentityError as error:
                diagnostics.append({'playerID': row.get('playerID'),
                                    'scheduleID': row.get('scheduleID'), 'reason': str(error)})
        return diagnostics
    return identity_transaction(register)
