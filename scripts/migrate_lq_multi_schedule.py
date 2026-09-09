import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lq.source_match_relation import migrate_source_match_relation_table


def main():
    parser = argparse.ArgumentParser(description="Create the lq_multi_schedule relation table.")
    parser.add_argument("--db-profile", default="default")
    args = parser.parse_args()
    migrate_source_match_relation_table(db_profile=args.db_profile)
    print("lq_multi_schedule migrated")


if __name__ == "__main__":
    main()
