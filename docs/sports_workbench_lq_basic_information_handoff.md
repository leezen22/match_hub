# Sports Workbench Basketball Basic Information Handoff

更新时间：2026-07-20

## 责任边界

Match Hub 负责定期采集并幂等落库 Titan 篮球基础资料，保留 Titan 原始 ID、字段、来源地址、采集时间和采集状态。

Sports Workbench 只读消费这些表，并自行处理身份绑定、时序关系、证据判断、业务完整性结论和跨来源 canonical identity。Match Hub 不生成 canonical ID，不按名称合并实体，不推断球员参赛或长期效力事实。

## 来源与 ID

- `source_namespace`: `titan_basketball`
- Titan 联赛外部 ID：`lq_league.leagueID` / `source_entity_id`
- Titan 球队外部 ID：`lq_team.ID` / `source_entity_id`
- Titan 球员外部 ID：`lq_player_profile.playerID` / `source_entity_id`
- `lq_player_profile.id` 是本地自增主键，仅用于本库内部隔离外部 ID，不代表 canonical player identity。

## 时间语义

- `captured_at`: 本次从 Titan 获取源资料的时间。
- `recorded_at`: 写入本地库的时间。
- `updated_at`: 本地记录最后更新时间。
- `source_state_valid_at`: Titan 明示的资料更新时间；Titan 没提供时为 `NULL`。
- `source_url_or_operation`: Titan URL 或本次采集操作来源。

## 表说明

### `lq_league`

联赛基础资料。主要字段：

- `leagueID`: Titan 联赛 ID。
- `name_sh`, `name_cn`, `name_tw`, `name_en`, `name_twsh`, `name_ensh`: Titan 返回的名称字段。
- `country`, `countryID`, `leagueKind`, `currMatchSeason`, `color`: Titan 联赛属性。
- `logo`: Titan 原始相对图标路径。
- `logo_url`: 补全域名后的图标 URL，当前域名为 `https://nba.titan007.com`。
- 通用采集字段：`source_namespace`, `source_entity_id`, `captured_at`, `recorded_at`, `updated_at`, `source_state_valid_at`, `source_url_or_operation`, `collection_status`, `has_data`。

`currMonth`、`currYear` 已不作为业务依赖字段使用。

### `lq_team`

球队基础资料，一支 Titan 球队只保留一条主记录。球队参加多个联赛或赛季时，不在 `lq_team` 内复制多条球队。

主要字段：

- `ID`: Titan TeamID。
- `leagueID`: Titan 本次球队资料来源里的联赛上下文，不应理解为唯一永久主联赛。
- `name_j`, `name_f`, `name_e`, `name_js`, `name_ft`, `name_et`: Titan 返回的球队名称字段。
- `locationID`, `matchAddrID`, `city`, `gymnasium`, `capacity`, `joinYear`: Titan 球队属性。
- `drillmaster`, `masterPic`, `matserIntro`: Titan 教练相关字段。
- `flag`: Titan 原始相对队标路径。
- `flag_url`: 补全域名后的队标 URL，当前域名为 `https://nba.titan007.com`。
- `source_team_kind`: `team` 或 `placeholder`。
- `is_placeholder`: 1 表示类似“胜者/败者/TBD”的非正常球队占位记录。
- 通用采集字段同上。

### `lq_team_league_relation`

Titan 联赛球队列表的采集关系，不表示 Match Hub 推断的主联赛。

- 主键：`source_namespace`, `source_entity_id`
- `source_entity_id`: `{teamID}:{leagueID}:{season}`
- `teamID`, `leagueID`, `season`: Titan source-local 关系上下文。
- `relationStatus`: `active` / `inactive`。
- `validFrom`: 首次或重新进入该 Titan 列表的采集时间。
- `validTo`: 从该 Titan 列表消失时的采集时间。

维护策略：每次更新某个联赛球队列表时，当期出现的关系置为 `active`；之前 active 但本次未出现的关系置为 `inactive`，不物理删除。

### `lq_player_profile`

球员基础资料，主要由球队阵容接口发现和更新。它不是比赛技术统计表，也不依赖球员打过比赛才发现。

主要字段：

- `id`: 本地自增主键。
- `playerID`: Titan playerid。
- `source_entity_id`: Titan playerid 字符串。
- `playerName`, `playerNameTrad`, `playerNameEn`, `shortName`, `shortNameTrad`, `shortNameEn`: Titan 名称字段。
- `birthDate`, `height`, `weight`, `nationality`, `nationalityTrad`, `nationalityEn`, `position`, `shirtNumber`, `experience`, `contractUntil`, `draftInfo`: Titan 球员属性。
- `annualSalary`: Titan 返回的年薪原始值。
- `annualSalaryCurrency`: 当前可判定币种；NBA/WNBA 等美元语境联赛写 `USD`，不能判定时为 `NULL`。
- `annualSalaryDisplay`: 带单位展示值，例如 `120万美元`。
- `playerPic`: Titan 原始相对照片路径。
- `playerPic_url`: 补全域名后的照片 URL；阵容接口有图时同步，独立照片补全任务可后续补充。
- `player_url`: Titan 球员详情页。
- `rawData`: Titan 阵容行原始数组 JSON。
- `photo_collection_status`, `photo_has_data`, `photo_captured_at`, `photo_updated_at`, `photo_source_url_or_operation`: 独立照片补全任务状态。
- 通用采集字段同上。

更新策略：通过阵容接口获取到球员资料时幂等 upsert。缺字段不会隐式清空已有资料；照片补全任务暂不建议高频运行。

### `lq_team_roster_current`

当前阵容视图，按 `source_namespace + leagueID + teamID + season + playerID` 保留最新状态。

- `rosterStatus`: `active` / `inactive`。
- `latest_snapshot_batch_id`: 最近一次产生快照的批次。
- `latest_captured_at`: 最近一次阵容源采集时间。
- `latest_checked_at`: 最近一次检查该阵容上下文的时间。
- 球员字段与 `lq_player_profile` 基本一致，代表该阵容上下文中的最新 Titan 返回值。

用途：Sports Workbench 查询某球队某联赛赛季下“当前 Match Hub 看到的阵容”。

### `lq_team_roster_snapshot_batch`

阵容采集批次表。

- `snapshot_batch_id`: 批次 ID。
- `leagueID`, `teamID`, `season`: Titan 阵容上下文。
- `roster_hash`: 按球员、号码、位置、合同/年薪等关键阵容字段计算的 hash。
- `changed_from_previous`: 1 表示相对上一次成功批次发生变化，0 表示无变化。
- `previous_snapshot_batch_id`: 上一个成功批次。
- 通用采集字段同上。

维护策略：每次采集都会记录批次；只有阵容 hash 变化或当前阵容缺失时，才写入明细快照，避免大量无效快照。

### `lq_team_roster_snapshot`

阵容变化快照明细。只在 `changed_from_previous=1` 或首次补齐当前阵容时写入。

- 主键：`snapshot_batch_id`, `playerID`
- 字段与 `lq_team_roster_current` 基本一致。

用途：Sports Workbench 可基于批次追溯阵容变更证据。

### `lq_player_team_competition_relation`

球员在 Titan 阵容上下文中的球队-联赛-赛季采集关系，保留历史状态，不是唯一最新事实表。

- 主键：`source_namespace`, `source_entity_id`
- `source_entity_id`: `{playerID}:{teamID}:{leagueID}:{season}`
- `playerID`, `teamID`, `leagueID`, `season`
- `relationStatus`: `active` / `inactive`
- `validFrom`, `validTo`

与 `lq_team_roster_current` 的区别：

- `lq_team_roster_current`: 查询当前阵容状态和最新球员字段。
- `lq_player_team_competition_relation`: 追踪球员出现在某球队/联赛/赛季阵容中的历史关系。

## 采集状态

- `success`: 本次源请求/解析/落库成功。
- `legacy`: 历史已有数据，非本次 Titan 基础资料新流程采集，但已补齐来源命名空间和状态，避免误判为待采集。
- `failed`: 请求或解析失败；需要人工或后续任务决定是否重试。
- `success_with_data`: 独立照片任务请求成功且获得照片。
- `success_empty`: 独立照片任务请求成功但源页无照片。默认不应重复请求。
- `NULL`: 目前仅照片状态还可能存在，表示照片补全任务尚未处理；基础资料主体状态不应为 `NULL`。

`has_data=1` 表示本次采集得到实体数据；`has_data=0` 表示采集成功但无实体数据，或关系被置为 inactive。

## 更新命令

迁移基础资料表：

```bash
venv/bin/python scripts/migrate_lq_basic_information_tables.py
```

全量基础资料更新，包含联赛、球队、球队阵容、球员基础资料、球员-球队-联赛关系；默认不抓独立照片页：

```bash
venv/bin/python lq_update.py basic-info
```

只更新联赛和球队基础资料，不更新阵容：

```bash
venv/bin/python lq_update.py basic-info --skip-roster
```

只更新某个联赛的球队资料：

```bash
venv/bin/python lq_update.py team-info --league-id 1
```

更新某个球队阵容：

```bash
venv/bin/python lq_update.py roster-info --team-id 2 --skip-photo
```

补齐尚未成功采集过阵容的球队：

```bash
venv/bin/python lq_update.py roster-info --missing-only --skip-photo
```

独立照片补全，默认单线程、小批量、跳过已失败行：

```bash
venv/bin/python lq_update.py photo-info
```

显式重试失败照片行，建议小批量执行：

```bash
venv/bin/python lq_update.py photo-info --retry-failed --limit 100
```

## 完成语义

基础资料主体完成：

- `lq_league.collection_status` 无 `NULL`。
- `lq_team.collection_status` 无 `NULL`。
- `lq_player_profile.collection_status='success'` 的球员已由阵容接口发现并落库。
- `lq_team.collection_status='success'` 且 `is_placeholder=0` 的球队，都存在至少一个 `lq_team_roster_snapshot_batch.collection_status='success'` 批次。

照片补全完成语义单独计算：

- `photo_collection_status='success_with_data'`: 有照片。
- `photo_collection_status='success_empty'`: 已确认源页无照片，默认不要重复请求。
- `photo_collection_status='failed'`: 请求失败或疑似被拦截，只有显式重试才处理。
- `photo_collection_status IS NULL`: 未处理照片补全。

## 当前巡检结果

巡检时间：2026-07-20 17:39 Asia/Shanghai。

- `lq_league.collection_status`: `success=286`, `legacy=106`, `NULL=0`
- `lq_team.collection_status`: `success=3351`, `legacy=3736`, `NULL=0`
- `lq_player_profile.collection_status`: `success=16584`
- `lq_team_roster_snapshot_batch.collection_status`: `success=3354`, `failed=2271`
- 成功采集且非占位球队缺少成功阵容批次：`0`
- 成功联赛缺少 `logo_url`: `37`
- 成功球队缺少 `flag_url`: `687`
- 成功球员缺少 `playerPic_url`: `13739`
- `lq_player_profile.photo_collection_status`: `success_with_data=2845`, `success_empty=4360`, `failed=1000`, `NULL=8379`

注意：照片采集目前按反爬风险保持暂停；上述 `playerPic_url` 缺口不影响联赛、球队、阵容、球员主体资料完成语义。
