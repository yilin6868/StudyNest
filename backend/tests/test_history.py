from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.services.history import HistoryService
from app.services.store import JsonStore

client = TestClient(app)
FIXED_TIME = datetime(2026, 9, 8, 23, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_record_increments_distinct_sessions(tmp_path):
    service = HistoryService(JsonStore(tmp_path))
    service.record(25, "session-1", completed_at=FIXED_TIME)
    service.record(25, "session-2", completed_at=FIXED_TIME)
    data = service.get()
    assert data["days"]["2026-09-08"] == {"tomato": 2, "minutes": 50}
    assert set(data["completedSessions"]) == {"session-1", "session-2"}


def test_same_session_is_only_recorded_once(tmp_path):
    service = HistoryService(JsonStore(tmp_path))
    _, first_created = service.record(25, "same-session", completed_at=FIXED_TIME)
    data, second_created = service.record(50, "same-session", completed_at=FIXED_TIME)
    assert first_created is True
    assert second_created is False
    assert data["days"]["2026-09-08"] == {"tomato": 1, "minutes": 25}


def test_history_persists_across_instances(tmp_path):
    store = JsonStore(tmp_path)
    HistoryService(store).record(25, "persisted", completed_at=FIXED_TIME)
    data = HistoryService(store).get()
    assert data["days"]["2026-09-08"]["tomato"] == 1


def test_version_one_history_is_compatible(tmp_path):
    store = JsonStore(tmp_path)
    store.write(
        "history",
        {"schemaVersion": 1, "days": {"2026-09-07": {"tomato": 1, "minutes": 25}}},
    )
    data = HistoryService(store).get()
    assert data["schemaVersion"] == 2
    assert data["days"]["2026-09-07"]["tomato"] == 1
    assert data["completedSessions"] == {}


def test_history_api_does_not_expose_session_ids(auth_headers):
    response = client.get("/api/v1/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert "totalTomato" in data
    assert "totalMinutes" in data
    assert "completedSessions" not in data
