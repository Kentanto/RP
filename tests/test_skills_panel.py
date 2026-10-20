import tempfile
import unittest
import json
from pathlib import Path

from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QGridLayout, QLabel, QPushButton, QSizePolicy,
)

from athas.config import ConfigManager
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
            """{"skills":[{"id":"fireball","title":"Fireball","description":"Burns.",
            "image":"fireball.svg","mana_cost":10,"max_level":5,"upgrade_cost":1,
            "base_damage":25,"damage_per_level":10}]}""",
            encoding="utf-8",
        )
        self.panel = SkillsPanel(self.config, SkillManager(self.skills_file))
        self.addCleanup(self.panel.close)

    def test_upgrade_spends_skill_points_and_improves_level(self):
        self.config.set("player", "skill_points", 2)
        self.panel.refresh()

        buttons = self.panel.findChildren(QPushButton)
        enabled_buttons = [button for button in buttons if button.isEnabled()]
        self.assertEqual(len(enabled_buttons), 1)
        enabled_buttons[0].click()

        self.assertEqual(self.config.get("player", "skill_points"), 1)
        self.assertEqual(self.config.get_nested("player", "skill_levels", "fireball"), 1)
        self.assertIn("SKILL POINTS: 1", self.panel._points_label.text())

    def test_upgrade_disabled_without_points(self):
        button = self.panel.findChild(QPushButton)

        self.assertIsNotNone(button)
        self.assertFalse(button.isEnabled())

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
                "image": "", "mana_cost": 6, "max_level": 3, "upgrade_cost": 1,
                "base_damage": 15, "damage_per_level": 5,
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
