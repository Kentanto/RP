"""
Mission Manager — scans local JSON mission files, detects new & updated missions,
 and persists a cache of previously seen files to trigger notifications.
"""
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, asdict


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
    """

    def __init__(
        self,
        missions_dir: str,
        cache_path: str,
        on_new_mission: Callable[[Mission], None] | None = None,
    ):
        self.missions_dir = Path(missions_dir)
        self.cache_path = Path(cache_path)
        self.on_new_mission = on_new_mission

        self.missions: Dict[str, Mission] = {}
        self._seen_hashes: Dict[str, str] = {}
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

    def _save_cache(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps({"seen_hashes": self._seen_hashes}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    @staticmethod
    def _file_hash(raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def save_mission(self, mission: Mission):
        """Write the mission back to its JSON source file."""
        path = Path(mission.source_file)
        try:
            if path.exists():
                raw = path.read_text(encoding="utf-8")
                try:
                    data = json.loads(raw)
                except Exception:
                    data = mission.to_dict()
                data["completed"] = mission.completed
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                raw_new = path.read_text(encoding="utf-8")
                self._seen_hashes[str(path.resolve())] = self._file_hash(raw_new)
                self._save_cache()
        except Exception:
            pass

    def scan(self) -> List[Mission]:
        """Scan missions directory and return current mission list."""
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        new_missions: List[Mission] = []
        current_keys: set = set()

        for file_path in self.missions_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in (".json", ".txt", ".md"):
                continue

            key = str(file_path.resolve())
            current_keys.add(key)
            try:
                raw = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            mission = Mission.from_json(raw, str(file_path))

            self.missions[key] = mission
            h = self._file_hash(raw)

            if key not in self._seen_hashes or self._seen_hashes.get(key) != h:
                self._seen_hashes[key] = h
                new_missions.append(mission)
                if self.on_new_mission:
                    self.on_new_mission(mission)

        # remove entries for deleted files
        for stale in list(self._seen_hashes.keys()):
            if stale not in current_keys:
                del self._seen_hashes[stale]
                self.missions.pop(stale, None)

        self._save_cache()
        return list(self.missions.values())

    def get_missions(self) -> List[Mission]:
        return list(self.missions.values())
