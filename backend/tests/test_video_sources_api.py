from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_video_sources_marks_selected_item(monkeypatch):
    from app.api import video as video_api
    from app.schemas.video import VideoSource
    from app.services.video_source_selection import VideoSourceSelectionStore

    monkeypatch.setattr(
        video_api,
        "video_source_service",
        type(
            "StubVideoSourceService",
            (),
            {
                "list_sources": lambda self: [
                    VideoSource(
                        id="device-0",
                        label="USB Capture Card",
                        backend="opencv",
                        is_capture_card_candidate=True,
                        is_selected=False,
                        device_index=0,
                    ),
                    VideoSource(
                        id="device-1",
                        label="OBS Virtual Camera",
                        backend="opencv",
                        is_capture_card_candidate=False,
                        is_selected=False,
                        device_index=1,
                    ),
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        video_api,
        "selection_store",
        VideoSourceSelectionStore(default_source_id="device-1"),
    )

    response = client.get("/api/video/sources")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sources"]) == 2
    assert payload["sources"][1]["is_selected"] is True
    assert payload["sources"][0]["is_capture_card_candidate"] is True
    assert payload["sources"][0]["device_index"] == 0
    assert payload["sources"][1]["device_index"] == 1


def test_select_video_source_updates_current_selection(monkeypatch):
    from app.api import video as video_api
    from app.schemas.video import VideoSource
    from app.services.video_source_selection import VideoSourceSelectionStore

    monkeypatch.setattr(
        video_api,
        "video_source_service",
        type(
            "StubVideoSourceService",
            (),
            {
                "list_sources": lambda self: [
                    VideoSource(
                        id="device-0",
                        label="USB Capture Card",
                        backend="opencv",
                        is_capture_card_candidate=True,
                        is_selected=False,
                        device_index=0,
                    ),
                    VideoSource(
                        id="device-1",
                        label="OBS Virtual Camera",
                        backend="opencv",
                        is_capture_card_candidate=False,
                        is_selected=False,
                        device_index=1,
                    ),
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        video_api,
        "selection_store",
        VideoSourceSelectionStore(default_source_id="device-0"),
    )

    response = client.post("/api/video/source/select", json={"source_id": "device-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_source_id"] == "device-1"

    sources_response = client.get("/api/video/sources")
    sources_payload = sources_response.json()
    assert sources_payload["sources"][1]["is_selected"] is True


def test_list_video_sources_prefers_obs_virtual_camera_when_selection_missing(monkeypatch):
    from app.api import video as video_api
    from app.schemas.video import VideoSource
    from app.services.video_source_selection import VideoSourceSelectionStore

    monkeypatch.setattr(
        video_api,
        "video_source_service",
        type(
            "StubVideoSourceService",
            (),
            {
                "list_sources": lambda self: [
                    VideoSource(
                        id="device-0",
                        label="Hagibis",
                        backend="dshow",
                        is_capture_card_candidate=True,
                        is_selected=False,
                        device_index=0,
                        capture_selector="Hagibis",
                        device_kind="physical",
                    ),
                    VideoSource(
                        id="device-1",
                        label="OBS Virtual Camera",
                        backend="opencv",
                        is_capture_card_candidate=False,
                        is_selected=False,
                        device_index=1,
                        capture_selector="OBS Virtual Camera",
                        device_kind="virtual",
                    ),
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        video_api,
        "selection_store",
        VideoSourceSelectionStore(default_source_id="device-missing"),
    )

    response = client.get("/api/video/sources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][1]["is_selected"] is True


def test_start_capture_session_prefers_obs_virtual_camera_when_selection_missing(monkeypatch):
    from app.api import video as video_api
    from app.schemas.video import VideoSource
    from app.services.video_source_selection import VideoSourceSelectionStore

    started_with: dict[str, object] = {}

    monkeypatch.setattr(
        video_api,
        "video_source_service",
        type(
            "StubVideoSourceService",
            (),
            {
                "list_sources": lambda self: [
                    VideoSource(
                        id="device-0",
                        label="Hagibis",
                        backend="dshow",
                        is_capture_card_candidate=True,
                        is_selected=False,
                        device_index=0,
                        capture_selector="Hagibis",
                        device_kind="physical",
                    ),
                    VideoSource(
                        id="device-1",
                        label="OBS Virtual Camera",
                        backend="opencv",
                        is_capture_card_candidate=False,
                        is_selected=False,
                        device_index=1,
                        capture_selector="OBS Virtual Camera",
                        device_kind="virtual",
                    ),
                ]
            },
        )(),
    )
    monkeypatch.setattr(
        video_api,
        "selection_store",
        VideoSourceSelectionStore(default_source_id="device-missing"),
    )
    monkeypatch.setattr(
        video_api,
        "capture_session_service",
        type(
            "StubCaptureSessionService",
            (),
            {
                "start": lambda self, source: started_with.setdefault("source", source) or {"running": True, "source_id": source["id"]},
            },
        )(),
    )

    response = client.post("/api/video/session/start")

    assert response.status_code == 200
    assert started_with["source"]["id"] == "device-1"
    assert started_with["source"]["capture_selector"] == "OBS Virtual Camera"
