"""
Drop Manager — the drops/ folder hand-out pipeline.

Anyone can drop a *.json or *.txt file into the `drops/` folder to grant
the local player gold, xp, skill points, constellation points, temporary
or permanent stat points, or to show a notification popup. The files are
processed once and then deleted — they are never uploaded by the app
(the folder is git-ignored and outside every git-sync path); sharing them
happens manually from the IDE if ever needed.

JSON format (any subset of the keys):
    {
        "gold": 100,
        "xp": 50,
        "skill_points": 1,
        "constellation_points": 2,
        "temp_points": 3,
        "perm_points": 1,
        "notification": {
            "title": "System Message",
            "message": "Well done, Wanderer."
        }
    }

TXT format — one `key: value` pair per line (key = value works too):
    gold: 100
    skill points: 1
    notification: The System acknowledges your progress.

Unknown keys and unparsable files are ignored (bad files are still
deleted so they cannot clog the folder).
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Keys a drop file may grant, mapped to their normalised names.
_INT_KEYS = {
    "gold", "xp", "skill_points", "constellation_points",
    "temp_points", "perm_points",
}

# Friendly aliases accepted in drop files (compared after normalising).
_KEY_ALIASES = {
    "con_points": "constellation_points",
    "constellation_point": "constellation_points",
    "constellations": "constellation_points",
    "sp": "skill_points",
    "skill_point": "skill_points",
    "skills": "skill_points",
    "money": "gold",
    "coins": "gold",
    "experience": "xp",
    "exp": "xp",
    "points": "temp_points",
    "bonus_points": "temp_points",
    "temp": "temp_points",
    "perm": "perm_points",
    "permanent": "perm_points",
}

_DROP_EXTS = {".json", ".txt"}


def _as_int(value, fallback=0) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return fallback
    return fallback


def _normalise_key(raw: Any) -> str:
    """'Con Points' / 'constellation-points' → 'constellation_points'."""
    if not isinstance(raw, str):
        return ""
    return re.sub(r"[\s\-]+", "_", raw.strip().lower())


def _clamp_int(value: Any) -> int:
    return max(0, _as_int(value))


class DropManager:
    """Watches the drops folder and converts drop files into grant dicts."""

    def __init__(self, drops_dir):
        self.drops_dir = Path(drops_dir)
        self.drops_dir.mkdir(parents=True, exist_ok=True)

    def collect(self) -> List[Dict[str, Any]]:
        """Read, parse, and delete every drop file.

        Returns a list of grant dicts (one per successfully read file):
            {
                'gold': int, 'xp': int, 'skill_points': int,
                'constellation_points': int, 'temp_points': int,
                'perm_points': int,
                'notification': {'title': str, 'message': str} or None,
                'source': '<file name>',
            }
        Files that fail to parse are still consumed; their grant dict is
        not returned."""
        grants: List[Dict[str, Any]] = []
        for path in sorted(self.drops_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in _DROP_EXTS:
                continue
            grant = self._parse_file(path)
            deleted = self._delete(path)
            if grant is not None and deleted:
                grants.append(grant)
            elif grant is not None and not deleted:
                # Locked file — leave it for the next scan, but do not
                # grant twice.
                pass
        return grants

    @staticmethod
    def _delete(path: Path) -> bool:
        for attempt in range(5):
            try:
                path.unlink()
                return True
            except OSError:
                import time
                time.sleep(0.05 * (2 ** attempt))
        return path.exists() is False

    def _parse_file(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None
        if path.suffix.lower() == ".json":
            data = self._parse_json_text(raw)
        else:
            data = self._parse_txt_text(raw)
        if data is None:
            return None
        grant = {key: 0 for key in _INT_KEYS}
        grant["notification"] = None
        grant["source"] = path.name
        for key, value in data.items():
            norm = _normalise_key(key)
            norm = _KEY_ALIASES.get(norm, norm)
            if norm in _INT_KEYS:
                grant[norm] = _clamp_int(value)
        notification = data.get("notification")
        if isinstance(notification, str):
            grant["notification"] = {"title": "SYSTEM MESSAGE", "message": notification}
        elif isinstance(notification, dict):
            grant["notification"] = {
                "title": str(notification.get("title") or "SYSTEM MESSAGE"),
                "message": str(notification.get("message")
                               or notification.get("description") or ""),
            }
        return grant

    @staticmethod
    def _parse_json_text(raw: str) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _parse_txt_text(raw: str) -> Dict[str, Any]:
        """Simple 'key: value' / 'key = value' lines."""
        data: Dict[str, Any] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^([^=:]+)[=:](.*)$", line)
            if not match:
                continue
            key = match.group(1).strip()
            value = match.group(2).strip()
            if not key:
                continue
            data[key] = value
        return data
