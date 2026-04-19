# Pokemon Champions Assistant 项目 Prime 与下一步建议

> **For Hermes:** 本轮只做 prime / planning，不执行实现。

**Goal:** 对整个项目做一次全局 prime，确认当前仓库状态、已完成能力、主要缺口，并给出接下来最值得推进的工作顺序。

**Architecture:** 项目当前是本地优先的 Web App：前端 Next.js/React，后端 FastAPI，本地视频采集与识别链路负责抓帧、阶段判断、ROI 裁剪、OCR 与资料联动；Windows 发行目标是面向终端用户的本地安装包。

**Tech Stack:** Next.js、React、FastAPI、OpenCV、ffmpeg、PaddleOCR（规划/适配中）、本地 JSON 数据层、Windows 打包发布链路。

---

## 1. Prime 结果

### 1.1 Git / 工作区状态
- 分支：`main`
- 同步状态：`main...origin/main`，当前工作区干净
- 最近提交集中在两条主线：
  1. **Windows 视频采集稳定性修复**
     - dshow 重试、避免 OpenCV fallback、设备枚举与 active capture 解耦
     - 最新提交已把 **OBS Virtual Camera 路由到 opencv backend**
  2. **识别结果结构化增强**
     - 状态面板 OCR（HP / 百分比 / 等级 / 异常）
     - debug panel 联动展示
     - Champions 数据抓取与规范化数据文件入库

### 1.2 仓库结构快照
- `backend/`
  - FastAPI API、capture session、phase / recognition pipeline、ROI / recognizer、tests
- `frontend/`
  - Next.js 页面、输入源面板、debug 面板、hooks、tests
- `data/`
  - champions 规范化数据与备份
- `.hermes/plans/`
  - 已有“下一阶段 phase-first 抓帧”和“Champions 数据与伤害计算调研”计划

### 1.3 已落地能力
1. **本地 Web App 基本形态成立**
   - 符合 PRD 里的“第二窗口 + 本地识别服务”方向
2. **Windows 输入源发现和基础抓帧能力已打通**
   - 能枚举 OBS Virtual Camera 与实体设备
   - OBS Virtual Camera 已改走 `opencv`，比反复 dshow reopen 更稳
3. **识别链路已具备 phase-first 雏形**
   - 已有 phase / recognition / layout anchor / ROI 相关代码
4. **战斗状态面板 OCR 有了结构化输出**
   - player/opponent status panel 已能输出更细字段
5. **项目已有初步 Champions 数据层**
   - 已有数据抓取脚本、数据文件与测试
6. **测试基础不错**
   - 最近一次验证：backend `93 passed`，frontend `11 passed`

### 1.4 与 PRD 对照后的主要缺口
按 PRD 的 MVP 定义，当前最关键缺口仍在以下几块：

#### A. 真实可用的视频识别稳定性还不够
- OBS Virtual Camera 已经更稳，但**实体采集卡（如 Hagibis）持续抓帧仍不稳**
- dshow 物理设备当前仍偏“单帧 reopen”思路，容易出现“抓到一帧后失败”
- 这会直接影响 MVP Feature 1 的可靠性

#### B. phase-first 还停留在“基础框架 + 局部结构化”
- 已有方向，但还没有真正形成：
  - 低成本阶段判定
  - 高质量 ROI 定向裁切
  - 基于真实样本回归的 phase/layout 状态机
- 当前距离“直播中持续可用”还有一段距离

#### C. “资料查询 / 克制查询”虽有数据基础，但业务闭环还没打透
- 规范化数据在积累
- 但从**识别结果 → 标准名匹配 → 资料卡 → 克制信息**的完整前后端闭环，还需要进一步明确和打磨

#### D. MVP 明确要求的“手动修正能力”还没有成为清晰产品能力
- PRD 把手动校正列为 MVP 范围
- 这对直播可用性非常关键，因为识别初期必然有误差

#### E. Windows 终端用户交付形态还没进入收口阶段
- 当前已有本地 Web App 形态
- 但离“普通用户双击安装、自动启动本地服务并打开浏览器”还有发行工程工作

---

## 2. 当前阶段最合理的项目判断

### 结论一句话
**项目已经越过“纯脚手架/纯规划期”，进入“把 MVP 核心链路打成稳定可演示版本”的阶段。**

也就是说，接下来不该继续大面积发散做很多新功能，而应该优先把下面这条主链路打通：

> **稳定输入源 → 稳定抓帧 → phase-first 识别 → 标准化结果 → 资料/克制展示 → 允许人工修正**

这条主链路一旦稳定，后面的伤害计算、推荐、完整数据库，都会变成“锦上添花”；如果这条主链路不稳，后面做再多功能都很难真正直播可用。

---

## 3. 推荐的下一步优先级（按顺序）

## P0：把视频采集稳定性收口到“可持续跑”

**为什么是第一优先级：**
没有稳定输入，后面的识别和资料链路都只是静态演示。

### 建议目标
1. 明确两类输入源策略：
   - **虚拟源（OBS Virtual Camera）**：默认优先、持续 `opencv` reader
   - **实体采集卡（Hagibis 等）**：补齐更稳的持续采集策略，而不是频繁 reopen
2. 为 capture session 增加：
   - 串行锁 / in-flight 保护
   - 更清晰的 capture diagnostics
   - 必要时记录首个成功模式（分辨率/帧率）供后续复用
3. 验证目标不是“偶尔抓到一帧”，而是：
   - 连续运行几分钟仍能稳定刷新
   - OBS 开着时仍可工作

### 关键文件
- `backend/app/services/capture_session.py`
- `backend/app/services/video_source_service.py`
- `backend/app/api/video.py`
- `backend/tests/test_capture_session.py`
- `backend/tests/test_video_sources_api.py`

### 验收标准
- OBS Virtual Camera 路径稳定
- Hagibis 路径至少有一条稳定方案（优先兼容 OBS 打开场景）
- debug panel 能清楚显示 capture method / backend / error diagnostics

---

## P1：把 phase-first 识别从“思路”推进到“真实样本驱动”

**为什么排第二：**
稳定抓帧后，最有价值的就是让每一帧的识别成本更低、准确率更高。

### 建议目标
1. 落实双层帧概念：
   - `phase_frame`：低成本阶段判断
   - `roi_source_frame`：高质量 ROI 裁切来源
2. 先收敛最小状态机：
   - `team_select_default`
   - `battle_default`
   - `battle_move_menu_open`
3. 用真实截图 fixture 驱动：
   - phase detector 回归
   - layout anchors 校准
   - ROI 裁切回归

### 关键文件
- `backend/app/services/phase_detector.py`
- `backend/app/services/layout_anchors.py`
- `backend/app/services/recognition_pipeline.py`
- `backend/app/services/roi_capture.py`
- `backend/tests/test_phase_detector_real_samples.py`（建议新增）
- `backend/tests/fixtures/frames/...`（建议新增）

### 验收标准
- 至少两大类状态在真实样本上可稳定判定
- 不同阶段触发不同 ROI 集合
- ROI 截图足够清晰，可直接支撑 OCR/模板匹配

---

## P2：补齐“识别结果 → 资料/克制”完整闭环

**为什么排第三：**
这是 MVP 对用户直接可见的价值层。

### 建议目标
1. 标准化识别结果结构
   - 当前名字 / HP / 状态等字段继续统一 schema
2. 名称模糊匹配与别名归一化
   - OCR 文本 → 标准 species 名
3. 前后端联动资料卡
   - 属性
   - 基础种族值
   - 常见特性 / 简述
4. 克制查询面板接到当前识别对象
   - 单属性 / 双属性攻击与防守关系

### 关键文件
- `backend/app/services/recognizers/chinese_ocr_recognizer.py`
- `backend/app/services/recognition_pipeline.py`
- `backend/app/schemas/recognition.py`
- `backend/app/api/recognition.py`
- `frontend/types/api.ts`
- `frontend/components/debug-info-panel.tsx`
- 前端资料卡 / 克制面板相关组件

### 验收标准
- 识别到场上宝可梦后，资料卡和克制信息自动更新
- OCR 误差在模糊匹配下仍能回到正确标准名

---

## P3：把“人工修正”正式做成 MVP 能力

**为什么重要：**
这是直播场景的兜底能力，没有它就很难叫“可靠可用”。

### 建议目标
1. 前端提供手动修正入口
   - 当前我方 / 对方宝可梦名称修正
2. 修正结果即时回灌
   - 资料卡
   - 克制信息
   - 当前会话状态
3. 明确“自动识别值”和“人工覆盖值”的优先级关系

### 验收标准
- 识别错时，主播可在几秒内手动修正并继续使用
- 修正状态可清晰可见，不会和自动结果打架

---

## P4：Windows 终端交付与安装体验收口

**为什么放到后面但不能忘：**
前面是“能用”，这一步是“普通用户真能装真能跑”。

### 建议目标
1. 固化 Windows release 流程
   - 后端服务
   - 前端静态资源或本地运行方式
   - ffmpeg / 依赖打包策略
2. 生成 `.exe` 安装包 / setup.exe
3. 安装后自动启动本地 app 并打开 dashboard
4. 做最小 smoke test

### 关键文件/方向
- GitHub Actions release workflow
- Windows packaging 脚本
- README / 安装说明

---

## 4. 建议暂缓的事

以下内容有价值，但建议在 P0-P3 主链路稳定前，不要抢优先级：

1. **完整伤害计算器接入**
   - 值得做，但现在更像 P2/P3 后的增强层
2. **选人阶段头像/道具全量识别**
   - 可以作为 phase-first 后的延伸，不宜先铺太大
3. **更复杂的 AI 决策与推荐系统**
   - 依赖前面数据链路和识别链路先稳定
4. **花哨 UI 重构**
   - 当前阶段稳定性和清晰度比视觉升级更重要

---

## 5. 我建议你现在立刻做的“下一步”

如果只选一个最有价值动作，我建议：

### 选项 A（最推荐）
**开一个新计划：`稳定 Hagibis / 物理采集卡持续抓帧`**
- 目标是解决“抓到一帧后失败”
- 这是当前最明显、最阻塞实际使用的问题

### 选项 B
**开一个新计划：`phase-first 双层帧 + 真实截图 fixtures`**
- 适合在输入源基本稳定后立刻推进
- 会显著影响识别质量和后续扩展效率

### 选项 C
**开一个新计划：`识别结果联动资料卡与克制信息闭环`**
- 适合你想先把“可展示价值”拉满时推进

---

## 6. 推荐执行顺序（最终版）

1. **先修采集稳定性（尤其 Hagibis / 物理采集卡）**
2. **再做 phase-first 双层帧与真实样本回归**
3. **再打通资料卡 / 克制信息闭环**
4. **再补人工修正**
5. **最后收口 Windows 安装包与发行体验**

---

## 7. 验证清单

在进入下一轮 execute 前，建议每次都围绕这 5 个问题验证：
- [ ] 输入源是否稳定连续刷新？
- [ ] 当前阶段是否判对？
- [ ] ROI 是否清晰到足以 OCR / 匹配？
- [ ] 资料卡 / 克制是否跟着识别结果自动更新？
- [ ] 识别失败时，人工修正能否兜底？

---

## 8. 结论

**这个项目现在最需要的不是再扩很多新功能，而是把 MVP 主链路做稳。**

对当前仓库而言，下一步最应该干的是：

> **优先解决物理采集卡持续抓帧稳定性，然后推进真实样本驱动的 phase-first 识别。**

只要这两步做扎实，后面的资料查询、克制展示、人工修正、Windows 安装包都会顺很多。
