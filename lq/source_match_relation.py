from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Mapping

import pymysql

from config.db_config import get_db_config


TABLE_NAME = "lq_multi_schedule"
SOURCE_CONTRACT_VERSION = "basketball_realtime_source_match_bindings.v0.3.0"
SOURCE_CONTRACT_VERSIONS = {
    "basketball_realtime_source_match_bindings.v0.2.0",
    SOURCE_CONTRACT_VERSION,
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `lq_multi_schedule` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'relation row identity; not lq_schedule.matchId',
  `ttid` varchar(64) CHARACTER SET utf8 NOT NULL,
  `lsid` varchar(64) CHARACTER SET utf8 NULL,
  `officialid` varchar(128) CHARACTER SET utf8 NULL,
  `relation_status` varchar(32) CHARACTER SET utf8 NOT NULL DEFAULT 'candidate',
  `confidence` decimal(6,5) NULL,
  `evidence_json` longtext CHARACTER SET utf8 NULL,
  `source_state_valid_at` datetime(6) NULL,
  `captured_at` datetime(6) NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lq_multi_schedule_ttid` (`ttid`),
  UNIQUE KEY `uk_lq_multi_schedule_lsid` (`lsid`),
  UNIQUE KEY `uk_lq_multi_schedule_officialid` (`officialid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8
"""


class SourceMatchRelationError(ValueError):
    pass


def migrate_source_match_relation_table(connection=None, *, db_profile=None) -> None:
    owns_connection = connection is None
    db = connection or _connect(db_profile)
    try:
        with db.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_connection:
            db.close()


def load_relation_candidates(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("contract_version") not in SOURCE_CONTRACT_VERSIONS:
        raise SourceMatchRelationError("source_binding_contract_version_invalid")
    associations = payload.get("associations")
    bindings = payload.get("bindings")
    if not isinstance(associations, list) or not isinstance(bindings, list):
        raise SourceMatchRelationError("source_binding_arrays_invalid")

    binding_by_ttid = {}
    for binding in bindings:
        if not isinstance(binding, Mapping):
            raise SourceMatchRelationError("source_binding_row_invalid")
        ttid = _required_source_id(binding.get("titan_match_id"), "binding_ttid")
        if ttid in binding_by_ttid:
            raise SourceMatchRelationError("duplicate_binding_ttid")
        binding_by_ttid[ttid] = binding

    rows = []
    seen_ttid = set()
    seen_lsid = set()
    seen_officialid = set()
    captured_at = _mysql_datetime(payload.get("generated_at"))
    for association in associations:
        if not isinstance(association, Mapping):
            raise SourceMatchRelationError("association_row_invalid")
        ttid = _required_source_id(association.get("ttid"), "association_ttid")
        lsid = _optional_source_id(association.get("lsid"), "association_lsid")
        officialid = _optional_source_id(association.get("officialid"), "association_officialid")
        _claim_unique(ttid, seen_ttid, "duplicate_association_ttid")
        if lsid is not None:
            _claim_unique(lsid, seen_lsid, "duplicate_association_lsid")
        if officialid is not None:
            _claim_unique(officialid, seen_officialid, "duplicate_association_officialid")

        binding = binding_by_ttid.get(ttid)
        confidence = None
        evidence = None
        source_state_valid_at = captured_at
        if binding is not None:
            if _optional_source_id(binding.get("leisu_match_id"), "binding_lsid") != lsid:
                raise SourceMatchRelationError("association_binding_lsid_mismatch")
            mapping = binding.get("mapping") or {}
            confidence = mapping.get("confidence")
            if confidence is not None and not 0 <= float(confidence) <= 1:
                raise SourceMatchRelationError("binding_confidence_invalid")
            evidence = binding.get("evidence_summary")
            source_state_valid_at = _mysql_datetime(
                (mapping.get("mapping_temporality") or {}).get("source_state_valid_at")
            ) or captured_at

        rows.append({
            "ttid": ttid,
            "lsid": lsid,
            "officialid": officialid,
            "relation_status": "candidate",
            "confidence": float(confidence) if confidence is not None else None,
            "evidence_json": _canonical_json(evidence) if evidence is not None else None,
            "source_state_valid_at": source_state_valid_at,
            "captured_at": captured_at,
        })
    return rows


def load_relation_invalidations(path: str | Path) -> list[dict[str, str | None]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("contract_version") not in SOURCE_CONTRACT_VERSIONS:
        raise SourceMatchRelationError("source_binding_contract_version_invalid")
    raw_rows = payload.get("invalidated_associations", [])
    if not isinstance(raw_rows, list):
        raise SourceMatchRelationError("invalidated_associations_invalid")
    rows = []
    seen_ttid = set()
    for row in raw_rows:
        if not isinstance(row, Mapping):
            raise SourceMatchRelationError("invalidated_association_row_invalid")
        ttid = _required_source_id(row.get("ttid"), "invalidated_ttid")
        _claim_unique(ttid, seen_ttid, "duplicate_invalidated_ttid")
        rows.append({
            "ttid": ttid,
            "lsid": _optional_source_id(row.get("lsid"), "invalidated_lsid"),
        })
    return rows


def upsert_relation_candidates(
    rows: list[Mapping[str, Any]], connection=None, *, db_profile=None,
    invalidated_rows: list[Mapping[str, Any]] | None = None,
) -> dict[str, int]:
    owns_connection = connection is None
    db = connection or _connect(db_profile)
    inserted = 0
    updated = 0
    unchanged = 0
    invalidated = 0
    try:
        with db.cursor(pymysql.cursors.DictCursor) as cursor:
            for incoming in rows:
                existing = _lock_related_rows(cursor, incoming)
                if len(existing) > 1:
                    raise SourceMatchRelationError("source_ids_bound_to_different_relation_rows")
                if not existing:
                    cursor.execute(
                        """
                        INSERT INTO `lq_multi_schedule`
                          (`ttid`, `lsid`, `officialid`, `relation_status`, `confidence`,
                           `evidence_json`, `source_state_valid_at`, `captured_at`)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        _row_params(incoming),
                    )
                    inserted += 1
                    continue

                current = existing[0]
                _validate_compatible(current, incoming)
                next_values = _merged_values(current, incoming)
                if _same_values(current, next_values):
                    unchanged += 1
                    continue
                cursor.execute(
                    """
                    UPDATE `lq_multi_schedule`
                    SET `lsid`=%s, `officialid`=%s, `relation_status`=%s,
                        `confidence`=%s, `evidence_json`=%s,
                        `source_state_valid_at`=%s, `captured_at`=%s
                    WHERE `id`=%s
                    """,
                    (
                        next_values["lsid"], next_values["officialid"],
                        next_values["relation_status"], next_values["confidence"],
                        next_values["evidence_json"], next_values["source_state_valid_at"],
                        next_values["captured_at"], current["id"],
                    ),
                )
                updated += 1
            active_ttid = {str(row["ttid"]) for row in rows}
            for invalidation in invalidated_rows or []:
                ttid = str(invalidation["ttid"])
                if ttid in active_ttid:
                    raise SourceMatchRelationError("active_relation_cannot_be_invalidated")
                cursor.execute(
                    "SELECT * FROM `lq_multi_schedule` WHERE `ttid`=%s FOR UPDATE",
                    (ttid,),
                )
                current_rows = list(cursor.fetchall())
                if not current_rows:
                    continue
                current = current_rows[0]
                if current.get("relation_status") == "confirmed":
                    raise SourceMatchRelationError("confirmed_relation_invalidation_requires_review")
                expected_lsid = invalidation.get("lsid")
                if expected_lsid is not None and str(current.get("lsid") or "") != str(expected_lsid):
                    raise SourceMatchRelationError("invalidation_lsid_mismatch")
                cursor.execute(
                    "DELETE FROM `lq_multi_schedule` WHERE `id`=%s",
                    (current["id"],),
                )
                invalidated += 1
        db.commit()
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged, "invalidated": invalidated}
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_connection:
            db.close()


def import_relation_candidates(
    path: str | Path, connection=None, *, db_profile=None
) -> dict[str, int]:
    rows = load_relation_candidates(path)
    invalidated_rows = load_relation_invalidations(path)
    result = upsert_relation_candidates(
        rows, connection=connection, db_profile=db_profile,
        invalidated_rows=invalidated_rows,
    )
    return {**result, "input_rows": len(rows), "invalidation_rows": len(invalidated_rows)}


def _connect(db_profile=None):
    config = get_db_config(db_profile)
    config["connect_timeout"] = 5
    return pymysql.connect(**config)


def _lock_related_rows(cursor, row):
    clauses = ["`ttid`=%s"]
    params = [row["ttid"]]
    for column in ("lsid", "officialid"):
        if row.get(column) is not None:
            clauses.append("`{0}`=%s".format(column))
            params.append(row[column])
    cursor.execute(
        "SELECT * FROM `lq_multi_schedule` WHERE {0} FOR UPDATE".format(" OR ".join(clauses)),
        tuple(params),
    )
    return list(cursor.fetchall())


def _validate_compatible(current, incoming):
    if str(current["ttid"]) != str(incoming["ttid"]):
        raise SourceMatchRelationError("ttid_relation_conflict")
    for column in ("lsid", "officialid"):
        old = current.get(column)
        new = incoming.get(column)
        if old is not None and new is not None and str(old) != str(new):
            raise SourceMatchRelationError("{0}_relation_conflict".format(column))


def _merged_values(current, incoming):
    confirmed = current.get("relation_status") == "confirmed"
    return {
        "lsid": current.get("lsid") or incoming.get("lsid"),
        "officialid": current.get("officialid") or incoming.get("officialid"),
        "relation_status": current.get("relation_status") if confirmed else incoming["relation_status"],
        "confidence": current.get("confidence") if confirmed else incoming.get("confidence"),
        "evidence_json": current.get("evidence_json") if confirmed else incoming.get("evidence_json"),
        "source_state_valid_at": current.get("source_state_valid_at") if confirmed else incoming.get("source_state_valid_at"),
        "captured_at": incoming.get("captured_at") or current.get("captured_at"),
    }


def _same_values(current, values):
    for key, value in values.items():
        current_value = current.get(key)
        if key == "confidence" and current_value is not None and value is not None:
            if Decimal(str(current_value)) != Decimal(str(value)):
                return False
        elif current_value != value:
            return False
    return True


def _row_params(row):
    return tuple(row.get(key) for key in (
        "ttid", "lsid", "officialid", "relation_status", "confidence",
        "evidence_json", "source_state_valid_at", "captured_at",
    ))


def _required_source_id(value, label):
    result = _optional_source_id(value, label)
    if result is None:
        raise SourceMatchRelationError("{0}_missing".format(label))
    return result


def _optional_source_id(value, label):
    if value is None:
        return None
    text = str(value).strip()
    if not text or len(text) > 128:
        raise SourceMatchRelationError("{0}_invalid".format(label))
    return text


def _claim_unique(value, seen, error):
    if value in seen:
        raise SourceMatchRelationError(error)
    seen.add(value)


def _mysql_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
