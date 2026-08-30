"""结构化 JSON 文件持久化：临时文件 + 原子替换，损坏时回退默认值。"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    def read(self, name: str, default: dict) -> dict:
        p = self._path(name)
        if not p.exists():
            return dict(default)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return dict(default)
            return data
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            # 文件损坏时回退默认值，不崩
            return dict(default)

    def write(self, name: str, data: dict) -> None:
        p = self._path(name)
        fd, tmp = tempfile.mkstemp(dir=str(self.data_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)  # 原子替换
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
