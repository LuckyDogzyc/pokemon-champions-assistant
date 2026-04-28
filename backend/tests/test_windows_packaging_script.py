from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO_ROOT / "release" / "scripts" / "package_windows_portable.ps1"


def test_windows_packaging_script_collects_backend_runtime_dependencies() -> None:
    script = PACKAGE_SCRIPT.read_text(encoding="utf-8")

    assert "python -m pip install -e './backend[ocr]'" in script
    assert "--paths (Join-Path $repoRoot 'backend')" in script
    assert "--hidden-import app.main" in script
    assert "--collect-all imageio_ffmpeg" in script
    assert "--collect-submodules pygrabber" in script
    assert "--hidden-import pygrabber.dshow_graph" in script
    # RapidOCR replaces paddleocr — no paddle/paddleocr bundles needed
    assert "--collect-all rapidocr_onnxruntime" in script
    assert "--collect-all paddleocr" not in script
    assert "--collect-all paddle" not in script


def test_backend_ocr_extra_includes_rapidocr() -> None:
    pyproject = (REPO_ROOT / 'backend' / 'pyproject.toml').read_text(encoding='utf-8')

    assert '"rapidocr-onnxruntime>=' in pyproject
    # paddleocr, paddle2onnx, onnxruntime are no longer direct deps —
    # rapidocr-onnxruntime pulls in onnxruntime automatically
    assert '"paddleocr>=' not in pyproject
    assert '"paddle2onnx>=' not in pyproject
    assert '"paddlepaddle>=' not in pyproject


def test_backend_pyproject_prefers_headless_opencv_and_windows_enumerator_dependency() -> None:
    pyproject = (REPO_ROOT / 'backend' / 'pyproject.toml').read_text(encoding='utf-8')

    assert 'opencv-python-headless>=' in pyproject
    assert 'pygrabber>=' in pyproject
    assert 'opencv-python>=' not in pyproject
