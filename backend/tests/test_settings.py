from app.main import app
from app.core.settings import get_settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_api_name_default():
    clear_settings_cache()
    settings = get_settings()

    assert settings.api_name == "Pokemon Champions Assistant API"
    assert settings.backend_port == 8000
    assert app.title == settings.api_name
    assert app.state.backend_port == settings.backend_port


def test_default_frame_interval_seconds():
    clear_settings_cache()
    settings = get_settings()

    assert settings.frame_interval_seconds == 3


def test_default_language_is_zh():
    clear_settings_cache()
    settings = get_settings()

    assert settings.language == "zh"


def test_stage_recognition_enabled_by_default():
    clear_settings_cache()
    settings = get_settings()

    assert settings.stage_recognition_enabled is True


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("PCA_API_NAME", "Custom API")
    monkeypatch.setenv("PCA_FRAME_INTERVAL_SECONDS", "5")
    monkeypatch.setenv("PCA_LANGUAGE", "en")
    monkeypatch.setenv("PCA_STAGE_RECOGNITION_ENABLED", "false")

    clear_settings_cache()
    settings = get_settings()

    assert settings.api_name == "Custom API"
    assert settings.frame_interval_seconds == 5
    assert settings.language == "en"
    assert settings.stage_recognition_enabled is False

    clear_settings_cache()
