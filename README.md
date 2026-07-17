# match_hub

Sports match data update project.

Main commands:

```powershell
.\venv\Scripts\python.exe lq_update.py
.\venv\Scripts\python.exe zq_update.py
```

Running an update file with no arguments uses the selected task block at the bottom of that file. Edit that block when you want a personal run panel. Passing a stage argument uses the command-line wrapper below.

Run one update stage:

```powershell
.\venv\Scripts\python.exe lq_update.py schedule-js
.\venv\Scripts\python.exe lq_update.py schedule
.\venv\Scripts\python.exe lq_update.py score
.\venv\Scripts\python.exe lq_update.py odds
.\venv\Scripts\python.exe lq_update.py details
.\venv\Scripts\python.exe lq_update.py enrichment --schedule-id 705106
.\venv\Scripts\python.exe lq_update.py enrichment-pending --league-id 406 --season-count 3 --start-time "2026-07-01 00:00:00" --until-time "2026-07-02 00:00:00" --limit 20

.\venv\Scripts\python.exe zq_update.py schedule-js
.\venv\Scripts\python.exe zq_update.py schedule
.\venv\Scripts\python.exe zq_update.py score
.\venv\Scripts\python.exe zq_update.py odds --start-time "2026-05-05 00:00:00"
```

Run a narrow basketball schedule refresh for one Titan league/cup season:

```powershell
.\venv\Scripts\python.exe lq_update.py schedule-league-season --league-id 406 --season 2026
.\venv\Scripts\python.exe lq_update.py schedule-recent-seasons --league-id 406
```

`--kind-type 1` is league schedule JS, and `--kind-type 2` is cup schedule JS
such as `c406.js`. If omitted, `match_hub` resolves `kind_type` from Titan
league metadata for the given league id. This command fetches and parses
schedule rows only. It does not update live scores, odds, odds details,
technical statistics, or event timelines.

Run basketball single-match enrichment:

```powershell
.\venv\Scripts\python.exe scripts\migrate_lq_technical_event_tables.py
.\venv\Scripts\python.exe lq_update.py technical --schedule-id 705106
.\venv\Scripts\python.exe lq_update.py text-live --schedule-id 705106
.\venv\Scripts\python.exe lq_update.py enrichment --schedule-id 705106
```

`technical` writes raw tech data, player match stats, and team stats into
`lq_teamtechnic_period`; `period=0` is full game and `period=1..4` are quarters.
The full-game rows also include Titan's live team supplement fields:
`quarterFoul`, `remainingPause`, `twoPointScore`, and `threePointScore`.
`text-live` writes raw text-live data and play-by-play event rows. `enrichment`
runs both. `enrichment-pending` selects matches whose `technical_f` or
`textlive_f` is still `0/1`; pass `--league-id` to limit it to one league and
`--season-count` to limit that league to recent seasons. A normal successful
request marks finished matches as `2`, even when Titan returns no team stats,
no player stats, or no event rows. Use `teamtechnic_has_data`,
`playertechnic_has_data`, and `textlive_has_data` on `lq_schedule` to distinguish
normal completion with data from normal completion without data. Running
`lq_update.py all --league-id 406
--season-count 3` also passes those bounds into the recent pending enrichment
window after score, odds, and detail updates.

Schedule data usually changes slowly, so this narrow refresh is a good first
step when a league is missing schedule rows or the local mirror is delayed.
Run it closer to report time for knockout/cup phases, where pairings and match
times can move with bracket results.

Run a narrow basketball local DB data refresh for one Titan league/cup season:

```powershell
.\venv\Scripts\python.exe lq_update.py league-season-data --league-id 406 --season 2026
.\venv\Scripts\python.exe lq_update.py league-recent-seasons-data --league-id 406
.\venv\Scripts\python.exe lq_update.py league-recent-seasons-data --league-id 406 --start-time "2026-01-01 00:00:00" --season-count 3
```

By default, `league-season-data` only accepts the current season plus the
previous two seasons for that league. Older explicit seasons are rejected to
avoid accidental historical backfills. `league-recent-seasons-data` runs the
same flow for those three allowed seasons. Use `--season-count` to change the
number of recent seasons, and `--start-time` to add a lower `matchTime` bound.

This refreshes each league-season schedule first, then updates selected local DB
rows whose match state or update flags still need score, odds, odds-detail,
technical-stat, player-stat, or event-timeline
work. Schedule refresh is full for the league season, but score, odds, and
odds-detail polling is bounded to matches whose `matchTime` is no later than
current time plus 3 days by default. Use `--until-days` or `--until-time` to
override that upper bound. Use `--include-finished` only for explicit
repair/backfill work, and `--skip-schedule` when the schedule was already
refreshed.

Structured basketball and football update requests are supported directly in
`match_hub`. Use this path for system-to-system calls:

```powershell
.\venv\Scripts\python.exe update_request.py --structured --sport basketball --league-id 406 --action data
.\venv\Scripts\python.exe update_request.py --structured --sport football --league-id 648 --action data
.\venv\Scripts\python.exe update_request.py --structured --sport football --league-id 648 --action schedule
```

The structured path does not parse natural-language request text. It uses
explicit `sport`, `league-id`, and `action` parameters, then lets the
sport-specific updater resolve omitted Titan season/type metadata.

Natural-language basketball and football update requests are supported for
operator-facing use:

```powershell
.\venv\Scripts\python.exe update_request.py "帮我更新 wnba 本地比赛信息"
.\venv\Scripts\python.exe update_request.py "更新 世亚预 比赛信息"
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 赛季赛程"
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 2026赛季赛程"
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 2026赛季本地DB数据"
.\venv\Scripts\python.exe lq_update.py request "帮我更新 wnba 赛程"
.\venv\Scripts\python.exe lq_update.py request "帮我更新 美国女子职业篮球联赛 本地DB数据"
.\venv\Scripts\python.exe zq_update.py request "更新 世亚预 比赛信息"
```

The `request` stage is dry-run by default and prints the resolved stage and
arguments. If the season is omitted, it resolves the latest Titan season for
that league. If `kind_type` is omitted, it resolves the upstream Titan league
kind from league metadata. League names can be resolved through Titan league
metadata plus local aliases such as WNBA's English and Chinese names. Add
`--execute` to perform the local DB write. Natural-language local DB data
updates use the same default `matchTime <= now + 3 days` upper bound for score,
odds, and odds-detail work.

When `update_request.py` runs a natural-language request with `--execute`, it
only delegates to the sport-specific updater script. Normal script output is
suppressed; a non-zero exit returns the error stream for diagnosis.

League metadata is cached locally for 24 hours under
`data/cache/league_metadata/`. When a natural-language request does not include
a sport, `update_request.py` probes cached basketball and football league
metadata. If exactly one sport matches, it routes to that updater. If both
sports match, it stops with an ambiguity error and requires `--sport` or the
structured interface.

External projects should not read those cache files directly. Use the compact
metadata query tool instead:

```powershell
.\venv\Scripts\python.exe scripts\query_league_metadata.py "更新 立陶甲 比赛信息"
.\venv\Scripts\python.exe scripts\query_league_metadata.py "更新 wnba 赛程" --sport basketball
```

The query tool performs cached league metadata lookup inside `match_hub`,
applies sport-specific aliases and normalization, and returns only the
necessary JSON fields such as `sport`, `league_id`, `league_name`, `season`,
`kind_type`, `league_type`, and `if_have_sub`. It never writes the local DB.
For basketball, the cached league list preserves the useful fields already
present in Titan `infoHeader_cn.js`, including `seasons`, country metadata, and
source URL, while keeping the existing `league_id`, `league_name`, and
`kind_type` fields stable for current update workflows. It also merges
multi-language league and country names from Titan `leftData.js`, including
simplified Chinese, traditional Chinese, and English names. If an older cache
is missing season or multi-language fields, `match_hub` refreshes it
automatically; a single-league season cache is kept only as a compatibility
fallback.

```powershell
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 赛季赛程" --execute
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 2026赛季本地DB数据" --execute
```

Local database config:

```powershell
.\venv\Scripts\python.exe scripts\init_local_config.py
```

Edit `config\db_config.local.py` on each device. This local file is ignored by Git, so real database host/user/password values will not be pushed to GitHub.

Check the active local config:

```powershell
.\venv\Scripts\python.exe scripts\check_runtime_config.py
```

Basketball schedule JS diagnosis:

```powershell
.\venv\Scripts\python.exe scripts\diagnose_lq_schedule_js.py --page-url "http://nba.titan007.com//cn/normal.aspx?SclassID=1&MatchSeason=2025-2026"
.\venv\Scripts\python.exe scripts\diagnose_lq_schedule_js.py --js-url "http://nba.titan007.com/jsData/matchResult/25-26/l1_1_2026_4.js"
```

Basketball schedule files are temporary by default. Configure these in `config/lqconfig_qt.py`:

```python
schedule_js_work_dir = str(DATA_DIR / 'work' / 'matchResult')
keep_schedule_js_cache = False
enable_finished_season_backfill = False
```

Football schedule files use the same temporary-file pattern. Configure these in `config/zqconfig_qt.py`:

```python
schedule_js_work_dir = str(DATA_DIR / 'work' / 'matchResult')
keep_schedule_js_cache = False
enable_finished_season_backfill = False
```

The first rebuild keeps the old business behavior runnable. Later refactor phases will split request, parser, service, and database responsibilities.
