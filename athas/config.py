"""
Athas — JSON config manager with auto-save.
"""
import json
from pathlib import Path


DEFAULTS = {
    "loading_screen": {"enabled": True},
    "audio": {"enabled": True, "volume": 0.1},
    "notifications": {"enabled": True, "duration_ms": 8000},
    "git_sync": {"enabled": True, "interval_ms": 15000},
    "player": {
        "name": "Wanderer",
        "rank": "E",
        "level": 1,
        "xp": 0,
        "health": 100,
        "magic": 50,
        "attack": 10,
        "defense": 5,
        "speed": 8,
        "temp_points": 10,
        "temp_allocations": {
            "health": 0,
            "magic": 0,
            "attack": 0,
            "defense": 0,
            "speed": 0,
        },
        "constellation_points": 0,
    },
}


class ConfigManager:
    """Loads, merges defaults, and saves a JSON config file."""

    def __init__(self, path: Path):
        self._path = path
        self._data = {}
        self.load()

    def _merge_defaults(self):
        for section, values in DEFAULTS.items():
            if section not in self._data:
                self._data[section] = {}
            if not isinstance(self._data[section], dict):
                self._data[section] = {}
            for key, default_val in values.items():
                if key not in self._data[section]:
                    self._data[section][key] = default_val

    def load(self):
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}
        self._merge_defaults()

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, section: str, key: str, default=None):
        try:
            return self._data[section][key]
        except (KeyError, TypeError):
            return default

    def set(self, section: str, key: str, value):
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value
        self.save()

    def get_nested(self, section: str, *keys, default=None):
        """Deep-get inside dicts, e.g. get_nested('player','temp_allocations','health')."""
        try:
            node = self._data[section]
            for key in keys:
                node = node[key]
            return node
        except (KeyError, TypeError):
            return default

    def set_nested(self, section: str, *keys_and_value):
        """Deep-set: set_nested('player','temp_allocations','health', 3)."""
        *keys, value = keys_and_value
        if section not in self._data:
            self._data[section] = {}
        node = self._data[section]
        for key in keys[:-1]:
            if key not in node or not isinstance(node[key], dict):
                node[key] = {}
            node = node[key]
        node[keys[-1]] = value
        self.save()

    @property
    def data(self):
        return self._data
