import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import sql_util


def _columns(table):
    rows = sql_util.select_dicts("SHOW COLUMNS FROM `{0}`".format(table))
    return {row["Field"] for row in rows}


def _add_missing_columns(table, statements):
    existing = _columns(table)
    pending = []
    for column, ddl in statements:
        if column in existing:
            print("skip {0}.{1}".format(table, column))
            continue
        print("add {0}.{1}".format(table, column))
        pending.append(ddl)
    if pending:
        sql_util.sqlExecute("ALTER TABLE {0} {1}, ALGORITHM=INPLACE, LOCK=NONE".format(table, ", ".join(pending)))


def migrate():
    _add_missing_columns(
        "zq_schedule",
        [
            (
                "half_totalodds_f",
                "ADD COLUMN half_totalodds_f tinyint(4) DEFAULT 0",
            ),
            (
                "half_asianodds_f",
                "ADD COLUMN half_asianodds_f tinyint(4) DEFAULT 0",
            ),
        ],
    )
    _add_missing_columns(
        "zq_totalscore",
        [
            ("halfHighOdds_F", "ADD COLUMN halfHighOdds_F float(8,3) NULL"),
            ("halfGoal_F", "ADD COLUMN halfGoal_F float(8,2) NULL"),
            ("halfLowOdds_F", "ADD COLUMN halfLowOdds_F float(8,3) NULL"),
            ("halfHighOdds", "ADD COLUMN halfHighOdds float(8,3) NULL"),
            ("halfGoal", "ADD COLUMN halfGoal float(8,2) NULL"),
            ("halfLowOdds", "ADD COLUMN halfLowOdds float(8,3) NULL"),
            ("halfModifyTime", "ADD COLUMN halfModifyTime datetime NULL"),
        ],
    )
    _add_missing_columns(
        "zq_asianodds",
        [
            ("halfHomeOdds_F", "ADD COLUMN halfHomeOdds_F float(8,3) NULL"),
            ("halfGoal_F", "ADD COLUMN halfGoal_F float(8,2) NULL"),
            ("halfAwayOdds_F", "ADD COLUMN halfAwayOdds_F float(8,3) NULL"),
            ("halfHomeOdds", "ADD COLUMN halfHomeOdds float(8,3) NULL"),
            ("halfGoal", "ADD COLUMN halfGoal float(8,2) NULL"),
            ("halfAwayOdds", "ADD COLUMN halfAwayOdds float(8,3) NULL"),
            ("halfModifyTime", "ADD COLUMN halfModifyTime datetime NULL"),
        ],
    )


if __name__ == "__main__":
    migrate()
