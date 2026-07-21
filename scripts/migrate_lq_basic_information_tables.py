import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import sql_util


def migrate():
    _ensure_team_identity()
    _create_team_league_relation()
    _create_player_team_competition_relation()
    _create_player_profile()
    _ensure_player_profile_identity()
    _create_roster_snapshot_batch()
    _create_roster_snapshot()
    _create_roster_current()
    _ensure_extra_columns()
    print("basketball basic information tables migrated")


def _ensure_team_identity():
    from lq.service.team import ensure_lq_team_schema

    ensure_lq_team_schema()


def _create_team_league_relation():
    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_team_league_relation` (
          `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
          `source_entity_id` varchar(128) CHARACTER SET utf8 NOT NULL,
          `teamID` int(11) NOT NULL,
          `leagueID` int(11) NOT NULL,
          `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT '',
          `validFrom` datetime NULL,
          `validTo` datetime NULL,
          `relationStatus` varchar(32) CHARACTER SET utf8 NULL,
          `captured_at` datetime NULL,
          `recorded_at` datetime NULL,
          `updated_at` datetime NULL,
          `source_state_valid_at` datetime NULL,
          `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
          `collection_status` varchar(32) CHARACTER SET utf8 NULL,
          `has_data` tinyint(4) NULL,
          PRIMARY KEY (`source_namespace`,`source_entity_id`),
          KEY `idx_lq_team_league_relation_team` (`teamID`),
          KEY `idx_lq_team_league_relation_league` (`leagueID`,`season`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """
    )


def _create_player_profile():
    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_player_profile` (
          `id` bigint unsigned NOT NULL AUTO_INCREMENT,
          `playerID` int(11) NOT NULL,
          `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
          `source_entity_id` varchar(64) CHARACTER SET utf8 NOT NULL,
          `playerName` varchar(100) CHARACTER SET utf8 NULL,
          `playerNameTrad` varchar(100) CHARACTER SET utf8 NULL,
          `playerNameEn` varchar(100) CHARACTER SET utf8 NULL,
          `shortName` varchar(100) CHARACTER SET utf8 NULL,
          `birthDate` date NULL,
          `height` varchar(20) CHARACTER SET utf8 NULL,
          `weight` varchar(20) CHARACTER SET utf8 NULL,
          `nationality` varchar(50) CHARACTER SET utf8 NULL,
          `position` varchar(20) CHARACTER SET utf8 NULL,
          `shirtNumber` varchar(20) CHARACTER SET utf8 NULL,
          `playerPic` varchar(255) CHARACTER SET utf8 NULL,
          `playerPic_url` varchar(255) CHARACTER SET utf8 NULL,
          `player_url` varchar(255) CHARACTER SET utf8 NULL,
          `shortNameTrad` varchar(100) CHARACTER SET utf8 NULL,
          `shortNameEn` varchar(100) CHARACTER SET utf8 NULL,
          `experience` varchar(20) CHARACTER SET utf8 NULL,
          `contractUntil` date NULL,
          `annualSalary` varchar(50) CHARACTER SET utf8 NULL,
          `annualSalaryCurrency` varchar(16) CHARACTER SET utf8 NULL,
          `annualSalaryDisplay` varchar(80) CHARACTER SET utf8 NULL,
          `nationalityTrad` varchar(50) CHARACTER SET utf8 NULL,
          `nationalityEn` varchar(50) CHARACTER SET utf8 NULL,
          `draftInfo` varchar(255) CHARACTER SET utf8 NULL,
          `rawData` text CHARACTER SET utf8 NULL,
          `activeStatus` varchar(32) CHARACTER SET utf8 NULL,
          `captured_at` datetime NULL,
          `recorded_at` datetime NULL,
          `updated_at` datetime NULL,
          `source_state_valid_at` datetime NULL,
          `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
          `collection_status` varchar(32) CHARACTER SET utf8 NULL,
          `has_data` tinyint(4) NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uk_lq_player_profile_source` (`source_namespace`,`source_entity_id`),
          KEY `idx_lq_player_profile_player` (`playerID`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """
    )


def _ensure_player_profile_identity():
    columns = {row[0] for row in sql_util.select("SHOW COLUMNS FROM `lq_player_profile`")}
    indexes = sql_util.select("SHOW INDEX FROM `lq_player_profile`")
    primary_columns = [row[4] for row in indexes if row[2] == "PRIMARY"]
    index_names = {row[2] for row in indexes}

    if "id" not in columns:
        if primary_columns:
            sql_util.sqlExecute(
                """
                ALTER TABLE `lq_player_profile`
                  DROP PRIMARY KEY,
                  ADD COLUMN `id` bigint unsigned NOT NULL AUTO_INCREMENT FIRST,
                  ADD PRIMARY KEY (`id`),
                  ADD UNIQUE KEY `uk_lq_player_profile_source` (`source_namespace`,`source_entity_id`)
                """
            )
        else:
            sql_util.sqlExecute(
                """
                ALTER TABLE `lq_player_profile`
                  ADD COLUMN `id` bigint unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST
                """
            )
    elif primary_columns != ["id"]:
        sql_util.sqlExecute(
            """
            ALTER TABLE `lq_player_profile`
              DROP PRIMARY KEY,
              ADD PRIMARY KEY (`id`)
            """
        )

    indexes = sql_util.select("SHOW INDEX FROM `lq_player_profile`")
    index_names = {row[2] for row in indexes}
    if "uk_lq_player_profile_source" not in index_names:
        sql_util.sqlExecute(
            """
            ALTER TABLE `lq_player_profile`
              ADD UNIQUE KEY `uk_lq_player_profile_source` (`source_namespace`,`source_entity_id`)
            """
        )


def _create_player_team_competition_relation():
    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_player_team_competition_relation` (
          `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
          `source_entity_id` varchar(160) CHARACTER SET utf8 NOT NULL,
          `playerID` int(11) NOT NULL,
          `teamID` int(11) NOT NULL,
          `leagueID` int(11) NOT NULL,
          `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT '',
          `validFrom` datetime NULL,
          `validTo` datetime NULL,
          `relationStatus` varchar(32) CHARACTER SET utf8 NULL,
          `captured_at` datetime NULL,
          `recorded_at` datetime NULL,
          `updated_at` datetime NULL,
          `source_state_valid_at` datetime NULL,
          `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
          `collection_status` varchar(32) CHARACTER SET utf8 NULL,
          `has_data` tinyint(4) NULL,
          PRIMARY KEY (`source_namespace`,`source_entity_id`),
          KEY `idx_lq_player_team_relation_player` (`playerID`),
          KEY `idx_lq_player_team_relation_team` (`teamID`),
          KEY `idx_lq_player_team_relation_scope` (`leagueID`,`teamID`,`season`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """
    )


def _create_roster_snapshot_batch():
    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_team_roster_snapshot_batch` (
          `snapshot_batch_id` varchar(160) CHARACTER SET utf8 NOT NULL,
          `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
          `leagueID` int(11) NOT NULL,
          `teamID` int(11) NOT NULL,
          `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT '',
          `roster_hash` char(64) CHARACTER SET utf8 NULL,
          `captured_at` datetime NULL,
          `recorded_at` datetime NULL,
          `updated_at` datetime NULL,
          `source_state_valid_at` datetime NULL,
          `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
          `collection_status` varchar(32) CHARACTER SET utf8 NULL,
          `has_data` tinyint(4) NULL,
          `changed_from_previous` tinyint(4) NULL,
          `previous_snapshot_batch_id` varchar(160) CHARACTER SET utf8 NULL,
          PRIMARY KEY (`snapshot_batch_id`),
          KEY `idx_lq_roster_batch_scope` (`source_namespace`,`leagueID`,`teamID`,`season`),
          KEY `idx_lq_roster_batch_captured` (`captured_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """
    )


def _create_roster_snapshot():
    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_team_roster_snapshot` (
          `snapshot_batch_id` varchar(160) CHARACTER SET utf8 NOT NULL,
          `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
          `leagueID` int(11) NOT NULL,
          `teamID` int(11) NOT NULL,
          `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT '',
          `playerID` int(11) NOT NULL,
          `source_entity_id` varchar(64) CHARACTER SET utf8 NULL,
          `playerName` varchar(100) CHARACTER SET utf8 NULL,
          `playerNameTrad` varchar(100) CHARACTER SET utf8 NULL,
          `playerNameEn` varchar(100) CHARACTER SET utf8 NULL,
          `shortName` varchar(100) CHARACTER SET utf8 NULL,
          `shirtNumber` varchar(20) CHARACTER SET utf8 NULL,
          `position` varchar(20) CHARACTER SET utf8 NULL,
          `playerPic` varchar(255) CHARACTER SET utf8 NULL,
          `playerPic_url` varchar(255) CHARACTER SET utf8 NULL,
          `player_url` varchar(255) CHARACTER SET utf8 NULL,
          `shortNameTrad` varchar(100) CHARACTER SET utf8 NULL,
          `shortNameEn` varchar(100) CHARACTER SET utf8 NULL,
          `birthDate` date NULL,
          `height` varchar(20) CHARACTER SET utf8 NULL,
          `weight` varchar(20) CHARACTER SET utf8 NULL,
          `experience` varchar(20) CHARACTER SET utf8 NULL,
          `contractUntil` date NULL,
          `annualSalary` varchar(50) CHARACTER SET utf8 NULL,
          `annualSalaryCurrency` varchar(16) CHARACTER SET utf8 NULL,
          `annualSalaryDisplay` varchar(80) CHARACTER SET utf8 NULL,
          `nationality` varchar(50) CHARACTER SET utf8 NULL,
          `nationalityTrad` varchar(50) CHARACTER SET utf8 NULL,
          `nationalityEn` varchar(50) CHARACTER SET utf8 NULL,
          `draftInfo` varchar(255) CHARACTER SET utf8 NULL,
          `rawData` text CHARACTER SET utf8 NULL,
          `rosterStatus` varchar(32) CHARACTER SET utf8 NULL,
          `captured_at` datetime NULL,
          `source_state_valid_at` datetime NULL,
          `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
          `collection_status` varchar(32) CHARACTER SET utf8 NULL,
          `has_data` tinyint(4) NULL,
          PRIMARY KEY (`snapshot_batch_id`,`playerID`),
          KEY `idx_lq_roster_snapshot_player` (`playerID`),
          KEY `idx_lq_roster_snapshot_scope` (`source_namespace`,`leagueID`,`teamID`,`season`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """
    )


def _create_roster_current():
    sql_util.sqlExecute(
        """
        CREATE TABLE IF NOT EXISTS `lq_team_roster_current` (
          `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
          `leagueID` int(11) NOT NULL,
          `teamID` int(11) NOT NULL,
          `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT '',
          `playerID` int(11) NOT NULL,
          `source_entity_id` varchar(64) CHARACTER SET utf8 NULL,
          `playerName` varchar(100) CHARACTER SET utf8 NULL,
          `playerNameTrad` varchar(100) CHARACTER SET utf8 NULL,
          `playerNameEn` varchar(100) CHARACTER SET utf8 NULL,
          `shortName` varchar(100) CHARACTER SET utf8 NULL,
          `shirtNumber` varchar(20) CHARACTER SET utf8 NULL,
          `position` varchar(20) CHARACTER SET utf8 NULL,
          `playerPic` varchar(255) CHARACTER SET utf8 NULL,
          `playerPic_url` varchar(255) CHARACTER SET utf8 NULL,
          `player_url` varchar(255) CHARACTER SET utf8 NULL,
          `shortNameTrad` varchar(100) CHARACTER SET utf8 NULL,
          `shortNameEn` varchar(100) CHARACTER SET utf8 NULL,
          `birthDate` date NULL,
          `height` varchar(20) CHARACTER SET utf8 NULL,
          `weight` varchar(20) CHARACTER SET utf8 NULL,
          `experience` varchar(20) CHARACTER SET utf8 NULL,
          `contractUntil` date NULL,
          `annualSalary` varchar(50) CHARACTER SET utf8 NULL,
          `annualSalaryCurrency` varchar(16) CHARACTER SET utf8 NULL,
          `annualSalaryDisplay` varchar(80) CHARACTER SET utf8 NULL,
          `nationality` varchar(50) CHARACTER SET utf8 NULL,
          `nationalityTrad` varchar(50) CHARACTER SET utf8 NULL,
          `nationalityEn` varchar(50) CHARACTER SET utf8 NULL,
          `draftInfo` varchar(255) CHARACTER SET utf8 NULL,
          `rawData` text CHARACTER SET utf8 NULL,
          `rosterStatus` varchar(32) CHARACTER SET utf8 NULL,
          `latest_snapshot_batch_id` varchar(160) CHARACTER SET utf8 NULL,
          `captured_at` datetime NULL,
          `latest_captured_at` datetime NULL,
          `latest_checked_at` datetime NULL,
          `updated_at` datetime NULL,
          `source_state_valid_at` datetime NULL,
          `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
          `collection_status` varchar(32) CHARACTER SET utf8 NULL,
          `has_data` tinyint(4) NULL,
          PRIMARY KEY (`source_namespace`,`leagueID`,`teamID`,`season`,`playerID`),
          KEY `idx_lq_roster_current_player` (`playerID`),
          KEY `idx_lq_roster_current_scope` (`leagueID`,`teamID`,`season`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8
        """
    )


def _ensure_extra_columns():
    _ensure_columns("lq_player_profile", {
        "shortNameTrad": "ADD COLUMN `shortNameTrad` varchar(100) CHARACTER SET utf8 NULL",
        "shortNameEn": "ADD COLUMN `shortNameEn` varchar(100) CHARACTER SET utf8 NULL",
        "experience": "ADD COLUMN `experience` varchar(20) CHARACTER SET utf8 NULL",
        "contractUntil": "ADD COLUMN `contractUntil` date NULL",
        "annualSalary": "ADD COLUMN `annualSalary` varchar(50) CHARACTER SET utf8 NULL",
        "annualSalaryCurrency": "ADD COLUMN `annualSalaryCurrency` varchar(16) CHARACTER SET utf8 NULL",
        "annualSalaryDisplay": "ADD COLUMN `annualSalaryDisplay` varchar(80) CHARACTER SET utf8 NULL",
        "nationalityTrad": "ADD COLUMN `nationalityTrad` varchar(50) CHARACTER SET utf8 NULL",
        "nationalityEn": "ADD COLUMN `nationalityEn` varchar(50) CHARACTER SET utf8 NULL",
        "draftInfo": "ADD COLUMN `draftInfo` varchar(255) CHARACTER SET utf8 NULL",
        "playerPic_url": "ADD COLUMN `playerPic_url` varchar(255) CHARACTER SET utf8 NULL",
        "player_url": "ADD COLUMN `player_url` varchar(255) CHARACTER SET utf8 NULL",
        "photo_collection_status": "ADD COLUMN `photo_collection_status` varchar(32) CHARACTER SET utf8 NULL",
        "photo_has_data": "ADD COLUMN `photo_has_data` tinyint(4) NULL",
        "photo_captured_at": "ADD COLUMN `photo_captured_at` datetime NULL",
        "photo_updated_at": "ADD COLUMN `photo_updated_at` datetime NULL",
        "photo_source_url_or_operation": "ADD COLUMN `photo_source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL",
        "rawData": "ADD COLUMN `rawData` text CHARACTER SET utf8 NULL",
    })
    extra = {
        "shortNameTrad": "ADD COLUMN `shortNameTrad` varchar(100) CHARACTER SET utf8 NULL",
        "shortNameEn": "ADD COLUMN `shortNameEn` varchar(100) CHARACTER SET utf8 NULL",
        "birthDate": "ADD COLUMN `birthDate` date NULL",
        "height": "ADD COLUMN `height` varchar(20) CHARACTER SET utf8 NULL",
        "weight": "ADD COLUMN `weight` varchar(20) CHARACTER SET utf8 NULL",
        "experience": "ADD COLUMN `experience` varchar(20) CHARACTER SET utf8 NULL",
        "contractUntil": "ADD COLUMN `contractUntil` date NULL",
        "annualSalary": "ADD COLUMN `annualSalary` varchar(50) CHARACTER SET utf8 NULL",
        "annualSalaryCurrency": "ADD COLUMN `annualSalaryCurrency` varchar(16) CHARACTER SET utf8 NULL",
        "annualSalaryDisplay": "ADD COLUMN `annualSalaryDisplay` varchar(80) CHARACTER SET utf8 NULL",
        "nationality": "ADD COLUMN `nationality` varchar(50) CHARACTER SET utf8 NULL",
        "nationalityTrad": "ADD COLUMN `nationalityTrad` varchar(50) CHARACTER SET utf8 NULL",
        "nationalityEn": "ADD COLUMN `nationalityEn` varchar(50) CHARACTER SET utf8 NULL",
        "draftInfo": "ADD COLUMN `draftInfo` varchar(255) CHARACTER SET utf8 NULL",
        "playerPic_url": "ADD COLUMN `playerPic_url` varchar(255) CHARACTER SET utf8 NULL",
        "player_url": "ADD COLUMN `player_url` varchar(255) CHARACTER SET utf8 NULL",
        "rawData": "ADD COLUMN `rawData` text CHARACTER SET utf8 NULL",
    }
    _ensure_columns("lq_team_roster_snapshot", extra)
    current_extra = dict(extra)
    current_extra["captured_at"] = "ADD COLUMN `captured_at` datetime NULL"
    current_extra["source_state_valid_at"] = "ADD COLUMN `source_state_valid_at` datetime NULL"
    _ensure_columns("lq_team_roster_current", current_extra)


def _ensure_columns(table, columns):
    existing = {row[0] for row in sql_util.select("SHOW COLUMNS FROM `{0}`".format(table))}
    for column, ddl in columns.items():
        if column not in existing:
            print("add {0}.{1}".format(table, column))
            sql_util.sqlExecute("ALTER TABLE `{0}` {1}".format(table, ddl))


if __name__ == "__main__":
    migrate()
