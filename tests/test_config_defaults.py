import tempfile
import unittest
from pathlib import Path

from athas.config import DEFAULTS, ConfigManager


class ConfigDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_nested_defaults_are_not_shared_between_configs(self):
        first = ConfigManager(self.root / "one" / "config.json")
        first.set_nested("player", "temp_allocations", "health", 7)
        first.save()

        second = ConfigManager(self.root / "two" / "config.json")

        self.assertEqual(second.get_nested("player", "temp_allocations", "health"), 0)
        self.assertEqual(DEFAULTS["player"]["temp_allocations"]["health"], 0)
        self.assertEqual(
            DEFAULTS["player"]["temp_allocations"],
            {"health": 0, "magic": 0, "attack": 0, "defense": 0, "speed": 0},
        )
