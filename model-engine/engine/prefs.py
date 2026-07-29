"""Persist last-used parameter values per generator.

Stored as JSON next to the add-in so settings survive Fusion restarts without
touching Fusion's own preference system.
"""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PREFS_PATH = os.path.abspath(os.path.join(_THIS_DIR, "..", "last_params.json"))


def load_all() -> dict:
    try:
        with open(_PREFS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def load_for(generator_id: str) -> dict:
    return load_all().get(generator_id, {})


def save_for(generator_id: str, params: dict) -> None:
    data = load_all()
    # JSON-friendly values only
    clean = {}
    for key, value in params.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = value
        else:
            clean[key] = str(value)
    data[generator_id] = clean
    try:
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except OSError:
        pass  # non-fatal if the folder is read-only
