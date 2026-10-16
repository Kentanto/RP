"""Headless smoke tests for the Athas game package.

Runs with SDL dummy drivers, drives the scene stack with synthetic events
and verifies the skill tree logic end to end (selection, leveling,
unlocking, persistence, navigation).
"""
import os
import sys
import tempfile
import time
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
from game.scenes.math_menu import MathMenuScene, TIERS  # noqa: E402
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
        artifact_points_before = db.get_artifact_points()
        app.push_scene(MathGameScene(1))
        scene = app.scene
        answer = scene.answer

        # Type the correct answer and submit.
        for char in str(answer):
            app.dispatch(key(unicode=char))
        app.dispatch(key(key_code=pygame.K_RETURN))
        self.assertEqual(len(app.scenes), 2)  # result overlay pushed
        self._draw_frame()

        # A correct Easy answer pays 10 skill points + 100 artifact points.
        self.assertEqual(db.get_current_points(), points_before + 10)
        self.assertEqual(db.get_artifact_points(), artifact_points_before + 100)
        self.assertEqual(scene.streak, 1)

        # Dismiss the overlay -> the next round fee (20) is charged.
        app.dispatch(key(key_code=pygame.K_SPACE))
        self.assertEqual(len(app.scenes), 1)
        self.assertEqual(db.get_current_points(), points_before - 10)

        # A second correct answer grows the streak (+10% artifact points).
        for char in str(scene.answer):
            app.dispatch(key(unicode=char))
        app.dispatch(key(key_code=pygame.K_RETURN))
        self.assertEqual(scene.streak, 2)
        self.assertEqual(db.get_artifact_points(), artifact_points_before + 210)

        # A wrong answer resets the streak.
        app.dispatch(key(key_code=pygame.K_SPACE))
        wrong = scene.answer + 0.7
        for char in str(wrong):
            app.dispatch(key(unicode=char))
        app.dispatch(key(key_code=pygame.K_RETURN))
        self.assertEqual(scene.streak, 0)

        # Dismiss the result overlay like a player, then leave: the pending
        # round fee is refunded and rewards are kept. Net for the session:
        # two rounds consumed (40) minus the two solve rewards (20).
        app.dispatch(key(key_code=pygame.K_SPACE))
        scene._leave(app)
        self.assertEqual(db.get_current_points(), points_before - 20)

    def test_math_difficulty_locks(self):
        app = self.app
        app.scenes.clear()
        app.push_scene(MathMenuScene())
        scene = app.scene
        self._draw_frame()
        points = db.get_current_points()
        level = db.get_base_stats()["level"]

        # Tiers above the character level are locked: nothing charged.
        locked = [tier for tier in TIERS if tier.level_req > level]
        if locked:                               # skipped naturally at high level
            rect = next(rect for rect, tier in scene.row_rects
                        if tier is locked[0])
            app.dispatch(click(rect.center))
            self.assertIsInstance(app.scene, MathMenuScene)
            self.assertEqual(db.get_current_points(), points)

        # Easy is open from the start and charges its fee.
        easy = TIERS[0]
        rect = next(rect for rect, tier in scene.row_rects if tier is easy)
        app.dispatch(click(rect.center))
        self.assertIsInstance(app.scene, MathGameScene)
        self.assertEqual(db.get_current_points(), points - easy.fee)

        # Leaving mid-round refunds the fee.
        app.scene._leave(app)
        self.assertEqual(db.get_current_points(), points)

    def test_item_use_and_sell(self):
        def owned(item_key):
            for row in db.get_inventory_items():
                if row["key"] == item_key:
                    return row["quantity"]
            return 0

        # Using a consumable restores HP and consumes one unit.
        db.add_item("health_potion")
        potions_before = owned("health_potion")
        db.adjust_resources(-10000, -10000)          # drop both pools to zero
        ok, message = db.use_item("health_potion")
        self.assertTrue(ok, message)
        self.assertGreater(db.get_resources()["hp"], 0)
        self.assertEqual(owned("health_potion"), potions_before - 1)

        # Selling pays the sell_price and consumes one unit.
        db.add_item("mana_crystal")
        crystals_before = owned("mana_crystal")
        points_before = db.get_current_points()
        ok, message = db.sell_item("mana_crystal")
        self.assertTrue(ok, message)
        self.assertEqual(db.get_current_points(), points_before + 50)
        self.assertEqual(owned("mana_crystal"), crystals_before - 1)

        # Equipped gear has to be taken off before selling it.
        db.add_item("iron_sword")
        db.equip_gear("weapon", "iron_sword")
        ok, _ = db.sell_item("iron_sword")
        self.assertFalse(ok)
        db.unequip_gear("weapon")

    def test_resources_regen_and_clamp(self):
        base = db.get_base_stats()

        # Spending clamps at zero, restoring clamps at the max.
        db.adjust_resources(-10000, -10000)
        self.assertEqual(db.get_resources()["hp"], 0)
        self.assertEqual(db.get_resources()["mana"], 0)
        db.adjust_resources(10000, 10000)
        self.assertEqual(db.get_resources()["hp"], base["hp"])
        self.assertEqual(db.get_resources()["mana"], base["mana"])

        # Time-based regen: fake ten minutes of rest.
        with db._connect() as conn:
            conn.execute("UPDATE stats SET hp_current=0, mana_current=0, "
                         "regen_at=? WHERE id=1", (int(time.time()) - 600,))
            conn.commit()
        resources = db.get_resources()
        self.assertGreater(resources["hp"], 0)
        self.assertGreater(resources["mana"], 0)
        self.assertLessEqual(resources["hp"], base["hp"])

    def test_missions_progress_and_claim(self):
        # Definitions were synced from data/missions.txt.
        missions = {m["key"]: m for m in db.get_missions()}
        self.assertTrue(missions)
        self.assertGreaterEqual(missions["boot_camp"]["target"], 1)

        # Counter progress bumps add up.
        db.bump_mission("math_correct", 3)
        self.assertGreaterEqual(
            {m["key"]: m for m in db.get_missions()}["boot_camp"]["progress"], 3)

        # Push to completion, then claim exactly once.
        boot = {m["key"]: m for m in db.get_missions()}["boot_camp"]
        db.bump_mission("math_correct", max(0, boot["target"] - boot["progress"]))
        mission = {m["key"]: m for m in db.get_missions()}["boot_camp"]
        points_before = db.get_current_points()
        ok, message = db.claim_mission("boot_camp")
        self.assertTrue(ok, message)
        self.assertEqual(db.get_current_points(),
                         points_before + mission["reward_points"])
        ok, _ = db.claim_mission("boot_camp")
        self.assertFalse(ok)                        # a mission pays out once

        # The artifact hook moves artifact missions along.
        before = next(m["progress"] for m in db.get_missions()
                      if m["mtype"] == "artifacts" and m["target"] == 3)
        db.add_artifact({"name": "Mission Hook", "main_stat": "ATK",
                         "main_stat_value": 1, "max_level": 5, "def_key": "relic"})
        after = next(m["progress"] for m in db.get_missions()
                     if m["mtype"] == "artifacts" and m["target"] == 3)
        self.assertEqual(after, before + 1)

        # The skill-upgrade hook counts owned upgrades.
        db.save_skill_progress("Ice Shard", 1, ["Frost"])
        upgrades = next(m["progress"] for m in db.get_missions()
                        if m["mtype"] == "upgrades")
        self.assertGreaterEqual(upgrades, 1)

    def test_all_scenes_draw_without_crashing(self):
        app = self.app
        app.scenes.clear()
        artifact_id = db.add_artifact({
            "name": "Test Artifact", "main_stat": "ATK", "main_stat_value": 10,
            "sub_stat1": "DEF", "sub_stat1_value": 5,
            "max_level": 20, "def_key": "relic"})
        from game.scenes.artifacts import ArtifactDetailScene, ArtifactsScene
        from game.scenes.inventory import ItemActionScene
        from game.scenes.status import GearPickerScene
        item = dict(db.get_item_defs()[0])
        item["quantity"] = 1
        for scene in (MainMenuScene(), MinigamesScene(), MathMenuScene(),
                      StatusScene(), SkillTreeScene(), InventoryScene(),
                      ShopScene(), MissionsScene(), ArtifactsScene(),
                      ArtifactDetailScene(artifact_id, equip_slot=1, remove_slot=1),
                      GearPickerScene("weapon"), ItemActionScene(item)):
            app.push_scene(scene)
            self._draw_frame(scene)
            app.dispatch(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (100, 100)}))
            self._draw_frame(scene)
            app.pop_scene()

    def test_ui_scale_system(self):
        """Fonts and fixed offsets scale with the window size, and resize
        events flow through the App."""
        settings.set_ui_scale(800, 600)
        self.assertEqual(settings.ui_scale(), 1.0)
        base = settings.get_font(40).get_height()

        settings.set_ui_scale(1600, 1200)
        self.assertEqual(settings.ui_scale(), 2.0)
        self.assertGreater(settings.get_font(40).get_height(), base)
        self.assertEqual(settings.scaled(20), 40)

        # Clamped at both ends so extreme windows stay usable.
        settings.set_ui_scale(4000, 4000)
        self.assertEqual(settings.ui_scale(), 2.0)
        settings.set_ui_scale(100, 100)
        self.assertEqual(settings.ui_scale(), 0.75)

        # VIDEORESIZE events update the app and the scale.
        self.app.dispatch(pygame.event.Event(
            pygame.VIDEORESIZE, {"w": 1024, "h": 768}))
        self.assertEqual((self.app.width, self.app.height), (1024, 768))
        self.assertAlmostEqual(settings.ui_scale(), 1.28)

        settings.set_ui_scale(800, 600)

    def test_scenes_draw_at_other_window_sizes(self):
        """The layout must survive window resizes: every scene renders at a
        large and a small window without crashing."""
        from game.scenes.artifacts import ArtifactDetailScene, ArtifactsScene
        from game.scenes.inventory import ItemActionScene
        from game.scenes.status import GearPickerScene
        artifact_id = db.add_artifact({
            "name": "Resize Artifact", "main_stat": "ATK",
            "main_stat_value": 10, "sub_stat1": "DEF", "sub_stat1_value": 5,
            "max_level": 20, "def_key": "relic"})
        item = dict(db.get_item_defs()[0])
        item["quantity"] = 1
        app = self.app
        app.scenes.clear()
        for width, height in ((1280, 800), (480, 320)):
            app.width, app.height = width, height
            settings.set_ui_scale(width, height)
            scenes = (MainMenuScene(), MinigamesScene(), MathMenuScene(),
                      StatusScene(), SkillTreeScene(), InventoryScene(),
                      ShopScene(), MissionsScene(), ArtifactsScene(),
                      ArtifactDetailScene(artifact_id, equip_slot=1,
                                         remove_slot=1),
                      GearPickerScene("weapon"), ItemActionScene(item),
                      MathGameScene(20))
            for scene in scenes:
                app.push_scene(scene)
                self._draw_frame(scene)
                if isinstance(scene, InventoryScene):
                    # Tabs must wrap inside the window, never overflow it,
                    # and the grid starts below the last tab row.
                    for rect in scene.tab_rects:
                        self.assertLessEqual(rect.right, width)
                        self.assertGreaterEqual(rect.x, 0)
                    padding, cell, _x, start_y, _cols, _rows = scene._grid(app)
                    self.assertGreater(start_y, max(r.bottom for r in scene.tab_rects))
                app.pop_scene()
        app.scenes.clear()
        app.width, app.height = 800, 600
        settings.set_ui_scale(800, 600)

    # --------------------------------------------------- content definitions

    def test_content_parser(self):
        from game import content
        path = os.path.join(TMP, "sample.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# comment\n[thing]\nname: Thing\ntags: a, b\n"
                         "boost: damage=1.5, mana_cost=0.9\n"
                         "range: ATK=10-40\n"
                         "desc: Long text\n    continues here.\n")
        entry = content.parse_file(path)["thing"]
        self.assertEqual(content.as_str(entry, "name"), "Thing")
        self.assertEqual(content.as_list(entry, "tags"), ("a", "b"))
        self.assertEqual(content.as_stat_map(entry, "boost"),
                         {"damage": 1.5, "mana_cost": 0.9})
        self.assertEqual(content.as_range_map(entry, "range"),
                         {"ATK": (10.0, 40.0)})
        self.assertIn("continues", content.as_str(entry, "desc"))

    def test_item_defs_synced_and_purchasable(self):
        defs = db.get_item_defs()
        self.assertTrue(any(d["key"] == "health_potion" for d in defs))
        self.assertTrue(any(d["category"] == "special" for d in defs))

        points = db.get_current_points()
        ok, message = db.purchase_item("health_potion")
        self.assertTrue(ok, message)
        owned = {row["key"]: row["quantity"] for row in db.get_inventory_items()}
        self.assertEqual(owned.get("health_potion"), 1)
        self.assertEqual(db.get_current_points(), points - 100)

        # granting respects stacking
        self.assertTrue(db.add_item("health_potion", 3))
        owned = {row["key"]: row["quantity"] for row in db.get_inventory_items()}
        self.assertEqual(owned.get("health_potion"), 4)

    def test_artifacts_generate_from_defs(self):
        artifact = db.generate_artifact_by_level(8)
        self.assertIsNotNone(artifact)
        self.assertIsNotNone(db.get_artifact_def(artifact["def_key"]))
        self.assertGreater(artifact["main_stat_value"], 0)
        if "sub_stat2" in artifact:
            self.assertIn("sub_stat1", artifact)
        artifact_id = db.add_artifact(artifact)
        row = db.get_artifact(artifact_id)
        self.assertEqual(row["def_key"], artifact["def_key"])

    # ------------------------------------------------------- character stats

    def test_base_stats_and_leveling(self):
        base = db.get_base_stats()
        self.assertEqual(base["level"], 1)
        self.assertEqual(base["hp"], 100)

        result = db.add_xp(db.xp_for_level(1))
        self.assertEqual(result["levels_gained"], 1)
        self.assertEqual(result["level"], 2)

        grown = db.get_base_stats()
        self.assertEqual(grown["atk"], base["atk"] + 2)
        self.assertEqual(grown["hp"], base["hp"] + 20)
        self.assertEqual(grown["def"], base["def"] + 1)

    def test_gear_equip_and_sheet_totals(self):
        from game import stats_model
        db.unequip_gear("weapon")
        bare_atk = stats_model.sheet()["stats"]["ATK"]["total"]

        self.assertTrue(db.add_item("iron_sword"))
        self.assertTrue(db.equip_gear("weapon", "iron_sword"))
        self.assertFalse(db.equip_gear("head", "iron_sword"))   # slot mismatch

        equipped = stats_model.sheet()["stats"]["ATK"]
        self.assertEqual(equipped["gear"], 5)
        self.assertEqual(equipped["total"], bare_atk + 5)

        db.unequip_gear("weapon")
        self.assertEqual(stats_model.sheet()["stats"]["ATK"]["total"], bare_atk)

    def test_artifact_bonuses_in_sheet(self):
        from game import stats_model
        artifact_id = db.add_artifact({
            "name": "Sheet Test", "main_stat": "ATK", "main_stat_value": 30,
            "sub_stat1": "ATK%", "sub_stat1_value": 0.10,
            "max_level": 20, "def_key": "relic"})
        self.assertTrue(db.set_equipped_artifact(1, artifact_id))
        atk = stats_model.sheet()["stats"]["ATK"]
        self.assertGreaterEqual(atk["artifact"], 30)
        self.assertGreaterEqual(atk["pct"], 0.10)
        db.remove_equipped_artifact(1, artifact_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)

