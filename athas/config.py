"""
Athas — JSON config manager with auto-save.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import time


DEFAULTS = {
    "loading_screen": {"enabled": True},
    "audio": {"enabled": True, "volume": 0.1, "sfx_volume": 0.3},
    "notifications": {"enabled": True, "duration_ms": 8000},
    "git_sync": {"enabled": True, "interval_ms": 15000, "folders": "missions,completed_missions,items,icons,cache,skills,library,shop"},
    "missions": {"zoom": 1.0},
    "player": {
        "name": "Wanderer",
        "rank": "F",
        "level": 1,
        "xp": 0,
        "health": 1,
        "magic": 1,
        "attack": 1,
        "defense": 1,
        "speed": 1,
        "temp_points": 10,
        "perm_points": 0,
        "skill_points": 0,
        "gold": 0,
        # Extra allocatable temp points granted by drop files (added to the
        # level-derived base pool — see stats_widget._base_temp_points).
        "bonus_temp_points": 0,
        # Ids of the equipped artifacts (max EQUIP_SLOTS entries).
        "equipped_artifacts": [],
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


def migrate_constellation_ranks(config, node_ids):
    """Move legacy constellation ranks from the old skills config section."""
    legacy_skills = config.data.get("skills")
    constellation_ranks = config.data.get("constellations")
    if not isinstance(constellation_ranks, dict):
        constellation_ranks = {}
        config.data["constellations"] = constellation_ranks

    if isinstance(legacy_skills, dict):
        for node_id in node_ids:
            if node_id in legacy_skills:
                constellation_ranks.setdefault(node_id, legacy_skills.pop(node_id))
        if not legacy_skills:
            config.data.pop("skills", None)


class ConfigManager:
    """Loads, merges defaults, and saves a JSON config file."""

    def __init__(self, path: Path):
        self._path = path
        self._data = {}
        self._save_lock = threading.RLock()
        self.load()
        if not self._path.exists():
            self.save()

    def _merge_defaults(self):
        for section, values in DEFAULTS.items():
            if section not in self._data:
                self._data[section] = {}
            if not isinstance(self._data[section], dict):
                self._data[section] = {}
            for key, default_val in values.items():
                if key not in self._data[section]:
                    # Deep-copy so nested defaults (e.g. temp_allocations)
                    # are never shared with future ConfigManager instances.
                    self._data[section][key] = copy.deepcopy(default_val)

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
        """Atomically save through a unique temp file, retrying transient Windows locks."""
        with self._save_lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self._data, indent=2)
            fd, tmp_name = tempfile.mkstemp(
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
            )
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
                    temp_file.write(payload)
                for attempt in range(5):
                    try:
                        os.replace(tmp, self._path)
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.05 * (2 ** attempt))
            finally:
                tmp.unlink(missing_ok=True)

    def get(self, section: str, key: str, default=None):
        try:
            return self._data[section][key]
        except (KeyError, TypeError):
            return default

    def set(self, section: str, key: str, value, save=True):
        with self._save_lock:
            if section not in self._data:
                self._data[section] = {}
            self._data[section][key] = value
            if save:
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

    def set_nested(self, section: str, *keys_and_value, save=True):
        """Deep-set: set_nested('player','temp_allocations','health', 3)."""
        with self._save_lock:
            *keys, value = keys_and_value
            if section not in self._data:
                self._data[section] = {}
            node = self._data[section]
            for key in keys[:-1]:
                if key not in node or not isinstance(node[key], dict):
                    node[key] = {}
                node = node[key]
            node[keys[-1]] = value
            if save:
                self.save()

    @property
    def data(self):
        return self._data
