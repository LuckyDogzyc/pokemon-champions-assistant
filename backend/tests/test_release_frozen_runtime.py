from pathlib import Path
import sys

import release.launcher.app as launcher_app


def test_detect_base_dir_uses_meipass_when_frozen(monkeypatch):
    fake_meipass = Path('/tmp/fake-bundle/_internal')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(fake_meipass), raising=False)
    monkeypatch.setattr(sys, 'executable', '/tmp/fake-bundle/PokemonChampionsAssistantLauncher', raising=False)

    assert launcher_app.detect_base_dir() == fake_meipass.resolve()


def test_detect_base_dir_falls_back_to_executable_parent_when_frozen_without_meipass(monkeypatch):
    fake_executable = Path('/tmp/fake-bundle/PokemonChampionsAssistantLauncher')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    if hasattr(sys, '_MEIPASS'):
        monkeypatch.delattr(sys, '_MEIPASS', raising=False)
    monkeypatch.setattr(sys, 'executable', str(fake_executable), raising=False)

    assert launcher_app.detect_base_dir() == fake_executable.resolve().parent
