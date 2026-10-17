"""
Solo Leveling System — JSON config manager with auto-save.
"""
import json
from pathlib import Path


DEFAULTS = {
    "loading_screen": {"enabled": True},
    "audio": {"enabled": True, "volume": 0.1},
    "notifications": {"enabled": True, "duration_ms": 8000},
    "git_sync": {"enabled": True, "interval_ms": 15000},
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

    @property
    def data(self):
        return self._data
