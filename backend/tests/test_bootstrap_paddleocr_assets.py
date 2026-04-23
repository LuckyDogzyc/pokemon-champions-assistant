from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

import release.scripts.bootstrap_paddleocr_assets as bootstrap


def test_model_specs_include_pinned_sha256() -> None:
    for spec in bootstrap.MODEL_SPECS:
        assert spec["sha256"]
        assert len(str(spec["sha256"])) == 64


def test_verify_sha256_raises_on_mismatch(tmp_path: Path) -> None:
    archive = tmp_path / "model.tar"
    archive.write_bytes(b"not-the-right-archive")

    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        bootstrap.verify_sha256(archive, "0" * 64)


def test_validate_archive_members_rejects_path_traversal() -> None:
    safe_member = tarfile.TarInfo("model/inference.pdmodel")
    unsafe_member = tarfile.TarInfo("../escape.txt")

    with pytest.raises(RuntimeError, match="Unsafe archive member"):
        bootstrap.validate_archive_members([safe_member, unsafe_member])
