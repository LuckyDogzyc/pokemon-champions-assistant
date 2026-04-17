from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO_ROOT / "release" / "scripts" / "package_windows_portable.ps1"


def test_windows_packaging_script_collects_backend_runtime_dependencies() -> None:
    script = PACKAGE_SCRIPT.read_text(encoding="utf-8")

    assert "--paths (Join-Path $repoRoot 'backend')" in script
    assert "--hidden-import app.main" in script
