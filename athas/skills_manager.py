"""Load backend-authored skill definitions from the skills folder."""
import json
from pathlib import Path
from typing import Any


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

        if isinstance(data, dict) and isinstance(data.get("skills"), list):
            entries = data["skills"]
        elif isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = [data]
        else:
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
        if not cls._is_positive_int(skill.get("max_level")):
            return "max_level must be a positive integer"
        if not cls._is_positive_int(skill.get("upgrade_cost")):
            return "upgrade_cost must be a positive integer"
        if not cls._is_nonnegative_int(skill.get("base_damage")):
            return "base_damage must be a non-negative integer"
        if not cls._is_nonnegative_int(skill.get("damage_per_level")):
            return "damage_per_level must be a non-negative integer"
        return None

    @staticmethod
    def _is_nonnegative_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @classmethod
    def _is_positive_int(cls, value: Any) -> bool:
        return cls._is_nonnegative_int(value) and value > 0
