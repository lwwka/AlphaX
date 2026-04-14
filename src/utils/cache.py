from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def make_cache_key(payload: Any) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cache(key: str, cache_dir: str | Path) -> dict[str, Any] | list[Any] | None:
    path = Path(cache_dir) / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_cache(key: str, data: Any, cache_dir: str | Path) -> None:
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{key}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
