from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import uvicorn

from release.launcher.runtime import LauncherConfig, build_runtime_config


def detect_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
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
    backend_package_root = str(config.paths.backend_app_dir.parent)
    if backend_package_root not in sys.path:
        sys.path.insert(0, backend_package_root)
    uvicorn.run("app.main:app", host="127.0.0.1", port=config.backend_port, reload=False, log_level="info")


def build_backend_proxy_url(config: LauncherConfig, path: str) -> str:
    return f"http://127.0.0.1:{config.backend_port}{path}"


def create_frontend_server(config: LauncherConfig) -> ThreadingHTTPServer:
    directory = str(config.paths.frontend_out_dir)

    class FrontendRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=directory, **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/"):
                self._proxy_to_backend()
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            if self.path.startswith("/api/"):
                self._proxy_to_backend()
                return
            self.send_error(405, "Method Not Allowed")

        def do_OPTIONS(self) -> None:  # noqa: N802
            if self.path.startswith("/api/"):
                self._proxy_to_backend()
                return
            self.send_error(405, "Method Not Allowed")

        def _proxy_to_backend(self) -> None:
            request_body = self._read_request_body()
            request_headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"host", "connection", "accept-encoding", "content-length"}
            }
            request = urllib.request.Request(
                build_backend_proxy_url(config, self.path),
                data=request_body,
                headers=request_headers,
                method=self.command,
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    response_body = response.read()
                    self.send_response(response.status)
                    self._copy_proxy_headers(response.headers, len(response_body))
                    self.end_headers()
                    self.wfile.write(response_body)
            except urllib.error.HTTPError as error:
                response_body = error.read()
                self.send_response(error.code)
                self._copy_proxy_headers(error.headers, len(response_body))
                self.end_headers()
                self.wfile.write(response_body)
            except urllib.error.URLError:
                response_body = json.dumps({"detail": "backend unavailable"}).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)

        def _read_request_body(self) -> bytes | None:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return None
            return self.rfile.read(length)

        def _copy_proxy_headers(self, headers: object, content_length: int) -> None:
            skipped_headers = {"connection", "content-length", "date", "server", "transfer-encoding"}
            for key, value in headers.items():
                if key.lower() not in skipped_headers:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(content_length))

    return ThreadingHTTPServer(("127.0.0.1", config.frontend_port), FrontendRequestHandler)


def run_frontend_server(config: LauncherConfig) -> None:
    server = create_frontend_server(config)
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
