from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import sys
import unittest
from unittest.mock import patch

import update_request
from utils import js2pyUtil


class MachineCliOutputTest(unittest.TestCase):
    def test_js_parse_failure_diagnostics_use_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch.object(js2pyUtil, "_execute_js", side_effect=SyntaxError("primary parse failed")),
            patch.object(js2pyUtil, "_execute_js_by_statement", side_effect=SyntaxError("fallback parse failed")),
            patch.object(js2pyUtil, "logLine"),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = js2pyUtil.parse_js_content(
                "var arr = [;",
                source="https://example.test/infoHeader.js",
                required_names=("arr",),
            )

        self.assertEqual(result, [0, ""])
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("JS parse failed: https://example.test/infoHeader.js", stderr.getvalue())
        self.assertIn("fallback parse failed", stderr.getvalue())

    def test_update_request_main_keeps_stdout_as_single_json_document(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        def fake_run_update_request(**kwargs):
            print("metadata refresh warning", file=sys.stderr)
            return {
                "request": None,
                "sport": kwargs["sport"],
                "league_id": kwargs["league_id"],
                "executed": False,
            }

        argv = [
            "update_request.py",
            "--structured",
            "--sport",
            "football",
            "--league-id",
            "648",
            "--action",
            "data",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(update_request, "run_update_request", side_effect=fake_run_update_request),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            update_request.main()

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["sport"], "football")
        self.assertEqual(payload["league_id"], 648)
        self.assertFalse(payload["executed"])
        self.assertEqual(stderr.getvalue(), "metadata refresh warning\n")


if __name__ == "__main__":
    unittest.main()
