"""Loading screen shown at startup (fades in over the menu background)."""
import pygame

from .. import audio
from ..core import Scene
from ..settings import Colors, get_font


class BootScene(Scene):
    def __init__(self):
        super().__init__()
        self.start_ticks = None
        self.duration = 2700  # ms; matches the old default loading time

    def on_enter(self, app):
        self.start_ticks = pygame.time.get_ticks()
        song_seconds = audio.start_random_song()
        if song_seconds:
            # Keep the old "loading time tracks the song intro" feel, capped.
            self.duration = min(6000, max(2000, int(song_seconds * 100)))

    def draw(self, app):
        elapsed = pygame.time.get_ticks() - self.start_ticks
        progress = min(elapsed / self.duration, 1.0)

        app.draw_background()

        fade = pygame.Surface((app.width, app.height))
        fade.fill(Colors.black)
        fade.set_alpha(int(255 * (1 - progress)))
        app.screen.blit(fade, (0, 0))

        bar_width = int(app.width * 0.5)
        bar_height = int(app.height * 0.05)
        bar_x = app.width // 2 - bar_width // 2
        bar_y = int(app.height * 0.6)
        fill_width = int(progress * bar_width)
        pygame.draw.rect(app.screen, Colors.white, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(app.screen, Colors.gold,
                         (bar_x + 2, bar_y + 2, fill_width - 4, bar_height - 4))

        font = get_font(40)
        text = font.render(f"Loading... {int(progress * 100)}%", True, Colors.white)
        app.screen.blit(text, (app.width // 2 - text.get_width() // 2,
                                app.height // 2 - text.get_height() // 2))

        if progress >= 1.0:
            from .menu import MainMenuScene
            app.replace_scene(MainMenuScene())
