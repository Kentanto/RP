"""
Solo Leveling System — Entry Point
Run this to launch the System UI.
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from solo_leveling_system.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SoloLevelingSystem")
    app.setApplicationDisplayName("System — Solo Leveling")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
