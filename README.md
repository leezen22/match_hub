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
