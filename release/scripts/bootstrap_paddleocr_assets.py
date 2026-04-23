#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MODEL_SPECS = (
    {
        "name": "det",
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar",
        "sha256": "5f7217e0a89612e2f80d62f3c99a8bf5f7ae9cdc1ffd706be7dde07765627edf",
        "relative_dir": Path("whl/det/ch/ch_PP-OCRv4_det_infer"),
    },
    {
        "name": "rec",
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar",
        "sha256": "830ea228e20c2b30c4db9666066c48512f67a63f5b1a32d0d33dc9170040ce7d",
        "relative_dir": Path("whl/rec/ch/ch_PP-OCRv4_rec_infer"),
    },
    {
        "name": "cls",
        "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
        "sha256": "507352585040d035da3b1e6374694ad679a850acb0a36a8d0d47984176357717",
        "relative_dir": Path("whl/cls/ch_ppocr_mobile_v2.0_cls_infer"),
    },
)

REQUIRED_FILENAMES = ("inference.pdmodel", "inference.pdiparams", "inference.pdiparams.info")


def verify_sha256(path: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"sha256 mismatch for {path}: expected {expected_sha256}, got {actual_sha256}")


def validate_archive_members(members: list[tarfile.TarInfo]) -> None:
    for member in members:
        member_path = Path(member.name)
        if member_path.is_absolute() or ".." in member_path.parts:
            raise RuntimeError(f"Unsafe archive member: {member.name}")


def ensure_model(output_dir: Path, spec: dict[str, object]) -> None:
    target_dir = output_dir / spec["relative_dir"]
    if all((target_dir / filename).exists() for filename in REQUIRED_FILENAMES):
        print(f"[bootstrap_paddleocr_assets] Reusing existing model: {target_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pca-paddleocr-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        archive_path = tmp_dir / "model.tar"
        print(f"[bootstrap_paddleocr_assets] Downloading {spec['url']} -> {archive_path}")
        with urllib.request.urlopen(str(spec["url"])) as response, archive_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        verify_sha256(archive_path, str(spec["sha256"]))

        extract_root = tmp_dir / "extract"
        extract_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r") as archive:
            members = archive.getmembers()
            validate_archive_members(members)
            archive.extractall(extract_root, members=members)

        extracted_dirs = [path for path in extract_root.iterdir() if path.is_dir()]
        if len(extracted_dirs) != 1:
            raise RuntimeError(f"Expected 1 extracted directory for {spec['name']}, got {len(extracted_dirs)}")

        extracted_dir = extracted_dirs[0]
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(extracted_dir, target_dir)
        print(f"[bootstrap_paddleocr_assets] Prepared {spec['name']} model at {target_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap pinned PaddleOCR model assets into a local bundle directory")
    parser.add_argument("--output-dir", required=True, help="Directory that should contain the .paddleocr asset tree")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    for spec in MODEL_SPECS:
        ensure_model(output_dir, spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
