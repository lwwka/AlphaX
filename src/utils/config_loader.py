from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.models.schemas import AccountConfig


def _load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_settings(path: str | Path = "config/settings.yaml") -> dict[str, Any]:
    load_dotenv()
    settings = _load_yaml(path)
    _validate_settings(settings)
    return settings


def load_accounts(path: str | Path = "config/accounts.yaml") -> list[AccountConfig]:
    payload = _load_yaml(path)
    accounts = payload.get("accounts", [])
    return [
        AccountConfig(
            handle=item["handle"],
            user_id=str(item["user_id"]),
            weight=float(item.get("weight", 1.0)),
            focus=list(item.get("focus", [])),
        )
        for item in accounts
    ]


def load_entity_map(path: str | Path = "config/entity_map.yaml") -> dict[str, Any]:
    return _load_yaml(path)


def read_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def _validate_settings(settings: dict[str, Any]) -> None:
    required_sections = ["twitter", "llm", "thresholds", "signal_rules", "paths"]
    missing = [key for key in required_sections if key not in settings]
    if missing:
        raise RuntimeError(f"settings.yaml is missing sections: {', '.join(missing)}")
