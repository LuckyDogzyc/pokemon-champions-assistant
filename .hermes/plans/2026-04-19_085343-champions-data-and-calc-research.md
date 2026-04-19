# Pokemon Champions 数据源与 Damage Calculator 调研

**时间：** 2026-04-19 08:53:43

## 已检查来源
- Serebii
  - https://www.serebii.net/pokemonchampions/pokemon.shtml
  - https://www.serebii.net/pokedex-champions/
  - https://www.serebii.net/attackdex-champions/
- Pokemon Zone
  - https://www.pokemon-zone.com/champions/
- Pikalytics
  - https://www.pikalytics.com/champions
  - https://www.pikalytics.com/calc
- Pokebase
  - https://pokebase.app/pokemon-champions/team-builder?team=69e06cdcb72a78158e1e2491
  - https://pokebase.app/pokemon-champions/damage-calc
  - https://pokebase.app/pokemon-champions/pokemon/incineroar
- 相邻可复用方案
  - `@smogon/calc`
  - `@pkmn/data`
  - `@pkmn/dex`
  - Pokémon Showdown 公共 dex 数据

## 关键结论

### 1. 最 API-friendly 的 Champions 数据源：Pikalytics
已确认存在可直接请求的 JSON 接口：
- 列表：`https://www.pikalytics.com/api/l/2026-03/championstournaments-1760`
- 单宝可梦详情：`https://www.pikalytics.com/api/p/2026-03/championstournaments-1760/incineroar`

价值：
- 可拿热门宝可梦、热门招式、热门特性、热门道具、队友共现、队伍样本
- 很适合做 meta 数据层与推荐层

风险：
- 私有未文档化接口
- 路径里带版本/赛季参数，后续可能变化

### 2. 最适合抓自建数据库页面源：Pokebase
已确认：
- 有 Team Builder
- 有 Champions Damage Calc
- 有单宝可梦详情页
- 页面里可解析出结构化 payload

价值：
- 适合抓 roster / forms / stats / 页面详情
- 也适合做手工校验与参考

风险：
- 暂未发现稳定公开 JSON API
- 更像抓取源，不像正式 API

### 3. Serebii 适合补全与交叉校验
已确认 Champions 相关索引页可访问。

价值：
- 可补全 pokedex / attackdex 条目
- 适合作为校验源

风险：
- 传统 HTML 抓取更脆
- 不建议作为唯一主数据源

### 4. Pokemon Zone 不建议作为自动化主依赖
当前实测会遭遇 Cloudflare/403 验证。

结论：
- 适合人工参考
- 不适合自动化项目的核心依赖

## Damage Calculator 方案结论

### 最推荐：自建可调用后端，核心复用 `@smogon/calc`
已确认：
- `@smogon/calc` 为 MIT License
- 工程成熟
- 适合作为后端可调用 damage calc 核心

推荐组合：
1. `@smogon/calc` 负责伤害计算
2. `@pkmn/data` / `@pkmn/dex` / Showdown 数据负责基础 dex / moves / items / typings
3. Pikalytics 负责 Champions meta / 热门队伍 / 热门配置
4. Pokebase + Serebii 负责 Champions 特定补全与校验

## 推荐工程策略

### 方案 A（推荐）
- **基础数据库层**：Showdown / `@pkmn/*`
- **伤害计算层**：`@smogon/calc`
- **Champions 环境层**：Pikalytics API
- **Champions 补全层**：Pokebase + Serebii

优点：
- 核心计算可控
- 授权最清晰的部分放在核心层
- 第三方网站只做补数据和校验

## 对当前项目的直接建议
1. 不要把别人的网页 damage calc 当未来核心依赖
2. 优先尽快验证：`@smogon/calc` 是否能直接承接 Champions 规则与形态
3. 并行做一个 `champions-data-adapter`：
   - 拉 Pikalytics JSON
   - 抓 Pokebase roster/details
   - 用 Serebii 做校验
4. 把结果统一落到本项目自己的规范化 JSON 数据层

## 下一步可落地任务
1. 新增一条数据线：验证 `@smogon/calc` + Showdown 数据是否覆盖 Champions 主要形态
2. 新增一个数据抓取脚本：先抓 Pikalytics champions 列表 JSON 并缓存
3. 设计本项目的规范化 schema：
   - pokemon
   - forms
   - moves
   - items
   - abilities
   - format/rule-set
   - meta usage
4. 再把这些接入前端查询/推荐/未来伤害计算 API
