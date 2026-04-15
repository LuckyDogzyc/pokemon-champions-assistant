from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import uvicorn

from release.launcher.runtime import LauncherConfig, build_runtime_config


def detect_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pokemon Champions Assistant Windows launcher")
    parser.add_argument("--base-dir", default=None, help="项目或打包产物根目录")
    parser.add_argument("--backend-port", type=int, default=None)
    parser.add_argument("--frontend-port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_paths(config: LauncherConfig) -> None:
    if not config.paths.backend_app_dir.exists():
        raise FileNotFoundError(f"backend app 目录不存在: {config.paths.backend_app_dir}")
    if not config.paths.data_dir.exists():
        raise FileNotFoundError(f"data 目录不存在: {config.paths.data_dir}")
    if not config.paths.frontend_out_dir.exists():
        raise FileNotFoundError(f"frontend out 目录不存在: {config.paths.frontend_out_dir}")


def run_backend_server(config: LauncherConfig) -> None:
    project_root = str(config.paths.backend_app_dir.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    uvicorn.run("app.main:app", host="127.0.0.1", port=config.backend_port, reload=False, log_level="info")


def run_frontend_server(config: LauncherConfig) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(config.paths.frontend_out_dir))
    server = ThreadingHTTPServer(("127.0.0.1", config.frontend_port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def wait_for_healthcheck(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"后端健康检查失败: {url}") from last_error


def run_launcher(config: LauncherConfig, no_browser: bool = False) -> None:
    validate_paths(config)
    backend_thread = threading.Thread(target=run_backend_server, args=(config,), daemon=True)
    frontend_thread = threading.Thread(target=run_frontend_server, args=(config,), daemon=True)
    backend_thread.start()
    frontend_thread.start()
    wait_for_healthcheck(config.backend_health_url)
    if not no_browser:
        webbrowser.open(config.frontend_url)
    while True:
        time.sleep(1)


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir).resolve() if args.base_dir else detect_base_dir()
    config = build_runtime_config(
        base_dir=base_dir,
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "base_dir": str(base_dir),
                    "backend_port": config.backend_port,
                    "frontend_port": config.frontend_port,
                    "backend_health_url": config.backend_health_url,
                    "frontend_url": config.frontend_url,
                    "backend_app_dir": str(config.paths.backend_app_dir),
                    "data_dir": str(config.paths.data_dir),
                    "frontend_out_dir": str(config.paths.frontend_out_dir),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    run_launcher(config, no_browser=args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
