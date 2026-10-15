"""Sound effects and music handling."""
import os
import random
import threading

import pygame

from . import settings

SONG_DURATIONS = {
    "feelGood.mp3": 53, "haldis.mp3": 73, "spell.mp3": 62, "mortals.mp3": 44,
    "worldBurn.mp3": 59, "shakeDown.mp3": 53, "disconnected.mp3": 47,
    "noSound.mp3": 73, "mySide.mp3": 50, "bornForThis.mp3": 56,
    "theEdge.mp3": 50, "invisible.mp3": 85, "myHeart.mp3": 60,
    "nekozilla.mp3": 70, "linked.mp3": 65, "ark.mp3": 70, "matafaka.mp3": 60,
    "whereWeStarted.mp3": 75, "fearless.mp3": 65, "brass.mp3": 70,
    "erika.mp3": 60, "departure.mp3": 70, "watchTheMoon.mp3": 65,
}

_music_fade_scheduled = False


def try_init_mixer():
    """Make sure the mixer is up; returns True when audio is available."""
    if pygame.mixer.get_init() is None:
        try:
            pygame.mixer.init()
        except pygame.error:
            return False
    return pygame.mixer.get_init() is not None


def load_ui_sounds():
    """Load hover/click/back sounds. Missing files become no-ops."""
    sounds = {}
    if not try_init_mixer():
        return sounds
    for key, filename, volume in (
        ("hover", "hover_sound.wav", 0.3),
        ("click", "click_sound.wav", 1.0),
        ("back", "back_sound.wav", 1.0),
        ("artifact_upgrade", "upgrade_artifact_sound.wav", 1.0),
        ("artifact_level_up", "upgrade_artifact_level_up.wav", 1.0),
    ):
        path = os.path.join(settings.SOUNDS_DIR, filename)
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(volume)
            sounds[key] = sound
        except (pygame.error, FileNotFoundError):
            sounds[key] = None
    return sounds


def play(app, key):
    sound = app.sounds.get(key)
    if sound:
        sound.play()


def start_random_song():
    """Pick and start a random song. Returns its duration in seconds (0 if muted)."""
    if not try_init_mixer():
        return 0
    playlist = list(SONG_DURATIONS)
    song = random.choice(playlist)
    path = os.path.join(settings.SONGS_DIR, song)
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.1)
        pygame.mixer.music.play(1)
        return SONG_DURATIONS.get(song, 60)
    except pygame.error:
        return 0


def schedule_music_fade(app):
    """Fade the intro song out 10s after the main menu opens (once per run)."""
    global _music_fade_scheduled
    if _music_fade_scheduled or pygame.mixer.get_init() is None:
        return
    _music_fade_scheduled = True

    def fade():
        start_ticks = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_ticks < 10000:
            if not pygame.get_init():
                return
            pygame.time.delay(100)
        if not pygame.get_init():
            return
        start_ticks = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_ticks < 3000:
            if not pygame.get_init():
                return
            elapsed = (pygame.time.get_ticks() - start_ticks) / 1000
            pygame.mixer.music.set_volume(max(0.0, 0.1 * (1 - elapsed / 3)))
            pygame.time.delay(100)
        if pygame.get_init():
            pygame.mixer.music.stop()

    threading.Thread(target=fade, daemon=True).start()


def shutdown():
    try:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except pygame.error:
        pass
