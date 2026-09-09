from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lq.source_match_relation import import_relation_candidates


DEFAULT_INPUT = (
    PROJECT_ROOT.parent
    / "sports_workbench/runtime/basketball/source_bindings/titan_leisu.current.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Basketball cross-source Match relation candidates into lq_multi_schedule."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--db-profile", default="default")
    args = parser.parse_args()
    result = import_relation_candidates(args.input, db_profile=args.db_profile)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
