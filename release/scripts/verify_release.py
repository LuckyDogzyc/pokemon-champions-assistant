#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from release.launcher.runtime import find_free_port


FRONTEND_DIR = REPO_ROOT / "frontend"


def normalize_command(command: list[str]) -> list[str]:
    if os.name == "nt" and command and command[0] == "npm":
        return ["npm.cmd", *command[1:]]
    return command


def run(command: list[str], cwd: Path | None = None) -> None:
    normalized_command = normalize_command(command)
    print(f"\n>>> {' '.join(normalized_command)}")
    subprocess.run(normalized_command, cwd=cwd or REPO_ROOT, check=True)


def wait_for_url(url: str, timeout_seconds: float = 20.0) -> str:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}") from last_error


def smoke_test_launcher() -> None:
    backend_port = find_free_port()
    frontend_port = find_free_port()
    command = [
        sys.executable,
        "-m",
        "release.launcher.app",
        "--no-browser",
        "--backend-port",
        str(backend_port),
        "--frontend-port",
        str(frontend_port),
    ]
    print(f"\n>>> {' '.join(command)}")
    process = subprocess.Popen(command, cwd=REPO_ROOT)
    try:
        frontend_html = wait_for_url(f"http://127.0.0.1:{frontend_port}/")
        proxied_health = wait_for_url(f"http://127.0.0.1:{frontend_port}/api/health")
        direct_health = wait_for_url(f"http://127.0.0.1:{backend_port}/api/health")
        if "Pokemon Champions Assistant" not in frontend_html:
            raise RuntimeError("Launcher smoke test failed: frontend HTML missing expected title")
        if '"status":"ok"' not in proxied_health:
            raise RuntimeError("Launcher smoke test failed: proxied /api/health is not healthy")
        if '"status":"ok"' not in direct_health:
            raise RuntimeError("Launcher smoke test failed: backend /api/health is not healthy")
        print("Launcher smoke test passed.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Pokemon Champions Assistant release readiness")
    parser.add_argument("--skip-smoke-test", action="store_true", help="Skip live launcher smoke test")
    args = parser.parse_args()

    run([sys.executable, "-m", "pytest", "backend/tests/test_release_runtime.py", "-q"])
    run([sys.executable, "-m", "pytest", "backend/tests/test_release_frontend_server.py", "-q"])
    run([sys.executable, "-m", "pytest", "backend/tests/", "-q"])
    if not (FRONTEND_DIR / "node_modules").exists():
        if os.name == "nt":
            raise SystemExit("frontend/node_modules 缺失；请先在 frontend 目录运行 npm install，再执行 verify_release.py")
        run(["npm", "install"], cwd=FRONTEND_DIR)
    run(["npm", "test", "--", "--runInBand"], cwd=FRONTEND_DIR)
    run(["npm", "run", "build"], cwd=FRONTEND_DIR)

    dry_run_output = subprocess.check_output(
        [sys.executable, "-m", "release.launcher.app", "--dry-run"],
        cwd=REPO_ROOT,
        text=True,
    )
    json.loads(dry_run_output)
    print("Launcher dry-run passed.")

    if not args.skip_smoke_test:
        smoke_test_launcher()

    print("\nRelease verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
