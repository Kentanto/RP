"""
Mission Manager — scans local mission files, detects new missions,
 and maintains a cache of previously seen files to detect changes.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, asdict


@dataclass
class Mission:
    title: str
    description: str
    difficulty: str  # E, D, C, B, A, S
    reward: str
    source_file: str
    completed: bool = False
    completed_at: str = ""

    @classmethod
    def from_text(cls, raw: str, source: str) -> "Mission":
        """Parse a simple text file into a Mission."""
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
        title = "Unknown"
        description = ""
        difficulty = "E"
        reward = ""

        for line in lines:
            if line.lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("desc:") or line.lower().startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif line.lower().startswith("difficulty:"):
                difficulty = line.split(":", 1)[1].strip().upper()
            elif line.lower().startswith("reward:"):
                reward = line.split(":", 1)[1].strip()
            elif not description:
                description = line
            elif not reward:
                reward = line

        # Default values if missing
        if not title or title == "Unknown":
            title = Path(source).stem.replace("_", " ").title()
        if not difficulty:
            difficulty = "E"
        if not reward:
            reward = "Experience"

        return cls(
            title=title,
            description=description,
            difficulty=difficulty,
            reward=reward,
            source_file=source,
        )


class MissionManager:
    """
    Handles scanning, caching, and change-detection for mission files.
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
        self._seen_files: set = set()
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                self._seen_files = set(data.get("seen_files", []))
            except Exception:
                self._seen_files = set()
        else:
            self._seen_files = set()

    def _save_cache(self):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps({"seen_files": sorted(self._seen_files)}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def scan(self) -> List[Mission]:
        """Scan missions directory and return current mission list."""
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        new_missions: List[Mission] = []

        for file_path in self.missions_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in (".txt", ".md"):
                continue

            key = str(file_path.resolve())
            try:
                raw = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            mission = Mission.from_text(raw, str(file_path))
            self.missions[key] = mission

            if key not in self._seen_files:
                self._seen_files.add(key)
                new_missions.append(mission)
                if self.on_new_mission:
                    self.on_new_mission(mission)

        self._save_cache()
        return list(self.missions.values())

    def get_missions(self) -> List[Mission]:
        return list(self.missions.values())
