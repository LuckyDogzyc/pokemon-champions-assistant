from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable, Mapping, Any

try:
    from scripts.champions.sources.official import fetch_official_ma1_pokemon_list
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.champions.sources.official import fetch_official_ma1_pokemon_list


JsonDict = dict[str, Any]
Fetcher = Callable[[], JsonDict]


def _default_version_provider() -> str:
    from datetime import datetime, UTC

    return datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")


def _default_data_root() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "champions"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _backup_current(current_dir: Path, backups_dir: Path, version: str) -> Path | None:
    if not current_dir.exists() or not any(current_dir.iterdir()):
        return None

    backup_dir = backups_dir / version
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(current_dir, backup_dir, dirs_exist_ok=True)
    return backup_dir


def build_default_fetchers(
    *,
    official_html_fetcher: Callable[[str], str] | None = None,
    pokemon_index: list[dict[str, Any]] | None = None,
    aliases_zh: dict[str, str] | None = None,
) -> dict[str, Fetcher]:
    return {
        "official": lambda: fetch_official_ma1_pokemon_list(
            html_fetcher=official_html_fetcher,
            pokemon_index=pokemon_index,
            aliases_zh=aliases_zh,
        ),
    }


def update_champions_database(
    *,
    data_root: Path,
    fetchers: Mapping[str, Fetcher],
    version_provider: Callable[[], str] | None = None,
) -> dict[str, Any]:
    version = (version_provider or _default_version_provider)()
    current_dir = data_root / "current"
    backups_dir = data_root / "backups"
    staging_dir = data_root / "staging"

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    aggregated_files: dict[str, Any] = {}
    manifest_sources: dict[str, Any] = {}

    for source_name, fetcher in fetchers.items():
        result = fetcher()
        source_files = dict(result.get("files") or {})
        aggregated_files.update(source_files)
        manifest_sources[source_name] = dict(result.get("meta") or {})

    manifest = {
        "version": version,
        "generated_at": version,
        "sources": manifest_sources,
    }
    aggregated_files["source-manifest.json"] = manifest

    for filename, payload in aggregated_files.items():
        _write_json(staging_dir / filename, payload)

    backup_dir = _backup_current(current_dir, backups_dir, version)

    if current_dir.exists():
        shutil.rmtree(current_dir)
    shutil.move(str(staging_dir), str(current_dir))

    return {
        "version": version,
        "current_dir": str(current_dir),
        "backup_dir": str(backup_dir) if backup_dir is not None else None,
        "files_written": sorted(aggregated_files.keys()),
    }


def run_update(
    *,
    data_root: Path | None = None,
    official_html_fetcher: Callable[[str], str] | None = None,
    version_provider: Callable[[], str] | None = None,
    pokemon_index: list[dict[str, Any]] | None = None,
    aliases_zh: dict[str, str] | None = None,
) -> dict[str, Any]:
    return update_champions_database(
        data_root=data_root or _default_data_root(),
        fetchers=build_default_fetchers(
            official_html_fetcher=official_html_fetcher,
            pokemon_index=pokemon_index,
            aliases_zh=aliases_zh,
        ),
        version_provider=version_provider,
    )


if __name__ == "__main__":
    summary = run_update()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
