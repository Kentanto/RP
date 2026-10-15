"""Main menu."""
import pygame

from .. import audio
from ..core import Scene
from ..settings import Colors
from ..ui import Button


class MainMenuScene(Scene):
    def __init__(self):
        super().__init__()
        self.minigames = Button("Minigames", 0.5, 0.2, 0.1, 0.1, Colors.hover_color)
        self.inventory = Button("Inventory", 0.5, 0.35, 0.1, 0.1, Colors.hover_color)
        self.missions = Button("Missions", 0.5, 0.5, 0.1, 0.1, Colors.hover_color)
        self.stats = Button("Stats", 0.5, 0.65, 0.1, 0.1, Colors.hover_color)

    def on_enter(self, app):
        audio.schedule_music_fade(app)

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
        self.minigames.draw(app)
        self.inventory.draw(app)
        self.missions.draw(app)
        self.stats.draw(app)
