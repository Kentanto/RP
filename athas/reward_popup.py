"""
Reward Popup — the drops-folder notification window.

A frameless, always-on-top card that appears centered over the main
window whenever a drop file is processed (or carries a notification).
The close button stays disabled for the first 2 seconds so a popup that
appears suddenly cannot be clicked away by accident.
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor

from athas.styles import CYAN, WHITE, GOLD

# How long the popup refuses to close (milliseconds).
LOCKOUT_MS = 2000


class RewardPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RewardPopup")
        self.setFixedSize(460, 240)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(f"""
            QFrame#RewardPopup {{
                background-color: rgba(5,5,8,240);
                border: 2px solid {GOLD};
                border-radius: 6px;
            }}
            QLabel {{ background: transparent; border: none; color: {WHITE}; }}
        """)

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(30)
        glow.setColor(QColor(GOLD))
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)

        head = QHBoxLayout()
        self._title = QLabel("SYSTEM REWARD")
        self._title.setStyleSheet(f"color: {GOLD}; font-size: 12px; font-weight: bold; letter-spacing: 3px;")
        head.addWidget(self._title)
        head.addStretch()
        layout.addLayout(head)

        self._message = QLabel("")
        self._message.setWordWrap(True)
        self._message.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._message.setStyleSheet("font-size: 14px; color: #ddd;")
        layout.addWidget(self._message, 1)

        self._close_btn = QPushButton("OK")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {GOLD}22; border: 1px solid {GOLD};
                color: {GOLD}; padding: 6px 24px; font-weight: bold;
                border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {GOLD}; color: #0a0a0a; }}
            QPushButton:disabled {{ color: #555; border-color: #333; background: transparent; }}
        """)
        self._close_btn.clicked.connect(self.hide)
        layout.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._lock_timer = QTimer(self)
        self._lock_timer.setSingleShot(True)
        self._lock_timer.timeout.connect(self._unlock)

        self.hide()

    def show_message(self, title: str, message: str):
        """Show the popup; the OK button unlocks after LOCKOUT_MS."""
        self._title.setText((title or "SYSTEM REWARD").upper())
        self._message.setText(message or "")
        self._close_btn.setEnabled(False)
        self._close_btn.setText("...")
        self.show()
        self.raise_()
        self._lock_timer.start(LOCKOUT_MS)

    def _unlock(self):
        self._close_btn.setEnabled(True)
        self._close_btn.setText("OK")

    def reposition(self, rect):
        """Center the popup over the given QRect (the main window area)."""
        x = rect.x() + (rect.width() - self.width()) // 2
        y = rect.y() + (rect.height() - self.height()) // 2
        self.move(x, y)
