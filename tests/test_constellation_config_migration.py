import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QWidget

from athas.ability_tree_panel import AbilityTreePanel, NODES, SkillMapCanvas
from athas.config import ConfigManager


class FakeSkillMapCanvas(QWidget):
    constellation_changed = Signal(int)

    def __init__(self, nodes, config, parent=None):
        super().__init__(parent)
        self.nodes = {node.id: node for node in nodes}
        self.config = config
        self.scale = 1.0
        SkillMapCanvas._load_ranks(self)


class ConstellationConfigMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_legacy_skill_ranks_migrate_to_constellations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager(Path(temp_dir) / "config.json")
            config.data["skills"] = {
                "A_Prevalence": 0,
                "B_Scales": 1,
            }

            with patch("athas.ability_tree_panel.SkillMapCanvas", FakeSkillMapCanvas):
                panel = AbilityTreePanel(config)

            self.assertEqual(config.get_nested("constellations", "A_Prevalence"), 0)
            self.assertEqual(config.get_nested("constellations", "B_Scales"), 1)
            self.assertNotIn("skills", config.data)
            self.assertTrue(all(node.id in config.data["constellations"] for node in NODES))
            panel.close()

    def test_existing_constellation_ranks_take_precedence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager(Path(temp_dir) / "config.json")
            config.data["skills"] = {"A_Prevalence": 0}
            config.data["constellations"] = {"A_Prevalence": 1}

            with patch("athas.ability_tree_panel.SkillMapCanvas", FakeSkillMapCanvas):
                panel = AbilityTreePanel(config)

            self.assertEqual(config.get_nested("constellations", "A_Prevalence"), 1)
            self.assertNotIn("skills", config.data)
            panel.close()
