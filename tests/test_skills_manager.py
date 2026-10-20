import json
import tempfile
import unittest
from pathlib import Path

from athas.skills_manager import SkillManager


class SkillManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.skills_file = Path(self.temp_dir.name) / "skills.json"
        self.manager = SkillManager(self.skills_file)

    def test_missing_file_has_no_skills(self):
        self.assertEqual(self.manager.load_skills(), [])

    def test_project_json_defines_fireball(self):
        project_file = Path(__file__).parent.parent / "skills" / "skills.json"
        fireball = SkillManager(project_file).load_skills()[0]

        self.assertEqual(fireball["id"], "fireball")
        self.assertEqual(fireball["title"], "Fireball")
        self.assertEqual(fireball["mana_cost"], 10)
        self.assertTrue((project_file.parent / fireball["image"]).is_file())

    def test_loads_authored_json_and_preserves_extra_fields(self):
        authored = {
            "skills": [
                {
                    "id": "quick-strike",
                    "title": "Quick Strike",
                    "description": "A swift attack.",
                    "image": "images/quick-strike.svg",
                    "mana_cost": 8,
                    "max_level": 5,
                    "upgrade_cost": 1,
                    "base_damage": 20,
                    "damage_per_level": 10,
                }
            ]
        }
        self.skills_file.write_text(json.dumps(authored), encoding="utf-8")

        self.assertEqual(self.manager.load_skills(), authored["skills"])

    def test_rejects_malformed_json_structure(self):
        self.skills_file.write_text('{"wrong": []}', encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "must contain a 'skills' list"):
            self.manager.load_skills()

    def test_rejects_duplicate_ids(self):
        self.skills_file.write_text(
            json.dumps(
                {
                    "skills": [
                        {
                            "id": "same", "title": "One", "description": "", "image": "",
                            "mana_cost": 0, "max_level": 1, "upgrade_cost": 1,
                            "base_damage": 0, "damage_per_level": 0,
                        },
                        {
                            "id": "same", "title": "Two", "description": "", "image": "",
                            "mana_cost": 0, "max_level": 1, "upgrade_cost": 1,
                            "base_damage": 0, "damage_per_level": 0,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Duplicate skill id"):
            self.manager.load_skills()

    def test_rejects_invalid_mana_cost(self):
        self.skills_file.write_text(
            json.dumps(
                {
                    "skills": [
                        {
                            "id": "fireball", "title": "Fireball", "description": "A spell.",
                            "image": "", "mana_cost": -1, "max_level": 5, "upgrade_cost": 1,
                            "base_damage": 25, "damage_per_level": 10,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "mana_cost"):
            self.manager.load_skills()
