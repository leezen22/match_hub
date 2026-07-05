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

.\venv\Scripts\python.exe zq_update.py schedule-js
.\venv\Scripts\python.exe zq_update.py schedule
.\venv\Scripts\python.exe zq_update.py score
.\venv\Scripts\python.exe zq_update.py odds --start-time "2026-05-05 00:00:00"
```

Run a narrow basketball schedule refresh for one Titan league/cup season:

```powershell
.\venv\Scripts\python.exe lq_update.py schedule-league-season --league-id 406 --season 2026
```

`--kind-type 1` is league schedule JS, and `--kind-type 2` is cup schedule JS
such as `c406.js`. If omitted, `match_hub` resolves `kind_type` from Titan
league metadata for the given league id. This command fetches and parses
schedule rows only. It does not update live scores, odds, odds details,
technical statistics, or event timelines.

Schedule data usually changes slowly, so this narrow refresh is a good first
step when a league is missing schedule rows or the local mirror is delayed.
Run it closer to report time for knockout/cup phases, where pairings and match
times can move with bracket results.

Run a narrow basketball local DB data refresh for one Titan league/cup season:

```powershell
.\venv\Scripts\python.exe lq_update.py league-season-data --league-id 406 --season 2026
```

This refreshes the league-season schedule first, then updates selected local DB
rows whose match state or update flags still need score, odds, or odds-detail
work. Schedule refresh is full for the league season, but score, odds, and
odds-detail polling is bounded to matches whose `matchTime` is no later than
current time plus 3 days by default. Use `--until-days` or `--until-time` to
override that upper bound. Use `--include-finished` only for explicit
repair/backfill work, and `--skip-schedule` when the schedule was already
refreshed.

Natural-language basketball update requests are supported directly in
`match_hub`:

```powershell
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 赛季赛程"
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 2026赛季赛程"
.\venv\Scripts\python.exe lq_update.py request "更新联赛ID 406 2026赛季本地DB数据"
.\venv\Scripts\python.exe lq_update.py request "帮我更新 wnba 赛程"
.\venv\Scripts\python.exe lq_update.py request "帮我更新 美国女子职业篮球联赛 本地DB数据"
```

The `request` stage is dry-run by default and prints the resolved stage and
arguments. If the season is omitted, it resolves the latest Titan season for
that league. If `kind_type` is omitted, it resolves the upstream Titan league
kind from league metadata. League names can be resolved through Titan league
metadata plus local aliases such as WNBA's English and Chinese names. Add
`--execute` to perform the local DB write. Natural-language local DB data
updates use the same default `matchTime <= now + 3 days` upper bound for score,
odds, and odds-detail work:

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
