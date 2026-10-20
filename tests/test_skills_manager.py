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

    def test_loads_authored_json_and_preserves_extra_fields(self):
        authored = {
            "skills": [
                {
                    "id": "quick-strike",
                    "name": "Quick Strike",
                    "description": "A swift attack.",
                    "effects": {"attack": 5},
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
                        {"id": "same", "name": "One"},
                        {"id": "same", "name": "Two"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Duplicate skill id"):
            self.manager.load_skills()
