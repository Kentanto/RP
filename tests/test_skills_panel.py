import tempfile
import unittest
import json
from pathlib import Path

from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QGridLayout, QLabel, QPushButton, QSizePolicy,
)

from athas.config import ConfigManager
from athas.skill_tree_dialog import SkillTreeDialog
from athas.skills_manager import SkillManager
from athas.skills_panel import SkillCard, SkillsPanel
from athas.stats_widget import StatsWidget


class SkillsPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.config = ConfigManager(self.root / "system_config.json")
        # Keep skill files in their own folder like the real app does, so the
        # config file is never picked up by the folder scan.
        self.skills_dir = self.root / "skills"
        self.skills_dir.mkdir()
        self.skills_file = self.skills_dir / "skills.json"
        self.skills_file.write_text(
            json.dumps({"skills": [{
                "id": "fireball", "title": "Fireball", "description": "Burns.",
                "image": "fireball.svg", "mana_cost": 10, "upgrade_cost": 1,
                "base_damage": 25,
                "upgrades": [
                    {"id": "core", "title": "Fireball Mastery",
                     "description": "A stronger orb.", "x": 100, "y": 200,
                     "max_rank": 5},
                    {"id": "nova", "title": "Nova", "description": "Burst finish.",
                     "x": 300, "y": 200, "max_rank": 2, "parents": ["core"]},
                ],
            }]}),
            encoding="utf-8",
        )
        self.panel = SkillsPanel(self.config, SkillManager(self.skills_file))
        self.addCleanup(self.panel.close)

    def test_card_click_invokes_its_callback(self):
        clicked = []

        def record_click():
            clicked.append(True)

        skill = SkillManager(self.skills_file).load_skills()[0]
        card = SkillCard(skill, self.skills_dir / skill["image"], record_click)
        self.addCleanup(card.deleteLater)

        card._handle_card_click()

        self.assertEqual(clicked, [True])

    def test_cards_have_no_upgrade_button_and_show_the_tip(self):
        self.assertIsNone(self.panel.findChild(QPushButton))

        texts = [label.text() for label in self.panel._cards[0].findChildren(QLabel)]
        self.assertTrue(any("CLICK TO VIEW UPGRADES" in text for text in texts))

    def test_unlock_spends_skill_points_and_saves_rank(self):
        self.config.set("player", "skill_points", 2)
        skill = SkillManager(self.skills_file).load_skills()[0]
        dialog = SkillTreeDialog(skill, self.config, SkillManager(self.skills_file))
        self.addCleanup(dialog.close)

        self.assertTrue(dialog._canvas.try_unlock_node("core"))

        self.assertEqual(self.config.get("player", "skill_points"), 1)
        saved = json.loads(self.skills_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["skills"][0]["upgrades"][0].get("rank"), 1)
        self.assertIn("✦ 1 SP", dialog._sp_label.text())

        self.panel.refresh()
        self.assertIn("SKILL POINTS: 1", self.panel._points_label.text())

    def test_unlock_refused_without_points(self):
        skill = SkillManager(self.skills_file).load_skills()[0]
        dialog = SkillTreeDialog(skill, self.config, SkillManager(self.skills_file))
        self.addCleanup(dialog.close)

        self.assertFalse(dialog._canvas.try_unlock_node("core"))
        saved = json.loads(self.skills_file.read_text(encoding="utf-8"))
        self.assertNotIn("rank", saved["skills"][0]["upgrades"][0])

    def test_unlock_child_requires_unlocked_parent(self):
        self.config.set("player", "skill_points", 3)
        skill = SkillManager(self.skills_file).load_skills()[0]
        dialog = SkillTreeDialog(skill, self.config, SkillManager(self.skills_file))
        self.addCleanup(dialog.close)

        self.assertFalse(dialog._canvas.try_unlock_node("nova"))
        self.assertTrue(dialog._canvas.try_unlock_node("core"))
        self.assertTrue(dialog._canvas.try_unlock_node("nova"))
        saved = json.loads(self.skills_file.read_text(encoding="utf-8"))
        upgrades = {node["id"]: node for node in saved["skills"][0]["upgrades"]}
        self.assertEqual(upgrades["nova"].get("rank"), 1)
        self.assertEqual(self.config.get("player", "skill_points"), 1)

    def test_unlock_refused_at_max_rank(self):
        self.config.set("player", "skill_points", 3)
        skill = SkillManager(self.skills_file).load_skills()[0]
        for node in skill["upgrades"]:
            if node["id"] == "nova":
                node["rank"] = 2
        self.skills_file.write_text(json.dumps({"skills": [skill]}), encoding="utf-8")
        skill = SkillManager(self.skills_file).load_skills()[0]
        dialog = SkillTreeDialog(skill, self.config, SkillManager(self.skills_file))
        self.addCleanup(dialog.close)

        self.assertFalse(dialog._canvas.try_unlock_node("nova"))
        self.assertEqual(self.config.get("player", "skill_points"), 3)

    def test_ranks_persist_in_the_skill_file(self):
        self.config.set("player", "skill_points", 1)
        skill = SkillManager(self.skills_file).load_skills()[0]
        dialog = SkillTreeDialog(skill, self.config, SkillManager(self.skills_file))
        self.addCleanup(dialog.close)
        self.assertTrue(dialog._canvas.try_unlock_node("core"))

        reopened = SkillTreeDialog(
            SkillManager(self.skills_file).load_skills()[0],
            self.config,
            SkillManager(self.skills_file),
        )
        self.addCleanup(reopened.close)

        self.assertEqual(reopened._canvas.nodes["core"].current_rank, 1)
        self.assertEqual(reopened._canvas.nodes["nova"].current_rank, 0)

    def test_config_ranks_migrate_into_skill_files_on_startup(self):
        self.config.set_nested("player", "skill_upgrades", "fireball", "core", 2)
        self.config.save()

        panel = SkillsPanel(self.config, SkillManager(self.skills_file))
        self.addCleanup(panel.close)

        saved = json.loads(self.skills_file.read_text(encoding="utf-8"))
        upgrades = {node["id"]: node for node in saved["skills"][0]["upgrades"]}
        self.assertEqual(upgrades["core"].get("rank"), 2)
        self.assertIsNone(self.config.get_nested("player", "skill_upgrades"))

    def test_fireball_svg_is_loaded(self):
        image_file = Path(__file__).parent.parent / "skills" / "images" / "fireball.svg"

        self.assertIsNotNone(SkillCard._load_image(image_file))

    def test_skill_cards_use_responsive_grid_columns(self):
        skill = SkillManager(self.skills_file).load_skills()[0]
        self.skills_file.write_text(
            json.dumps({"skills": [skill, {**skill, "id": "second"}, {**skill, "id": "third"}]}),
            encoding="utf-8",
        )
        self.panel.refresh()
        self.panel._list.resize(960, 500)
        self.panel._arrange_cards()

        self.assertIsInstance(self.panel._list_layout, QGridLayout)
        self.assertEqual(SkillsPanel._columns_for_width(600), 1)
        self.assertEqual(SkillsPanel._columns_for_width(700), 2)
        self.assertEqual(SkillsPanel._columns_for_width(960), 3)
        self.assertIsNotNone(self.panel._list_layout.itemAtPosition(0, 2))
        self.assertEqual(
            self.panel._cards[0].sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Fixed,
        )

    def test_mission_skill_points_are_separate_from_stat_points(self):
        stats = StatsWidget(self.config)
        stats.grant_skill_points(3)

        self.assertEqual(self.config.get("player", "skill_points"), 3)
        self.assertEqual(self.config.get("player", "temp_points"), 10)
        stats.close()

    def test_new_skill_file_appears_and_disappears_automatically(self):
        self.assertEqual(len(self.panel._cards), 1)

        new_file = self.skills_dir / "ice-lance.json"
        new_file.write_text(
            json.dumps({
                "id": "ice-lance", "title": "Ice Lance", "description": "Freezes.",
                "image": "", "mana_cost": 6, "upgrade_cost": 1, "base_damage": 15,
                "upgrades": [
                    {"id": "core", "title": "Ice Lance Mastery",
                     "description": "A colder lance.", "x": 50, "y": 60,
                     "max_rank": 3},
                ],
            }),
            encoding="utf-8",
        )
        self._wait_for_cards(2)

        new_file.unlink()
        self._wait_for_cards(1)

    def test_edited_skill_file_reloads_automatically(self):
        skill = SkillManager(self.skills_file).load_skills()[0]
        skill["title"] = "Inferno"
        self.skills_file.write_text(json.dumps({"skills": [skill]}), encoding="utf-8")

        def card_titles():
            return [
                label.text()
                for card in self.panel._cards
                for label in card.findChildren(QLabel)
            ]

        self._wait_for_condition(lambda: "Inferno" in card_titles())

    def test_broken_skill_file_shows_error(self):
        (self.skills_dir / "broken.json").write_text("{not json", encoding="utf-8")

        self._wait_for_condition(lambda: not self.panel._error_label.isHidden())

        self.assertIn("broken.json", self.panel._error_label.text())

    def _wait_for_cards(self, expected: int, timeout_ms: int = 5000):
        self._wait_for_condition(lambda: len(self.panel._cards) == expected, timeout_ms)

    def _wait_for_condition(self, condition, timeout_ms: int = 5000):
        """Spin the event loop until the condition holds (or time runs out)."""
        waited = 0
        while not condition() and waited < timeout_ms:
            QTest.qWait(50)
            waited += 50
        self.assertTrue(condition())
