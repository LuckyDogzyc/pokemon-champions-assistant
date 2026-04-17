from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from release.launcher.app import create_frontend_server
from release.launcher.runtime import build_runtime_config, find_free_port


class BackendHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/health":
            payload = json.dumps({"status": "ok", "via": "backend"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/echo":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def test_create_frontend_server_serves_static_files_and_proxies_api(tmp_path: Path) -> None:
    base_dir = tmp_path / "portable-root"
    (base_dir / "backend" / "app").mkdir(parents=True)
    (base_dir / "data").mkdir(parents=True)
    frontend_out_dir = base_dir / "frontend" / "out"
    frontend_out_dir.mkdir(parents=True)
    (frontend_out_dir / "index.html").write_text("<html><body>release frontend</body></html>", encoding="utf-8")

    backend_port = find_free_port()
    backend_server = ThreadingHTTPServer(("127.0.0.1", backend_port), BackendHandler)
    backend_thread = threading.Thread(target=backend_server.serve_forever, daemon=True)
    backend_thread.start()

    config = build_runtime_config(base_dir=base_dir, backend_port=backend_port, frontend_port=find_free_port())
    frontend_server = create_frontend_server(config)
    frontend_thread = threading.Thread(target=frontend_server.serve_forever, daemon=True)
    frontend_thread.start()

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{config.frontend_port}/", timeout=3) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert "release frontend" in html

        with urllib.request.urlopen(f"http://127.0.0.1:{config.frontend_port}/api/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload == {"status": "ok", "via": "backend"}

        request = urllib.request.Request(
            f"http://127.0.0.1:{config.frontend_port}/api/echo",
            data=json.dumps({"name": "喷火龙"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert payload == {"name": "喷火龙"}
    finally:
        frontend_server.shutdown()
        frontend_server.server_close()
        backend_server.shutdown()
        backend_server.server_close()
        frontend_thread.join(timeout=2)
        backend_thread.join(timeout=2)


def test_create_frontend_server_returns_bad_gateway_when_backend_is_unreachable(tmp_path: Path) -> None:
    base_dir = tmp_path / "portable-root"
    (base_dir / "backend" / "app").mkdir(parents=True)
    (base_dir / "data").mkdir(parents=True)
    frontend_out_dir = base_dir / "frontend" / "out"
    frontend_out_dir.mkdir(parents=True)
    (frontend_out_dir / "index.html").write_text("<html><body>release frontend</body></html>", encoding="utf-8")

    config = build_runtime_config(base_dir=base_dir, backend_port=find_free_port(), frontend_port=find_free_port())
    frontend_server = create_frontend_server(config)
    frontend_thread = threading.Thread(target=frontend_server.serve_forever, daemon=True)
    frontend_thread.start()

    try:
        request = urllib.request.Request(f"http://127.0.0.1:{config.frontend_port}/api/health", method="GET")
        with urllib.request.urlopen(request, timeout=3):
            raise AssertionError("Expected the frontend proxy to return HTTP 502 when backend is unreachable")
    except urllib.error.HTTPError as error:
        assert error.code == 502
    finally:
        frontend_server.shutdown()
        frontend_server.server_close()
        frontend_thread.join(timeout=2)
