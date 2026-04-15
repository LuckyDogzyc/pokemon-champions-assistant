from pathlib import Path

from release.launcher.runtime import (
    LauncherConfig,
    build_backend_health_url,
    build_frontend_url,
    build_runtime_config,
    find_free_port,
    resolve_project_paths,
)


def test_find_free_port_returns_positive_integer():
    port = find_free_port()

    assert isinstance(port, int)
    assert port > 0


def test_build_frontend_url_uses_loopback_address():
    assert build_frontend_url(43123) == "http://127.0.0.1:43123"


def test_build_backend_health_url_points_to_api_health():
    assert build_backend_health_url(8000) == "http://127.0.0.1:8000/api/health"


def test_resolve_project_paths_returns_expected_release_directories(tmp_path: Path):
    base_dir = tmp_path / "runtime-root"
    backend_dir = base_dir / "backend" / "app"
    data_dir = base_dir / "data"
    frontend_out_dir = base_dir / "frontend" / "out"

    backend_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    frontend_out_dir.mkdir(parents=True)

    paths = resolve_project_paths(base_dir)

    assert paths.backend_app_dir == backend_dir
    assert paths.data_dir == data_dir
    assert paths.frontend_out_dir == frontend_out_dir


def test_build_runtime_config_uses_requested_ports_and_paths(tmp_path: Path):
    base_dir = tmp_path / "runtime-root"
    (base_dir / "backend" / "app").mkdir(parents=True)
    (base_dir / "data").mkdir(parents=True)
    (base_dir / "frontend" / "out").mkdir(parents=True)

    config = build_runtime_config(base_dir=base_dir, backend_port=18000, frontend_port=13000)

    assert isinstance(config, LauncherConfig)
    assert config.backend_port == 18000
    assert config.frontend_port == 13000
    assert config.frontend_url == "http://127.0.0.1:13000"
    assert config.backend_health_url == "http://127.0.0.1:18000/api/health"
    assert config.paths.frontend_out_dir == base_dir / "frontend" / "out"
