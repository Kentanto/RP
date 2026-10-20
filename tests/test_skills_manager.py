import json
import tempfile
import unittest
from pathlib import Path

from athas.skills_manager import SkillManager


def _skill(**overrides) -> dict:
    skill = {
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
    skill.update(overrides)
    return skill


class SkillManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.skills_dir = Path(self.temp_dir.name)
        self.manager = SkillManager(self.skills_dir)

    def write(self, name: str, payload) -> Path:
        path = self.skills_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_missing_folder_has_no_skills(self):
        self.assertEqual(SkillManager(self.skills_dir / "missing").load_skills(), [])

    def test_accepts_a_single_file_path(self):
        self.write("skills.json", {"skills": [_skill()]})

        manager = SkillManager(self.skills_dir / "skills.json")

        self.assertEqual(manager.skills_dir, self.skills_dir)
        self.assertEqual(len(manager.load_skills()), 1)

    def test_project_folder_defines_fireball(self):
        project_folder = Path(__file__).parent.parent / "skills"
        fireball = SkillManager(project_folder).load_skills()[0]

        self.assertEqual(fireball["id"], "fireball")
        self.assertEqual(fireball["title"], "Fireball")
        self.assertEqual(fireball["mana_cost"], 10)
        self.assertTrue((project_folder / fireball["image"]).is_file())

    def test_loads_every_json_file_in_the_folder(self):
        self.write("skills.json", {"skills": [_skill()]})
        self.write("fireball.json", _skill(id="fireball", title="Fireball"))
        self.write("bundle.json", [_skill(id="third", title="Third")])

        skills = self.manager.load_skills()

        # Files are read in alphabetical order: bundle, fireball, skills.
        self.assertEqual([skill["id"] for skill in skills], ["third", "fireball", "quick-strike"])
        self.assertEqual(self.manager.load_errors, [])

    def test_ignores_non_json_files_and_subfolders(self):
        (self.skills_dir / "images").mkdir()
        (self.skills_dir / "images" / "fireball.svg").write_text("<svg/>", encoding="utf-8")
        (self.skills_dir / "notes.txt").write_text("not a skill", encoding="utf-8")

        self.assertEqual(self.manager.load_skills(), [])
        self.assertEqual(self.manager.load_errors, [])

    def test_loads_authored_json_and_preserves_extra_fields(self):
        authored_skill = _skill()
        authored_skill["author_note"] = "hidden"
        self.write("skills.json", {"skills": [authored_skill]})

        self.assertEqual(self.manager.load_skills(), [authored_skill])

    def test_skips_malformed_json_structure(self):
        self.write("skills.json", {"wrong": []})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(self.manager.load_errors)

    def test_skips_unreadable_json_file_but_loads_others(self):
        (self.skills_dir / "a-broken.json").write_text("{not json", encoding="utf-8")
        self.write("b-valid.json", {"skills": [_skill()]})

        self.assertEqual(len(self.manager.load_skills()), 1)
        self.assertTrue(any("a-broken.json" in error for error in self.manager.load_errors))

    def test_skips_duplicate_ids_across_files(self):
        self.write("a-first.json", {"skills": [_skill(title="First")]})
        self.write("b-second.json", {"skills": [_skill(title="Second")]})

        skills = self.manager.load_skills()

        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["title"], "First")
        self.assertTrue(any("duplicate" in error for error in self.manager.load_errors))

    def test_skips_invalid_mana_cost(self):
        self.write("skills.json", {"skills": [_skill(mana_cost=-1)]})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(any("mana_cost" in error for error in self.manager.load_errors))

    def test_removed_file_drops_its_skills(self):
        path = self.write("skills.json", {"skills": [_skill()]})
        self.assertEqual(len(self.manager.load_skills()), 1)

        path.unlink()

        self.assertEqual(self.manager.load_skills(), [])
