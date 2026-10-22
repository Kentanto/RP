import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from athas.config import ConfigManager
from athas.stats_widget import BASE_TEMP_POINTS, StatsWidget


class FortuneMultiplierTests(unittest.TestCase):
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

    def test_base_pool_without_fortune(self):
        widget = self.make_widget()

        self.assertEqual(widget._pool, BASE_TEMP_POINTS)

    def test_fortune_multiplies_the_pool(self):
        self.config.set_nested("constellations", "B_Fortune", 1, save=False)
        self.config.save()

        widget = self.make_widget()

        self.assertEqual(widget._pool, BASE_TEMP_POINTS * 2)

    def test_ranking_fortune_up_grants_the_extra_points(self):
        widget = self.make_widget()
        widget._bars["health"]._allocate(4)
        self.assertEqual(widget._pool, BASE_TEMP_POINTS - 4)

        self.config.set_nested("constellations", "B_Fortune", 1, save=False)
        self.config.save()
        widget.refresh()

        self.assertEqual(widget._pool, BASE_TEMP_POINTS * 2 - 4)
        self.assertEqual(
            self.config.get_nested("player", "temp_allocations", "health"), 4
        )

    def test_spent_points_stay_spent_on_refresh(self):
        widget = self.make_widget()
        widget._bars["health"]._allocate(4)

        widget.refresh()

        self.assertEqual(widget._pool, BASE_TEMP_POINTS - 4)

    def test_released_points_are_not_duplicated(self):
        widget = self.make_widget()
        widget._bars["health"]._allocate(4)
        widget._bars["health"].release_all()

        widget.refresh()

        self.assertEqual(widget._pool, BASE_TEMP_POINTS)
