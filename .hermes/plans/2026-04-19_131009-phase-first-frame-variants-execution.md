# Phase-first 双帧变体执行计划

> **For Hermes:** 按 LuckyDog 的中文优先 workflow 执行；实现阶段遵守 TDD，先写失败测试，再补最小实现。

**Goal:** 在现有 OBS-first 与 1 秒抓帧基线上，为识别链路引入明确的双帧变体契约：`phase_frame` 用于低成本阶段判断，`roi_source_frame` 用于高质量 ROI 裁切，作为后续真实样本驱动 phase-first 识别的第一块地基。

**Architecture:** 不先大改业务识别器，而是先把 capture → pipeline 的数据契约稳定下来。`RecognitionPipeline` 不再默认把同一份 `frame` 同时喂给 phase detector 和 ROI recognizer，而是接收一个可兼容旧结构的新 payload：其中显式区分 phase 检测输入和 ROI 裁切输入。第一轮保持数据仍来自同一原图的不同变体，先把接口、测试和调试输出版面做稳。

**Tech Stack:** FastAPI, Pydantic, OpenCV, pytest

---

## Prime 结论

### 当前已确认现状
1. `backend/app/core/settings.py`
   - 默认 `frame_interval_seconds` 已经是 `1`。
2. `frontend/components/phase-status-panel.tsx`
   - 首页文案已更新为 `默认抓帧频率：每 1 秒 1 帧`。
3. `backend/app/services/capture_session.py`
   - 当前抓帧结果仍以单一 frame dict 形式向下游传播，没有显式 `phase_frame` / `roi_source_frame` 分层契约。
4. `backend/app/services/phase_detector.py`
   - 已支持基于 `ocr_texts` / `layout_variant_hint` 的轻量阶段判断，非常适合接到 `phase_frame`。
5. `backend/app/services/recognition_pipeline.py`
   - 已经有 `phase_snapshot` 与 `roi_payloads` 输出，但 `recognize()` 仍只接收单一 `frame` 参数。
   - `build_roi_payloads()` 虽然已经在 payload 中标了 `source=phase-frame` / `roi-source-frame`，但底层并没有真的引入双帧输入对象。

### 本轮最值得先做的子任务
**先做“契约成型”，再做“真实样本校准”。**

原因：
- 没有双帧契约，就很难继续把低成本 phase 检测和高质量 ROI 裁切彻底分开。
- 现在就去做真实样本和复杂识别，后面大概率还要返工 schema / pipeline。
- 先把契约和回归测试钉住，后续加 team_select / battle 的真实 ROI recognizer 会顺很多。

---

## Task 1: 为 pipeline 定义兼容式 FrameVariants 契约

**Objective:** 让识别管线可以显式接收 `phase_frame` 与 `roi_source_frame`，但暂不打破现有调用方。

**Files:**
- Create: `backend/app/services/frame_variants.py`
- Modify: `backend/app/services/recognition_pipeline.py`
- Test: `backend/tests/test_phase_first_pipeline.py`

**Step 1: 写失败测试**
- 新增测试覆盖：
  - 传入旧单帧 dict 时，pipeline 仍能工作。
  - 传入双帧 payload 时，phase detector 收到 `phase_frame`，ROI enrich / recognizer 收到 `roi_source_frame`。
- 先让“不同组件收到不同帧”的断言失败。

**Step 2: 跑测试确认失败**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_phase_first_pipeline.py -q`
- Expected: FAIL，提示 pipeline 仍把同一 frame 传给所有阶段。

**Step 3: 写最小实现**
- `frame_variants.py` 建议提供：
  - `build_frame_variants(frame: dict) -> dict`
  - `resolve_phase_frame(payload: dict) -> dict`
  - `resolve_roi_source_frame(payload: dict) -> dict`
- `recognition_pipeline.py` 中：
  - `recognize()` 入口统一先规范化 payload
  - phase detector 读 `phase_frame`
  - ROI payload crop / side recognizer 读 `roi_source_frame`
  - timestamp / layout_variant 等共享字段从规范化 payload 回填

**Step 4: 跑测试确认通过**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_phase_first_pipeline.py backend/tests/test_recognition_pipeline.py backend/tests/test_recognition_pipeline_enhanced.py -q`
- Expected: PASS

---

## Task 2: 把 phase snapshot / roi payload 调试输出升级为“双源可见”

**Objective:** 让 API/调试层能看见本次 phase 用的是哪张图、ROI 用的是哪张图，避免后续样本调参盲飞。

**Files:**
- Modify: `backend/app/services/recognition_pipeline.py`
- Modify: `backend/app/api/recognition.py`
- Modify: `backend/app/schemas/recognition.py`
- Test: `backend/tests/test_recognition_api.py`

**Step 1: 写失败测试**
- 对 `/api/recognition/current` 或 pipeline payload 增加断言：
  - `phase_snapshot.source_frame == 'phase_frame'`
  - `roi_payloads.*.source == 'roi-source-frame'` 继续成立
  - 如有需要，新增顶层 `frame_variants` 调试字段

**Step 2: 跑测试确认失败**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_recognition_api.py -q`

**Step 3: 写最小实现**
- 不做前端展示大改，只补 schema 与 API 返回结构。
- 保持兼容旧字段，新增字段尽量可选。

**Step 4: 跑测试确认通过**
- 同上命令，预期 PASS。

---

## Task 3: 在 capture_session 侧生成首版双帧 payload

**Objective:** 让 capture 层开始提供 phase-first 所需的两个 frame 入口，但第一轮先使用轻量复制/缩略元信息，不做重压缩算法优化。

**Files:**
- Modify: `backend/app/services/capture_session.py`
- Modify: `backend/app/services/frame_store.py`（如需要）
- Test: `backend/tests/test_capture_session.py`

**Step 1: 写失败测试**
- 新增断言：capture 成功后保存的 latest frame 中包含可解析的双帧变体结构。
- 至少覆盖：
  - `phase_frame`
  - `roi_source_frame`
  - 共享 `timestamp/source_id/layout_variant_hint`

**Step 2: 跑测试确认失败**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_capture_session.py -q`

**Step 3: 写最小实现**
- 在不影响前端截图预览的前提下，把 capture 输出标准化为“原有字段 + frame_variants”。
- 第一轮 `phase_frame` 可以先复用原图并补 `variant='phase_frame'`，后续再做真正低成本派生。

**Step 4: 跑测试确认通过**
- 同上命令，预期 PASS。

---

## Task 4: 为下一轮真实样本驱动的 phase detector 铺 fixture 目录与回归骨架

**Objective:** 给后面的 team_select / battle 样本校准预留稳定落点。

**Files:**
- Create if missing:
  - `backend/tests/fixtures/frames/team_select/README.md`
  - `backend/tests/fixtures/frames/battle/README.md`
- Modify: `backend/tests/test_phase_detector_real_samples.py`

**Step 1: 写失败测试或骨架测试**
- 如果暂时没有真实样本，就至少把目录约定和加载器骨架补齐。
- 测试名明确标出后续需要的样本格式（annotation json / OCR texts / layout variant）。

**Step 2: 跑测试**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_phase_detector_real_samples.py -q`

**Step 3: 最小实现/文档补齐**
- README 说明每张样本需要哪些配套文件。

**Step 4: 再验证**
- 预期 PASS 或 xfail（视当前测试设计而定）。

---

## 本轮实施边界

### 要做
- 先把 phase-first 双帧数据契约钉住
- 保持旧单帧调用兼容
- 为 API 调试输出补充足够信息
- 为真实样本阶段铺好目录和测试骨架

### 不做
- 本轮不直接做宝可梦头像识别 / 道具识别
- 本轮不直接接入复杂图像匹配或 CLIP
- 本轮不重构前端展示层
- 本轮不对 Hagibis 直连再做专项优化

---

## 验收标准

1. `RecognitionPipeline` 能同时兼容旧单帧输入和新双帧输入。
2. phase detector 与 ROI recognizer 能在测试中证明读取的是不同 frame 入口。
3. API / pipeline 调试输出能够明确看到 phase / ROI 的 frame source。
4. capture 层产出的 latest frame 已可承接后续真实 phase-first 优化。
5. 相关后端测试保持通过。

---

## 执行顺序建议

1. **先做 Task 1**：把数据契约钉牢
2. **再做 Task 2**：把调试可见性补上
3. **然后做 Task 3**：从 capture 层补齐双帧输出
4. **最后做 Task 4**：给真实样本阶段铺路
