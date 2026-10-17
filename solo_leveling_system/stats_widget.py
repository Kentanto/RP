"""
Solo Leveling System — Player stats dashboard with temporary point allocation.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QProgressBar, QPushButton,
)

from solo_leveling_system.styles import CYAN, WHITE, GRAY


STAT_COLORS = {
    "health":  ("#ff2a2a", "#ff2a2a33"),
    "magic":   ("#9c27b0", "#9c27b033"),
    "attack":  ("#ff9800", "#ff980033"),
    "defense": ("#2196f3", "#2196f333"),
    "speed":   ("#4caf50", "#4caf5033"),
}


class TinyButton(QPushButton):
    """Square +/- pill button."""
    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}22;
                border: 1px solid {color};
                color: {color};
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {color}44;
            }}
            QPushButton:disabled {{
                background-color: #222;
                border: 1px solid #444;
                color: #444;
            }}
        """)


class AllocatedStatBar(QFrame):
    """A stat bar that shows base + temporary values, with tiny +/- buttons."""

    def __init__(self, label, base, temp, max_total, color_tuple, on_change, parent=None):
        super().__init__(parent)
        self._base = base
        self._temp = temp
        self._max_total = max_total
        self._color = color_tuple[0]
        self._on_change = on_change

        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(90)
        self._lbl.setStyleSheet(f"color: {WHITE}; font-size: 13px; font-weight: bold;")
        layout.addWidget(self._lbl)

        self._minus = TinyButton("-", self._color)
        self._minus.clicked.connect(self._decrement)
        layout.addWidget(self._minus)

        fg, bg = color_tuple
        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setRange(0, max_total)
        self._bar.setFixedHeight(14)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {bg};
                border: 1px solid {fg}44;
                border-radius: 7px;
            }}
            QProgressBar::chunk {{
                background-color: {fg};
                border-radius: 7px;
            }}
        """)
        layout.addWidget(self._bar, 1)

        self._plus = TinyButton("+", self._color)
        self._plus.clicked.connect(self._increment)
        layout.addWidget(self._plus)

        self._val = QLabel()
        self._val.setStyleSheet(f"color: {WHITE}; font-size: 12px; font-weight: bold;")
        self._val.setFixedWidth(100)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._val)

        self._update_display()

    @property
    def temp(self):
        return self._temp

    @temp.setter
    def temp(self, value):
        self._temp = value
        self._update_display()

    def _increment(self):
        if self._on_change(+1):
            self._temp += 1
            self._update_display()

    def _decrement(self):
        if self._temp > 0 and self._on_change(-1):
            self._temp -= 1
            self._update_display()

    def _update_display(self):
        total = self._base + self._temp
        self._bar.setValue(total)
        self._val.setText(f"{self._base} + {self._temp}" if self._temp else f"{self._base}")
        vcol = self._color if self._temp else GRAY
        self._val.setStyleSheet(f"color: {vcol}; font-size: 12px; font-weight: bold;")
        self._minus.setEnabled(self._temp > 0)


class LevelBadge(QFrame):
    def __init__(self, rank, level, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setStyleSheet(f"""
            QFrame {{ background-color: rgba(0,240,255,8); border: 3px solid {CYAN}; border-radius: 80px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        rank_lbl = QLabel(f"RANK {rank}")
        rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_lbl.setStyleSheet(f"color: {CYAN}; font-size: 14px; font-weight: bold; letter-spacing: 3px;")
        layout.addWidget(rank_lbl)

        lvl_lbl = QLabel(str(level))
        lvl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lvl_lbl.setStyleSheet(f"color: {WHITE}; font-size: 48px; font-weight: bold;")
        layout.addWidget(lvl_lbl)

        sub = QLabel("LEVEL")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {CYAN}88; font-size: 11px; letter-spacing: 4px;")
        layout.addWidget(sub)


class StatsWidget(QWidget):
    """Status Window with temp point allocation."""

    MAX_STAT = 500

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._pool = config.get("player", "temp_points", 10)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        title = QLabel("STATUS WINDOW")
        title.setStyleSheet(f"color: {CYAN}; font-size: 28px; font-weight: bold; letter-spacing: 3px;")
        main_layout.addWidget(title)

        top = QHBoxLayout()
        top.setSpacing(32)

        self._badge = LevelBadge(config.get("player", "rank", "E"), config.get("player", "level", 1))
        top.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        right = QVBoxLayout()
        right.setSpacing(10)

        name_row = QHBoxLayout()
        self._name_lbl = QLabel(config.get("player", "name", "Hunter"))
        self._name_lbl.setStyleSheet(f"color: {WHITE}; font-size: 22px; font-weight: bold;")
        name_row.addWidget(self._name_lbl)
        name_row.addStretch()

        self._xp_lbl = QLabel()
        self._xp_lbl.setStyleSheet("color: #888; font-size: 12px;")
        name_row.addWidget(self._xp_lbl)
        right.addLayout(name_row)

        self._xp_bar = QProgressBar()
        self._xp_bar.setTextVisible(False)
        self._xp_bar.setFixedHeight(8)
        self._xp_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #222; border: 1px solid {CYAN}44; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {CYAN}; border-radius: 4px; }}
        """)
        right.addWidget(self._xp_bar)

        pool_frame = QFrame()
        pool_frame.setStyleSheet(f"""
            QFrame {{ background-color: rgba(0,240,255,6); border: 1px solid {CYAN}44; border-radius: 4px; }}
        """)
        pool_layout = QHBoxLayout(pool_frame)
        pool_layout.setContentsMargins(16, 8, 16, 8)
        self._pool_icon = QLabel("TEMP")
        self._pool_icon.setStyleSheet(f"color: {CYAN}; font-size: 12px; font-weight: bold; letter-spacing: 2px;")
        pool_layout.addWidget(self._pool_icon)
        self._pool_lbl = QLabel()
        self._pool_lbl.setStyleSheet(f"color: {WHITE}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        pool_layout.addWidget(self._pool_lbl)
        pool_layout.addStretch()
        self._pool_hint = QLabel("Allocate points into stats above.")
        self._pool_hint.setStyleSheet(f"color: {GRAY}; font-size: 10px;")
        pool_layout.addWidget(self._pool_hint)
        right.addWidget(pool_frame)
        right.addStretch()
        top.addLayout(right, 1)

        main_layout.addLayout(top)

        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background-color: {CYAN}44;")
        main_layout.addWidget(sep)

        stats = [
            ("health", "HEALTH"),
            ("magic", "MAGIC"),
            ("attack", "ATTACK"),
            ("defense", "DEFENSE"),
            ("speed", "SPEED"),
        ]
        self._bars = {}
        for key, label in stats:
            base = config.get("player", key, 0)
            temp = config.get_nested("player", "temp_allocations", key, default=0)
            bar = AllocatedStatBar(
                label, base, temp, self.MAX_STAT,
                STAT_COLORS[key],
                on_change=self._try_spend,
            )
            main_layout.addWidget(bar)
            self._bars[key] = bar

        main_layout.addStretch()

        self._refresh_xp_display()
        self._refresh_pool_display()

    def _try_spend(self, delta):
        if delta > 0 and self._pool <= 0:
            return False
        self._pool -= delta
        self._refresh_pool_display()
        self._persist_state()
        return True

    def _persist_state(self):
        self.config.set("player", "temp_points", self._pool)
        for key, bar in self._bars.items():
            self.config.set_nested("player", "temp_allocations", key, bar.temp)

    def _refresh_pool_display(self):
        self._pool_lbl.setText(f"POINTS: {self._pool}")
        colour = CYAN if self._pool else GRAY
        self._pool_icon.setStyleSheet(f"color: {colour}; font-size: 12px; font-weight: bold; letter-spacing: 2px;")
        self._pool_lbl.setStyleSheet(
            f"color: {colour}; font-size: 13px; font-weight: bold; letter-spacing: 1px;"
        )
        self._pool_hint.setText(
            "Allocate points into stats above." if self._pool else "All points spent."
        )
        for bar in self._bars.values():
            bar._plus.setEnabled(self._pool > 0)

    def _xp_for_next_level(self, level):
        return int(100 * (level ** 1.5))

    def _refresh_xp_display(self):
        lvl = self.config.get("player", "level", 1)
        xp = self.config.get("player", "xp", 0)
        need = self._xp_for_next_level(lvl)
        self._xp_bar.setRange(0, need)
        self._xp_bar.setValue(min(xp, need))
        self._xp_lbl.setText(f"EXP  {xp} / {need}")

    def refresh(self):
        rank = self.config.get("player", "rank", "E")
        level = self.config.get("player", "level", 1)
        self._badge.deleteLater()
        self._badge = LevelBadge(rank, level)
        self.layout().itemAt(1).layout().insertWidget(
            0, self._badge, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        self._name_lbl.setText(self.config.get("player", "name", "Hunter"))
        self._refresh_xp_display()
        for key, bar in self._bars.items():
            temp = self.config.get_nested("player", "temp_allocations", key, default=0)
            bar.temp = temp
        self._pool = self.config.get("player", "temp_points", 10)
        self._refresh_pool_display()

