import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from athas.config import ConfigManager
from athas.stats_widget import (
    BASE_TEMP_POINTS,
    LEVEL_PERM_BONUS,
    LEVEL_TEMP_BONUS,
    StatsWidget,
    xp_for_next_level,
)


class LevelUpPointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = ConfigManager(Path(self.temp_dir.name) / "config.json")

    def make_widget(self):
        widget = StatsWidget(self.config)
        self.addCleanup(widget.close)
        return widget

    def test_level_up_grants_temp_and_permanent_points(self):
        widget = self.make_widget()

        levels = widget.grant_xp(xp_for_next_level(1))

        self.assertEqual(levels, 1)
        self.assertEqual(self.config.get("player", "level"), 2)
        self.assertEqual(
            self.config.get("player", "temp_points"),
            BASE_TEMP_POINTS + LEVEL_TEMP_BONUS,
        )
        self.assertEqual(self.config.get("player", "perm_points"), LEVEL_PERM_BONUS)
        self.assertEqual(widget._pool, BASE_TEMP_POINTS + LEVEL_TEMP_BONUS)
        self.assertEqual(widget._perm_pool, LEVEL_PERM_BONUS)

    def test_multiple_levels_scale_the_grant(self):
        widget = self.make_widget()

        levels = widget.grant_xp(xp_for_next_level(1) + xp_for_next_level(2))

        self.assertEqual(levels, 2)
        self.assertEqual(
            self.config.get("player", "temp_points"),
            BASE_TEMP_POINTS + 2 * LEVEL_TEMP_BONUS,
        )
        self.assertEqual(
            self.config.get("player", "perm_points"), 2 * LEVEL_PERM_BONUS
        )

    def test_xp_below_the_threshold_grants_nothing(self):
        widget = self.make_widget()

        levels = widget.grant_xp(xp_for_next_level(1) - 1)

        self.assertEqual(levels, 0)
        self.assertEqual(self.config.get("player", "temp_points"), BASE_TEMP_POINTS)
        self.assertEqual(self.config.get("player", "perm_points"), 0)

    def test_permanent_point_raises_a_stat_base_for_good(self):
        widget = self.make_widget()
        start_attack = self.config.get("player", "attack")
        widget.grant_xp(xp_for_next_level(1))

        widget._bars["attack"]._perm_allocate()

        self.assertEqual(self.config.get("player", "attack"), start_attack + 1)
        self.assertEqual(self.config.get("player", "perm_points"), 0)
        self.assertEqual(widget._bars["attack"].base, start_attack + 1)

        widget.refresh()
        self.assertEqual(widget._bars["attack"].base, start_attack + 1)
        self.assertFalse(widget._bars["attack"]._perm_btn.isEnabled())

    def test_perm_button_state_follows_the_balance(self):
        widget = self.make_widget()
        self.assertFalse(widget._bars["health"]._perm_btn.isEnabled())

        widget.grant_xp(xp_for_next_level(1))

        self.assertTrue(widget._bars["health"]._perm_btn.isEnabled())

    def test_permanent_point_refused_without_a_balance(self):
        widget = self.make_widget()
        start_attack = self.config.get("player", "attack")

        widget._bars["attack"]._perm_allocate()

        self.assertEqual(self.config.get("player", "attack"), start_attack)
        self.assertEqual(self.config.get("player", "perm_points"), 0)

    def test_permanent_point_respects_the_stat_cap(self):
        widget = self.make_widget()
        self.config.set("player", "attack", StatsWidget.MAX_STAT, save=False)
        self.config.save()
        widget.refresh()

        widget.grant_xp(xp_for_next_level(1))
        widget._bars["attack"]._perm_allocate()

        self.assertEqual(self.config.get("player", "attack"), StatsWidget.MAX_STAT)
        self.assertEqual(self.config.get("player", "perm_points"), LEVEL_PERM_BONUS)

    def test_uncompleting_revokes_the_unspent_level_rewards(self):
        widget = self.make_widget()
        widget.grant_xp(xp_for_next_level(1))

        lost = widget.remove_xp(xp_for_next_level(1))

        self.assertEqual(lost, 1)
        self.assertEqual(self.config.get("player", "level"), 1)
        self.assertEqual(self.config.get("player", "temp_points"), BASE_TEMP_POINTS)
        self.assertEqual(self.config.get("player", "perm_points"), 0)


if __name__ == "__main__":
    unittest.main()
