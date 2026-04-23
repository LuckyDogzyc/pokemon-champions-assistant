from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO_ROOT / "release" / "scripts" / "package_windows_portable.ps1"


def test_windows_packaging_script_collects_backend_runtime_dependencies() -> None:
    script = PACKAGE_SCRIPT.read_text(encoding="utf-8")

    assert "python -m pip install -e './backend[ocr]'" in script
    assert "$env:PADDLE_OCR_BASE_DIR" in script
    assert "python release/scripts/bootstrap_paddleocr_assets.py --output-dir $ocrBundleRoot" in script
    assert "Remove-Item -Recurse -Force $ocrBundleRoot" not in script
    assert "--add-data \"$ocrBundleRoot;.paddleocr\"" in script
    assert "--paths (Join-Path $repoRoot 'backend')" in script
    assert "--hidden-import app.main" in script
    assert "--collect-all imageio_ffmpeg" in script
    assert "--collect-submodules pygrabber" in script
    assert "--hidden-import pygrabber.dshow_graph" in script
    assert "--collect-all paddleocr" in script
    assert "--collect-submodules paddleocr" in script
    assert "--collect-all paddle" in script
    assert "--collect-data Cython" in script


def test_backend_ocr_extra_includes_paddle_runtime_dependency() -> None:
    pyproject = (REPO_ROOT / 'backend' / 'pyproject.toml').read_text(encoding='utf-8')

    assert '"paddleocr>=' in pyproject
    assert '"paddlepaddle>=' in pyproject


def test_backend_pyproject_prefers_headless_opencv_and_windows_enumerator_dependency() -> None:
    pyproject = (REPO_ROOT / 'backend' / 'pyproject.toml').read_text(encoding='utf-8')

    assert 'opencv-python-headless>=' in pyproject
    assert 'pygrabber>=' in pyproject
    assert 'opencv-python>=' not in pyproject
