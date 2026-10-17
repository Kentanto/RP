"""
Solo Leveling System — Loading overlay painted on top of MainWindow.
The parent window UI is built but idle; when the bar hits 100 %
the overlay is destroyed and the parent unpauses background tasks.
"""
import sys
import random
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QUrl, QPoint
from PySide6.QtWidgets import QWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QPainter, QColor, QFont, QPen

from solo_leveling_system.styles import WHITE, GOLD


class LoadingScreen(QWidget):
    """
    Child overlay that blocks everything underneath.
    Music starts immediately; the black overlay fades to transparent
    until ``finished`` is emitted when progress hits 100 %.
    """
    finished = Signal()

    SONG_DURATIONS = {
        "feelGood.mp3": 53,
        "haldis.mp3": 73,
        "spell.mp3": 62,
        "mortals.mp3": 44,
        "worldBurn.mp3": 59,
        "shakeDown.mp3": 53,
        "disconnected.mp3": 47,
        "noSound.mp3": 73,
        "mySide.mp3": 50,
        "bornForThis.mp3": 56,
        "theEdge.mp3": 50,
        "invisible.mp3": 85,
        "myHeart.mp3": 68,
        "nekozilla.mp3": 47,
        "linked.mp3": 50,
        "ark.mp3": 53,
        "matafaka.mp3": 54,
        "whereWeStarted.mp3": 62,
        "fearless.mp3": 62,
        "brass.mp3": 55,
        "erika.mp3": 45,
        "departure.mp3": 47,
        "watchTheMoon.mp3": 61,
    }
    SONG_DROPS = {}

    def __init__(
        self,
        media_player: QMediaPlayer,
        audio_output: QAudioOutput,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if parent is not None:
            self.setGeometry(parent.rect())
        self.lower()
        self.player = media_player
        self.audio = audio_output
        self.audio.setVolume(0.1)
        self._setup_song_and_timer()

    def _base_path(self):
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent

    def _resolve_song_path(self, name: str):
        return self._base_path() / "sounds" / "songs" / name

    def _setup_song_and_timer(self):
        playlist = list(self.SONG_DURATIONS.keys())
        self.chosen_song = random.choice(playlist)

        drop_ms = self.SONG_DROPS.get(self.chosen_song, 0)
        self.loading_time = drop_ms if drop_ms > 0 else self.SONG_DURATIONS[self.chosen_song] * 100

        song_path = self._resolve_song_path(self.chosen_song)
        if song_path.exists():
            self.player.setSource(QUrl.fromLocalFile(str(song_path)))
            self.player.play()
        else:
            print(f"[LoadingScreen] Song not found: {song_path}")

        self.elapsed_ms = 0
        self.progress = 0.0
        self.overlay_alpha = 255

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def paintEvent(self, _event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor(0, 0, 0, int(self.overlay_alpha)))

            bar_w = 400
            bar_h = 30
            bar_x = (self.width() - bar_w) // 2
            bar_y = self.height() - 100

            pen = QPen(QColor(WHITE))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(bar_x, bar_y, bar_w, bar_h)

            fill_w = max(0, int(self.progress * bar_w) - 4)
            if fill_w > 0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(GOLD))
                painter.drawRect(bar_x + 2, bar_y + 2, fill_w, bar_h - 4)

            painter.setPen(QColor(WHITE))
            font = QFont("Segoe UI", 14, QFont.Weight.Bold)
            painter.setFont(font)
            text = f"Loading... {int(self.progress * 100)}%"
            text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            text_rect.moveCenter(QPoint(self.width() // 2, bar_y - 25))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        finally:
            painter.end()

    def resizeEvent(self, event):
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())
        super().resizeEvent(event)

    def _tick(self):
        self.elapsed_ms += 16
        self.progress = min(self.elapsed_ms / self.loading_time, 1.0)
        self.overlay_alpha = 255 * (1.0 - self.progress)
        self.update()
        if self.progress >= 1.0:
            self._timer.stop()
            self.finished.emit()
