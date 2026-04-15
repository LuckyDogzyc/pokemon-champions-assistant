# MVP 视频识别查询工具实施计划

> **给 Hermes：** 使用 `subagent-driven-development` 技能按任务逐条实现本计划。

**目标：** 构建 Pokemon Champions Assistant 的首个可用版本：接入采集卡实时视频源，优先识别中文界面下**双方当前场上宝可梦名称**，并在第二窗口 Web UI 中联动展示宝可梦资料与属性克制信息，同时支持人工修正。

**架构：** 采用本地优先的分层架构：Next.js 前端负责第二窗口界面，FastAPI 后端负责资料查询 API 与识别编排，Python + OpenCV 负责视频采集和帧处理，OCR 通过可替换适配器接入。MVP 严格限制为“识别双方当前场上名称 + 资料查询 + 属性克制 + 人工修正”，不扩展到完整战局解析。

**技术栈：** Next.js 15 + React + TypeScript、FastAPI + Pydantic、Python 3.11、OpenCV、中文优先 OCR 适配接口、本地 JSON 数据文件、pytest、vitest。

---

## 范围锁定

本计划只实现 `PRD.md` 中已确认的 MVP：
- 采集卡实时视频输入
- 识别**双方当前场上宝可梦名称**
- 中文优先识别
- 宝可梦资料查询
- 属性克制查询
- 识别错误时支持人工修正
- 浏览器第二窗口界面

本计划**不包含**：
- 伤害计算器
- 阵容推荐器
- 完整战局状态解析
- 自动策略建议
- 第一版直接上线多语言 OCR

---

## 目标目录结构

仓库根目录：

```text
pokemon-champions-assistant/
  frontend/
  backend/
  data/
  tests/
  .agents/plans/
  PRD.md
  CLAUDE.md
```

后端目录：

```text
backend/
  app/
    api/
    core/
    models/
    services/
    schemas/
    main.py
  tests/
```

前端目录：

```text
frontend/
  app/
  components/
  lib/
  types/
  tests/
```

数据目录：

```text
data/
  pokemon/
    pokemon_zh_index.json
    type_chart.json
    aliases_zh.json
```

---

## 执行时需要查阅的外部文档

- OpenCV Python 文档：视频采集与设备接入
- FastAPI 文档：依赖注入、响应模型、后台任务
- Next.js App Router 文档
- OCR 库文档：优先评估中文能力，先以可插拔适配器接入

---

## 实施策略

1. 先搭建后端与前端骨架。
2. 先把本地静态数据与查询 API 做通。
3. 再做视频源枚举和帧采集。
4. 先接入 mock 识别器，确保整条链路能跑。
5. 再替换为中文 OCR 适配器。
6. 补 recognition session / current state API。
7. 完成第二窗口 UI。
8. 加入人工修正流程。
9. 最后做整体验证与运行文档。

---

## 分步任务

### 任务 1：创建后端 Python 项目骨架

**目标：** 建立 FastAPI 后端基础结构和依赖清单。

**文件：**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_health.py`

**Step 1: 先写失败测试**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_ok():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
```

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_health.py -v`
期望：FAIL —— 模块或 app 尚不存在。

**Step 3: 编写最小实现**

创建 `backend/app/main.py`，提供 FastAPI app 和 `/api/health` 路由。

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_health.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: scaffold backend fastapi app"
```

---

### 任务 2：创建前端 Next.js 骨架

**目标：** 建立第二窗口前端应用。

**文件：**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/globals.css`
- Test: `frontend/tests/home.test.tsx`

**Step 1: 先写失败测试**

测试首页会渲染产品标题和占位状态文字。

**Step 2: 运行测试确认失败**

运行：`cd frontend && npm test -- --runInBand home.test.tsx`
期望：FAIL —— 前端未初始化。

**Step 3: 编写最小实现**

渲染页面标题 `Pokemon Champions Assistant`，以及状态文字如 `Recognition idle`。

**Step 4: 再次运行测试确认通过**

运行：`cd frontend && npm test -- --runInBand home.test.tsx`
期望：PASS。

**Step 5: 提交**

```bash
git add frontend
git commit -m "feat: scaffold frontend nextjs app"
```

---

### 任务 3：增加后端配置与环境变量支持

**目标：** 集中管理后端端口、采集参数、识别模式等配置。

**文件：**
- Create: `backend/app/core/settings.py`
- Create: `backend/.env.example`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings.py`

**Step 1: 先写失败测试**

测试 settings 能正确加载默认配置，如：
- API 名称
- 帧轮询间隔
- 识别器模式
- 默认语言为 `zh`

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_settings.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

使用 Pydantic settings，至少包含：
- `APP_NAME`
- `CAPTURE_FRAME_INTERVAL_MS`
- `RECOGNIZER_MODE`
- `DEFAULT_LANGUAGE=zh`

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_settings.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add backend settings"
```

---

### 任务 4：增加宝可梦与属性数据文件

**目标：** 准备 MVP 所需的本地资料数据源。

**文件：**
- Create: `data/pokemon/pokemon_zh_index.json`
- Create: `data/pokemon/type_chart.json`
- Create: `data/pokemon/aliases_zh.json`
- Create: `backend/app/services/data_loader.py`
- Test: `backend/tests/test_data_loader.py`

**Step 1: 先写失败测试**

测试 data loader 能读取宝可梦数据、别名数据和属性克制表。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_data_loader.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

- 至少放入 6 只宝可梦种子数据。
- 放入完整 18 属性克制数据。
- 提供函数：
  - `load_pokemon_index()`
  - `load_aliases()`
  - `load_type_chart()`

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_data_loader.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add data backend
git commit -m "feat: add pokemon seed data and loaders"
```

---

### 任务 5：实现宝可梦搜索与详情 API

**目标：** 基于本地数据提供宝可梦资料查询能力。

**文件：**
- Create: `backend/app/schemas/pokemon.py`
- Create: `backend/app/services/pokemon_service.py`
- Create: `backend/app/api/pokemon.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_pokemon_api.py`

**Step 1: 先写失败测试**

增加测试：
- `GET /api/pokemon/search?q=喷火龙`
- `GET /api/pokemon/喷火龙`

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_pokemon_api.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

支持：
- 精确中文名称
- 中文别名映射
- 必要时大小写无关的兜底匹配

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_pokemon_api.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add pokemon lookup api"
```

---

### 任务 6：实现属性克制 API

**目标：** 提供单属性和双属性组合的克制关系查询。

**文件：**
- Create: `backend/app/schemas/types.py`
- Create: `backend/app/services/type_service.py`
- Create: `backend/app/api/types.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_types_api.py`

**Step 1: 先写失败测试**

测试：
- `GET /api/type/Fire/matchups`
- `POST /api/type/combined-matchups`，输入 `['Fire', 'Flying']`

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_types_api.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

返回：
- 攻击端克制 / 被克制
- 防守端弱点 / 抗性 / 免疫
- 双属性组合防守倍率

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_types_api.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add type matchup api"
```

---

### 任务 7：实现视频源枚举服务

**目标：** 检测本机可用视频设备，并优先兼容采集卡场景。

**文件：**
- Create: `backend/app/schemas/video.py`
- Create: `backend/app/services/video_source_service.py`
- Create: `backend/app/api/video.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_video_sources_api.py`

**Step 1: 先写失败测试**

测试 `GET /api/video/sources` 返回稳定结构的视频源列表。
测试中若无法访问真实硬件，需 mock 设备枚举逻辑。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_video_sources_api.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

返回字段至少包含：
- `id`
- `label`
- `backend`
- `is_capture_card_candidate`

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_video_sources_api.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add video source enumeration api"
```

---

### 任务 8：实现帧采集会话服务

**目标：** 能针对指定视频设备启动采集会话并安全读取帧。

**文件：**
- Create: `backend/app/services/capture_session.py`
- Create: `backend/app/services/frame_store.py`
- Modify: `backend/app/api/video.py`
- Test: `backend/tests/test_capture_session.py`

**Step 1: 先写失败测试**

测试采集会话可启动，并能通过 mock 视频源返回当前帧状态或占位结果。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_capture_session.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

- 实现 start / stop session。
- 将最新帧元信息保存在内存中。
- 当前阶段不用做完整流媒体，只需能支持轮询 current state。

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_capture_session.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add frame capture session service"
```

---

### 任务 9：定义双方识别状态模型

**目标：** 建立识别结果、置信度、人工修正状态的统一结构。

**文件：**
- Create: `backend/app/schemas/recognition.py`
- Create: `backend/app/models/recognition_state.py`
- Test: `backend/tests/test_recognition_models.py`

**Step 1: 先写失败测试**

测试以下字段的序列化：
- `player_active_name`
- `opponent_active_name`
- 双方置信度
- 数据来源（`ocr` / `manual` / `mock`）
- 时间戳

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_recognition_models.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

显式区分我方与对方识别结果，不允许混成单一字段。

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_recognition_models.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add recognition state schemas"
```

---

### 任务 10：实现识别器接口与 mock 识别器

**目标：** 将帧采集和 OCR 解耦，在真实 OCR 接入前先打通整条链路。

**文件：**
- Create: `backend/app/services/recognizers/base.py`
- Create: `backend/app/services/recognizers/mock_recognizer.py`
- Create: `backend/app/services/recognition_pipeline.py`
- Test: `backend/tests/test_recognition_pipeline.py`

**Step 1: 先写失败测试**

测试 pipeline 能接收帧输入，并通过 mock 识别器返回双方识别结果。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_recognition_pipeline.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

- 定义 `recognize(frame) -> RecognitionState`
- mock 识别器返回固定双方名称，确保测试可重复

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_recognition_pipeline.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add recognition pipeline abstraction"
```

---

### 任务 11：接入中文优先 OCR 适配器

**目标：** 加入可替换 OCR 适配器，并首先支持中文名称识别。

**文件：**
- Create: `backend/app/services/recognizers/ocr_adapter.py`
- Create: `backend/app/services/recognizers/chinese_ocr_recognizer.py`
- Modify: `backend/app/core/settings.py`
- Test: `backend/tests/test_chinese_ocr_recognizer.py`

**Step 1: 先写失败测试**

测试 OCR 识别器会对中文识别结果做规范化，再通过别名映射输出双方名称。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_chinese_ocr_recognizer.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

- OCR 适配器接口必须屏蔽具体 OCR 实现细节。
- 测试中用注入的 OCR 结果 payload 代替真实 OCR 调用。
- 通过 `aliases_zh.json` 做中文名称归一化。

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_chinese_ocr_recognizer.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend data
git commit -m "feat: add chinese-first ocr recognizer adapter"
```

---

### 任务 12：实现 recognition session API

**目标：** 提供启动识别会话和获取当前识别状态的接口。

**文件：**
- Create: `backend/app/api/recognition.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_recognition_api.py`

**Step 1: 先写失败测试**

测试：
- `POST /api/recognition/session/start`
- `GET /api/recognition/current`

使用 mocked capture + recognizer service。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_recognition_api.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

`/api/recognition/current` 至少返回：
- 当前我方名称
- 当前对方名称
- 双方置信度
- 若资料查询成功则返回关联资料摘要

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_recognition_api.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add recognition session api"
```

---

### 任务 13：实现人工修正 API

**目标：** 保证主播在识别错误时能立即修正，不依赖 OCR 下一轮刷新。

**文件：**
- Modify: `backend/app/api/recognition.py`
- Modify: `backend/app/services/recognition_pipeline.py`
- Test: `backend/tests/test_manual_override_api.py`

**Step 1: 先写失败测试**

测试 `POST /api/recognition/override`，请求体示例：

```json
{
  "side": "player",
  "name": "喷火龙"
}
```

并验证 current state 变为 `source=manual`。

**Step 2: 运行测试确认失败**

运行：`cd backend && pytest tests/test_manual_override_api.py -v`
期望：FAIL。

**Step 3: 编写最小实现**

支持按 side（`player` / `opponent`）分别覆盖当前识别结果。

**Step 4: 再次运行测试确认通过**

运行：`cd backend && pytest tests/test_manual_override_api.py -v`
期望：PASS。

**Step 5: 提交**

```bash
git add backend
git commit -m "feat: add manual override api"
```

---

### 任务 14：实现前端 API client 和轮询 hooks

**目标：** 前端能获取视频源与当前识别状态。

**文件：**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/hooks.ts`
- Create: `frontend/types/api.ts`
- Test: `frontend/tests/api-client.test.ts`

**Step 1: 先写失败测试**

测试 API client 调用了正确的后端接口，并能解析 recognition payload。

**Step 2: 运行测试确认失败**

运行：`cd frontend && npm test -- --runInBand api-client.test.ts`
期望：FAIL。

**Step 3: 编写最小实现**

提供 typed 方法：
- `getVideoSources()`
- `startRecognitionSession()`
- `getCurrentRecognition()`
- `overrideRecognition()`
- `searchPokemon()`

**Step 4: 再次运行测试确认通过**

运行：`cd frontend && npm test -- --runInBand api-client.test.ts`
期望：PASS。

**Step 5: 提交**

```bash
git add frontend
git commit -m "feat: add frontend api client"
```

---

### 任务 15：构建第二窗口识别仪表盘 UI

**目标：** 提供可在直播时放在 OBS 旁边使用的 MVP 界面。

**文件：**
- Create: `frontend/components/video-source-panel.tsx`
- Create: `frontend/components/recognition-status-panel.tsx`
- Create: `frontend/components/pokemon-card.tsx`
- Create: `frontend/components/type-matchup-card.tsx`
- Modify: `frontend/app/page.tsx`
- Test: `frontend/tests/dashboard.test.tsx`

**Step 1: 先写失败测试**

测试仪表盘会渲染：
- 视频源选择器
- 我方识别面板
- 对方识别面板
- 联动资料卡区域

**Step 2: 运行测试确认失败**

运行：`cd frontend && npm test -- --runInBand dashboard.test.tsx`
期望：FAIL。

**Step 3: 编写最小实现**

界面至少包含：
- 当前视频源
- 识别状态
- 我方宝可梦卡片
- 对方宝可梦卡片
- 属性克制摘要

**Step 4: 再次运行测试确认通过**

运行：`cd frontend && npm test -- --runInBand dashboard.test.tsx`
期望：PASS。

**Step 5: 提交**

```bash
git add frontend
git commit -m "feat: build recognition dashboard ui"
```

---

### 任务 16：增加人工修正 UI

**目标：** 识别错误时可在直播场景下快速修正。

**文件：**
- Create: `frontend/components/manual-override-form.tsx`
- Modify: `frontend/app/page.tsx`
- Test: `frontend/tests/manual-override-form.test.tsx`

**Step 1: 先写失败测试**

测试用户可以：
- 选择 `player` 或 `opponent`
- 输入中文宝可梦名称
- 提交修正请求

**Step 2: 运行测试确认失败**

运行：`cd frontend && npm test -- --runInBand manual-override-form.test.tsx`
期望：FAIL。

**Step 3: 编写最小实现**

提供紧凑的直播友好修正表单，包含：
- side selector
- 文本输入框
- 提交按钮
- 最新修正结果状态

**Step 4: 再次运行测试确认通过**

运行：`cd frontend && npm test -- --runInBand manual-override-form.test.tsx`
期望：PASS。

**Step 5: 提交**

```bash
git add frontend
git commit -m "feat: add manual override ui"
```

---

### 任务 17：补充本地运行文档与脚本

**目标：** 让开发者可以按文档成功跑起 MVP。

**文件：**
- Create: `README.md`
- Create: `backend/Makefile`
- Create: `frontend/.env.local.example`
- Modify: `CLAUDE.md`
- Test: README 中记录手工验收步骤

**Step 1: 先列出手工验收清单**

当前任务不要求先写自动化单测，但必须先定义人工验收步骤。

**Step 2: 编写最小实现与文档**

文档至少包含：
- 后端安装
- 前端安装
- 后端 dev server 启动
- 前端 dev server 启动
- 打开第二窗口 UI
- 选择采集卡视频源
- 查看当前识别状态
- 使用人工修正

**Step 3: 运行验证命令**

运行：
```bash
cd backend && pytest -q
cd ../frontend && npm test -- --runInBand
```

期望：全部通过。

**Step 4: 提交**

```bash
git add README.md backend frontend CLAUDE.md
git commit -m "docs: add local runbook for mvp"
```

---

### 任务 18：完整集成验证

**目标：** 确认 MVP 各层能够协同工作。

**文件：**
- Modify as needed based on failures
- Test: backend + frontend full suites

**Step 1: 运行后端验证**

运行：`cd backend && pytest -q`
期望：PASS。

**Step 2: 运行前端验证**

运行：`cd frontend && npm test -- --runInBand`
期望：PASS。

**Step 3: 运行启动 smoke test**

本地启动后端与前端，手工验证：
1. 浏览器打开 UI。
2. 列出视频源。
3. 启动识别会话。
4. 确认 recognition state 会刷新。
5. 手动覆盖一侧宝可梦名称。
6. 确认资料卡与克制信息同步更新。

**Step 4: 最终提交**

```bash
git add -A
git commit -m "feat: complete mvp recognition query workflow"
```

---

## 验收清单

- [ ] 已实现采集卡候选视频源枚举
- [ ] 识别会话可启动
- [ ] current API 分别返回双方当前名称
- [ ] 中文优先 OCR 适配路径已接通
- [ ] 人工修正支持按 side 覆盖
- [ ] 可根据识别名称查到宝可梦资料
- [ ] 属性克制查询可用
- [ ] 前端仪表盘可作为第二窗口使用
- [ ] 后端测试通过
- [ ] 前端测试通过

---

## 验证命令

```bash
cd backend && pytest -q
cd frontend && npm test -- --runInBand
```

可选手工运行：

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

---

## 执行时重点风险

1. OpenCV 设备索引会因系统与硬件不同而变化。
2. 采集卡设备名称可能不稳定。
3. 中文 OCR 可能误读游戏界面字体。
4. 名称归一化需要能容忍 OCR 噪声。
5. 轮询频率不能过高，否则会增加直播电脑负载。

---

## 给执行代理的备注

- OCR provider 必须藏在 adapter 后面，不要把某个 OCR 库硬编码到所有逻辑里。
- 人工修正必须尽早落地，保证直播场景始终可恢复。
- 不要把 MVP 扩展成完整战局解析。
- 测试优先使用 mocked OCR 和 mocked frame input，保证稳定性。
- 如果 CI 或当前环境无法访问真实硬件，视频源枚举和采集测试必须保持可 mock。

---

**计划已完成。后续执行时，按 subagent-driven-development 流程：每个任务先做规格符合性审查，再做代码质量审查。**