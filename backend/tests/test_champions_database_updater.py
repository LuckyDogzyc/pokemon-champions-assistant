from __future__ import annotations

import json
from pathlib import Path


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class FixedClock:
    def __init__(self, value: str) -> None:
        self.value = value

    def __call__(self) -> str:
        return self.value


class StubSourceFetcher:
    def __init__(self, payload: dict, meta: dict | None = None) -> None:
        self.payload = payload
        self.meta = meta or {}
        self.calls = 0

    def __call__(self) -> dict:
        self.calls += 1
        return {
            "files": self.payload,
            "meta": self.meta,
        }


def test_update_champions_database_writes_current_dataset_and_manifest(tmp_path: Path):
    from scripts.champions.update_database import update_champions_database

    fetchers = {
        "pikalytics": StubSourceFetcher(
            payload={
                "pokemon.json": [{"id": "006", "name": "Charizard"}],
                "meta-usage.json": {"format": "champions"},
            },
            meta={"format": "championstournaments-1760", "snapshot": "2026-03"},
        ),
        "pokebase": StubSourceFetcher(
            payload={
                "moves.json": [{"id": "flamethrower", "name": "Flamethrower"}],
            },
            meta={"pages_fetched": 2},
        ),
    }

    summary = update_champions_database(
        data_root=tmp_path / "data" / "champions",
        fetchers=fetchers,
        version_provider=FixedClock("2026-04-19_090000"),
    )

    current_dir = tmp_path / "data" / "champions" / "current"
    assert summary["version"] == "2026-04-19_090000"
    assert current_dir.exists()
    assert _read_json(current_dir / "pokemon.json") == [{"id": "006", "name": "Charizard"}]
    assert _read_json(current_dir / "moves.json") == [{"id": "flamethrower", "name": "Flamethrower"}]
    assert _read_json(current_dir / "meta-usage.json") == {"format": "champions"}

    manifest = _read_json(current_dir / "source-manifest.json")
    assert manifest["version"] == "2026-04-19_090000"
    assert manifest["sources"]["pikalytics"]["format"] == "championstournaments-1760"
    assert manifest["sources"]["pokebase"]["pages_fetched"] == 2
    assert fetchers["pikalytics"].calls == 1
    assert fetchers["pokebase"].calls == 1


def test_update_champions_database_backs_up_previous_current_before_replacing(tmp_path: Path):
    from scripts.champions.update_database import update_champions_database

    current_dir = tmp_path / "data" / "champions" / "current"
    current_dir.mkdir(parents=True)
    (current_dir / "pokemon.json").write_text('[{"id": "001", "name": "Bulbasaur"}]', encoding="utf-8")
    (current_dir / "source-manifest.json").write_text('{"version": "old-version"}', encoding="utf-8")

    summary = update_champions_database(
        data_root=tmp_path / "data" / "champions",
        fetchers={
            "pikalytics": StubSourceFetcher(
                payload={"pokemon.json": [{"id": "025", "name": "Pikachu"}]},
                meta={"snapshot": "2026-04"},
            )
        },
        version_provider=FixedClock("2026-04-19_091500"),
    )

    backup_dir = tmp_path / "data" / "champions" / "backups" / "2026-04-19_091500"
    assert summary["backup_dir"] == str(backup_dir)
    assert backup_dir.exists()
    assert _read_json(backup_dir / "pokemon.json") == [{"id": "001", "name": "Bulbasaur"}]
    assert _read_json(tmp_path / "data" / "champions" / "current" / "pokemon.json") == [{"id": "025", "name": "Pikachu"}]


def test_update_champions_database_cleans_staging_directory_after_success(tmp_path: Path):
    from scripts.champions.update_database import update_champions_database

    update_champions_database(
        data_root=tmp_path / "data" / "champions",
        fetchers={
            "pikalytics": StubSourceFetcher(payload={"pokemon.json": [{"id": "006"}]})
        },
        version_provider=FixedClock("2026-04-19_093000"),
    )

    staging_dir = tmp_path / "data" / "champions" / "staging"
    assert not staging_dir.exists()
