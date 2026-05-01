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
