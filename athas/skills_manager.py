"""Load backend-authored skill definitions from the skills folder."""
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def _nonnegative_int(value: Any) -> int:
    """Coerce saved rank values to a safe non-negative int."""
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    return 0


class SkillManager:
    """Read every skill definition found in the skills folder.

    Each ``*.json`` file inside the folder may hold a single skill object,
    a list of skills, or the wrapped ``{"skills": [...]}`` format. Files
    that cannot be parsed or fail validation are skipped (and reported in
    ``load_errors``) so one bad file cannot break the whole catalogue.
    Duplicate skill ids are also skipped — the first file in alphabetical
    order wins.
    """

    def __init__(self, skills_path: str | Path):
        path = Path(skills_path)
        # Accept either the skills folder itself or one JSON file inside it.
        self.skills_dir = path.parent if path.suffix.lower() == ".json" else path
        self.load_errors: list[str] = []

    def skill_files(self) -> list[Path]:
        """Return the JSON skill files inside the folder, in a stable order."""
        return list(self._iter_skill_files(self.skills_dir))

    def load_skills(self) -> list[dict[str, Any]]:
        """Load every valid skill in the folder, or return empty when none."""
        skills: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        self.load_errors = []
        for file_path in self._iter_skill_files(self.skills_dir):
            for skill in self._skills_in_file(file_path):
                if skill["id"] in seen_ids:
                    self.load_errors.append(
                        f"{file_path.name}: duplicate skill id '{skill['id']}' skipped"
                    )
                    continue
                seen_ids.add(skill["id"])
                skills.append(skill)
        return skills

    def save_ranks(self, skill_id: str, ranks: dict[str, int]) -> None:
        """Store upgrade ranks inside the skill's own JSON file.

        Only the matching skill's upgrade nodes get a ``rank`` field; the rest
        of the file is preserved as-is and written back atomically.
        """
        clean_ranks = {
            node_id: _nonnegative_int(rank) for node_id, rank in ranks.items()
        }
        if not clean_ranks:
            return
        for file_path in self._iter_skill_files(self.skills_dir):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            entries = self._entries_in_data(data)
            if entries is None:
                continue
            changed = False
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("id") != skill_id:
                    continue
                for node in entry.get("upgrades", []):
                    if not isinstance(node, dict) or node.get("id") not in clean_ranks:
                        continue
                    rank = clean_ranks[node["id"]]
                    if node.get("rank", 0) == rank:
                        continue
                    if rank > 0:
                        node["rank"] = rank
                    else:
                        node.pop("rank", None)
                    changed = True
            if changed:
                self._write_json(file_path, data)

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        """Atomically save through a unique temp file, retrying transient locks."""
        payload = json.dumps(data, indent=2)
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp",
        )
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
                temp_file.write(payload)
            for attempt in range(5):
                try:
                    os.replace(tmp, path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (2 ** attempt))
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _entries_in_data(data: Any):
        """Return the skill entries container inside parsed file data, or None."""
        if isinstance(data, dict) and isinstance(data.get("skills"), list):
            return data["skills"]
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return None

    @staticmethod
    def _iter_skill_files(folder: Path):
        """Yield the JSON skill files inside a folder, in a stable order."""
        if not folder.is_dir():
            return
        for file_path in sorted(folder.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() == ".json":
                yield file_path

    def _skills_in_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Parse one JSON file into a list of validated skill dicts."""
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.load_errors.append(f"{file_path.name}: not readable JSON")
            return []

        entries = self._entries_in_data(data)
        if entries is None:
            self.load_errors.append(
                f"{file_path.name}: must contain a skill object, a list of skills, or a 'skills' list"
            )
            return []

        valid: list[dict[str, Any]] = []
        for index, skill in enumerate(entries):
            error = self._skill_error(skill)
            if error is not None:
                self.load_errors.append(f"{file_path.name}: skill {index + 1} skipped — {error}")
                continue
            valid.append(skill)
        return valid

    @classmethod
    def _skill_error(cls, skill: Any) -> str | None:
        """Return why the entry is not a valid skill, or None when it is."""
        if not isinstance(skill, dict):
            return "entry must be a skill object"
        if not isinstance(skill.get("id"), str) or not skill["id"].strip():
            return "id must be a non-empty string"
        if not isinstance(skill.get("title"), str) or not skill["title"].strip():
            return "title must be a non-empty string"
        if not isinstance(skill.get("description"), str):
            return "description must be a string"
        if not isinstance(skill.get("image"), str):
            return "image must be a string"
        if not cls._is_nonnegative_int(skill.get("mana_cost")):
            return "mana_cost must be a non-negative integer"
        if not cls._is_positive_int(skill.get("upgrade_cost")):
            return "upgrade_cost must be a positive integer"
        if not cls._is_nonnegative_int(skill.get("base_damage")):
            return "base_damage must be a non-negative integer"
        return cls._upgrades_error(skill.get("upgrades"))

    @staticmethod
    def _is_nonnegative_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @classmethod
    def _is_positive_int(cls, value: Any) -> bool:
        return cls._is_nonnegative_int(value) and value > 0

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def _upgrades_error(cls, upgrades: Any) -> str | None:
        """Validate a skill's upgrade tree as a whole."""
        if not isinstance(upgrades, list) or not upgrades:
            return "upgrades must be a non-empty list of upgrade nodes"
        known_ids: set[str] = set()
        for index, upgrade in enumerate(upgrades):
            error = cls._upgrade_error(upgrade)
            if error is not None:
                return f"upgrade {index + 1}: {error}"
            if upgrade["id"] in known_ids:
                return f"upgrade {index + 1}: duplicate id '{upgrade['id']}'"
            known_ids.add(upgrade["id"])
        for upgrade in upgrades:
            for parent_id in upgrade.get("parents", []):
                if parent_id == upgrade["id"]:
                    return f"upgrade '{upgrade['id']}': cannot be its own parent"
                if parent_id not in known_ids:
                    return f"upgrade '{upgrade['id']}': unknown parent '{parent_id}'"
        if cls._has_parent_cycle(upgrades):
            return "upgrade parents form a cycle"
        return None

    @classmethod
    def _upgrade_error(cls, upgrade: Any) -> str | None:
        """Return why the entry is not a valid upgrade node, or None when it is."""
        if not isinstance(upgrade, dict):
            return "entry must be an upgrade object"
        if not isinstance(upgrade.get("id"), str) or not upgrade["id"].strip():
            return "id must be a non-empty string"
        if not isinstance(upgrade.get("title"), str) or not upgrade["title"].strip():
            return "title must be a non-empty string"
        if not isinstance(upgrade.get("description"), str):
            return "description must be a string"
        if not cls._is_number(upgrade.get("x")) or not cls._is_number(upgrade.get("y")):
            return "x and y must be numbers"
        if not cls._is_positive_int(upgrade.get("max_rank")):
            return "max_rank must be a positive integer"
        parents = upgrade.get("parents", [])
        if not isinstance(parents, list) or any(
            not isinstance(parent, str) or not parent.strip() for parent in parents
        ):
            return "parents must be a list of upgrade ids"
        if len(set(parents)) != len(parents):
            return "parents must not repeat the same id"
        color = upgrade.get("color")
        if color is not None and (not isinstance(color, str) or not color.strip()):
            return "color must be a non-empty string"
        return None

    @classmethod
    def _has_parent_cycle(cls, upgrades: list) -> bool:
        """True when following parent links loops forever."""
        parents_of = {
            upgrade["id"]: [
                parent for parent in upgrade.get("parents", [])
                if parent != upgrade["id"]
            ]
            for upgrade in upgrades
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def has_cycle(node_id: str) -> bool:
            visiting.add(node_id)
            for parent_id in parents_of[node_id]:
                if parent_id in visiting:
                    return True
                if parent_id not in visited and has_cycle(parent_id):
                    return True
            visiting.discard(node_id)
            visited.add(node_id)
            return False

        return any(
            node_id not in visited and has_cycle(node_id)
            for node_id in parents_of
        )


def migrate_skill_ranks(config, skill_manager: SkillManager) -> None:
    """Move legacy per-skill ranks from the config into the skill files.

    Ranks already saved in a skill file win over config copies, mirroring how
    constellation ranks are migrated. Consumed entries leave the config; the
    ``player.skill_upgrades`` section disappears once fully drained.
    """
    legacy = config.get_nested("player", "skill_upgrades")
    if not isinstance(legacy, dict) or not legacy:
        return

    skills_by_id = {skill["id"]: skill for skill in skill_manager.load_skills()}
    changed_config = False
    for skill_id in list(legacy.keys()):
        node_ranks = legacy[skill_id]
        skill = skills_by_id.get(skill_id)
        if not isinstance(node_ranks, dict) or skill is None:
            continue  # unknown skill or bad shape — keep until it reappears
        nodes_by_id = {node["id"]: node for node in skill.get("upgrades", [])}
        pending: dict[str, int] = {}
        for node_id in list(node_ranks.keys()):
            node = nodes_by_id.get(node_id)
            if node is None:
                continue  # unknown node — keep until it reappears
            if _nonnegative_int(node.get("rank")) <= 0:
                config_rank = _nonnegative_int(node_ranks[node_id])
                if config_rank > 0:
                    pending[node_id] = config_rank
            del node_ranks[node_id]
            changed_config = True
        if pending:
            skill_manager.save_ranks(skill_id, pending)
        if not node_ranks:
            del legacy[skill_id]
    if not legacy:
        player = config.data.get("player")
        if isinstance(player, dict) and "skill_upgrades" in player:
            del player["skill_upgrades"]
            changed_config = True
    if changed_config:
        config.save()
