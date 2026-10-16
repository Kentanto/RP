"""Main menu."""
import pygame

from .. import audio, db, stats_model
from ..core import Scene
from ..settings import Colors, get_font, scaled
from ..ui import Button


class MainMenuScene(Scene):
    def __init__(self):
        super().__init__()
        self.minigames = Button("Minigames", 0.5, 0.2, 0.1, 0.1, Colors.hover_color)
        self.inventory = Button("Inventory", 0.5, 0.35, 0.1, 0.1, Colors.hover_color)
        self.missions = Button("Missions", 0.5, 0.5, 0.1, 0.1, Colors.hover_color)
        self.stats = Button("Stats", 0.5, 0.65, 0.1, 0.1, Colors.hover_color)
        self.header = ""

    def on_enter(self, app):
        audio.schedule_music_fade(app)
        sheet = stats_model.sheet()
        self.header = (f"Level {sheet['level']}    "
                       f"Points: {db.get_current_points()}    "
                       f"XP: {sheet['xp']}/{sheet['needed']}")

    def handle_event(self, app, event):
        if self.minigames.is_clicked(app, event):
            from .minigames import MinigamesScene
            app.push_scene(MinigamesScene())
        elif self.inventory.is_clicked(app, event):
            from .inventory import InventoryScene
            app.push_scene(InventoryScene())
        elif self.missions.is_clicked(app, event):
            from .missions import MissionsScene
            app.push_scene(MissionsScene())
        elif self.stats.is_clicked(app, event):
            from .status import StatusScene
            app.push_scene(StatusScene())

    def draw(self, app):
        header = get_font(30).render(self.header, True, Colors.light_gray)
        app.screen.blit(header, (app.width // 2 - header.get_width() // 2,
                                 scaled(14)))
        self.minigames.draw(app)
        self.inventory.draw(app)
        self.missions.draw(app)
        self.stats.draw(app)
