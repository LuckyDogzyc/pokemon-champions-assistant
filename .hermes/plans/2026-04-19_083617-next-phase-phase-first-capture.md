# 下一阶段：阶段优先识别与 1 秒抓帧实施计划

> **For Hermes:** 本轮只做 planning，不执行实现；后续可按此计划进入 TDD 执行。

**Goal:** 让 Pokemon Champions Assistant 进入下一阶段：默认优先使用 OBS Virtual Camera，在保留手动切换实体采集卡能力的前提下，将抓帧频率从 3 秒提升到 1 秒，并改造成“低成本判阶段 + 高质量裁 ROI 识别”的 phase-first 流程。

**Architecture:** 保持现有 Next.js + FastAPI + 本地识别管线，但将识别链路拆成两层：第一层做轻量级阶段判断（可接受低分辨率/模糊采样），第二层根据阶段选择固定 ROI，以更高质量裁剪图送入 OCR / 图像匹配，从而兼顾速度与文字可读性。

**Tech Stack:** Next.js/React、FastAPI、OpenCV、现有 capture_session / phase_detector / recognition_pipeline、中文 OCR 适配器、未来可引入模板匹配/CLIP 风格图像匹配用于宝可梦头像与道具识别。

---

## Prime 结论

### 当前仓库状态
- 分支：`main`
- 当前存在未提交改动：
  - `backend/app/api/recognition.py`
  - `backend/tests/test_recognition_api.py`
  - `frontend/app/page.tsx`
  - `frontend/tests/dashboard.test.tsx`
  - `frontend/types/api.ts`
- 最近相关提交集中在：Windows 输入源枚举、active capture、抓帧诊断、ffmpeg dshow 重试。

### 当前已具备能力
1. Windows 输入源能枚举出 `OBS Virtual Camera` 与实体设备。
2. 当前识别链路已经是“先 phase，再 recognition”：
   - `backend/app/services/phase_detector.py`
   - `backend/app/services/recognition_pipeline.py`
3. 已有布局锚点基础：
   - `backend/app/services/layout_anchors.py`
4. 团队选择和战斗阶段已有基础结构字段：
   - `team_preview`
   - `layout_variant`
   - `phase_evidence`
   - `debug_raw_text`
5. 当前抓帧默认仍是 `3` 秒：
   - `backend/app/core/settings.py`

### 当前关键不足
1. 默认视频源仍不是 OBS Virtual Camera 优先。
2. 抓帧节奏是“全局固定 3 秒”，不适合实战响应。
3. phase detector 仍偏 mock/规则占位，缺少真实截图驱动的状态机。
4. 识别 ROI 还太粗，尚未形成“按阶段切不同 ROI”的完整方案。
5. 选人阶段的“双方宝可梦形象 + 道具”识别还没落地。
6. 战斗阶段的“我方信息 / 敌方信息 / 技能区”多 ROI 裁剪还没落地。

---

## 用户本轮明确要求

1. **默认选择 OBS Virtual Camera**，但保留手动切换其他输入源的能力。
2. **抓帧频率提高到 1 秒 1 次。**
3. 不希望简单粗暴降清晰度导致 OCR 失效。
4. 更偏向：
   - 先用较轻量方式判断当前处于什么状态
   - 再按状态裁出特定区域
   - 保证这些 ROI 图足够清晰，适合文字识别/图像匹配
5. 阶段目标：
   - **选人阶段**：识别双方宝可梦形象，对应宝可梦与道具
   - **战斗阶段**：识别
     - 左下我方宝可梦信息
     - 右上敌方宝可梦信息
     - 右下我方技能

---

## 建议的下一步，不是直接大改，而是按 4 个子阶段推进

## 阶段 A：输入源默认策略与 1 秒抓帧切换

**目标：** 先把“默认输入源”和“响应速度”改到可用。

### 具体任务
1. 默认选中策略改成：
   - 首选 `OBS Virtual Camera`
   - 其次选上次用户选择
   - 再其次选实体采集卡候选
2. 将默认 `frame_interval_seconds` 从 `3` 改为 `1`
3. 前端文案同步更新：从“每 3 秒 1 帧”改成“每 1 秒 1 帧”
4. 为后续 phase-first 准备：把配置扩成双层频率概念
   - `PHASE_POLL_INTERVAL_SECONDS=1`
   - `ROI_REFRESH_INTERVAL_SECONDS=1`（先可同值）

### 可能修改文件
- `backend/app/core/settings.py`
- `backend/app/api/video.py`
- `backend/app/services/video_source_selection.py`
- `backend/app/services/video_source_service.py`
- `frontend/app/page.tsx`
- `frontend/tests/dashboard.test.tsx`
- `backend/tests/test_settings.py`
- `backend/tests/test_video_sources_api.py`

### 验证方式
- 后端测试确认默认源优先选 `OBS Virtual Camera`
- 前端测试确认页面文案为 1 秒 1 帧
- 手工验证：启动时默认落在 OBS Virtual Camera，但用户仍可切 Hagibis/其他源

---

## 阶段 B：phase-first 双层采样架构

**目标：** 不再把“整帧识别”和“细节 OCR/匹配”混成一步。

### 建议架构
1. **阶段检测输入（低成本）**
   - 用缩小帧 / 灰度帧 / 少量全局 OCR 文本做 phase detection
   - 重点识别：team_select / battle / switching / move_resolution
2. **阶段 ROI 识别输入（高质量）**
   - 一旦确定阶段，就只对该阶段关心的 ROI 做高质量裁切
   - ROI 保持原始分辨率优先，不要先全局压小再 OCR
3. **识别管线输出分层**
   - `phase_snapshot`：当前阶段判断证据
   - `roi_payloads`：本次被裁出的关键块
   - `recognition_result`：OCR/匹配结果

### 推荐新增概念
- `FrameVariants`
  - `phase_frame`：低分辨率/快速判断用
  - `roi_source_frame`：原始或轻压缩高质量图
- `PhaseAwareCapturePayload`
  - phase detector 用哪张图
  - recognizer 用哪组 ROI

### 可能修改文件
- `backend/app/services/capture_session.py`
- `backend/app/services/phase_detector.py`
- `backend/app/services/recognition_pipeline.py`
- `backend/app/schemas/recognition.py`
- 新增：`backend/app/services/frame_variants.py`（建议）
- 新增测试：`backend/tests/test_phase_first_pipeline.py`

### 验证方式
- 单测验证：phase detector 接收低成本输入也能判对阶段
- 单测验证：battle/team_select 阶段会请求不同 ROI 集合
- 手工验证：1 秒刷新下，CPU/延迟可接受

---

## 阶段 C：基于真实截图固化 ROI 与状态机

**目标：** 用真实截图样本把 phase 和 ROI 从“估计”推进到“可用”。

### 你这轮给出的方向非常对
应该先做：
1. **模糊/低成本截图判状态**
2. **一旦判定状态，按状态取高质量 ROI**

### 推荐先固化两类状态
1. `team_select_default`
2. `battle_move_menu_open` / `battle_default`

### Team Select 需要的 ROI
- 选人标题/指令区
- 我方队伍头像列表区
- 对方队伍头像列表区
- 道具图标区（如果 UI 中稳定存在）

### Battle 需要的 ROI
- 左下我方宝可梦信息区（名称/HP/状态）
- 右上敌方宝可梦信息区（名称/HP/状态）
- 右下技能区（四技能）

### 推荐做法
- 先收集一小批真实截图样本
- 在 `layout_anchors.py` 里把默认 anchor 从“approx”逐步校正
- 必要时引入 `layout_variant` 专门区分：
  - `team_select_default`
  - `battle_default`
  - `battle_move_menu_open`
  - 后续再扩展其他变体

### 可能修改文件
- `backend/app/services/layout_anchors.py`
- `backend/app/services/phase_detector.py`
- `backend/tests/test_phase_detector_real_samples.py`
- 新增样本目录（建议）：
  - `backend/tests/fixtures/frames/team_select/`
  - `backend/tests/fixtures/frames/battle/`

### 验证方式
- 用真实截图 fixture 做回归测试
- 每种 layout_variant 至少要有 3~5 张样本

---

## 阶段 D：识别能力扩展——从“名字 OCR”到“头像/道具/技能”

**目标：** 补齐你定义的下一阶段业务价值。

### D1. 选人阶段：头像识别 + 道具识别

#### 推荐策略
- **头像识别优先走图像匹配，不要只靠 OCR**
  - 宝可梦头像/立绘不适合 OCR
  - 更适合模板匹配、特征匹配，或后续引入 embedding/CLIP 路线
- **道具识别分两层**
  - 如果道具有文字：走 OCR
  - 如果只有图标：走图像匹配/模板库

#### 推荐结果结构
- `team_preview.player_team[]` 扩展为对象而不是纯字符串
- 例如：
  - `species_name`
  - `item_name`
  - `sprite_match_confidence`
  - `item_match_confidence`

### D2. 战斗阶段：多 ROI 识别

#### 本阶段输出建议
- `player_active`
  - name
  - hp_text
  - status_text
- `opponent_active`
  - name
  - hp_text
  - status_text
- `move_options[]`
  - move_name
  - pp_text
  - move_type（若可识别）

#### 推荐策略
- 名称、HP、PP：OCR
- 状态异常/属性 icon：后续单独做图标识别
- 技能区建议单独建 recognizer，而不是塞进 side recognizer

### 可能修改文件
- `backend/app/schemas/recognition.py`
- `backend/app/services/recognition_pipeline.py`
- `backend/app/services/recognizers/chinese_ocr_recognizer.py`
- 新增：
  - `backend/app/services/recognizers/team_select_recognizer.py`
  - `backend/app/services/recognizers/move_menu_recognizer.py`
  - `backend/app/services/recognizers/sprite_matcher.py`
  - `backend/app/services/recognizers/item_matcher.py`

### 验证方式
- 选人截图 fixtures：能输出双方阵容对象列表
- 战斗截图 fixtures：能输出双方 active info + 4 个技能文本

---

## 为什么我建议先做 A + B，再进入 C + D

因为现在最大的风险不是“识别算法不够花”，而是：

1. 刷新频率提高后，整条链路会不会变卡
2. 全帧 OCR 会不会让性能和精度一起掉
3. 当前数据结构能不能承接“头像/道具/技能”这些新结果

所以建议顺序是：

1. **先把默认源和 1 秒抓帧改对**
2. **再把识别链路改成 phase-first**
3. **然后用真实截图把 ROI 校准**
4. **最后补头像/道具/技能识别**

这样风险最低，也最符合你要的方向。

---

## 我认为“下一步应该做什么”——优先级排序

### P0（下一手就做）
1. 默认选择 `OBS Virtual Camera`，保留手动改源
2. 把默认抓帧间隔从 3 秒改成 1 秒
3. 补一份“phase-first 识别”实施计划并落到测试骨架

### P1（紧接着做）
4. 把 capture pipeline 拆成：低成本 phase 检测 + 高质量 ROI 裁切
5. 建立 `team_select_default` 与 `battle_default / battle_move_menu_open` 的 ROI 套件
6. 基于真实截图样本做阶段识别回归测试

### P2（然后做）
7. 选人阶段：先做宝可梦头像识别，再做道具识别
8. 战斗阶段：先做双方 active name/HP，再做技能区识别

### P3（后续增强）
9. 引入可配置的多档性能模式
   - `fast`
   - `balanced`
   - `accurate`
10. 在前端 debug 面板显示当前阶段所用 ROI 与裁切图

---

## 风险与权衡

### 风险 1：1 秒抓帧导致 CPU 开销上升
**缓解：** phase 用低成本输入，OCR 只打 ROI。

### 风险 2：真实 UI 布局存在分辨率/缩放差异
**缓解：** anchors 采用相对坐标；按 layout_variant 管理。

### 风险 3：头像识别比 OCR 难很多
**缓解：** 先做 battle 阶段文字信息；选人阶段先识别阵容轮廓，再逐步补头像/道具。

### 风险 4：OBS Virtual Camera 画面与实体源存在缩放/压缩差异
**缓解：** 优先用 OBS Virtual Camera 样本建立 ROI，必要时为实体源保留单独 variant。

---

## 建议的执行顺序（给下一轮开发）

### 任务 1
实现“默认选 OBS Virtual Camera + 仍支持手动切换”

### 任务 2
实现“默认 1 秒抓帧”并补测试

### 任务 3
补一个 phase-first pipeline 测试文件，先把接口/数据结构定住

### 任务 4
为 team_select / battle 定义第一版 ROI 集合

### 任务 5
接入真实截图样本，校准 phase detector 与 anchors

### 任务 6
先做 battle 阶段多 ROI OCR

### 任务 7
再做 team_select 阶段头像/道具识别

---

## 本轮建议给 LuckyDog 的直接结论

- 现在应该进入 **“phase-first 识别架构”** 阶段，而不是继续只调单帧抓图参数。
- 第一优先级是：
  1. 默认选 OBS Virtual Camera
  2. 抓帧频率提到 1 秒
  3. 改成“低成本判阶段 + 高质量裁 ROI 识别”
- 在此之后，先落地 **战斗阶段多 ROI OCR**，再推进 **选人阶段头像/道具识别**。

---

## 执行验证命令（后续开发时）

### Backend
```bash
cd /root/projects/pokemon-champions-assistant/backend
python -m pytest tests/test_settings.py tests/test_video_sources_api.py tests/test_phase_detector.py tests/test_phase_detector_real_samples.py -q
```

### Frontend
```bash
cd /root/projects/pokemon-champions-assistant/frontend
npm test -- --runInBand dashboard.test.tsx debug-panel.test.tsx video-source-panel-selection.test.tsx
```

### 手工验证
1. 打开 OBS，启动 Virtual Camera
2. 启动助手，确认默认源为 OBS Virtual Camera
3. 确认页面 1 秒级刷新
4. 切到选人画面，观察阶段是否切到 `team_select`
5. 切到战斗画面，观察阶段是否切到 `battle`
6. 检查 debug panel 中 ROI/截图是否足够清晰
