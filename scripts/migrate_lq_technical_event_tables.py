import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import sql_util


def _table_exists(table):
    return len(sql_util.select_rows("SHOW TABLES LIKE '{0}'".format(table))) > 0


def _columns(table):
    if not _table_exists(table):
        return set()
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
        sql_util.sqlExecute("ALTER TABLE `{0}` {1}".format(table, ", ".join(pending)))


def _drop_columns(table, columns):
    existing = _columns(table)
    pending = []
    for column in columns:
        if column not in existing:
            print("skip drop {0}.{1}".format(table, column))
            continue
        print("drop {0}.{1}".format(table, column))
        pending.append("DROP COLUMN `{0}`".format(column))
    if pending:
        sql_util.sqlExecute("ALTER TABLE `{0}` {1}".format(table, ", ".join(pending)))


def migrate():
    _add_missing_columns(
        "lq_schedule",
        [
            ("technical_f", "ADD COLUMN `technical_f` tinyint(4) DEFAULT 0"),
            ("textlive_f", "ADD COLUMN `textlive_f` tinyint(4) DEFAULT 0"),
            ("teamtechnic_has_data", "ADD COLUMN `teamtechnic_has_data` tinyint(4) DEFAULT 0"),
            ("playertechnic_has_data", "ADD COLUMN `playertechnic_has_data` tinyint(4) DEFAULT 0"),
            ("textlive_has_data", "ADD COLUMN `textlive_has_data` tinyint(4) DEFAULT 0"),
        ],
    )

    if _table_exists("lq_teamtechnic"):
        print("drop legacy table lq_teamtechnic")
        sql_util.sqlExecute("DROP TABLE `lq_teamtechnic`")

    if _table_exists("lq_teamtechnic_period") and "statType" in _columns("lq_teamtechnic_period"):
        print("recreate lq_teamtechnic_period from comparison-row schema to team-period schema")
        sql_util.sqlExecute("DROP TABLE `lq_teamtechnic_period`")

    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_matchtechnic_raw` (
          `ID` int(11) NOT NULL AUTO_INCREMENT,
          `scheduleID` int(11) NOT NULL,
          `matchID` int(11) NULL,
          `sourceUrl` varchar(255) NULL,
          `sourceOperation` varchar(64) NULL,
          `captureID` varchar(36) NULL,
          `capturedAt` datetime(6) NULL COMMENT 'UTC source fetch completion time',
          `rawTech` longtext NULL,
          `createTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `updateTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`ID`),
          UNIQUE KEY `uk_lq_matchtechnic_raw_schedule` (`scheduleID`),
          KEY `idx_lq_matchtechnic_raw_match` (`matchID`),
          KEY `idx_lq_matchtechnic_raw_capture` (`captureID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _add_missing_columns(
        "lq_matchtechnic_raw",
        [
            ("sourceOperation", "ADD COLUMN `sourceOperation` varchar(64) NULL AFTER `sourceUrl`"),
            ("captureID", "ADD COLUMN `captureID` varchar(36) NULL AFTER `sourceOperation`"),
            ("capturedAt", "ADD COLUMN `capturedAt` datetime(6) NULL COMMENT 'UTC source fetch completion time' AFTER `captureID`"),
        ],
    )

    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_playertechnic` (
          `ID` int(11) NOT NULL AUTO_INCREMENT,
          `scheduleID` int(11) NOT NULL,
          `matchID` int(11) NULL,
          `teamID` int(11) NULL,
          `matchSeason` varchar(10) NULL,
          `isHome` bit(1) NULL,
          `playerID` int(11) NULL,
          `playerName` varchar(100) NULL,
          `playerNameTrad` varchar(100) NULL,
          `playerNameEn` varchar(100) NULL,
          `isUnknown` tinyint(4) NULL,
          `position` varchar(20) NULL,
          `playTime` smallint(6) NULL,
          `shoot_Hit` smallint(6) NULL,
          `shoot` smallint(6) NULL,
          `threeMin_Hit` smallint(6) NULL,
          `threeMin` smallint(6) NULL,
          `punishBall_Hit` smallint(6) NULL,
          `punishBall` smallint(6) NULL,
          `attack` smallint(6) NULL,
          `defend` smallint(6) NULL,
          `rebound` smallint(6) NULL,
          `helpAttack` smallint(6) NULL,
          `foul` smallint(6) NULL,
          `rob` smallint(6) NULL,
          `misplay` smallint(6) NULL,
          `cover` smallint(6) NULL,
          `score` smallint(6) NULL,
          `isFirst` tinyint(4) NULL,
          `shortName` varchar(100) NULL,
          `plusMinus` smallint(6) NULL,
          `shirtNumber` varchar(20) NULL,
          `playerPic` varchar(255) NULL,
          `rawData` text NULL,
          `rawCaptureID` varchar(36) NULL,
          `createTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `updateTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`ID`),
          UNIQUE KEY `uk_lq_playertechnic_match_player` (`scheduleID`,`teamID`,`playerID`),
          KEY `idx_lq_playertechnic_match` (`matchID`),
          KEY `idx_lq_playertechnic_player` (`playerID`),
          KEY `idx_lq_playertechnic_capture` (`rawCaptureID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _add_missing_columns(
        "lq_playertechnic",
        [("rawCaptureID", "ADD COLUMN `rawCaptureID` varchar(36) NULL AFTER `rawData`")],
    )

    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_teamtechnic_period` (
          `ID` int(11) NOT NULL AUTO_INCREMENT,
          `scheduleID` int(11) NOT NULL,
          `matchID` int(11) NULL,
          `teamID` int(11) NULL,
          `matchSeason` varchar(10) NULL,
          `isHome` bit(1) NULL,
          `period` tinyint(4) NOT NULL DEFAULT 0,
          `playTime` smallint(6) NULL,
          `score` smallint(6) NULL,
          `loseScore` smallint(6) NULL,
          `shoot` smallint(6) NULL,
          `shoot_Hit` smallint(6) NULL,
          `threeMin` smallint(6) NULL,
          `threeMin_Hit` smallint(6) NULL,
          `punishBall` smallint(6) NULL,
          `punishBall_Hit` smallint(6) NULL,
          `attack` smallint(6) NULL,
          `defend` smallint(6) NULL,
          `rebound` smallint(6) NULL,
          `helpAttack` smallint(6) NULL,
          `rob` smallint(6) NULL,
          `cover` smallint(6) NULL,
          `misplay` smallint(6) NULL,
          `foul` smallint(6) NULL,
          `twoAttack` smallint(6) NULL,
          `totalMis` smallint(6) NULL,
          `fast` smallint(6) NULL,
          `inside` smallint(6) NULL,
          `exceed` smallint(6) NULL,
          `quarterFoul` smallint(6) NULL,
          `remainingPause` smallint(6) NULL,
          `twoPointScore` smallint(6) NULL,
          `threePointScore` smallint(6) NULL,
          `rawData` varchar(255) NULL,
          `rawCaptureID` varchar(36) NULL,
          `createTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `updateTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`ID`),
          UNIQUE KEY `uk_lq_teamtechnic_period_team` (`scheduleID`,`period`,`teamID`),
          KEY `idx_lq_teamtechnic_period_match` (`matchID`),
          KEY `idx_lq_teamtechnic_period_schedule` (`scheduleID`,`period`),
          KEY `idx_lq_teamtechnic_period_capture` (`rawCaptureID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _add_missing_columns(
        "lq_teamtechnic_period",
        [
            ("teamID", "ADD COLUMN `teamID` int(11) NULL AFTER `matchID`"),
            ("matchSeason", "ADD COLUMN `matchSeason` varchar(10) NULL AFTER `teamID`"),
            ("isHome", "ADD COLUMN `isHome` bit(1) NULL AFTER `matchSeason`"),
            ("playTime", "ADD COLUMN `playTime` smallint(6) NULL AFTER `period`"),
            ("score", "ADD COLUMN `score` smallint(6) NULL AFTER `playTime`"),
            ("loseScore", "ADD COLUMN `loseScore` smallint(6) NULL AFTER `score`"),
            ("shoot", "ADD COLUMN `shoot` smallint(6) NULL AFTER `loseScore`"),
            ("shoot_Hit", "ADD COLUMN `shoot_Hit` smallint(6) NULL AFTER `shoot`"),
            ("threeMin", "ADD COLUMN `threeMin` smallint(6) NULL AFTER `shoot_Hit`"),
            ("threeMin_Hit", "ADD COLUMN `threeMin_Hit` smallint(6) NULL AFTER `threeMin`"),
            ("punishBall", "ADD COLUMN `punishBall` smallint(6) NULL AFTER `threeMin_Hit`"),
            ("punishBall_Hit", "ADD COLUMN `punishBall_Hit` smallint(6) NULL AFTER `punishBall`"),
            ("attack", "ADD COLUMN `attack` smallint(6) NULL AFTER `punishBall_Hit`"),
            ("defend", "ADD COLUMN `defend` smallint(6) NULL AFTER `attack`"),
            ("rebound", "ADD COLUMN `rebound` smallint(6) NULL AFTER `defend`"),
            ("helpAttack", "ADD COLUMN `helpAttack` smallint(6) NULL AFTER `rebound`"),
            ("rob", "ADD COLUMN `rob` smallint(6) NULL AFTER `helpAttack`"),
            ("cover", "ADD COLUMN `cover` smallint(6) NULL AFTER `rob`"),
            ("misplay", "ADD COLUMN `misplay` smallint(6) NULL AFTER `cover`"),
            ("foul", "ADD COLUMN `foul` smallint(6) NULL AFTER `misplay`"),
            ("twoAttack", "ADD COLUMN `twoAttack` smallint(6) NULL AFTER `foul`"),
            ("totalMis", "ADD COLUMN `totalMis` smallint(6) NULL AFTER `twoAttack`"),
            ("fast", "ADD COLUMN `fast` smallint(6) NULL AFTER `totalMis`"),
            ("inside", "ADD COLUMN `inside` smallint(6) NULL AFTER `fast`"),
            ("exceed", "ADD COLUMN `exceed` smallint(6) NULL AFTER `inside`"),
            ("quarterFoul", "ADD COLUMN `quarterFoul` smallint(6) NULL AFTER `exceed`"),
            ("remainingPause", "ADD COLUMN `remainingPause` smallint(6) NULL AFTER `quarterFoul`"),
            ("twoPointScore", "ADD COLUMN `twoPointScore` smallint(6) NULL AFTER `remainingPause`"),
            ("threePointScore", "ADD COLUMN `threePointScore` smallint(6) NULL AFTER `twoPointScore`"),
            ("rawCaptureID", "ADD COLUMN `rawCaptureID` varchar(36) NULL AFTER `rawData`"),
        ],
    )
    _migrate_teamtechnic_period_indexes()
    _drop_columns(
        "lq_teamtechnic_period",
        [
            "statType",
            "homeMade",
            "homeAttempted",
            "awayMade",
            "awayAttempted",
            "homePercent",
            "awayPercent",
        ],
    )

    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_textlive_raw` (
          `ID` int(11) NOT NULL AUTO_INCREMENT,
          `scheduleID` int(11) NOT NULL,
          `matchID` int(11) NULL,
          `sourceUrl` varchar(255) NULL,
          `sourceOperation` varchar(64) NULL,
          `captureID` varchar(36) NULL,
          `capturedAt` datetime(6) NULL COMMENT 'UTC source fetch completion time',
          `rawTextLive` longtext NULL,
          `createTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `updateTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`ID`),
          UNIQUE KEY `uk_lq_textlive_raw_schedule` (`scheduleID`),
          KEY `idx_lq_textlive_raw_match` (`matchID`),
          KEY `idx_lq_textlive_raw_capture` (`captureID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _add_missing_columns(
        "lq_textlive_raw",
        [
            ("sourceOperation", "ADD COLUMN `sourceOperation` varchar(64) NULL AFTER `sourceUrl`"),
            ("captureID", "ADD COLUMN `captureID` varchar(36) NULL AFTER `sourceOperation`"),
            ("capturedAt", "ADD COLUMN `capturedAt` datetime(6) NULL COMMENT 'UTC source fetch completion time' AFTER `captureID`"),
        ],
    )

    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_textlive` (
          `ID` int(11) NOT NULL AUTO_INCREMENT,
          `scheduleID` int(11) NOT NULL,
          `matchID` int(11) NULL,
          `period` tinyint(4) NULL,
          `clock` varchar(20) NULL,
          `eventType` tinyint(4) NULL,
          `homeScore` smallint(6) NULL,
          `awayScore` smallint(6) NULL,
          `content` varchar(500) NULL,
          `liveID` int(11) NULL,
          `eventIndex` int(11) NULL,
          `sequence` int(11) NULL,
          `rawData` text NULL,
          `rawCaptureID` varchar(36) NULL,
          `createTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `updateTime` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`ID`),
          UNIQUE KEY `uk_lq_textlive_schedule_live` (`scheduleID`,`liveID`),
          KEY `idx_lq_textlive_match` (`matchID`),
          KEY `idx_lq_textlive_schedule_period` (`scheduleID`,`period`,`eventIndex`),
          KEY `idx_lq_textlive_capture` (`rawCaptureID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _add_missing_columns(
        "lq_textlive",
        [("rawCaptureID", "ADD COLUMN `rawCaptureID` varchar(36) NULL AFTER `rawData`")],
    )


def _indexes(table):
    rows = sql_util.select_dicts("SHOW INDEX FROM `{0}`".format(table))
    indexes = {}
    for row in rows:
        indexes.setdefault(row["Key_name"], []).append(row["Column_name"])
    return indexes


def _migrate_teamtechnic_period_indexes():
    indexes = _indexes("lq_teamtechnic_period")
    if "uk_lq_teamtechnic_period" in indexes:
        print("drop lq_teamtechnic_period.uk_lq_teamtechnic_period")
        sql_util.sqlExecute("ALTER TABLE `lq_teamtechnic_period` DROP INDEX `uk_lq_teamtechnic_period`")
    indexes = _indexes("lq_teamtechnic_period")
    if "uk_lq_teamtechnic_period_team" not in indexes:
        print("add lq_teamtechnic_period.uk_lq_teamtechnic_period_team")
        sql_util.sqlExecute(
            "ALTER TABLE `lq_teamtechnic_period` "
            "ADD UNIQUE KEY `uk_lq_teamtechnic_period_team` (`scheduleID`,`period`,`teamID`)"
        )


if __name__ == "__main__":
    migrate()
