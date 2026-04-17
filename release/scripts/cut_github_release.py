#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_SCRIPT = REPO_ROOT / "release" / "scripts" / "verify_release.py"


def run(command: list[str]) -> None:
    print(f"\n>>> {' '.join(command)}")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def get_output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=REPO_ROOT, text=True).strip()


def normalize_tag(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify, tag, and push a GitHub release")
    parser.add_argument("version", help="Release version, e.g. v0.1.0 or 0.1.0")
    parser.add_argument("--skip-verify", action="store_true", help="Skip release verification script")
    args = parser.parse_args()

    tag = normalize_tag(args.version)

    status = get_output(["git", "status", "--short"])
    if status:
        raise SystemExit("Git working tree is not clean. Commit or stash changes before cutting a release.")

    if not args.skip_verify:
        run([sys.executable, str(VERIFY_SCRIPT)])

    existing_tags = get_output(["git", "tag", "--list", tag])
    if existing_tags:
        raise SystemExit(f"Tag already exists: {tag}")

    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
    run(["git", "push", "origin", "main"])
    run(["git", "push", "origin", tag])

    print(f"\nRelease tag pushed: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
