# Pokemon Champions Assistant

本项目是一个 **本地运行的宝可梦对战辅助 MVP**，面向主播 / 内容创作者使用，配合采集卡、OBS 或其他视频输入源工作。

当前版本重点是：

- 本地前后端应用可启动
- 前端可轮询后端识别状态
- 支持列出/选择视频输入源
- 默认每 3 秒抓 1 帧
- 先识别对局阶段，再做轻量识别
- 当前支持调试 `battle` / `team_select` 链路
- 前端调试面板可展示：
  - 当前阶段
  - `layout_variant`
  - `phase_evidence`
  - OCR `raw_text`
  - `ROI`
  - `matched_by`
  - `team_preview`

> 当前仍属于 **MVP 调试版**。适合你现在拿真实画面试跑、观察识别链路、继续积累样本；还不是完全打磨好的长期直播正式版。

---

## 1. 环境要求

建议环境：

- **Python 3.11+**
- **Node.js 20+**（Node 18 理论上也可，但推荐 20）
- **npm 10+**
- Linux / macOS / Windows 都可以

如果你要测试真实视频输入源，建议额外准备：

- 采集卡 / 摄像头 / OBS Virtual Camera
- OpenCV Python 包（README 下面会装）

---

## 2. 克隆项目

```bash
git clone https://github.com/LuckyDogzyc/pokemon-champions-assistant.git
cd pokemon-champions-assistant
```

---

## 3. 安装后端

进入后端目录：

```bash
cd backend
```

### 3.1 创建虚拟环境

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3.2 安装后端依赖

```bash
pip install -e ".[dev]"
```

### 3.3 安装视频输入相关依赖（推荐）

如果你要让后端尽量发现真实摄像头 / 采集卡，继续安装：

```bash
pip install opencv-python
```

> 说明：当前项目代码会优先尝试用 OpenCV 探测视频源；如果没装 OpenCV，也能启动，但视频源列表会退回到一个默认占位设备。

### 3.4 启动后端

仍然在 `backend/` 目录下运行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后，访问：

- 健康检查：<http://localhost:8000/api/health>

正常情况下会返回：

```json
{"status":"ok"}
```

---

## 4. 安装前端

打开第二个终端，进入项目根目录后再进前端目录：

```bash
cd pokemon-champions-assistant/frontend
```

安装依赖：

```bash
npm install
```

### 4.1 配置后端地址（可选）

默认前端会请求：

- `http://localhost:8000`

如果你的后端不是跑在这个地址，可以先设置环境变量：

Linux / macOS:

```bash
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Windows PowerShell:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

### 4.2 启动前端

```bash
npm run dev
```

启动后打开：

- <http://localhost:3000>

---

## 5. 最小试跑流程

当前推荐你按下面顺序试：

### 步骤 1：确认后端健康

打开：

- <http://localhost:8000/api/health>

确认返回 `{"status":"ok"}`。

### 步骤 2：打开前端 dashboard

浏览器访问：

- <http://localhost:3000>

如果前后端都启动正常，你应该能看到：

- 输入源选择
- 当前阶段
- 我方识别
- 对方识别
- 宝可梦资料区
- 属性克制摘要
- 调试面板按钮

### 步骤 3：展开调试面板

点击：

- `展开调试面板`

你会看到当前调试信息，包括：

- 布局模板 `layout_variant`
- 阶段证据 `phase_evidence`
- OCR 原始文本 `debug_raw_text`
- 识别 ROI
- 匹配方式 `matched_by`
- 队伍预览 `team_preview`

### 步骤 4：查看视频源接口

你也可以直接检查视频源接口：

- <http://localhost:8000/api/video/sources>

如果装了 OpenCV 且系统能识别到设备，这里会返回检测到的视频输入源；
如果没有检测到，会返回一个默认占位设备。

### 步骤 5：启动识别会话

可以用浏览器插件 / API 工具 / curl 调接口试跑：

```bash
curl -X POST http://localhost:8000/api/recognition/session/start
```

然后查看当前识别状态：

```bash
curl http://localhost:8000/api/recognition/current
```

---

## 6. 常用开发命令

### 后端测试

在 `backend/` 目录：

```bash
pytest -q
```

### 前端测试

在 `frontend/` 目录：

```bash
npm test -- --runInBand
```

### 前端构建

在 `frontend/` 目录：

```bash
npm run build
```

---

## 7. 常用环境变量

后端环境变量统一使用前缀：`PCA_`

常用项：

```bash
PCA_BACKEND_PORT=8000
PCA_FRONTEND_ORIGIN=http://localhost:3000
PCA_FRAME_INTERVAL_SECONDS=3
PCA_VIDEO_SOURCE=0
PCA_RECOGNITION_MODE=ocr
PCA_LANGUAGE=zh
PCA_STAGE_RECOGNITION_ENABLED=true
PCA_STAGE_RECOGNITION_THRESHOLD=0.8
PCA_OCR_PROVIDER=mock
```

说明：

- `PCA_FRONTEND_ORIGIN`：允许前端页面访问后端 API 的地址，默认是 `http://localhost:3000`
- `PCA_FRAME_INTERVAL_SECONDS`：默认 3 秒抓 1 帧
- `PCA_OCR_PROVIDER`：当前默认 `mock`，项目已预留 OCR adapter / recognizer 壳层，但真实 OCR runtime 还在持续接入中

---

## 8. 当前已知限制

当前版本是 **可联调的 MVP**，不是最终正式版。已知限制包括：

1. **真实 OCR runtime 还未完全落地**
   - 当前更适合联调与观察 debug 信息
   - 已有 OCR adapter / 后处理 / 名称归一化 / phase 识别链路

2. **阶段识别与布局模板还在持续迭代**
   - 当前重点覆盖 `battle` 与 `team_select`
   - 需要继续用真实截图扩 regression 样本

3. **视频源发现依赖 OpenCV**
   - 没装 `opencv-python` 时，后端会退回默认设备占位

4. **team preview 目前偏调试展示**
   - 已能展示结构化队伍预览
   - 但还没完全做成正式对战辅助 UI

---

## 9. 推荐你第一次试跑时这样做

建议你先按下面路线试：

1. 启动后端
2. 启动前端
3. 打开 dashboard
4. 接入采集卡 / OBS Virtual Camera
5. 展开调试面板
6. 观察这些信息是否合理：
   - `current_phase`
   - `layout_variant`
   - `phase_evidence`
   - `debug_raw_text`
   - `ROI`
   - `matched_by`
   - `team_preview`

如果你试跑时发现某张画面：

- 阶段识别不对
- 名称识别不对
- 队伍预览有漏项
- ROI 偏了

就把截图留给我，我可以继续把这些问题接回：

- `phase_detector.py`
- `layout_anchors.py`
- `chinese_ocr_recognizer.py`
- 前端 debug panel / dashboard

---

## 10. 当前验证状态

当前仓库最新状态已经验证过：

### 后端

```bash
pytest -q
```

### 前端

```bash
npm test -- --runInBand
npm run build
```

并且前后端本地联调所需的 CORS 已经接通，默认允许：

- `http://localhost:3000` -> `http://localhost:8000`

---

## 11. 下一步建议

如果你这次能顺利跑起来，下一步最值得做的是：

1. 接真实视频源进行联调
2. 收集更多 battle / team_select 截图样本
3. 继续补 phase/layout/OCR regression
4. 接真实 OCR runtime（PaddleOCR）
5. 把 team preview 和资料卡进一步做成正式可用 UI

---

如果你按这个 README 跑的时候遇到任何一步报错，直接把：

- 你执行的命令
- 报错截图 / 报错文本
- 当前系统（Windows / macOS / Linux）

发给我，我会继续帮你把安装流程修平。