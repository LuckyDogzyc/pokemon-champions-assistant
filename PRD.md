# Pokemon Champions Assistant — PRD

## 1. Executive Summary

Pokemon Champions Assistant 是一个面向**主播 / 内容创作者**的宝可梦对战**全流程辅助工具**。

它运行在电脑端，配合 OBS 虚拟摄像头从 Switch 对战画面中获取信息，在**独立浏览器窗口**中实时追踪每一场对局的全生命周期——从选人开始，到结算结束——自动识别双方队伍、场上宝可梦、HP、技能使用等变化，并持续生成对战记录。

---

## 2. 核心设计：对战数据模型（BattleSession）

### 设计原则
每一局对战是一份**独立的 JSON 数据对象**，随着识别过程逐步填充，UI 始终从该对象读取展示，不依赖瞬时识别结果。

```json
{
  "battle_id": "battle-abc123-1700000000",
  "side": {
    "player": { ... },
    "opponent": { ... }
  },
  "turn": 1,
  "log": [ ... ]
}
```

### 数据填充流程
```
选人开始 ──→ 双方队伍 12 只逐步填入（名称+道具+性别）
                    ↓
           每只宝可梦自动查询种族值（HP/物攻/物防/特攻/特防/速度）
                    ↓
           首次上场 → 填入出战宝可梦 slot
                    ↓
           战斗中逐步填入：当前HP、技能 4 招、PP、状态、buff/debuff
                    ↓
           结算检测 → 标记对局结束，UI 清除数据，LOG 保留
```

### 每只宝可梦的数据结构（可扩展）
```
{
  "name": "振翼发",
  "species": "振翼发",
  "pokemon_id": "mimikyu",
  "types": ["Ghost", "Fairy"],
  "base_stats": { "hp": 55, "attack": 90, "defense": 80, "sp_attack": 50, "sp_defense": 105, "speed": 96 },
  "item": "爽喉喷雾",
  "gender": "female",
  "level": 50,
  "current_hp": 145,
  "max_hp": 167,
  "current_hp_percent": 86.8,
  "status": ["烧伤"],        // 异常状态列表，可扩展多状态
  "stat_stages": { "attack": 0, "defense": -1, "sp_attack": 0, "sp_defense": 0, "speed": 0, "accuracy": 0, "evasion": 0 },
  "buffs": [],               // 未来扩展：能力变化/场地效果
  "debuffs": [],
  "moves": [
    {
      "name": "月亮之力",
      "type": "Fairy",
      "category": "Special",
      "base_power": 95,
      "pp_current": 8,
      "pp_max": 15,
      "description": "...（鼠标 hover 显示）"
    },
    { "name": "..." }
  ],
  "revealed_moves": ["月亮之力", "暗影球"],
  "is_fainted": false,
  "turns_on_field": 3
}
```

---

## 3. MVP Scope

### In Scope

#### 能力 1：对战数据模型（BattleSessionStore）
- 后端新增 `BattleSessionStore`，替代部分 `BattleStateStore` 功能
- 每局一个 `BattleSession` 对象
- 选人阶段填充队伍 12 只（名称+道具+性别）
- 自动查种族值并附加到每只宝可梦
- 战斗阶段填充出战宝可梦的 HP、技能、PP、状态
- 结算后清除数据，保留 LOG 直到下一局开始

#### 能力 2：选人阶段队伍识别修复
- 确保 `TeamSelectRecognizer` 结果正确写入 `roi_payloads['player_mon_1~6']`
- 确保 `BattleSessionStore` 正确读取并保存到 `player_team` / `opponent_team`
- 前端 `TeamSlots` 从 battle_session 的 team 列表读取，而不是 roi_payloads

#### 能力 3：出战宝可梦卡片能力值 + 技能详情
- 6 维基础能力值（HP/物攻/物防/特攻/特防/速度）以迷你网格展示
- 4 个技能每个显示：技能名、属性标签（带颜色）、伤害值、PP（xx/xx格式）
- 技能支持 `title` tooltip 显示描述

#### 能力 4：HP 识别修复
- 我方 HP 格式：`145/167 87%`
- 确保 pipeline 的 HP OCR 正确写入 `player_hp_current` / `player_hp_max`
- 确保 `BattleSession` 的 `current_hp` 和 `max_hp` 正确更新

#### 能力 5：对战 LOG 可滑动 + 拷贝
- LOG 区域可滚动查看
- 底部或右侧有「复制全部」按钮
- 结算后 LOG 不清除，停止更新，直到下一局开始

#### 能力 6：结算不清除 LOG
- `final_result` 触发时：清除队伍/出战/HP 等数据，但 LOG 保留
- 下一局 `team_select` 再触发时：LOG 继续追加新的

### Out of Scope (for now)
- 伤害计算器
- 阵容推荐器
- 属性克制自动展示
- 对方队伍缩略图匹配

---

## 3.2. 代码审计后的真实状态（2026-05-03 更新）

> 重要修正：上一版 PRD 将很多“字段/组件/接口形状已经存在”的内容写成“已实现”。本次按代码层面重新审计后，结论是：当前项目有不少模块能跑，但核心业务闭环质量不足。下面状态以**代码证据 + 现有测试 + 实际测试运行**为准，而不是以 PRD 自述为准。

### 本次审计执行记录

已执行/确认：

- 后端重点测试：`62 passed`（video source / capture / recognition pipeline / manual override / OCR 局部能力等重点集）
- 后端全量测试：`pytest -q` 可通过：`163 passed, 1 skipped`
- 根目录 `pytest.ini` 已统一 `pythonpath = . backend`，并注册 `real_ocr` marker
- 前端测试：`npm test -- --runInBand` 通过：`10 suites / 57 tests`
- 前端构建：`npm run build` 通过
- 前端测试存在 React `act(...)` warning，但未导致失败
- `real_ocr` marker 未被根目录 `pytest.ini` 注册，会产生 warning

### 总体判断

当前代码状态不是“PRD 已完整落地”，而是：

1. **视频源 / OBS Virtual Camera 优先 / Capture 相关能力相对扎实**，有后端 mock 测试和 API 测试支撑。
2. **RecognitionPipeline 有阶段检测、ROI、debug payload、OCR 局部能力的框架**，但 HP / 技能 / 状态 / BattleSession 写入链路断点较多。
3. **BattleSession 是 PRD 的核心，但目前不是可靠单一数据源**：模型存在、API 会返回，但同步、LOG、结算、手动修正、测试覆盖都不足。
4. **前端真实首页与组件测试割裂**：`BattleInfoPanel` / `TeamRosterPanel` / `MovePanel` / `VideoSourcePanel` 有文件和测试，但当前首页大量使用 `page.tsx` 内联组件，很多“已测组件”并未真实接入。
5. **现有测试偏“壳/字段/mock/孤立组件”**，不足以证明完整对局生命周期可用。

---

## 3.3. PRD 能力真实完成度矩阵

| 能力 | 当前真实状态 | 完成度 | 代码证据 | 主要问题 |
|---|---|---:|---|---|
| BattleSession 数据模型 | 模型和 store 存在，已补第一批生命周期测试，正在成为主数据源 | 65% | `backend/app/schemas/battle_session.py`, `backend/app/services/battle_session_store.py`, `backend/tests/test_battle_session_store.py` | 已覆盖 slot 顺序、active、HP、moves、status、final_result/LOG 保留，并补 `BattleStateStore.move_log` 去重同步入口；仍需更多真实 OCR/API/UI 端到端 |
| 每局独立 JSON，UI 从对象读取 | 首页已通过类型契约读取 `battle_session`，并有真实首页 fixture 覆盖队伍、active、HP、技能、LOG 优先来自 `battle_session` | 60% | `frontend/types/api.ts`, `frontend/app/page.tsx`, `frontend/tests/home-battle-session.test.tsx`, `npm run build` | 前端主链路已固定；仍需覆盖 final_result/下一局 reset、复制 LOG 反馈和去除更多 legacy fallback |
| 选人阶段填充双方队伍 | Store 层已保持 slot 顺序并补双方基础数据；OCR/缩略图端仍不足 | 65% | `TeamSelectRecognizer`, `RecognitionPipeline.build_roi_payloads`, `BattleSessionStore.sync_from_recognition`, `test_battle_session_store.py` | 对方“缩略图匹配”未实现；错误识别不会覆盖；真实 OCR → BattleSession 仍需端到端测试 |
| 自动查种族值 | Store 层我方/对方按名称均会补基础数据 | 60% | `BattleSessionStore._lookup_base_stats`, `_mon_from_name`, `test_battle_session_store.py` | 依赖名称匹配；sprite id 路径和真实 OCR 端到端仍需补测试 |
| 当前出战宝可梦 | 有字段和局部同步 | 45% | `set_player_active`, `set_opponent_active` | active 与 team、status、HP、moves 未形成稳定闭环 |
| HP OCR 与写入 | Store 可接收 payload 并写入 BattleSession；OCR → payload 链路仍断裂 | 45% | `ChineseOcrSideRecognizer._extract_hp`, `RecognitionPipeline`, `BattleSessionStore.update_player_hp`, `test_battle_session_store.py` | status panel OCR 结果未可靠转成 `player_hp_current/max`；`player_hp_text` ROI 未真正 OCR；真实 OCR 端到端仍需测试 |
| 技能 4 招 + PP | Store 可写入技能和 PP，并修复英文 moves index；真实 OCR 识别仍不稳 | 50% | `MoveListRecognizer`, `ChineseOcrSideRecognizer._recognize_move_list`, `BattleSessionStore.set_player_moves`, `test_battle_session_store.py` | `MoveListRecognizer` 仍使用宝可梦 `NameMatcher` 匹配技能；move slot OCR 断裂；我方技能和对方 revealed moves 语义混乱 |
| 状态异常识别 | Store 可从 ROI payload 写入 BattleSession；真实 OCR → payload 仍需验收 | 62% | `ChineseOcrSideRecognizer._extract_status_abnormality`, `BattleStateStore._parse_status`, `BattleSessionStore.update_statuses_from_roi_payloads`, `BattleSessionStore.append_log_batch` | 状态 LOG 可经旧 `move_log` 同步到 `BattleSession.log`；仍需要标准状态枚举映射和真实 OCR 端到端测试 |
| 对战 LOG 自动生成 | 旧 `BattleStateStore.move_log` 已同步到 `BattleSession.log`，并补去重/API start 验收 | 55% | `BattleStateStore._make_log`, `BattleSessionStore.append_log_batch`, `RecognizeScheduler`, `test_recognition_api.py`, `test_battle_session_store.py` | 已覆盖 start 首帧 LOG；还需要连续识别、final_result、前端复制/滚动的 API/UI 端到端测试 |
| 结算清数据但保留 LOG | Store 级实现为“结算 freeze；下一局 TEAM_SELECT 清战斗数据并保留 LOG” | 58% | `BattleSessionStore.sync_from_recognition`, `BattleSessionStore.append_log_batch`, `test_battle_session_store.py` | 行为已固定为下一局清且 LOG 保留；仍需 API/UI 端到端测试；旧 `BattleStateStore` final_result reset 语义后续应收敛 |
| 手动修正 API | PRD 路径 `/api/battle-session/manual-override` 已实现并同步 BattleSession active；旧 recognition override 仍保留 | 60% | `POST /api/battle-session/manual-override`, `POST /api/recognition/override`, `test_battle_session_api.py`, `test_manual_override_api.py` | 已支持当前 active 修正；仍不支持 team slot/item/HP/move/status 的结构化修正 |
| `/api/battle-session/status` | 已实现，返回当前 BattleSession | 100% | `GET /api/battle-session/status`, `backend/app/api/battle.py`, `test_battle_session_api.py` | 可作为 PRD 兼容路径；后续前端可逐步从 recognition enriched payload 收敛到该路径 |
| `/api/recognition/current` 返回 battle_session | 字段存在，start/manual override 已同步首帧/修正结果 | 65% | `backend/app/api/recognition.py::_enrich_state`, `test_recognition_api.py`, `test_manual_override_api.py` | 仍需补更完整 API fixture：队伍、HP、技能、LOG、结算状态的端到端断言 |
| OBS Virtual Camera 优先 | 相对完成 | 75% | `VideoSourceService`, `api/video.py`, `CaptureSessionService` | 依赖设备 label；不是 OBS WebSocket 集成；非 Windows label 能力有限 |
| Windows Release 流水线 | 基本存在 | 70% | `.github/workflows/release-windows.yml`, `release/scripts/*` | 本地默认 pytest 入口不稳；Windows 真实设备兼容仍靠实测 |
| 前端 5 列布局 | 真实接入 | 85% | `frontend/app/page.tsx`, `globals.css .main-content-5col` | 响应式不足；出战/队伍使用内联组件，未复用已测组件 |
| 前端 LOG 滚动/复制 | 代码存在但无测试 | 70% | `page.tsx` battle log 区域，`.battle-log-list` | 无复制成功/失败反馈；无 clipboard 测试；顺序与滚动体验需明确 |
| 速度比较 / 伤害计算 | 简化函数存在，但真实首页未接入 | 35% | `frontend/lib/damage-calc.ts`, `BattleInfoPanel`, `MovePanel` | `@smogon/calc` 完整集成是占位；首页没用 `BattleInfoPanel/MovePanel`；属性克制不自动计算 |

---

## 3.4. 当前代码中最严重的产品风险

### P0 风险：BattleSession 不是可信数据源

PRD 的核心设计是“每局一个 `BattleSession` JSON，UI 始终从它读取”。当前实现不满足这个目标：

- `BattleSessionStore` 已补第一批生命周期测试，但仍需要覆盖更多 API 和真实 OCR 端到端路径
- `BattleStateStore` 与 `BattleSessionStore` 双轨并存
- `/api/recognition/session/start` 已同步 `BattleSessionStore`
- `BattleSession.log` 没有和自动生成的 `BattleStateStore.move_log` 打通
- manual override 已同步当前 BattleSession active，但还没有 PRD 里的 `/api/battle-session/manual-override` 路径和完整 team slot 修正能力
- final_result 已有“结算 freeze；下一局 TEAM_SELECT 新开 session 并保留 LOG”的 store 级测试，仍需 API/UI 端到端验收

**产品影响**：前端可能显示一个看似完整的 `battle_session` 区域，但核心数据为空、滞后或与旧 state 不一致。

### P0 风险：HP / 技能 / 状态链路不是端到端可用

当前有很多局部能力：OCR 能识别 HP 文本、move_list 能解析文本、状态关键词能提取。但局部能力没有可靠汇总到最终 BattleSession：

- HP：`player_status_panel.hp_text` 没有稳定变成 `player_hp_current/max`
- 技能：`MoveListRecognizer` 使用宝可梦名称 matcher 匹配技能；字段命名错误；move slot 与整体 move_list 逻辑混乱
- 状态：识别后未写入 `BattleMon.status`

**产品影响**：真实画面下 UI 很可能只显示壳，关键战斗信息缺失。

### P0 风险：测试给了错误安全感

现有测试的问题不是数量少，而是验收方向偏离：

- 很多测试测的是未接入首页的组件
- 很多后端测试测的是 synthetic payload 或 ROI 壳，不测完整链路
- 没有 BattleSessionStore 生命周期测试
- 没有真实 `HomePage + battle_session fixture` 测试

**产品影响**：测试全绿不代表 PRD 成立。

---

## 3.5. 必补验收测试清单

在继续堆功能前，必须先补以下测试，避免继续“看起来实现了”。

### P0：BattleSessionStore 生命周期测试

新增测试文件建议：`backend/tests/test_battle_session_store.py`

必须覆盖：

1. `TEAM_SELECT` 填充我方 6 只：名称 / 道具 / 性别 / slot 顺序 / base_stats
2. `TEAM_SELECT` 填充对方 6 只：名称 / slot 顺序 / base_stats 或明确标注暂不支持
3. 空洞 slot 不压缩：slot2 有值时必须保持在 index 1
4. `BATTLE` 阶段写入 active Pokémon
5. `BATTLE` 阶段写入我方 `current_hp/max_hp/current_hp_percent`
6. `BATTLE` 阶段写入对方 `hp_percent`
7. `BATTLE` 阶段写入 4 个技能：name/type/category/base_power/PP/description
8. 状态异常写入 active mon `status`
9. `FINAL_RESULT` 行为：按产品决定立即清数据还是下一局清，但必须测试固定
10. LOG 保留：结算后和下一局开始后旧 LOG 仍可复制/查看

### P0：Recognition API 端到端测试

新增/扩展：`backend/tests/test_recognition_battle_session_api.py`

必须覆盖：

1. `/api/recognition/session/start` 返回的 `current_state.battle_session` 已同步首帧结果
2. `/api/recognition/current` 返回完整 `battle_session`，不是空壳
3. `manual override` 会同步更新 `BattleSession` 的 active/team，而不只是 `_last_result`
4. 明确最终 API 路径：
   - 如果采用 PRD：实现并测试 `/api/battle-session/status` 与 `/api/battle-session/manual-override`
   - 如果采用现有路径：更新 PRD，并测试 `GET /api/battle/session` 与 `/api/recognition/override`

### P0：前端真实首页验收测试

新增/扩展：`frontend/tests/home-battle-session.test.tsx`

必须覆盖：

1. `HomePage` 从 `battle_session.player_team/opponent_team` 渲染队伍，而不是从 `roi_payloads`
2. `player_active` 显示名称、HP、base_stats、状态
3. 4 个技能显示名称、属性、威力、PP、tooltip
4. `battle_session.log` 显示在中心 LOG 区
5. 点击“复制全部”调用 `navigator.clipboard.writeText`
6. `is_over=true` 时 LOG 仍保留，战斗数据按 PRD 规则清空/隐藏

### P1：真实 OCR 样本端到端测试

在已有 `real_ocr` 样本基础上补：

1. 战斗样本：`RecognitionPipeline.recognize()` 后断言 `player_hp_current/max`，而不是只断言 `roi_payloads.player_status_panel.hp_text`
2. 战斗样本：断言 4 个技能进入 `BattleSession.player_active.moves`
3. 选人样本：断言 6 个我方 slot 进入 `BattleSession.player_team`
4. 对方样本：若缩略图匹配暂不做，明确跳过并在 PRD 标注“未实现”

---

## 3.6. 下一阶段修复路线（建议）

### Phase 1：先统一数据源，不改 UI 大功能

目标：让 `BattleSession` 成为真正可信对象。

任务：

1. 给 `BattleSessionStore` 补 P0 生命周期测试
2. 修复 `sync_from_recognition()`：保持 slot 顺序，不压缩空洞 slot
3. `/api/recognition/session/start` 首帧同步 `BattleSessionStore`
4. 打通 `BattleStateStore.move_log` → `BattleSession.log`，或废弃旧 log 源，统一由 BattleSession 生成
5. 明确 final_result 行为并测试：推荐“结算时 freeze + 保留 LOG；下一局 TEAM_SELECT 时清战斗数据并继续保留 LOG”
6. manual override 改为同步 BattleSession

### Phase 2：修 HP / 技能 / 状态端到端链路

目标：不是让 ROI payload 好看，而是让 `battle_session.player_active` 真实可用。

任务：

1. status panel OCR 结果统一转成 `player_hp_current/max` 和 `opponent_hp_percent`
2. 废弃 `MoveListRecognizer` 中用宝可梦 `NameMatcher` 匹配技能的实现，改为技能索引/别名/模糊匹配
3. 统一我方 move list 与对方 revealed moves 的字段语义
4. 状态异常写入 `BattleMon.status`
5. 补真实样本端到端测试

### Phase 3：前端从真实 BattleSession 渲染，删除/合并未接入组件

目标：避免“组件有测试但产品不用”。

任务：

1. `RecognitionState` 类型补 `battle_session`
2. 去掉 `(state as any)?.battle_session`
3. 决定复用 `BattleInfoPanel/TeamRosterPanel/MovePanel`，或删除/合并到首页内联组件
4. 给真实 `HomePage + battle_session fixture` 补验收测试
5. LOG copy 加成功/失败反馈与测试

---

## 3.7. 当前应视为“已完成”的能力

这些能力可以继续保留为已完成/基本完成：

- 本地前后端项目结构
- FastAPI health / recognition / video source 基础 API
- Next.js 首页基础布局
- 5 列对战界面框架
- 视频源列表、选择、OBS Virtual Camera 优先排序（后端）
- CaptureSession 基础读帧和 frame variants
- DebugInfoPanel 展示 ROI / phase evidence / frame variants / preview
- OCR 局部 recognizer：HP 文本、状态关键词、move_list 文本有一定基础
- Windows portable release 脚本和 GitHub Actions 基础框架

## 3.8. 当前不应再标为“已完成”的能力

以下能力只能标为“部分实现/待修复”，不能作为已交付能力宣传：

- BattleSession 作为唯一可信数据源
- 选人阶段双方 12 只可靠进入 BattleSession
- 对方队伍缩略图匹配
- HP OCR 端到端写入 BattleSession
- 4 技能 + PP 端到端写入 BattleSession
- 状态异常端到端写入 BattleSession
- 自动 LOG 进入 BattleSession 并结算保留
- `/api/battle-session/status`
- `/api/battle-session/manual-override`
- 手动修正 UI
- 完整 `@smogon/calc` 伤害计算
- 前端所有已测组件均已真实接入首页

---

## 4. 页面布局

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [视频源选择] [调试] [清除数据]                                    标题栏    │
├──────────┬────────────────────┬──────────────────┬────────────────────┬──────┤
│ 我方队伍  │ 我方出战宝可梦      │   对战记录        │ 对方出战宝可梦      │ 对方 │
│ (6只)    │                    │  (可滑动拷贝)      │                    │ 队伍 │
│          │ 名称 Lv.50         │                   │                    │ (6只)│
│ 名字     │ ♂/♀ 道具           │ ⏱ 第 1 回合      │                    │      │
│ 道具/性别 │                    │ 🏃 我方派出振翼发  │                    │      │
│          │ ████░░ 145/167 87% │ ⚔️ 振翼发 使用了  │                    │      │
│          │                    │    月亮之力       │                    │      │
│          │ HP 物攻 物防 特攻   │                   │                    │      │
│          │ 55  90   80  50    │                   │                    │      │
│          │ 特防 速度          │                   │                    │      │
│          │ 105  96           │                   │                    │      │
│          │                    │                   │                    │      │
│          │ 招式               │                   │                    │      │
│          │ ⚔️ 月亮之力 妖 95  │                   │                    │      │
│          │   PP 8/15          │                   │                    │      │
│          │ 🔮 暗影球  鬼 80   │                   │                    │      │
│          │   PP 10/15         │                   │                    │      │
│          │ ⚔️ 喷射火焰 火 90  │                   │                    │      │
│          │   PP 10/15         │                   │                    │      │
│          │ ✦ 替身     普 --   │                   │                    │      │
│          │   PP 10/10         │                   │                    │      │
├──────────┴────────────────────┴──────────────────┴────────────────────┴──────┤
│ 底部：输入源信息                                                    [复制LOG] │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. API 扩展

### 新增 `POST /api/battle-session/status`
返回当前 BattleSession 完整 JSON 对象（包含双方全队伍+出战宝可梦详细数据）。

### 扩展 `GET /api/recognition/current`
`battle_state` 字段扩展为包含完整的 `battle_session` 对象。

---

## 6. Implementation Phases

### Phase 3（当前迭代）
1. **BattleSessionStore** — 后端对战数据模型
2. **选人阶段队伍填充修复** — TeamSelectRecognizer → battle_session.player_team
3. **HP 识别修复** — 确保 HP 数值正确写入模型
4. **技能识别同步** — move_slot → 当前出战宝可梦的 moves 列表
5. **PokeCard 能力值+技能详情** — 前端 UI
6. **LOG 可滑动+拷贝** — 前端
7. **结算不清除 LOG** — 后端逻辑调整
8. **对话框 OCR 记录到 LOG** — 可选

### Phase 4+
- 搜索体验优化
- 伤害计算器
- 属性克制展示
- 更多对战信息展示
