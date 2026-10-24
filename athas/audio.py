"""
Audio — the System's central SFX player.

Every sound effect goes through `play(event)`: a single event-to-file map
decides which file in sounds/ plays. Files that do not exist are skipped
silently, so dropping in a new wav and adding it to EVENT_SOUNDS is all
it takes to wire a new sound.

The player reads the `audio` config section: `enabled` mutes everything,
`volume` drives the background music (QMediaPlayer) and `sfx_volume` the
sound effects. Everything is best-effort — in headless/test environments
(QSoundEffect missing, no config) playing is a no-op.
"""
from pathlib import Path

try:
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # headless / test environments
    QSoundEffect = None

try:
    from PySide6.QtCore import QUrl
except Exception:  # headless / test environments
    QUrl = None

# Where the wav files live: <repo root>/sounds
SOUNDS_DIR = Path(__file__).parent.parent / "sounds"

# Event name → file inside sounds/. Unmapped events simply stay silent,
# so new events can be referenced before their sound file exists.
EVENT_SOUNDS = {
    # generic UI
    "click": "click_sound.wav",
    "hover": "hover_sound.wav",
    "back": "back_sound.wav",
    # workshop
    "upgrade": "upgrade_artifact_sound.wav",
    "upgrade_max": "upgrade_artifact_level_up.wav",
    "equip": "click_sound.wav",
    "refund": "click_sound.wav",
    "reroll": "click_sound.wav",
    "forge": "upgrade_artifact_level_up.wav",
    # shop
    "buy": "click_sound.wav",
    # progression
    "level_up": "upgrade_artifact_level_up.wav",
    "mission_complete": "upgrade_artifact_level_up.wav",
    "reward": "upgrade_artifact_level_up.wav",
    "skill_unlock": "click_sound.wav",
}

# Volume used when no config is available.
DEFAULT_SFX_VOLUME = 0.3


class SfxPlayer:
    """Caches one QSoundEffect per file and plays them by event name."""

    def __init__(self, sounds_dir=None):
        self.sounds_dir = Path(sounds_dir) if sounds_dir else SOUNDS_DIR
        self._config = None
        self._effects = {}

    def set_config(self, config):
        """Attach the app's ConfigManager (audio.enabled / audio.sfx_volume)."""
        self._config = config

    def _enabled(self) -> bool:
        try:
            return bool(self._config.get("audio", "enabled", True))
        except Exception:
            return True

    def _volume(self) -> float:
        try:
            value = float(self._config.get("audio", "sfx_volume", DEFAULT_SFX_VOLUME))
        except Exception:
            value = DEFAULT_SFX_VOLUME
        return max(0.0, min(1.0, value))

    def _effect(self, filename: str):
        """Load (and cache) one sound file; None when it cannot play."""
        if QSoundEffect is None or QUrl is None:
            return None
        effect = self._effects.get(filename)
        if effect is None:
            path = self.sounds_dir / filename
            if not path.exists():
                return None
            try:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self._volume())
                self._effects[filename] = effect
            except Exception:
                return None
        return effect

    def play(self, event: str) -> bool:
        """Play the sound mapped to an event name. True when a sound played."""
        if not self._enabled():
            return False
        filename = EVENT_SOUNDS.get(event)
        if not filename:
            return False
        try:
            effect = self._effect(filename)
            if effect is None:
                return False
            effect.setVolume(self._volume())
            effect.play()
            return True
        except Exception:
            return False


# The one player every panel shares. The main window attaches the config
# at startup; panels just call `audio.play(...)`.
player = SfxPlayer()


def play(event: str) -> bool:
    """Module-level convenience: play the sound for an event name."""
    return player.play(event)
