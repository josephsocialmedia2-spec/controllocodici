from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_FOLDER_NAME = "F1AssistenteTelefonico"

DEFAULT_CONFIG: dict[str, Any] = {
    "customer_device_index": None,
    "customer_device_name": "",
    "microphone_device_index": None,
    "microphone_device_name": "",
    "always_on_top": True,
    "selected_script": "",
    "audio_chunk_ms": 100,
}


def config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_FOLDER_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    data = dict(DEFAULT_CONFIG)
    path = config_path()
    if not path.exists():
        return data
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data.update(loaded)
    except (OSError, json.JSONDecodeError):
        pass
    return data


def save_config(config: dict[str, Any]) -> Path:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = config_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return path
