import json
import tempfile
import unittest
from pathlib import Path

from athas.config import ConfigManager
from athas.skills_manager import SkillManager, migrate_skill_ranks


def _skill(**overrides) -> dict:
    skill = {
        "id": "quick-strike",
        "title": "Quick Strike",
        "description": "A swift attack.",
        "image": "images/quick-strike.svg",
        "mana_cost": 8,
        "upgrade_cost": 1,
        "base_damage": 20,
        "upgrades": [
            {"id": "core", "title": "Quick Strike Mastery",
             "description": "Faster.", "x": 100, "y": 100, "max_rank": 5},
            {"id": "flow", "title": "Flowing Blade", "description": "Smoother.",
             "x": 300, "y": 100, "max_rank": 2, "parents": ["core"]},
        ],
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

    def test_skill_without_upgrades_is_skipped(self):
        skill = _skill()
        skill.pop("upgrades")
        self.write("skills.json", {"skills": [skill]})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(any("upgrades" in error for error in self.manager.load_errors))

    def test_skips_invalid_upgrade_entries(self):
        skill = _skill(upgrades=[{"id": "", "title": "Broken", "description": "?",
                                  "x": 0, "y": 0, "max_rank": 1}])
        self.write("skills.json", {"skills": [skill]})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(any("upgrade 1" in error for error in self.manager.load_errors))

    def test_skips_duplicate_upgrade_ids(self):
        skill = _skill(upgrades=[
            {"id": "core", "title": "A", "description": "a", "x": 0, "y": 0, "max_rank": 1},
            {"id": "core", "title": "B", "description": "b", "x": 10, "y": 0, "max_rank": 1},
        ])
        self.write("skills.json", {"skills": [skill]})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(any("duplicate" in error for error in self.manager.load_errors))

    def test_skips_unknown_parent(self):
        skill = _skill(upgrades=[
            {"id": "core", "title": "A", "description": "a", "x": 0, "y": 0,
             "max_rank": 1, "parents": ["ghost"]},
        ])
        self.write("skills.json", {"skills": [skill]})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(any("unknown parent" in error for error in self.manager.load_errors))

    def test_skips_parent_cycles(self):
        skill = _skill(upgrades=[
            {"id": "a", "title": "A", "description": "a", "x": 0, "y": 0,
             "max_rank": 1, "parents": ["b"]},
            {"id": "b", "title": "B", "description": "b", "x": 10, "y": 0,
             "max_rank": 1, "parents": ["a"]},
        ])
        self.write("skills.json", {"skills": [skill]})

        self.assertEqual(self.manager.load_skills(), [])
        self.assertTrue(any("cycle" in error for error in self.manager.load_errors))

    def test_accepts_root_without_parents_and_optional_color(self):
        skill = _skill(upgrades=[
            {"id": "core", "title": "A", "description": "a", "x": 0, "y": 0,
             "max_rank": 2, "color": "#ff9800"},
        ])
        self.write("skills.json", {"skills": [skill]})

        self.assertEqual(len(self.manager.load_skills()), 1)
        self.assertEqual(self.manager.load_errors, [])

    def test_save_ranks_writes_rank_into_the_skill_file(self):
        self.write("skills.json", {"skills": [_skill()]})

        self.manager.save_ranks("quick-strike", {"core": 2})

        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["skills"][0]["upgrades"][0]["rank"], 2)
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][1])

    def test_save_ranks_round_trips_through_load(self):
        self.write("skills.json", {"skills": [_skill()]})
        self.manager.save_ranks("quick-strike", {"core": 1})

        skill = self.manager.load_skills()[0]

        self.assertEqual(skill["upgrades"][0]["rank"], 1)
        self.assertNotIn("rank", skill["upgrades"][1])

    def test_save_ranks_updates_and_clears_existing_rank(self):
        skill = _skill()
        skill["upgrades"][0]["rank"] = 1
        self.write("skills.json", {"skills": [skill]})

        self.manager.save_ranks("quick-strike", {"core": 2})
        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["skills"][0]["upgrades"][0]["rank"], 2)

        self.manager.save_ranks("quick-strike", {"core": 0})
        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][0])

    def test_save_ranks_preserves_other_skills_and_fields(self):
        authored = _skill()
        authored["author_note"] = "hidden"
        self.write("skills.json", {"skills": [authored, _skill(id="other")]})

        self.manager.save_ranks("other", {"core": 1})

        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["skills"][0]["author_note"], "hidden")
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][0])
        self.assertEqual(saved["skills"][1]["upgrades"][0]["rank"], 1)

    def test_save_ranks_handles_a_single_skill_file(self):
        self.write("solo.json", _skill(id="solo"))

        self.manager.save_ranks("solo", {"core": 1})

        saved = json.loads((self.skills_dir / "solo.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["id"], "solo")
        self.assertEqual(saved["upgrades"][0]["rank"], 1)

    def test_save_ranks_ignores_unknown_skill(self):
        self.write("skills.json", {"skills": [_skill()]})

        self.manager.save_ranks("ghost", {"core": 1})

        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][0])

    def _config_with_legacy_ranks(self, ranks) -> ConfigManager:
        # Keep the config outside the skills folder so the scan ignores it.
        cfg_dir = self.skills_dir / "cfg"
        cfg_dir.mkdir(exist_ok=True)
        config = ConfigManager(cfg_dir / "system_config.json")
        config.data["player"]["skill_upgrades"] = ranks
        config.save()
        return config

    def test_migrate_moves_config_ranks_into_the_skill_file(self):
        self.write("skills.json", {"skills": [_skill()]})
        config = self._config_with_legacy_ranks(
            {"quick-strike": {"core": 2, "flow": 0}}
        )

        migrate_skill_ranks(config, self.manager)

        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["skills"][0]["upgrades"][0]["rank"], 2)
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][1])
        self.assertNotIn("skill_upgrades", config.data["player"])

    def test_migrate_file_rank_wins_over_config(self):
        skill = _skill()
        skill["upgrades"][0]["rank"] = 3
        self.write("skills.json", {"skills": [skill]})
        config = self._config_with_legacy_ranks({"quick-strike": {"core": 1}})

        migrate_skill_ranks(config, self.manager)

        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["skills"][0]["upgrades"][0]["rank"], 3)
        self.assertNotIn("skill_upgrades", config.data["player"])

    def test_migrate_keeps_entries_for_unknown_skills(self):
        self.write("skills.json", {"skills": [_skill()]})
        config = self._config_with_legacy_ranks({"ghost-skill": {"core": 2}})

        migrate_skill_ranks(config, self.manager)

        self.assertEqual(
            config.get_nested("player", "skill_upgrades", "ghost-skill", "core"), 2
        )
        saved = json.loads((self.skills_dir / "skills.json").read_text(encoding="utf-8"))
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][0])
