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
    """Cached default font (lazily created after pygame.init())."""
    import pygame

    font = _FONTS.get(size)
    if font is None:
        font = pygame.font.SysFont(None, size)
        _FONTS[size] = font
    return font


def debug_print(*args):
    if DEBUG:
        print(*args)
