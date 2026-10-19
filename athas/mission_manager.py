"""
Mission Manager — scans local JSON mission files, detects new & updated missions,
and persists a cache of previously seen files to trigger notifications.

A mission counts as completed when its JSON carries the hidden author mark
("completed": true — there is no UI toggle for players) or when its file sits
in the completed folder. Completed files are moved out of the active folder
and credited (notification + XP) to the player exactly once per file name.
"""
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass

# Matches "+50 EXP", "+1,000 XP", "Bronze Key, +200 EXP", "300 experience" ...
_XP_PATTERN = re.compile(r"([+-]?\d[\d,]*)\s*(?:experience|exp|xp)s?\b", re.IGNORECASE)


def _parse_xp(data: Dict[str, Any], reward: str) -> int:
    """How much XP this mission grants: an explicit "xp" field wins,
    otherwise the number attached to EXP/XP inside the reward text."""
    raw = data.get("xp")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return max(0, int(raw))
    match = _XP_PATTERN.search(reward or "")
    if match:
        try:
            return max(0, int(match.group(1).replace(",", "").lstrip("+")))
        except ValueError:
            return 0
    return 0


@dataclass
class Mission:
    title: str
    description: str
    story: str
    difficulty: str  # E, D, C, B, A, S
    reward: str
    source_file: str
    completed: bool = False
    completed_at: str = ""
    xp: int = 0

    @classmethod
    def from_json(cls, raw: str, source: str) -> "Mission":
        """Parse a JSON mission file into a Mission."""
        data: Dict[str, Any] = {}
        try:
            data = json.loads(raw)
        except Exception:
            pass

        title = data.get("title", "Unknown")
        description = data.get("description", "")
        story = data.get("story", "")
        difficulty = data.get("difficulty", "E")
        reward = data.get("reward", "")
        completed = bool(data.get("completed", False))

        if not title or title == "Unknown":
            title = Path(source).stem.replace("_", " ").title()
        if not difficulty:
            difficulty = "E"
        if not reward:
            reward = "Experience"

        return cls(
            title=title,
            description=description,
            story=story,
            difficulty=difficulty,
            reward=reward,
            source_file=source,
            completed=completed,
            xp=_parse_xp(data, reward),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "story": self.story,
            "difficulty": self.difficulty,
            "reward": self.reward,
            "completed": self.completed,
        }


class MissionManager:
    """
    Handles scanning, caching, and change-detection for JSON mission files.

    A mission counts as completed when its JSON carries the hidden author
    mark ("completed": true) or when its file sits in the completed folder.
    Every completed file is credited to the player exactly once (per file
    name), then moved out of the active folder.
    """

    def __init__(
        self,
        missions_dir: str,
        cache_path: str,
        completed_dir: str | None = None,
        on_new_mission: Callable[[Mission], None] | None = None,
        on_completed_mission: Callable[[Mission], None] | None = None,
    ):
        self.missions_dir = Path(missions_dir)
        self.completed_dir = (
            Path(completed_dir) if completed_dir is not None
            else self.missions_dir.parent / "completed_missions"
        )
        self.cache_path = Path(cache_path)
        self.credited_path = self.cache_path.parent / "credited_missions.json"
        self.on_new_mission = on_new_mission
        self.on_completed_mission = on_completed_mission

        self.missions: Dict[str, Mission] = {}
        self._seen_hashes: Dict[str, str] = {}
        self._credited: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                self._seen_hashes = data.get("seen_hashes", {})
            except Exception:
                self._seen_hashes = {}
        else:
            self._seen_hashes = {}

        self._credited = {}
        if self.credited_path.exists():
            try:
                data = json.loads(self.credited_path.read_text(encoding="utf-8"))
                self._credited = data.get("credited", {})
            except Exception:
                self._credited = {}

    def _save_cache(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps({"seen_hashes": self._seen_hashes}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _save_credited(self):
        try:
            self.credited_path.parent.mkdir(parents=True, exist_ok=True)
            self.credited_path.write_text(
                json.dumps({"credited": self._credited}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    @staticmethod
    def _file_hash(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _iter_mission_files(folder: Path):
        """Yield the mission-ish files inside a folder, in a stable order."""
        if not folder.is_dir():
            return
        for file_path in sorted(folder.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in (".json", ".txt", ".md"):
                yield file_path

    def _retire_mission(self, mission: Mission, raw: str, move_to: Path | None):
        """Credit a completed mission to the player once (per file name),
        then move its file into the completed folder so it leaves the
        active rotation."""
        name = Path(mission.source_file).name
        if name not in self._credited:
            mission.completed_at = datetime.now().isoformat(timespec="seconds")
            self._credited[name] = {
                "title": mission.title,
                "hash": self._file_hash(raw),
                "xp": mission.xp,
                "credited_at": mission.completed_at,
            }
            self._save_credited()
            if self.on_completed_mission:
                self.on_completed_mission(mission)

        if move_to is not None:
            try:
                move_to.mkdir(parents=True, exist_ok=True)
                target = move_to / name
                if target.exists():
                    target.unlink()
                shutil.move(str(Path(mission.source_file)), str(target))
            except Exception:
                pass

    def scan(self) -> List[Mission]:
        """Scan the mission folders and return the ACTIVE mission list.

        Completed missions never appear in the list: they are credited the
        first time they are seen and moved into the completed folder."""
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        self.completed_dir.mkdir(parents=True, exist_ok=True)
        current_keys: set = set()

        # 1) Active folder — retire anything carrying the completed mark.
        for file_path in self._iter_mission_files(self.missions_dir):
            try:
                raw = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            mission = Mission.from_json(raw, str(file_path))

            if mission.completed:
                self._retire_mission(mission, raw, move_to=self.completed_dir)
                continue

            key = str(file_path.resolve())
            current_keys.add(key)
            self.missions[key] = mission
            h = self._file_hash(raw)

            if key not in self._seen_hashes or self._seen_hashes.get(key) != h:
                self._seen_hashes[key] = h
                if self.on_new_mission:
                    self.on_new_mission(mission)

        # 2) Completed folder — files placed here directly count as completed.
        for file_path in self._iter_mission_files(self.completed_dir):
            try:
                raw = file_path.read_text(encoding="utf-8")
            except Exception:
                continue
            mission = Mission.from_json(raw, str(file_path))
            mission.completed = True
            self._retire_mission(mission, raw, move_to=None)

        # remove entries for deleted files
        for stale in list(self._seen_hashes.keys()):
            if stale not in current_keys:
                del self._seen_hashes[stale]
                self.missions.pop(stale, None)

        self._save_cache()
        return list(self.missions.values())

    def get_missions(self) -> List[Mission]:
        return list(self.missions.values())
