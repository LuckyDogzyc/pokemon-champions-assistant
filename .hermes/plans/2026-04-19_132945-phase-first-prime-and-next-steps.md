# Phase-first 主线 Prime 与下一步建议

> **For Hermes:** 当前阶段只做 prime / plan，不直接改业务代码；实现时遵守 TDD，先写失败测试再补最小实现。

**Goal:** 基于已完成的 OBS Virtual Camera-only 收口，对 Pokémon Champions Assistant 的下一阶段（phase-first 双层识别链路）做一次只读 prime，并给出最合理的执行顺序。

**Architecture:** 当前项目已经具备 OBS-first 输入推荐、1 秒抓帧频率、基础 phase detector、状态栏/技能列表结构化 ROI 输出。下一阶段不应再扩散到 Hagibis 或复杂图像识别，而应先把 capture → pipeline 的双帧契约钉牢：低成本 `phase_frame` 用于阶段判断，高质量 `roi_source_frame` 用于局部 ROI 裁切与后续 OCR / 图像识别。

**Tech Stack:** FastAPI, Pydantic, OpenCV, Next.js/React, pytest, jest

---

## 1. Prime 结论

### 1.1 已经成立的基线
1. **视频输入主线已经收口到 OBS Virtual Camera**
   - `backend/app/api/video.py`
   - `frontend/components/video-source-panel.tsx`
   - 后端推荐顺序已经是：
     1. label 包含 `obs virtual camera`
     2. `device_kind == 'virtual'`
     3. `is_capture_card_candidate`
   - 前端已明确展示“推荐输入”和 OBS 优先提示。

2. **后端抓帧默认已是 1 秒，但前端实际轮询仍有一处 3 秒残留**
   - `backend/app/core/settings.py:16` → `frame_interval_seconds = 1`
   - `frontend/components/phase-status-panel.tsx:10` → 文案写的是 `默认抓帧频率：每 1 秒 1 帧`
   - `frontend/lib/hooks.ts:37` → `useRecognitionPolling(intervalMs = 3000)`
   - `frontend/app/page.tsx:54` → 当前首页直接调用 `useRecognitionPolling()`，没有显式传入 `1000`
   - 结论：**后端基线已是 1 秒，但前端当前实际 polling 默认值仍是 3 秒；这是一个已识别的不一致点。**

3. **当前真正缺的不是轮询频率，而是帧语义分层**
   - `backend/app/services/recognition_pipeline.py` 仍只接受单一 `frame`
   - `build_roi_payloads()` 虽然已经给 payload 打上 `phase-frame` / `roi-source-frame` source 标签，但底层没有真正的双帧入口
   - 这意味着当前“phase-first”仍然主要停留在命名层，而不是数据契约层

4. **阶段检测器已经适合接低成本 phase_frame**
   - `backend/app/services/phase_detector.py`
   - 已能依赖 `ocr_texts` + `layout_variant_hint` 做轻量判断
   - 非常适合后续接“模糊/降采样/低成本截图”输入

5. **ROI 富化与结构化输出已经具备可复用基础**
   - `backend/app/services/recognition_pipeline.py`
   - 现有 `move_list` / `player_status_panel` / `opponent_status_panel` 已走命名 ROI 富化
   - 对下一步“战斗阶段：左下我方、右上敌方、右下技能”非常贴近

### 1.2 与你最新产品想法的对齐情况

#### 已对齐
- 默认 OBS Virtual Camera：**已对齐**
- 1 秒频率：**已对齐**
- 先判状态/阶段，再进入定向识别：**方向已对齐，但契约未完成**
- 战斗阶段识别双方状态+我方技能：**ROI 基础已基本具备**

#### 尚未真正落地
- `phase_frame` 与 `roi_source_frame` 的真实双帧输入结构
- 选人阶段“双方宝可梦形象 + 道具”识别链路
- 战斗阶段 ROI 的“高质量局部截图”和来源可见性
- 真实样本驱动回归骨架

---

## 2. 当前最关键判断

### 判断 A：不要再把时间花在输入源路线争论上
OBS-only 已经是正确收口，当前不该再回头优化 Hagibis 直连路线。

### 判断 B：不要先上头像识别/道具识别
如果现在直接做 team select 图像识别，后面大概率会因为 frame contract、API 调试结构、fixture 目录不稳定而返工。

### 判断 C：当前第一优先级必须是 FrameVariants 契约
这是后续所有阶段化识别的地基：
- phase detector 该吃什么图
- ROI crop 该从哪张图裁
- 调试面板该显示哪张图的来源
- 样本回归该固定哪类输入

---

## 3. 下一步应该做什么

### P0：先完成 `phase1`
**Task 1: 为 pipeline 定义兼容式 FrameVariants 契约（先写失败测试）**

这是现在最应该做的事，而且必须先做。

**原因：**
- 它是 phase-first 的真正开始点
- 它能让后续 phase2/3/4 都变成顺推，而不是反复返工
- 它和你要的“先低成本判状态，再对 ROI 做高清截图”完全一致

**这一步的最小产物：**
- 新增 `backend/app/services/frame_variants.py`
- `RecognitionPipeline.recognize()` 兼容：
  - 旧单帧 dict 输入
  - 新双帧 payload 输入
- phase detector 显式读取 `phase_frame`
- ROI enrich / named ROI / side recognizer 显式读取 `roi_source_frame`

**这一步的测试重点：**
- 旧单帧仍兼容
- 双帧输入时不同组件拿到的不是同一帧

---

### P1：紧接着做 `phase2`
**Task 2: 升级 recognition API / 调试输出，显式展示 phase_frame 与 roi_source_frame 来源**

**原因：**
- 如果调试层看不到 frame source，后续你采真实样本时会“盲飞”
- 一旦进入 team select / battle 的真实校准阶段，没有来源可见性会非常痛苦

**这一步的目标：**
- `phase_snapshot` 里能明确看到 source frame
- `roi_payloads` 继续保留 `source`
- 必要时在 API 顶层新增 `frame_variants` 调试字段

---

### P2：然后做 `phase3`
**Task 3: 在 capture_session 侧生成首版双帧 payload**

**原因：**
- phase1/2 把契约与可见性钉住后，capture 层再补输出最稳
- 第一轮不用做复杂图像优化，只要先把结构生产出来

**建议第一版策略：**
- `roi_source_frame` 先复用当前高质量原图语义
- `phase_frame` 第一轮可以仍基于原图，但加 variant 元信息
- 第二轮再把它变成真正的降采样/模糊/低成本帧

这比一开始就做复杂缩放/压缩稳得多。

---

### P3：最后做 `phase4`
**Task 4: 补真实样本 fixture 目录与 phase detector 回归骨架**

**原因：**
- 样本和回归要建立在稳定契约之上
- 到这一步再开始收集 team_select / battle 样本，返工会少很多

**建议目录结构：**
- `backend/tests/fixtures/frames/team_select/`
- `backend/tests/fixtures/frames/battle/`

**每组样本至少约定：**
- 原图
- phase_frame 对应产物/描述
- annotation json
- 期望 phase
- 可选 OCR 文本列表
- layout variant

---

## 4. 面向产品目标的后续路线图（在 phase1-4 之后）

### 阶段 A：选人阶段识别
当 FrameVariants 稳定后，再进入：
- 识别双方队伍卡位/头像 ROI
- 先做样本驱动的宝可梦形象识别
- 道具识别先作为“可选增强”，不要与头像识别绑死

**建议顺序：**
1. 先识别双方队伍中的宝可梦是谁
2. 再评估道具是否值得在 MVP 先做

### 阶段 B：战斗阶段识别闭环
- 左下：我方状态面板
- 右上：敌方状态面板
- 右下：技能列表
- 再把识别结果接到资料卡 / 克制逻辑

### 阶段 C：资料卡/克制闭环
- 识别结果 → 名称归一化
- 名称归一化 → 本地资料
- 当前对战对象 → 克制信息
- 最后补人工修正

---

## 5. 建议的执行顺序（最终版）

1. **先做 phase1**：FrameVariants 契约 + failing tests
2. **再做 phase2**：API / 调试输出可见性
3. **然后做 phase3**：capture_session 产出首版双帧 payload
4. **最后做 phase4**：真实样本 fixture 与回归骨架
5. **随后才进入**：
   - team select 图像识别
   - battle ROI 高清识别增强
   - 资料卡 / 克制闭环
   - 人工修正
   - Windows 打包收口

---

## 6. 本轮不建议做的事

- 不继续修 Hagibis 直连路径
- 不先做复杂模型识别（CLIP / 大模型图像分类）
- 不先改前端大 UI
- 不先做 Windows 打包
- 不先做全量 battle intelligence

这些都应该排在 FrameVariants 契约之后。

---

## 7. 验收口径

本轮 prime 完成后，正确的下一阶段定义应该是：

> **不是“去做更多识别功能”，而是“先把 phase-first 的双帧数据契约、调试可见性和 capture 输出打通”。**

如果这三件事没打通，后面做选人头像识别、道具识别、战斗阶段高清 ROI，都会反复返工。

---

## 8. 当前仓库状态备注

- 分支：`main...origin/main`
- 当前未提交内容：
  - `.hermes/plans/2026-04-19_131009-phase-first-frame-variants-execution.md`
  - `.hermes/plans/2026-04-19_132945-phase-first-prime-and-next-steps.md`
- 当前 session task list：
  - `phase1` in_progress
  - `phase2` pending
  - `phase3` pending
  - `phase4` pending
