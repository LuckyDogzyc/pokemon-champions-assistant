# OBS Virtual Camera-only 收口实施计划

> **For Hermes:** 按 LuckyDog 的中文优先 workflow 执行；实现阶段遵守 TDD，先写失败测试，再补最小实现。

**Goal:** 把 Windows 采集主链路正式收口到 **OBS Virtual Camera**，统一默认选择、错误引导、UI 文案与测试基线，停止继续为 Hagibis 直连路径做产品级优化。

**Architecture:** 后端继续保留 `device_kind=physical -> backend=dshow` / `device_kind=virtual -> backend=opencv` 的底层能力，但产品层默认与推荐路径全部围绕 OBS Virtual Camera。前端输入源面板、识别错误引导、测试夹具与计划文档统一改成 OBS-first 叙事，减少用户和代码的双重分叉心智负担。

**Tech Stack:** FastAPI, Pydantic, React/Next.js, TypeScript, pytest, jest

---

## Prime 结论

### 已经正确的部分
1. `backend/app/services/video_source_service.py`
   - Windows 虚拟设备已按 `backend='opencv'` 构建。
2. `backend/app/api/video.py`
   - 默认选择已优先命中 `OBS Virtual Camera`。
3. `backend/app/api/recognition.py`
   - dshow 占用错误已能给出“切换到 OBS Virtual Camera”的结构化提示。
4. `frontend/components/video-source-panel.tsx`
   - 已展示 `backend` / `device_kind` 元信息。
5. `frontend/app/page.tsx`
   - 已提供“切换到 OBS Virtual Camera” CTA。

### 仍残留的 OBS-only 不一致点
1. `frontend/tests/dashboard.test.tsx`
   - mock 里 `OBS Virtual Camera` 仍写成 `backend: 'dshow'`，与当前真实实现冲突。
2. `frontend/tests/debug-panel-status-panel.test.tsx`
   - 输入源 fixture 仍只使用 `Hagibis`，不符合当前产品主路径。
3. `backend/tests/test_video_sources_api.py`
   - 仍保留多处 `Hagibis + OBS` 双源叙事；底层能力可保留，但 API 层默认/推荐行为测试应明确 OBS-first。
4. 前端输入源面板文案仍偏中性：
   - `可展开页面下方调试面板...确认输入源是否正确`
   - 缺少“推荐先在 OBS 中开启 Virtual Camera”的显式引导。
5. 当前计划/测试基线还没有专门覆盖：
   - “如果列表中存在 OBS Virtual Camera，则它应成为默认选中项”
   - “建议切换 CTA 点击后，前端应 select + restart，并与 OBS backend=opencv 一致”

---

## Task 1: 固化后端 OBS-first 默认选择规则测试

**Objective:** 先把“存在 OBS Virtual Camera 时默认选它”的行为钉成回归测试。

**Files:**
- Modify: `backend/tests/test_video_sources_api.py`
- Read: `backend/app/api/video.py`

**Step 1: 写失败测试**
- 新增或强化测试：当 source 列表同时包含实体设备与 `OBS Virtual Camera` 时，`GET /api/video/sources` 返回的 `is_selected` 应落在 OBS 源上。
- 若当前已有类似测试但断言不够明确，先改到能在旧行为下失败。

**Step 2: 跑单测确认失败**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_video_sources_api.py -q`
- Expected: 至少新增的 OBS-first 断言先失败。

**Step 3: 写最小实现**
- 仅在 `backend/app/api/video.py` 调整 `_pick_preferred_source()` 或其调用链（如果测试证明已有实现足够，则不改生产代码，只保留更明确测试）。

**Step 4: 跑单测确认通过**
- 同上命令，预期 PASS。

---

## Task 2: 固化前端 dashboard 的 OBS backend=opencv 基线

**Objective:** 修正前端首页测试夹具，让它反映当前真实主路径，而不是过期的 dshow 虚拟源语义。

**Files:**
- Modify: `frontend/tests/dashboard.test.tsx`
- Read: `frontend/app/page.tsx`
- Read: `frontend/types/api.ts`

**Step 1: 写失败测试**
- 先把 mock 中 `OBS Virtual Camera` 的 `backend` 改成 `opencv`，并增加断言：页面仍能正确显示 CTA / 错误引导 / 截图区。
- 如有必要，增加对 `OBS Virtual Camera` 源元信息的断言。

**Step 2: 跑单测确认失败或至少捕获不一致**
- Run: `cd /root/projects/pokemon-champions-assistant/frontend && npx jest frontend/tests/dashboard.test.tsx --no-coverage`

**Step 3: 写最小实现**
- 仅当页面或组件确实依赖旧数据时，修复对应前端逻辑；否则只保留测试修正。

**Step 4: 跑单测确认通过**
- 同上命令，预期 PASS。

---

## Task 3: 给输入源面板补 OBS 推荐文案与测试

**Objective:** 让 UI 明确告诉用户“正式支持路径就是 OBS Virtual Camera”。

**Files:**
- Modify: `frontend/components/video-source-panel.tsx`
- Modify: `frontend/tests/video-source-panel-selection.test.tsx`

**Step 1: 写失败测试**
- 在 `video-source-panel-selection.test.tsx` 里先新增断言：
  - 当存在虚拟设备且 label 包含 `OBS Virtual Camera` 时，面板显示推荐文案，例如：
    - `推荐：先在 OBS 中开启 Virtual Camera，再在这里选择 OBS Virtual Camera。`
- 先让测试失败。

**Step 2: 跑单测确认失败**
- Run: `cd /root/projects/pokemon-champions-assistant/frontend && npx jest frontend/tests/video-source-panel-selection.test.tsx --no-coverage`

**Step 3: 写最小实现**
- 在 `frontend/components/video-source-panel.tsx` 中：
  - 检测 sources 中是否存在 `OBS Virtual Camera`
  - 若存在，显示明确推荐文案
  - 避免写成与 Hagibis 并列的模糊建议

**Step 4: 跑单测确认通过**
- 同上命令，预期 PASS。

---

## Task 4: 清理过期的 Hagibis 测试夹具叙事

**Objective:** 保留物理设备底层兼容测试，但把前端/产品层测试默认样例收敛到 OBS 主路径。

**Files:**
- Modify: `frontend/tests/debug-panel-status-panel.test.tsx`
- Inspect/optionally modify: `backend/tests/test_recognition_api.py`
- Inspect/optionally modify: `backend/tests/test_video_sources_api.py`

**Step 1: 写失败测试或直接修正夹具**
- `debug-panel-status-panel.test.tsx` 的 source fixture 从单独 `Hagibis` 改成更符合当前产品方向的 OBS source。
- 后端测试里保留物理设备错误引导案例，但把“建议目标”统一成 OBS-first，而不是继续强化 Hagibis 直连成功叙事。

**Step 2: 跑相关测试**
- Backend: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest backend/tests/test_recognition_api.py backend/tests/test_video_sources_api.py -q`
- Frontend: `cd /root/projects/pokemon-champions-assistant/frontend && npx jest frontend/tests/debug-panel-status-panel.test.tsx --no-coverage`

**Step 3: 最小实现/夹具修正**
- 只改测试数据与必要文案；不要扩张功能范围。

**Step 4: 重新验证通过**
- 同上两组命令，预期 PASS。

---

## Task 5: 跑全量回归并更新工作记录

**Objective:** 确认 OBS-only 收口没有打坏现有 OCR / capture / frontend 基线。

**Files:**
- Update if needed: `.hermes/plans/2026-04-19_123942-obs-virtual-camera-only-convergence.md`

**Step 1: 跑后端全量**
- Run: `cd /root/projects/pokemon-champions-assistant/backend && python3 -m pytest -q`
- Expected: 全绿。

**Step 2: 跑前端全量**
- Run: `cd /root/projects/pokemon-champions-assistant/frontend && npx jest --no-coverage`
- Expected: 全绿。

**Step 3: 记录结果**
- 若测试全绿，进入提交阶段。
- commit message 建议：`feat: converge video input flow on obs virtual camera`

---

## 实施边界

### 要做
- OBS Virtual Camera 作为默认选择与推荐路径
- UI 文案与测试夹具统一 OBS-first
- 继续保留实体设备底层诊断能力，但不再把它当产品主路径

### 不做
- 不继续新增 Hagibis reopen/retry 专项优化
- 不在本任务内接真实 PaddleOCR
- 不在本任务内推进 phase-first / 资料卡闭环实现
- 不在本任务内做 Windows 打包

---

## 验收标准

1. 代码与测试中，`OBS Virtual Camera` 的虚拟源语义统一为 `backend='opencv'`。
2. 如果 source 列表里存在 OBS Virtual Camera，默认选中与推荐文案都明显偏向它。
3. 前端 CTA / 错误引导 / 输入源面板形成一致的 OBS-first 用户路径。
4. 后端与前端全量测试保持通过。

---

## 执行顺序建议

1. 先做 **Task 2 + Task 3**（前端基线最明显，收益最大）
2. 再做 **Task 1 + Task 4**（把默认选择与测试叙事钉死）
3. 最后跑 **Task 5** 全量回归
