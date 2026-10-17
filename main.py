"""
Athas — Entry Point
Run this to launch the System UI.
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from athas.config import ConfigManager
from athas.loading_screen import LoadingScreen
from athas.main_window import MainWindow

_CONFIG_PATH = Path(__file__).parent / "cache" / "system_config.json"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Athas")
    app.setApplicationDisplayName("Athas System")

    config = ConfigManager(_CONFIG_PATH)

    player = QMediaPlayer()
    audio_output = QAudioOutput()
    player.setAudioOutput(audio_output)

    loading_enabled = config.get("loading_screen", "enabled", True)

    window = MainWindow(
        config=config,
        player=player,
        audio_output=audio_output,
    )

    if loading_enabled:
        loading = LoadingScreen(player, audio_output, parent=window.root)
        window.attach_loading_screen(loading)
    else:
        window.show_without_loading_screen()

    window.show()
    sys.exit(app.exec())
