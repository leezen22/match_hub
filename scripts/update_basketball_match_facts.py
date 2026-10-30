"""JSON CLI for Match Hub's identity-checked single basketball match updater."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule-id", type=int, required=True)
    parser.add_argument("--expected-match-id", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        with redirect_stdout(sys.stderr):
            from lq_update import update_match_facts
            result = update_match_facts(args.schedule_id,
                                        expected_match_id=args.expected_match_id,
                                        force=args.force)
    except Exception as error:
        result = {"request_ok": False, "error_type": type(error).__name__}
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result.get("request_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
