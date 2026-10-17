"""
Solo Leveling System — Player stats dashboard (the DASHBOARD page).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QProgressBar,
)

from solo_leveling_system.styles import CYAN, WHITE


STAT_COLORS = {
    "health":  ("#ff2a2a", "#ff2a2a33"),
    "magic":   ("#9c27b0", "#9c27b033"),
    "attack":  ("#ff9800", "#ff980033"),
    "defense": ("#2196f3", "#2196f333"),
    "speed":   ("#4caf50", "#4caf5033"),
}


class StatBar(QFrame):
    def __init__(self, label: str, current: int, maximum: int, color_tuple, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        fg, bg = color_tuple
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(100)
        self._lbl.setStyleSheet(f"color: {WHITE}; font-size: 13px; font-weight: bold;")
        layout.addWidget(self._lbl)

        bar = QProgressBar()
        bar.setTextVisible(False)
        bar.setRange(0, maximum)
        bar.setValue(current)
        bar.setFixedHeight(12)
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {bg}; border: 1px solid {fg}44; border-radius: 6px; }}
            QProgressBar::chunk {{ background-color: {fg}; border-radius: 6px; }}
        """)
        layout.addWidget(bar, 1)

        self._val = QLabel(f"{current} / {maximum}")
        self._val.setStyleSheet(f"color: {fg}; font-size: 12px; font-weight: bold;")
        self._val.setFixedWidth(70)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._val)

    def set_value(self, current: int, maximum: int):
        bar = self.findChild(QProgressBar)
        bar.setMaximum(maximum)
        bar.setValue(current)
        self._val.setText(f"{current} / {maximum}")



class LevelBadge(QFrame):
    def __init__(self, rank: str, level: int, parent=None):
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
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        # Title
        title = QLabel("STATUS WINDOW")
        title.setStyleSheet(f"color: {CYAN}; font-size: 28px; font-weight: bold; letter-spacing: 3px;")
        main_layout.addWidget(title)

        # Top row: badge + XP
        top = QHBoxLayout()
        top.setSpacing(32)

        self._badge = LevelBadge(config.get("player", "rank", "E"), config.get("player", "level", 1))
        top.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        xp_col = QVBoxLayout()
        xp_col.setSpacing(8)

        name_row = QHBoxLayout()
        self._name_lbl = QLabel(config.get("player", "name", "Hunter"))
        self._name_lbl.setStyleSheet(f"color: {WHITE}; font-size: 22px; font-weight: bold;")
        name_row.addWidget(self._name_lbl)
        name_row.addStretch()

        self._xp_lbl = QLabel()
        self._xp_lbl.setStyleSheet("color: #888; font-size: 12px;")
        name_row.addWidget(self._xp_lbl)
        xp_col.addLayout(name_row)

        self._xp_bar = QProgressBar()
        self._xp_bar.setTextVisible(False)
        self._xp_bar.setFixedHeight(8)
        self._xp_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #222; border: 1px solid {CYAN}44; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {CYAN}; border-radius: 4px; }}
        """)
        xp_col.addWidget(self._xp_bar)

        hint = QLabel("Complete missions to gain EXP and rank up.")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        xp_col.addWidget(hint)
        xp_col.addStretch()
        top.addLayout(xp_col, 1)

        main_layout.addLayout(top)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background-color: {CYAN}44;")
        main_layout.addWidget(sep)

        # Stat grid
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(1, 1)

        self._bars: dict = {}
        stats = [
            ("health", "HEALTH"),
            ("magic", "MAGIC"),
            ("attack", "ATTACK"),
            ("defense", "DEFENSE"),
            ("speed", "SPEED"),
        ]
        row = 0
        for key, label in stats:
            current = config.get("player", key, 0)
            bar = StatBar(label, current, 500, STAT_COLORS[key])
            grid.addWidget(bar, row, 0, 1, 2)
            self._bars[key] = bar
            row += 1

        main_layout.addLayout(grid)
        main_layout.addStretch()

        self._refresh_xp_display()

    def _xp_for_next_level(self, level: int) -> int:
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
            current = self.config.get("player", key, 0)
            bar.set_value(current, 500)
