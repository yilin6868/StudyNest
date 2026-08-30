from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.services.history import HistoryService
from app.services.store import JsonStore

client = TestClient(app)


def test_record_increments(tmp_path):
    svc = HistoryService(JsonStore(tmp_path))
    svc.record(25)
    svc.record(25)
    today = datetime.now().strftime("%Y-%m-%d")
    data = svc.get()
    assert data["days"][today]["tomato"] == 2
    assert data["days"][today]["minutes"] == 50


def test_history_persists_across_instances(tmp_path):
    store = JsonStore(tmp_path)
    HistoryService(store).record(25)
    data = HistoryService(store).get()
    today = datetime.now().strftime("%Y-%m-%d")
    assert data["days"][today]["tomato"] == 1


def test_history_api(auth_headers):
    r = client.get("/api/v1/history", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "days" in data
    assert "totalTomato" in data
    assert "totalMinutes" in data
