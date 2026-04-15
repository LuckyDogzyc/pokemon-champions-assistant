from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket


@dataclass(frozen=True)
class ProjectPaths:
    backend_app_dir: Path
    data_dir: Path
    frontend_out_dir: Path


@dataclass(frozen=True)
class LauncherConfig:
    backend_port: int
    frontend_port: int
    backend_health_url: str
    frontend_url: str
    paths: ProjectPaths


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_frontend_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def build_backend_health_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/health"


def resolve_project_paths(base_dir: str | Path) -> ProjectPaths:
    root = Path(base_dir).resolve()
    return ProjectPaths(
        backend_app_dir=root / "backend" / "app",
        data_dir=root / "data",
        frontend_out_dir=root / "frontend" / "out",
    )


def build_runtime_config(
    base_dir: str | Path,
    backend_port: int | None = None,
    frontend_port: int | None = None,
) -> LauncherConfig:
    resolved_backend_port = backend_port or find_free_port()
    resolved_frontend_port = frontend_port or find_free_port()
    return LauncherConfig(
        backend_port=resolved_backend_port,
        frontend_port=resolved_frontend_port,
        backend_health_url=build_backend_health_url(resolved_backend_port),
        frontend_url=build_frontend_url(resolved_frontend_port),
        paths=resolve_project_paths(base_dir),
    )
