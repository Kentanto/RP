"""Load backend-authored skill definitions from JSON."""
import json
from pathlib import Path
from typing import Any


class SkillManager:
    """Read skill definitions without exposing in-app editing controls."""

    def __init__(self, skills_file: str | Path):
        self.skills_file = Path(skills_file)

    def load_skills(self) -> list[dict[str, Any]]:
        """Load the authored ``skills`` list, or return empty when not configured."""
        if not self.skills_file.exists():
            return []

        try:
            data = json.loads(self.skills_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read skill definitions from '{self.skills_file}'.") from exc

        if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
            raise ValueError(
                f"Skill definitions in '{self.skills_file}' must contain a 'skills' list."
            )

        skills = data["skills"]
        seen_ids = set()
        for index, skill in enumerate(skills):
            if (
                not isinstance(skill, dict)
                or not isinstance(skill.get("id"), str)
                or not skill["id"].strip()
                or not isinstance(skill.get("name"), str)
                or not skill["name"].strip()
                or not isinstance(skill.get("description", ""), str)
            ):
                raise ValueError(
                    f"Skill entry {index + 1} in '{self.skills_file}' "
                    "must have a non-empty id and name, and a text description."
                )
            if skill["id"] in seen_ids:
                raise ValueError(f"Duplicate skill id '{skill['id']}' in '{self.skills_file}'.")
            seen_ids.add(skill["id"])

        return skills
