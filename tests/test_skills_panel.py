import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QPushButton

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
        self.skills_file = self.root / "skills.json"
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

    def test_mission_skill_points_are_separate_from_stat_points(self):
        stats = StatsWidget(self.config)
        stats.grant_skill_points(3)

        self.assertEqual(self.config.get("player", "skill_points"), 3)
        self.assertEqual(self.config.get("player", "temp_points"), 10)
        stats.close()
