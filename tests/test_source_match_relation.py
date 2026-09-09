from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from lq.source_match_relation import (
    SOURCE_CONTRACT_VERSION,
    SourceMatchRelationError,
    load_relation_candidates,
    upsert_relation_candidates,
)


class SourceMatchRelationTest(unittest.TestCase):
    def test_loads_candidate_without_persisting_transport_id(self):
        payload = _payload()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bindings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            rows = load_relation_candidates(path)

        self.assertEqual(rows[0]["ttid"], "727841")
        self.assertEqual(rows[0]["lsid"], "3940028")
        self.assertNotIn("id", rows[0])
        self.assertEqual(rows[0]["relation_status"], "candidate")
        self.assertEqual(rows[0]["confidence"], 0.98)

    def test_rejects_duplicate_source_identity(self):
        payload = _payload()
        payload["associations"].append({
            "id": "assoc_other", "ttid": "727842", "lsid": "3940028", "officialid": None,
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bindings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SourceMatchRelationError, "duplicate_association_lsid"):
                load_relation_candidates(path)

    def test_inserts_relation_in_one_transaction(self):
        connection = FakeConnection([])
        result = upsert_relation_candidates([_row()], connection=connection)

        self.assertEqual(result, {"inserted": 1, "updated": 0, "unchanged": 0, "invalidated": 0})
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        self.assertTrue(any(sql.lstrip().startswith("INSERT") for sql, _ in connection.cursor_instance.calls))

    def test_candidate_does_not_downgrade_confirmed_relation(self):
        current = {
            "id": 8, "ttid": "727841", "lsid": "3940028", "officialid": "official-1",
            "relation_status": "confirmed", "confidence": 1.0, "evidence_json": "confirmed",
            "source_state_valid_at": None, "captured_at": None,
        }
        connection = FakeConnection([current])
        row = _row()
        row["officialid"] = None
        result = upsert_relation_candidates([row], connection=connection)

        self.assertEqual(result["unchanged"], 1)
        self.assertFalse(any(sql.lstrip().startswith("UPDATE") for sql, _ in connection.cursor_instance.calls))

    def test_conflict_rolls_back_whole_batch(self):
        current = {
            "id": 8, "ttid": "727841", "lsid": "999", "officialid": None,
            "relation_status": "candidate", "confidence": None, "evidence_json": None,
            "source_state_valid_at": None, "captured_at": None,
        }
        connection = FakeConnection([current])
        with self.assertRaisesRegex(SourceMatchRelationError, "lsid_relation_conflict"):
            upsert_relation_candidates([_row()], connection=connection)
        self.assertFalse(connection.committed)
        self.assertTrue(connection.rolled_back)

    def test_explicit_invalidation_deletes_candidate_relation(self):
        current = {
            "id": 8, "ttid": "727841", "lsid": "3940028", "officialid": None,
            "relation_status": "candidate", "confidence": 0.98, "evidence_json": "{}",
            "source_state_valid_at": None, "captured_at": None,
        }
        connection = FakeConnection([current])
        result = upsert_relation_candidates(
            [],
            connection=connection,
            invalidated_rows=[{"ttid": "727841", "lsid": "3940028"}],
        )
        self.assertEqual(result["invalidated"], 1)
        self.assertTrue(any(sql.lstrip().startswith("DELETE") for sql, _ in connection.cursor_instance.calls))

    def test_explicit_invalidation_cannot_delete_confirmed_relation(self):
        current = {
            "id": 8, "ttid": "727841", "lsid": "3940028", "officialid": None,
            "relation_status": "confirmed", "confidence": 1.0, "evidence_json": "{}",
            "source_state_valid_at": None, "captured_at": None,
        }
        connection = FakeConnection([current])
        with self.assertRaisesRegex(
            SourceMatchRelationError,
            "confirmed_relation_invalidation_requires_review",
        ):
            upsert_relation_candidates(
                [],
                connection=connection,
                invalidated_rows=[{"ttid": "727841", "lsid": "3940028"}],
            )
        self.assertTrue(connection.rolled_back)

    def test_mysql_decimal_confidence_does_not_cause_spurious_update(self):
        current = {
            "id": 8, "ttid": "727841", "lsid": "3940028", "officialid": None,
            "relation_status": "candidate", "confidence": Decimal("0.98000"),
            "evidence_json": "{}", "source_state_valid_at": None, "captured_at": None,
        }
        connection = FakeConnection([current])
        result = upsert_relation_candidates([_row()], connection=connection)

        self.assertEqual(result, {"inserted": 0, "updated": 0, "unchanged": 1, "invalidated": 0})
        self.assertFalse(any(sql.lstrip().startswith("UPDATE") for sql, _ in connection.cursor_instance.calls))


class FakeConnection:
    def __init__(self, selected):
        self.cursor_instance = FakeCursor(selected)
        self.committed = False
        self.rolled_back = False

    def cursor(self, *_args, **_kwargs):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class FakeCursor:
    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.selected


def _row():
    return {
        "ttid": "727841", "lsid": "3940028", "officialid": None,
        "relation_status": "candidate", "confidence": 0.98,
        "evidence_json": "{}", "source_state_valid_at": None, "captured_at": None,
    }


def _payload():
    return {
        "contract_version": SOURCE_CONTRACT_VERSION,
        "generated_at": "2026-09-09T12:00:00Z",
        "associations": [
            {"id": "assoc_runtime_only", "ttid": "727841", "lsid": "3940028", "officialid": None},
        ],
        "bindings": [{
            "titan_match_id": "727841",
            "leisu_match_id": "3940028",
            "binding_status": "candidate",
            "evidence_summary": {"method": "participant_time_candidate"},
            "mapping": {
                "confidence": 0.98,
                "mapping_temporality": {"source_state_valid_at": "2026-09-09T11:59:00Z"},
            },
        }],
    }


if __name__ == "__main__":
    unittest.main()
