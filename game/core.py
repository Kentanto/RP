"""App core: window, main loop, and the scene stack.

The old code navigated by calling the next menu function inside the current
menu's while-loop (main_menu() -> status_window() -> skill_tree_menu() -> ...),
so the Python call stack grew forever and "Back" never really returned.
The scene stack replaces that: opening a screen pushes a scene, going back
pops it. O(1) navigation, no leaks, one event loop, one FPS-capped clock.
"""
import os

import pygame

from . import settings
from .settings import Colors


class Scene:
    """Base class for every screen."""

    def __init__(self):
        self.flash_text = None
        self.flash_color = Colors.red
        self.flash_until = 0

    # -- lifecycle ------------------------------------------------------
    def on_enter(self, app):
        """Called when the scene becomes the top of the stack."""

    def on_exit(self, app):
        """Called when the scene stops being the top of the stack."""

    # -- per-frame ------------------------------------------------------
    def handle_event(self, app, event):
        pass

    def draw(self, app):
        pass

    # -- helpers ---------------------------------------------------------
    def flash(self, text, color=Colors.red, ms=1500):
        self.flash_text = text
        self.flash_color = color
        self.flash_until = pygame.time.get_ticks() + ms

    def draw_flash(self, app):
        from . import ui
        if self.flash_text:
            if not ui.draw_flash(app.screen, self.flash_text, self.flash_color,
                                 app.width, app.height, self.flash_until):
                self.flash_text = None


class App:
    """Owns the window, the clock, the sounds, and the scene stack."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Athas system")
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        settings.set_ui_scale(self.width, self.height)
        self.clock = pygame.time.Clock()
        self.scenes = []
        self.sounds = {}
        self.running = True
        self._background_raw = self._load_background()
        self._background_scaled = None

    # ------------------------------------------------------------ background
    def _load_background(self):
        path = os.path.join(settings.ICONS_DIR, "background_menu.png")
        try:
            return pygame.image.load(path).convert()
        except (pygame.error, FileNotFoundError):
            return None

    def _rescale_background(self):
        if self._background_raw is not None:
            self._background_scaled = pygame.transform.scale(
                self._background_raw, (self.width, self.height))

    def draw_background(self):
        if self._background_scaled is None:
            self._rescale_background()
        if self._background_scaled is not None:
            self.screen.blit(self._background_scaled, (0, 0))
        else:
            self.screen.fill((16, 16, 24))

    # ------------------------------------------------------------ scene stack
    @property
    def scene(self):
        return self.scenes[-1] if self.scenes else None

    def push_scene(self, scene):
        if self.scene is not None:
            self.scene.on_exit(self)
        self.scenes.append(scene)
        scene.on_enter(self)

    def pop_scene(self):
        if not self.scenes:
            return
        self.scenes[-1].on_exit(self)
        self.scenes.pop()
        if self.scene is not None:
            self.scene.on_enter(self)

    def pop_to_scene(self, scene_class):
        """Pop until the top scene is (a subclass of) scene_class."""
        while self.scenes and not isinstance(self.scene, scene_class):
            self.pop_scene()

    def replace_scene(self, scene):
        if self.scenes:
            self.pop_scene()
        self.push_scene(scene)

    # ----------------------------------------------------------------- loop
    def dispatch(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.width = max(1, event.w)
            self.height = max(1, event.h)
            settings.set_ui_scale(self.width, self.height)
            self._background_scaled = None
            return
        # ESC goes back everywhere, except in scenes that opt out
        # (e.g. the math game, where leaving refunds the round fee).
        if event.type == pygame.KEYDOWN and getattr(event, "key", None) == pygame.K_ESCAPE:
            scene = self.scene
            if scene is not None and getattr(scene, "handles_escape", False):
                scene.handle_event(self, event)
            elif len(self.scenes) > 1:
                self.pop_scene()
            return
        scene = self.scene
        if scene is not None:
            scene.handle_event(self, event)

    def run(self):
        while self.running and self.scenes:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                self.dispatch(event)

            scene = self.scene
            if scene is not None:
                self.draw_background()
                scene.draw(self)
                pygame.display.flip()
            self.clock.tick(settings.FPS)

    def quit(self):
        self.running = False
