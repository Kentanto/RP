"""Central configuration: paths, colors, fonts and tuning constants."""
import os
import sys

if getattr(sys, "frozen", False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(BASE_PATH, "database", "artifacts.db")
DATA_DIR = os.path.join(BASE_PATH, "data")
ICONS_DIR = os.path.join(BASE_PATH, "icons")
SOUNDS_DIR = os.path.join(BASE_PATH, "sounds")
SONGS_DIR = os.path.join(SOUNDS_DIR, "songs")
WORDLISTS_DIR = os.path.join(BASE_PATH, "librarby")

FPS = 60
DEBUG = False

# Resource regen: fraction of max HP/mana recovered per minute
# (applied while playing and while away, exactly like points).
HP_REGEN_PER_MIN = 0.02
MANA_REGEN_PER_MIN = 0.02

POINTS_CAP = 600            # hard cap on stored skill points

# ------------------------------------------------------------- UI scaling
#
# The game is designed around an 800x600 window. `set_ui_scale()` derives a
# factor from the actual window size; fonts and fixed design offsets are
# multiplied by it, so the layout stays proportional and readable at any
# window size. Scenes should use get_font(size) and scaled(px) instead of
# raw pixel constants, and stack elements from measured text sizes rather
# than magic offsets so nothing can overlap.

UI_BASE_WIDTH = 800
UI_BASE_HEIGHT = 600
MIN_UI_SCALE = 0.75
MAX_UI_SCALE = 2.0

_ui_scale = 1.0


def set_ui_scale(width, height):
    """Recompute the global UI scale for the current window size."""
    global _ui_scale
    factor = min(width / UI_BASE_WIDTH, height / UI_BASE_HEIGHT)
    _ui_scale = max(MIN_UI_SCALE, min(MAX_UI_SCALE, factor))


def ui_scale():
    return _ui_scale


def scaled(value):
    """A fixed design-pixel value scaled to the current window."""
    return max(1, int(round(value * _ui_scale)))


class Colors:
    white = (255, 255, 255)
    black = (0, 0, 0)
    blue = (0, 0, 255)
    purple = (128, 0, 128)
    gold = (255, 215, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    orange = (255, 165, 0)
    brown = (139, 69, 19)
    gray = (128, 128, 128)
    light_gray = (200, 200, 200)
    dark_gray = (50, 50, 50)
    dark_green = (0, 100, 0)
    light_green = (150, 255, 150)
    dark_red = (139, 0, 0)
    light_red = (255, 150, 150)
    dark_yellow = (128, 128, 0)
    light_yellow = (255, 255, 150)
    dark_blue = (0, 0, 125)
    light_blue = (100, 100, 255)
    hover_color = (0, 150, 255)
    stat_text_color = (218, 165, 32)
    artifact_text_color = (147, 112, 219)

    # New UI palette used by the revamped scenes.
    panel = (30, 30, 38, 235)
    panel_light = (52, 52, 64, 235)
    panel_dark = (18, 18, 24, 220)
    veil = (8, 8, 16, 170)
    accent = (100, 160, 255)


_FONTS = {}


def get_font(size):
    """Cached default font (lazily created after pygame.init()).

    `size` is in design pixels: it is multiplied by the current UI scale,
    so text grows and shrinks with the window.
    """
    import pygame

    actual = max(10, int(round(size * _ui_scale)))
    font = _FONTS.get(actual)
    if font is None:
        font = pygame.font.SysFont(None, actual)
        _FONTS[actual] = font
    return font


def debug_print(*args):
    if DEBUG:
        print(*args)
