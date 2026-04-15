# Windows Release 版本实施计划

> **给 Hermes：** 使用 `subagent-driven-development` 技能按任务逐条实现本计划。

**目标：** 为 Pokemon Champions Assistant 增加首个可下载的 Windows Release 版本：在 GitHub Releases 页面提供可下载产物，用户下载后双击 `exe` 即可自动启动本地后端、提供前端静态页面并自动打开浏览器访问 dashboard。

**架构：** 保持当前“本地 Web App”架构不变，不重写为 Electron/Tauri。前端先构建为静态站点，后端继续使用 FastAPI；新增一个 Python 启动器作为桌面壳层，负责启动后端、启动静态文件服务、等待健康检查通过、自动打开浏览器。GitHub Actions 在 Windows runner 上构建前端静态资源、用 PyInstaller 打包启动器，并把便携版 zip 上传到 GitHub Release。

**技术栈：** Next.js 15 静态导出、FastAPI、Python 3.11、PyInstaller、GitHub Actions、PowerShell、标准库 `webbrowser` / `subprocess` / `socket` / `http.server`。

---

## 范围锁定

本计划第一阶段只实现：

- Windows 可运行的 launcher `exe`
- launcher 自动启动本地后端
- launcher 自动提供前端静态页面
- launcher 自动打开浏览器
- GitHub Actions 基于 tag 自动构建
- GitHub Releases 自动上传 **portable zip** 资产
- README 增加 release 下载/构建说明

本阶段**暂不实现**：

- 真正的安装器 `setup.exe`（Inno Setup / NSIS）
- 自动更新
- 托盘图标
- 开机自启
- 代码签名
- 内嵌浏览器窗口

> 说明：先交付一个在 GitHub Releases 可下载的 `portable` 版本，满足“可下载 release 版本”的要求；安装器在下一轮做。

---

## 目标目录结构

```text
pokemon-champions-assistant/
  backend/
  frontend/
  release/
    launcher/
      __init__.py
      app.py
      runtime.py
    scripts/
      build_frontend_static.ps1
      package_windows_portable.ps1
    windows/
      app.manifest
  .github/
    workflows/
      release-windows.yml
  backend/tests/
    test_release_runtime.py
  .agents/plans/
    release-windows-github-release.md
```

---

## 实施策略

1. 先把前端改为可静态导出，保证 release 不依赖 `next dev`。
2. 先做 Python launcher 的纯逻辑函数，并用 pytest 覆盖端口分配、URL 生成、资源路径解析等。
3. 再做 launcher 主程序，串起后端进程、静态文件服务、浏览器自动打开。
4. 再补 Windows 打包脚本。
5. 最后补 GitHub Actions release workflow，并以 tag 触发上传 zip 资产。

---

## 分步任务

### 任务 1：补 release 计划与范围文档

**目标：** 明确第一阶段只交付 portable GitHub Release，不把安装器混进同一轮。

**文件：**
- Create: `.agents/plans/release-windows-github-release.md`
- Modify: `README.md`

**Step 1: 写明 release 目标与不做项**

在计划和 README 中说明：
- 本轮产物是 `portable zip`
- 下载后运行 `exe`
- 自动打开浏览器
- 安装器后续再做

**Step 2: 提交**

```bash
git add .agents/plans/release-windows-github-release.md README.md
git commit -m "docs: add windows release implementation plan"
```

---

### 任务 2：让前端支持静态导出

**目标：** 让前端构建后输出静态文件，可由本地静态服务器直接托管。

**文件：**
- Modify: `frontend/next.config.ts`
- Test/Verify: `cd frontend && npm run build`

**Step 1: 先写失败验证**

运行：
```bash
cd frontend && npm run build
```
观察当前是否已产出 `frontend/out/`。

**Step 2: 实现最小改动**

在 `next.config.ts` 中添加：
```ts
const nextConfig: NextConfig = {
  output: 'export',
};
```

**Step 3: 再次运行验证**

运行：
```bash
cd frontend && npm run build
```
期望：生成 `frontend/out/index.html`。

**Step 4: 提交**

```bash
git add frontend/next.config.ts
git commit -m "feat: enable static export for release builds"
```

---

### 任务 3：为 launcher 先写失败测试

**目标：** 用 TDD 固定 launcher 运行时核心逻辑，避免直接堆脚本。

**文件：**
- Create: `backend/tests/test_release_runtime.py`
- Create: `release/launcher/runtime.py`

**Step 1: 先写失败测试**

至少覆盖：
- `find_free_port()` 返回正整数端口
- `build_frontend_url(port)` 返回 `http://127.0.0.1:{port}`
- `resolve_project_paths(base_dir)` 返回 backend/data/frontend-out 的绝对路径

**Step 2: 运行测试确认失败**

```bash
pytest backend/tests/test_release_runtime.py -v
```
期望：FAIL —— 模块不存在。

**Step 3: 编写最小实现**

实现纯函数：
- `find_free_port()`
- `build_frontend_url(port)`
- `resolve_project_paths(base_dir)`

**Step 4: 再次运行测试确认通过**

```bash
pytest backend/tests/test_release_runtime.py -v
```

**Step 5: 提交**

```bash
git add backend/tests/test_release_runtime.py release/launcher/runtime.py
git commit -m "feat: add release launcher runtime helpers"
```

---

### 任务 4：实现 launcher 主程序

**目标：** 提供一个本地桌面入口：启动后端、启动静态文件服务、打开浏览器。

**文件：**
- Create: `release/launcher/app.py`
- Modify: `release/launcher/runtime.py`
- Verify: `python -m release.launcher.app --help` 或 dry-run

**Step 1: 先写失败测试**

如果主程序可测试成本过高，至少先对这些辅助函数写测试：
- 生成后端启动命令
- 生成静态服务启动命令
- 生成打开浏览器 URL

**Step 2: 实现最小主程序**

主程序应：
1. 找两个空闲端口（backend/frontend）
2. 启动 uvicorn 后端子进程
3. 启动静态文件 HTTP 服务子进程
4. 轮询 `/api/health`
5. 调用 `webbrowser.open(url)`
6. 保持进程存活，退出时清理子进程

**Step 3: 本地验证**

```bash
python -m release.launcher.app --dry-run
```
或提供 `--no-browser` 选项。

**Step 4: 提交**

```bash
git add release/launcher
git commit -m "feat: add local webapp launcher for windows release"
```

---

### 任务 5：补 Windows 打包脚本

**目标：** 能在 Windows runner 上一条命令产出 portable 包目录。

**文件：**
- Create: `release/scripts/build_frontend_static.ps1`
- Create: `release/scripts/package_windows_portable.ps1`
- Create: `release/windows/app.manifest`

**Step 1: 先写失败验证**

手动检查仓库当前不存在任何 Windows 打包脚本。

**Step 2: 编写脚本**

脚本要做：
- 安装前端依赖并 `npm run build`
- 验证 `frontend/out` 存在
- 安装 Python 打包依赖（如 `pyinstaller`）
- 打包 launcher
- 复制 `backend/app`、`data/`、`frontend/out` 到 dist
- 压缩成 zip

**Step 3: 静态审查**

至少保证：
- 路径全部用 PowerShell 绝对路径处理
- 输出目录固定，如 `dist/windows-portable/`

**Step 4: 提交**

```bash
git add release/scripts release/windows
git commit -m "build: add windows portable packaging scripts"
```

---

### 任务 6：补 GitHub Actions Release workflow

**目标：** push tag 后自动构建并上传 Release 资产。

**文件：**
- Create: `.github/workflows/release-windows.yml`

**Step 1: 先写失败验证**

确认仓库当前没有 `.github/workflows/*.yml`。

**Step 2: 实现 workflow**

触发条件：
- `push.tags: ['v*']`

主要步骤：
1. checkout
2. setup-node
3. setup-python
4. 运行 `release/scripts/build_frontend_static.ps1`
5. 运行 `release/scripts/package_windows_portable.ps1`
6. 创建 GitHub Release
7. 上传 zip 资产

**Step 3: YAML 自检**

至少检查：
- 路径引用存在
- `permissions.contents: write`
- 资产路径与脚本输出一致

**Step 4: 提交**

```bash
git add .github/workflows/release-windows.yml
git commit -m "ci: add windows github release workflow"
```

---

### 任务 7：补 README Release 章节

**目标：** 让用户知道如何下载 release、如何本地打 tag 触发发布。

**文件：**
- Modify: `README.md`

**Step 1: 补充内容**

新增：
- Releases 下载说明
- portable zip 说明
- tag 发布命令
- 当前限制（尚无 setup 安装器）

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add github release usage guide"
```

---

### 任务 8：整体验证

**目标：** 确认本地代码与 CI 逻辑至少在当前环境下自洽。

**文件：**
- Verify only

**Step 1: 运行后端测试**

```bash
cd backend && pytest -q
```

**Step 2: 运行前端测试和构建**

```bash
cd frontend && npm test -- --runInBand
cd frontend && npm run build
```

**Step 3: 运行 release 相关测试**

```bash
pytest backend/tests/test_release_runtime.py -v
```

**Step 4: 提交最终验证通过状态**

```bash
git add .
git commit -m "chore: finalize windows release foundation"
```

---

## 验收标准

完成后应满足：

- [ ] 仓库存在清晰的 Windows release 计划
- [ ] 前端可静态导出
- [ ] 存在 launcher 运行时模块及测试
- [ ] 存在 Windows portable 打包脚本
- [ ] 存在 GitHub Actions release workflow
- [ ] `v*` tag 可触发 GitHub Release 自动构建资产
- [ ] README 说明用户如何下载和触发 release

---

## 风险与取舍

1. **本轮先不做安装器**
   - 因为安装器会显著增加 CI 复杂度
   - 先交付 portable zip 更快落地

2. **本轮先不打单文件 onefile exe**
   - onefile 对资源路径和冷启动更敏感
   - 建议先做 one-folder portable，更稳

3. **真实 OCR / OpenCV Windows 依赖可能增大包体积**
   - 第一版优先追求可运行，不先优化体积

4. **GitHub Actions 只能验证构建，不等于验证所有用户机器环境**
   - 发布后仍需要真实 Windows 机回归测试
