from __future__ import annotations

from pathlib import Path

import release.scripts.verify_release as verify_release


def test_verify_release_skip_frontend_modes_does_not_require_node_modules(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    frontend_dir = repo_root / "frontend"
    frontend_out_dir = frontend_dir / "out"
    frontend_out_dir.mkdir(parents=True)
    (frontend_out_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (frontend_out_dir / "404.html").write_text("<html>404</html>", encoding="utf-8")
    (frontend_out_dir / "_next").mkdir()

    recorded_commands: list[list[str]] = []

    def fake_run(command: list[str], cwd: Path | None = None) -> None:
        recorded_commands.append(command)

    monkeypatch.setattr(verify_release, "REPO_ROOT", repo_root)
    monkeypatch.setattr(verify_release, "FRONTEND_DIR", frontend_dir)
    monkeypatch.setattr(verify_release, "run", fake_run)
    monkeypatch.setattr(verify_release, "smoke_test_launcher", lambda: None)
    monkeypatch.setattr(verify_release.subprocess, "check_output", lambda *args, **kwargs: "{}")
    monkeypatch.setattr(
        verify_release.sys,
        "argv",
        [
            "verify_release.py",
            "--skip-frontend-tests",
            "--skip-frontend-build",
            "--skip-smoke-test",
        ],
    )

    assert verify_release.main() == 0
    assert recorded_commands == [
        [verify_release.sys.executable, "-m", "pytest", "backend/tests/test_release_runtime.py", "-q"],
        [verify_release.sys.executable, "-m", "pytest", "backend/tests/test_release_frontend_server.py", "-q"],
        [verify_release.sys.executable, "-m", "pytest", "backend/tests/", "-q"],
    ]
