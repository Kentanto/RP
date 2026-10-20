import tempfile
import unittest
from pathlib import Path

from athas.config import ConfigManager, migrate_constellation_ranks


class ConstellationConfigMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = ConfigManager(Path(self.temp_dir.name) / "config.json")

    def test_legacy_constellation_ranks_migrate_out_of_skills(self):
        self.config.data["skills"] = {
            "A_Prevalence": 0,
            "B_Scales": 1,
            "unrelated": "preserved",
        }

        migrate_constellation_ranks(self.config, {"A_Prevalence", "B_Scales"})

        self.assertEqual(self.config.get_nested("constellations", "A_Prevalence"), 0)
        self.assertEqual(self.config.get_nested("constellations", "B_Scales"), 1)
        self.assertEqual(self.config.data["skills"], {"unrelated": "preserved"})

    def test_existing_constellation_ranks_take_precedence(self):
        self.config.data["skills"] = {"A_Prevalence": 0}
        self.config.data["constellations"] = {"A_Prevalence": 1}

        migrate_constellation_ranks(self.config, {"A_Prevalence"})

        self.assertEqual(self.config.get_nested("constellations", "A_Prevalence"), 1)
        self.assertNotIn("skills", self.config.data)
