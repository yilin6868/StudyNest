from app.services.store import JsonStore


def test_read_missing_returns_default(tmp_path):
    store = JsonStore(tmp_path)
    assert store.read("x", {"a": 1}) == {"a": 1}


def test_write_then_read_roundtrip(tmp_path):
    store = JsonStore(tmp_path)
    store.write("x", {"a": 1, "b": "中文"})
    assert store.read("x", {}) == {"a": 1, "b": "中文"}


def test_corrupted_file_falls_back(tmp_path):
    store = JsonStore(tmp_path)
    (tmp_path / "x.json").write_text("{broken json", encoding="utf-8")
    assert store.read("x", {"default": True}) == {"default": True}


def test_atomic_write_leaves_no_tmp(tmp_path):
    store = JsonStore(tmp_path)
    store.write("x", {"a": 1})
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []
