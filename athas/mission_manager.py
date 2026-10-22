"""
Mission Manager — scans local JSON mission files, detects new & updated missions,
and persists a cache of previously seen files to trigger notifications.

A mission counts as completed when its JSON carries the hidden author mark
("completed": true — there is no UI toggle for players) or when its file sits
in the completed folder without an explicit false mark. Completed files are
credited once per completion; a credit ends when the file leaves the completed
state (or its content changed since it was credited), which restores the
recorded rewards and lets a later completion credit again.
"""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Callable
from dataclasses import dataclass


def _parse_xp(data: Dict[str, Any]) -> int:
    """Read the XP amount from the mission's numeric xp field."""
    raw = data.get("xp")
    if isinstance(raw, int) and not isinstance(raw, bool):
        return max(0, raw)
    return 0


def _parse_points(data: Dict[str, Any], field: str) -> int:
    raw = data.get(field)
    if isinstance(raw, int) and not isinstance(raw, bool):
        return max(0, raw)
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
    completion_marked: bool = False
    completed_at: str = ""
    xp: int = 0
    constellation_points: int = 0
    skill_points: int = 0

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
        completion_marked = "completed" in data

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
            completion_marked=completion_marked,
            xp=_parse_xp(data),
            constellation_points=_parse_points(data, "constellation_points"),
            skill_points=_parse_points(data, "skill_points"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "story": self.story,
            "difficulty": self.difficulty,
            "reward": self.reward,
            "xp": self.xp,
            "constellation_points": self.constellation_points,
            "skill_points": self.skill_points,
            "completed": self.completed,
        }


class MissionManager:
    """
    Handles scanning, caching, and change-detection for JSON mission files.

    A mission counts as completed when its JSON carries the hidden author
    mark ("completed": true) or when its file sits in the completed folder
    without an explicit false mark. Completed files are credited exactly once
    per completion; explicitly uncompleted files are restored to the active
    folder and their recorded rewards are revoked.
    """

    def __init__(
        self,
        missions_dir: str,
        cache_path: str,
        completed_dir: str | None = None,
        on_new_mission: Callable[[Mission], None] | None = None,
        on_completed_mission: Callable[[Mission], None] | None = None,
        on_uncompleted_mission: Callable[[Mission, int], None] | None = None,
        on_uncompleted_rewards: Callable[[Mission, Dict[str, int]], None] | None = None,
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
        self.on_uncompleted_mission = on_uncompleted_mission
        self.on_uncompleted_rewards = on_uncompleted_rewards

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
            payload = json.dumps({"seen_hashes": self._seen_hashes}, indent=2)
            try:
                if self.cache_path.read_text(encoding="utf-8") == payload:
                    return  # identical — skip the write so file watchers stay quiet
            except OSError:
                pass  # missing or unreadable — write it fresh below
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(payload, encoding="utf-8")
        except Exception:
            pass

    def _save_credited(self):
        try:
            payload = json.dumps({"credited": self._credited}, indent=2)
            try:
                if self.credited_path.read_text(encoding="utf-8") == payload:
                    return  # identical — skip the write so file watchers stay quiet
            except OSError:
                pass  # missing or unreadable — write it fresh below
            self.credited_path.parent.mkdir(parents=True, exist_ok=True)
            self.credited_path.write_text(payload, encoding="utf-8")
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
        """Credit a completed mission to the player, then move its file into
        the completed folder so it leaves the active rotation.

        A file counts as a fresh completion when it was never credited or
        when its content changed since the last credit — the old reward is
        revoked before the new one is granted."""
        name = Path(mission.source_file).name
        h = self._file_hash(raw)
        credited = self._credited.get(name)
        if credited is None or credited.get("hash") != h:
            if credited is not None:
                self._revoke_credit(name, mission)
            mission.completed_at = datetime.now().isoformat(timespec="seconds")
            self._credited[name] = {
                "title": mission.title,
                "hash": h,
                "xp": mission.xp,
                "constellation_points": mission.constellation_points,
                "skill_points": mission.skill_points,
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

    def _restore_mission(self, mission: Mission, raw: str) -> bool:
        """Return an explicitly uncompleted mission to the active folder."""
        name = Path(mission.source_file).name
        source = Path(mission.source_file)
        target = self.missions_dir / name
        try:
            self.missions_dir.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            shutil.move(str(source), str(target))
        except Exception:
            return False

        mission.source_file = str(target)
        self._revoke_credit(name, mission)

        key = str(target.resolve())
        self.missions[key] = mission
        self._seen_hashes[key] = self._file_hash(raw)
        return True

    def _revoke_credit(self, name: str, mission: Mission | None = None):
        """Drop a mission's credit record and revoke the rewards it granted.

        Fires for every completion that ends: an explicit uncomplete, a file
        that left the completed state, or a re-credit after a content change."""
        credited = self._credited.pop(name, None)
        if credited is None:
            return
        self._save_credited()
        rewards = {
            field: max(0, value) if isinstance(value, int) and not isinstance(value, bool) else 0
            for field in ("xp", "constellation_points", "skill_points")
            for value in (credited.get(field, 0),)
        }
        if mission is None:
            mission = Mission(
                title=str(credited.get("title") or name),
                description="", story="", difficulty="E", reward="",
                source_file=name,
            )
        if self.on_uncompleted_mission:
            self.on_uncompleted_mission(mission, rewards["xp"])
        if self.on_uncompleted_rewards:
            self.on_uncompleted_rewards(mission, rewards)

    def scan(self) -> List[Mission]:
        """Scan the mission folders and return the ACTIVE mission list.

        Completed missions never appear in the list. Explicitly uncompleted
        files found in the completed folder are restored during this scan."""
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        self.completed_dir.mkdir(parents=True, exist_ok=True)
        current_keys: set = set()
        completed_names: set = set()

        # 1) Active folder — retire anything carrying the completed mark.
        for file_path in self._iter_mission_files(self.missions_dir):
            try:
                raw = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            mission = Mission.from_json(raw, str(file_path))

            if mission.completed:
                completed_names.add(Path(mission.source_file).name)
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

        # 2) Completed folder — files placed here directly count as completed,
        # unless the author explicitly changed the completion mark to false.
        for file_path in self._iter_mission_files(self.completed_dir):
            try:
                raw = file_path.read_text(encoding="utf-8")
            except Exception:
                continue
            mission = Mission.from_json(raw, str(file_path))
            if mission.completion_marked and not mission.completed:
                if self._restore_mission(mission, raw):
                    current_keys.add(str((self.missions_dir / file_path.name).resolve()))
                continue
            mission.completed = True
            completed_names.add(file_path.name)
            self._retire_mission(mission, raw, move_to=None)

        # remove entries for deleted files
        for stale in list(self._seen_hashes.keys()):
            if stale not in current_keys:
                del self._seen_hashes[stale]
                self.missions.pop(stale, None)

        # Revoke credits whose mission left the completed state (moved back
        # to the active folder, reworked, or deleted) so completing the
        # mission again grants fresh rewards instead of being blocked by a
        # stale record.
        for name in list(self._credited):
            if name not in completed_names:
                self._revoke_credit(name)

        self._save_cache()
        return list(self.missions.values())

    def get_missions(self) -> List[Mission]:
        return list(self.missions.values())
