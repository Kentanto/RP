"""Headless smoke tests for the Athas game package.

Runs with SDL dummy drivers, drives the scene stack with synthetic events
and verifies the skill tree logic end to end (selection, leveling,
unlocking, persistence, navigation).
"""
import os
import sys
import tempfile
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from game import db, settings, skills_data  # noqa: E402

TMP = tempfile.mkdtemp(prefix="athas_test_")
settings.DB_PATH = os.path.join(TMP, "artifacts.db")
db.initialize_database()

from game.core import App  # noqa: E402
from game.scenes.inventory import InventoryScene  # noqa: E402
from game.scenes.math_menu import MathMenuScene  # noqa: E402
from game.scenes.menu import MainMenuScene  # noqa: E402
from game.scenes.missions import MissionsScene  # noqa: E402
from game.scenes.minigames import (MathGameScene, MinigamesScene,  # noqa: E402
                                   generate_math_equation, safe_eval)
from game.scenes.shop import ShopScene  # noqa: E402
from game.scenes.skill_tree import SkillTreeScene  # noqa: E402
from game.scenes.status import StatusScene  # noqa: E402


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})


def key(unicode="", key_code=None):
    attrs = {"unicode": unicode}
    if key_code is not None:
        attrs["key"] = key_code
    return pygame.event.Event(pygame.KEYDOWN, attrs)


class AthasSmokeTest(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = App()

    def _draw_frame(self, scene=None):
        scene = scene or self.app.scene
        self.app.draw_background()
        scene.draw(self.app)

    # ------------------------------------------------------------- data

    def test_layout_covers_all_nodes(self):
        positions = skills_data.compute_layout()
        self.assertEqual(len(positions), 14)  # 2 skills + 12 upgrades
        for source, target in skills_data.edges():
            self.assertIn(source, positions)
            self.assertIn(target, positions)

    def test_safe_eval(self):
        self.assertEqual(safe_eval("2**3+1"), 9)
        self.assertAlmostEqual(safe_eval("(2+3)*4"), 20)
        with self.assertRaises(ValueError):
            safe_eval("__import__('os').system('true')")

    def test_generated_equations_are_safe_and_valid(self):
        for _ in range(200):
            equation = generate_math_equation(3)
            safe_eval(equation)  # must not raise

    def test_skill_progress_persistence(self):
        db.save_skill_progress("Fireball", 2, ["Fireball Mastery"])
        stored = db.load_skill_progress()
        self.assertEqual(stored["Fireball"]["level"], 2)
        self.assertEqual(stored["Fireball"]["upgrades"], ["Fireball Mastery"])

    # ------------------------------------------------------- navigation

    def test_menu_to_status_to_skill_tree(self):
        app = self.app
        app.scenes.clear()
        app.push_scene(MainMenuScene())
        self._draw_frame()

        # "Stats" button sits at (0.5, 0.65) of an 800x600 window.
        app.dispatch(click((400, 390)))
        self.assertIsInstance(app.scene, StatusScene)
        self._draw_frame()

        # "Skills" button sits at (0.5, 0.05).
        app.dispatch(click((400, 30)))
        self.assertIsInstance(app.scene, SkillTreeScene)
        self.assertGreater(app.scene.points, 0)
        self._draw_frame()

        # ESC goes back through the stack without recursion.
        app.dispatch(key(key_code=pygame.K_ESCAPE))
        self.assertIsInstance(app.scene, StatusScene)
        app.dispatch(key(key_code=pygame.K_ESCAPE))
        self.assertIsInstance(app.scene, MainMenuScene)
        app.dispatch(key(key_code=pygame.K_ESCAPE))
        self.assertIsInstance(app.scene, MainMenuScene)  # root: nothing to pop

    def test_skill_tree_level_up_and_unlock(self):
        app = self.app
        app.scenes.clear()
        # Reset progress (other tests may have written to the shared test DB).
        db.save_skill_progress("Fireball", 0, [])
        db.save_skill_progress("Ice Shard", 0, [])
        app.push_scene(SkillTreeScene())
        scene = app.scene
        points_before = scene.points
        self._draw_frame()

        # Camera frames the Fireball root at screen center (400, 300).
        app.dispatch(click((400, 300)))
        self.assertEqual(scene.selected, "Fireball")

        # Panel action button (bottom of the right-hand panel).
        button_center = scene._action_button_rect(app).center
        app.dispatch(click(button_center))
        self.assertEqual(scene.progress["Fireball"]["level"], 1)
        self.assertEqual(scene.points, points_before - 1)
        self._draw_frame()

        # Level up once more, then unlock Fireball Mastery (needs level 2).
        app.dispatch(click(button_center))
        self.assertEqual(scene.progress["Fireball"]["level"], 2)

        mastery_world = scene.layout["Fireball Mastery"]
        screen_pos = scene.camera.world_to_screen(
            mastery_world[0], mastery_world[1], (app.width, app.height))
        app.dispatch(click(screen_pos))
        self.assertEqual(scene.selected, "Fireball Mastery")
        self._draw_frame()
        app.dispatch(click(button_center))
        self.assertIn("Fireball Mastery", scene.progress["Fireball"]["upgrades"])
        self.assertEqual(scene.points, points_before - 2 - 50)

        # Double-click quick action: level Fireball via node clicks.
        app.dispatch(click((400, 300)))
        app.dispatch(click((400, 300)))
        self.assertEqual(scene.progress["Fireball"]["level"], 3)

        # Persisted to the database.
        stored = db.load_skill_progress()
        self.assertEqual(stored["Fireball"]["level"], 3)
        self.assertIn("Fireball Mastery", stored["Fireball"]["upgrades"])

        # Zoom keeps the world point under the cursor anchored.
        world_before = scene.camera.screen_to_world(400, 300, (800, 600))
        app.dispatch(pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1, "pos": (400, 300)}))
        world_after = scene.camera.screen_to_world(400, 300, (800, 600))
        self.assertAlmostEqual(world_before[0], world_after[0], places=3)

    def test_math_game_round_flow(self):
        app = self.app
        app.scenes.clear()
        points_before = db.get_current_points()
        app.push_scene(MathGameScene(1))
        scene = app.scene
        answer = scene.answer

        # Type the correct answer and submit.
        for char in str(answer):
            app.dispatch(key(unicode=char))
        app.dispatch(key(key_code=pygame.K_RETURN))
        self.assertEqual(len(app.scenes), 2)  # result overlay pushed
        self._draw_frame()

        # Dismiss the overlay -> next round is charged (20) and continues.
        app.dispatch(key(key_code=pygame.K_SPACE))
        self.assertEqual(len(app.scenes), 1)
        self.assertEqual(db.get_current_points(), points_before - 20)

        # Leaving refunds the round fee.
        scene._leave(app)
        self.assertEqual(db.get_current_points(), points_before)

    def test_all_scenes_draw_without_crashing(self):
        app = self.app
        app.scenes.clear()
        db.add_artifact("Test Artifact", "ATK", 10, "DEF", 5, None, None)
        from game.scenes.artifacts import ArtifactDetailScene, ArtifactsScene
        for scene in (MainMenuScene(), MinigamesScene(), MathMenuScene(),
                      StatusScene(), SkillTreeScene(), InventoryScene(),
                      ShopScene(), MissionsScene(), ArtifactsScene(),
                      ArtifactDetailScene(1, equip_slot=1, remove_slot=1)):
            app.push_scene(scene)
            self._draw_frame(scene)
            app.dispatch(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (100, 100)}))
            self._draw_frame(scene)
            app.pop_scene()


if __name__ == "__main__":
    unittest.main(verbosity=2)

