"""
Athas — animated notification popup for new missions.
Slides in from the right with a typing effect.
"""
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, Qt, QPoint
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QFont

from athas.styles import CYAN, BLACK, WHITE, DIFF_COLOURS


class NotificationWidget(QFrame):
    """
    A sleek system-alert panel that slides in/out.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotificationWidget")
        self.setFixedSize(420, 110)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(f"""
            QFrame#NotificationWidget {{
                background-color: rgba(5,5,8,230);
                border: 2px solid {CYAN};
                border-radius: 4px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {WHITE};
            }}
        """)

        # Shadow glow
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(30)
        glow.setColor(QColor(CYAN))
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Difficulty indicator (left side block)
        self.level_label = QLabel("E")
        self.level_label.setFixedSize(48, 48)
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.level_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0,240,255,30);
                border: 1px solid {CYAN};
                border-radius: 24px;
                color: {CYAN};
                font-size: 22px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.level_label)

        text_container = QVBoxLayout()
        text_container.setSpacing(4)

        self.title_label = QLabel("NEW MISSION DETECTED")
        self.title_label.setStyleSheet(f"color: {CYAN}; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        text_container.addWidget(self.title_label)

        self.mission_label = QLabel("")
        self.mission_label.setStyleSheet(f"color: {WHITE}; font-size: 16px; font-weight: bold;")
        text_container.addWidget(self.mission_label)

        self.desc_label = QLabel("")
        self.desc_label.setStyleSheet(f"color: #aaaaaa; font-size: 12px;")
        self.desc_label.setWordWrap(True)
        text_container.addWidget(self.desc_label)

        layout.addLayout(text_container, 1)

        # Position off-screen to the right
        self._hide_pos = QPoint(1500, 20)
        self._show_pos = QPoint(0, 0)
        self.move(self._hide_pos)

        self._animation = QPropertyAnimation(self, b"pos")
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hiding = False
        self._animation.finished.connect(self._on_slide_finished)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide_notification)

        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._type_next_char)
        self._type_text = ""
        self._type_index = 0

        self.hide()

    def show_notification(self, title: str, description: str, difficulty: str = "E", duration_ms=6000):
        """Slide in and type out the mission info."""
        col = DIFF_COLOURS.get(difficulty.upper(), CYAN)
        self.level_label.setText(difficulty.upper())
        self.level_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0,240,255,30);
                border: 1px solid {col};
                border-radius: 24px;
                color: {col};
                font-size: 22px;
                font-weight: bold;
            }}
        """)

        self.mission_label.setText(title)
        self._hiding = False
        self._type_text = description
        self._type_index = 0
        self.desc_label.setText("")

        self.show()
        self.raise_()

        self._animation.setStartValue(self._hide_pos)
        self._animation.setEndValue(self._show_pos)
        self._animation.start()

        self._type_timer.start(35)
        self._dismiss_timer.start(duration_ms)

    def hide_notification(self):
        self._hiding = True
        self._animation.setStartValue(self._show_pos)
        self._animation.setEndValue(self._hide_pos)
        self._animation.start()

    def _on_slide_finished(self):
        if self._hiding:
            self._hiding = False
            self.hide()

    def _type_next_char(self):
        if self._type_index < len(self._type_text):
            self._type_index += 1
            self.desc_label.setText(self._type_text[:self._type_index])
        else:
            self._type_timer.stop()

    def reposition(self, top_right: QPoint):
        """Call when parent resizes to keep notification in top-right corner."""
        self._show_pos = QPoint(top_right.x() - self.width() - 24, top_right.y() + 24)
        self._hide_pos = QPoint(top_right.x() + 20, self._show_pos.y())
        if self.isVisible():
            self.move(self._show_pos)
