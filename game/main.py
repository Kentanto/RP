"""Application entry point."""
import os
import shutil

import pygame

from . import audio, db, settings


def _move(source, destination):
    if os.path.exists(destination):
        return
    try:
        os.replace(source, destination)
    except OSError:
        try:
            shutil.move(source, destination)
        except OSError:
            pass


def organize_files():
    """One-time housekeeping: move stray assets into their folders."""
    image_exts = (".png", ".jpg", ".jpeg", ".webp", ".ico")
    sound_exts = (".wav", ".mp3", ".ogg", ".flac", ".m4a")
    icons = os.path.join(settings.BASE_PATH, "icons")
    sounds = os.path.join(settings.BASE_PATH, "sounds")
    songs = os.path.join(sounds, "songs")
    for path in (icons, sounds, songs):
        os.makedirs(path, exist_ok=True)
    for file in os.listdir(settings.BASE_PATH):
        source = os.path.join(settings.BASE_PATH, file)
        if not os.path.isfile(source):
            continue
        lower = file.lower()
        if lower.endswith(image_exts):
            _move(source, os.path.join(icons, file))
        elif lower.endswith(".mp3"):
            _move(source, os.path.join(songs, file))
        elif lower.endswith(sound_exts):
            _move(source, os.path.join(sounds, file))


def run():
    db.initialize_database()
    organize_files()

    from .core import App
    from .scenes.boot import BootScene

    app = App()
    app.sounds = audio.load_ui_sounds()
    app.push_scene(BootScene())
    try:
        app.run()
    finally:
        audio.shutdown()
        pygame.quit()
