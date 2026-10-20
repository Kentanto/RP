"""
Athas — Player stats dashboard with temporary point allocation.
"""
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QBrush, QLinearGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QProgressBar, QPushButton,
    QSizePolicy, QApplication, QInputDialog,
)

from athas.styles import CYAN, WHITE, GRAY, DANGER


# ── Dashboard surfaces (shared by everything on this page) ──
SURFACE = "#101016"     # card background (stat panel)
SURFACE_HI = "#16161d"  # inset track / button rest state
EDGE = "#232330"        # subtle card border
EDGE_HI = "#2e2e3e"     # control borders
TEXT_DIM = "#8b93a7"    # secondary text / hints

STAT_COLORS = {
    "health":  "#ff5252",
    "magic":   "#b57bee",
    "attack":  "#ffb84d",
    "defense": "#4db5ff",
    "speed":   "#6fe07f",
}


def _as_int(value, fallback=0):
    """Coerce a config value to a non-negative int; fall back if missing/corrupt."""
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return fallback
    return fallback


def xp_for_next_level(level) -> int:
    """XP needed to advance from the given level to the next one."""
    level = max(1, _as_int(level, 1))
    return int(100 * (level ** 1.5))


class TinyButton(QPushButton):
    """Square +/- pill button — neutral at rest, stat-coloured on hover."""
    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {SURFACE_HI};
                border: 1px solid {EDGE_HI};
                color: {WHITE};
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {color}26;
                border: 1px solid {color};
                color: {color};
            }}
            QPushButton:pressed {{
                background-color: {color}44;
            }}
            QPushButton:disabled {{
                background-color: {SURFACE};
                border: 1px solid {EDGE};
                color: #45454f;
            }}
        """)


class StatBar(QWidget):
    """Custom-painted bar: solid base segment + hatched temporary segment.

    Interactions:
      • left-click   → allocate +1  (Shift +10, Ctrl +100)
      • right-click  → exact-amount dialog
      • scroll wheel → ± step (with the same modifiers)
    """

    step_requested = Signal(int)
    custom_requested = Signal()

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._temp_color = QColor(color).lighter(155)
        self._base = 0
        self._temp = 0
        self._maximum = 1
        self.setFixedHeight(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_values(self, base, temp, maximum):
        self._base = max(0, _as_int(base))
        self._temp = max(0, _as_int(temp))
        self._maximum = max(1, _as_int(maximum), self._base + self._temp)
        self.update()

    @staticmethod
    def _step():
        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            return 100
        if mods & Qt.KeyboardModifier.ShiftModifier:
            return 10
        return 1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.step_requested.emit(self._step())
        elif event.button() == Qt.MouseButton.RightButton:
            self.custom_requested.emit()

    def wheelEvent(self, event):
        direction = 1 if event.angleDelta().y() > 0 else -1
        self.step_requested.emit(direction * self._step())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        h = self.height()
        radius = h / 2 - 1
        track = QRectF(1, 1, self.width() - 2, h - 2)

        # Inset track — a real surface, so the bar never blends into the page.
        p.setPen(QColor(EDGE_HI))
        p.setBrush(QColor(SURFACE_HI))
        p.drawRoundedRect(track, radius, radius)

        inner = track.adjusted(1, 1, -1, -1)
        span = inner.width()
        base_w = span * self._base / self._maximum
        temp_w = span * self._temp / self._maximum
        if base_w <= 0 and temp_w <= 0:
            return

        clip = QPainterPath()
        clip.addRoundedRect(inner, radius - 1, radius - 1)
        p.save()
        p.setClipPath(clip)
        top, height = inner.top(), inner.height()

        if base_w > 0:
            # Solid base segment with a subtle gradient for depth.
            grad = QLinearGradient(0, 0, base_w, 0)
            grad.setColorAt(0.0, self._color.darker(140))
            grad.setColorAt(1.0, self._color)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRect(QRectF(inner.left(), top, base_w, height))

        if temp_w > 0:
            # Temporary segment: lighter fill, offset by a small gap, with
            # diagonal hatching so it reads as "borrowed" points at a glance.
            x = inner.left() + base_w + 2
            w = max(0.0, temp_w - 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._temp_color)
            p.drawRect(QRectF(x, top, w, height))
            p.setPen(QPen(self._temp_color.darker(220), 1))
            i = -height
            while i < w + height:
                p.drawLine(QPointF(x + i, top + height), QPointF(x + i + height, top))
                i += 6
        p.restore()


class AllocatedStatBar(QFrame):
    """A stat row: label, −/+ steppers, custom bar, MAX button and readout."""

    def __init__(self, label, base, temp, max_total, color, on_change, on_commit, parent=None):
        super().__init__(parent)
        self._base = _as_int(base)
        self._temp = max(0, _as_int(temp))
        self._max_total = max_total
        self._color = color
        self._on_change = on_change     # (±amount) -> points actually applied
        self._on_commit = on_commit
        self._pool_left = 0

        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(90)
        self._lbl.setStyleSheet(f"color: {WHITE}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self._lbl)

        self._minus = TinyButton("-", color)
        self._minus.clicked.connect(lambda: self._release(self._stepper()))
        layout.addWidget(self._minus)

        self._bar = StatBar(color)
        self._bar.step_requested.connect(self._apply_step)
        self._bar.custom_requested.connect(self._custom_amount)
        layout.addWidget(self._bar, 1)

        self._plus = TinyButton("+", color)
        self._plus.clicked.connect(lambda: self._allocate(self._stepper()))
        layout.addWidget(self._plus)

        self._max_btn = QPushButton("MAX")
        self._max_btn.setFixedSize(46, 30)
        self._max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._max_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {EDGE_HI};
                color: {TEXT_DIM};
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                border-radius: 5px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {color}26;
                border: 1px solid {color};
                color: {color};
            }}
            QPushButton:disabled {{
                background-color: {SURFACE};
                border: 1px solid {EDGE};
                color: #3a3a44;
            }}
        """)
        self._max_btn.clicked.connect(self._allocate_room)
        layout.addWidget(self._max_btn)

        self._val = QLabel()
        self._val.setFixedWidth(96)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._val)

        self._update_display()

    @property
    def temp(self):
        return self._temp

    @temp.setter
    def temp(self, value):
        self._temp = max(0, _as_int(value))
        self._update_display()

    def set_pool_state(self, pool_left):
        """Called by the dashboard whenever the pool changes, so the
        +/MAX buttons reflect both cap room and available points."""
        self._pool_left = max(0, _as_int(pool_left))
        self._sync_controls()

    def release_all(self, commit=True):
        """Return every allocated point to the pool."""
        if self._temp <= 0:
            return
        self._on_change(-self._temp)
        self._temp = 0
        self._update_display()
        if commit:
            self._on_commit()

    # ── allocation ──
    @staticmethod
    def _stepper():
        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            return 100
        if mods & Qt.KeyboardModifier.ShiftModifier:
            return 10
        return 1

    def _room(self):
        return max(0, self._max_total - (self._base + self._temp))

    def _allocate(self, amount):
        amount = min(max(0, _as_int(amount)), self._room())
        if amount <= 0:
            return
        applied = self._on_change(amount)   # clamped by the pool
        if applied > 0:
            self._temp += applied
            self._update_display()
            self._on_commit()

    def _release(self, amount):
        amount = min(max(0, _as_int(amount)), self._temp)
        if amount <= 0:
            return
        self._on_change(-amount)
        self._temp -= amount
        self._update_display()
        self._on_commit()

    def _apply_step(self, signed):
        if signed >= 0:
            self._allocate(signed)
        else:
            self._release(-signed)

    def _allocate_room(self):
        """MAX: dump as many points as the pool and the cap allow."""
        self._allocate(self._room())

    def _custom_amount(self):
        amount, ok = QInputDialog.getInt(
            self, "Allocate Points",
            f"Points into {self._lbl.text()} (negative removes points):",
            1, -self._temp, 10_000_000, 10,
        )
        if ok:
            self._apply_step(amount)

    # ── display ──
    def _update_display(self):
        self._bar.set_values(self._base, self._temp, self._max_total)
        if self._temp:
            self._val.setText(f"{self._base} +{self._temp}")
            self._val.setStyleSheet(f"color: {self._color}; font-size: 12px; font-weight: bold;")
        else:
            self._val.setText(str(self._base))
            self._val.setStyleSheet(f"color: {WHITE}; font-size: 12px; font-weight: bold;")
        self.setToolTip(f"{self._base} + {self._temp} = {self._base + self._temp} / {self._max_total}")
        self._sync_controls()

    def _sync_controls(self):
        can_add = self._room() > 0 and self._pool_left > 0
        self._plus.setEnabled(can_add)
        self._max_btn.setEnabled(can_add)
        self._minus.setEnabled(self._temp > 0)


class LevelBadge(QFrame):
    def __init__(self, rank, level, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: qradialgradient(cx:0.5, cy:0.42, radius:0.95, stop:0 #0c1822, stop:1 #0a0e14);
                border: 2px solid {CYAN}55;
                border-radius: 80px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        rank_lbl = QLabel(f"RANK {rank}")
        rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_lbl.setStyleSheet(f"color: {CYAN}; font-size: 14px; font-weight: bold; letter-spacing: 3px;")
        layout.addWidget(rank_lbl)

        lvl_lbl = QLabel(str(int(level) if isinstance(level, float) and level.is_integer() else level))
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
    abilities_clicked = Signal()
    skills_clicked = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._pool = max(0, _as_int(config.get("player", "temp_points", 10), 10))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(24)

        top = QHBoxLayout()
        top.setSpacing(32)

        self._badge = LevelBadge(config.get("player", "rank", "E"), config.get("player", "level", 1))
        self._badge_layout = top
        top.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        right = QVBoxLayout()
        right.setSpacing(14)

        name_row = QHBoxLayout()
        self._name_lbl = QLabel(config.get("player", "name", "Wanderer"))
        self._name_lbl.setStyleSheet(f"color: {WHITE}; font-size: 22px; font-weight: bold;")
        name_row.addWidget(self._name_lbl)
        name_row.addStretch()

        self._xp_lbl = QLabel()
        self._xp_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        name_row.addWidget(self._xp_lbl)
        right.addLayout(name_row)

        self._xp_bar = QProgressBar()
        self._xp_bar.setTextVisible(False)
        self._xp_bar.setFixedHeight(8)
        self._xp_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {SURFACE_HI}; border: 1px solid {EDGE_HI}; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0090a8, stop:1 {CYAN}); border-radius: 3px; }}
        """)
        right.addWidget(self._xp_bar)

        pool_frame = QFrame()
        pool_frame.setObjectName("PoolPanel")
        pool_frame.setStyleSheet(f"""
            QFrame#PoolPanel {{ background-color: #0c1218; border: 1px solid {CYAN}44; border-radius: 6px; }}
        """)
        pool_layout = QHBoxLayout(pool_frame)
        pool_layout.setContentsMargins(16, 10, 16, 10)
        pool_layout.setSpacing(10)

        self._pool_icon = QLabel("POINTS")
        self._pool_icon.setStyleSheet(f"color: {CYAN}; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        pool_layout.addWidget(self._pool_icon)

        self._pool_lbl = QLabel()
        self._pool_lbl.setStyleSheet(f"color: {WHITE}; font-size: 20px; font-weight: bold;")
        pool_layout.addWidget(self._pool_lbl)

        pool_layout.addStretch()

        self._pool_hint = QLabel()
        self._pool_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        pool_layout.addWidget(self._pool_hint)

        self._reset_btn = QPushButton("RESET")
        self._reset_btn.setFixedHeight(26)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {EDGE_HI};
                color: {TEXT_DIM};
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {DANGER}22;
                border: 1px solid {DANGER};
                color: {DANGER};
            }}
            QPushButton:disabled {{
                border: 1px solid {EDGE};
                color: #3a3a44;
            }}
        """)
        self._reset_btn.clicked.connect(self._reset_allocations)
        pool_layout.addWidget(self._reset_btn)

        right.addWidget(pool_frame)

        right.addStretch()
        top.addLayout(right, 1)

        main_layout.addLayout(top)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {EDGE};")
        main_layout.addWidget(sep)

        stats_panel = QFrame()
        stats_panel.setObjectName("StatPanel")
        stats_panel.setStyleSheet(f"""
            QFrame#StatPanel {{ background-color: {SURFACE}; border: 1px solid {EDGE}; border-radius: 8px; }}
        """)
        panel_layout = QVBoxLayout(stats_panel)
        panel_layout.setContentsMargins(20, 16, 20, 16)
        panel_layout.setSpacing(14)

        caption = QHBoxLayout()
        cap_lbl = QLabel("STATS")
        cap_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-weight: bold; letter-spacing: 3px;")
        caption.addWidget(cap_lbl)
        caption.addStretch()
        help_lbl = QLabel("click ±1 · shift ±10 · ctrl ±100 · scroll to adjust · right-click bar for exact amount")
        help_lbl.setStyleSheet("color: #5d6373; font-size: 10px;")
        caption.addWidget(help_lbl)
        panel_layout.addLayout(caption)

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
                on_commit=self._commit_state,
            )
            panel_layout.addWidget(bar)
            self._bars[key] = bar

        main_layout.addWidget(stats_panel)

        main_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        abilities_btn = QPushButton("ABILITIES")
        skills_btn = QPushButton("SKILLS")
        for btn in (abilities_btn, skills_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(48)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SURFACE_HI};
                    border: 1px solid rgba(0, 240, 255, 102);
                    color: {CYAN};
                    padding: 12px 0px;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    letter-spacing: 3px;
                }}
                QPushButton:hover {{
                    background-color: {CYAN};
                    color: #0a0a0a;
                    border: 1px solid {CYAN};
                }}
                QPushButton:pressed {{
                    background-color: rgba(0, 240, 255, 180);
                    color: #0a0a0a;
                    border: 1px solid {CYAN};
                }}
            """)
        abilities_btn.clicked.connect(self._on_abilities_clicked)
        skills_btn.clicked.connect(self._on_skills_clicked)
        btn_row.addWidget(abilities_btn, 1)
        btn_row.addWidget(skills_btn, 1)
        main_layout.addLayout(btn_row)

        self._refresh_xp_display()
        self._refresh_pool_display()

    def _on_abilities_clicked(self):
        self.abilities_clicked.emit()

    def _on_skills_clicked(self):
        self.skills_clicked.emit()

    def _try_spend(self, delta):
        """Validate and apply a pool change of ±N points. Returns how many
        points were actually applied — spending is clamped by what's left
        in the pool, so batch requests can never overdraw it. Does NOT
        persist anything: the calling bar updates its temp value first,
        then calls _commit_state, so the saved data is never stale."""
        if delta > 0:
            applied = min(delta, self._pool)
            self._pool -= applied
            return applied
        self._pool -= delta   # negative delta refunds points
        return -delta

    def _commit_state(self):
        """Called after a bar's temp value changed: refresh UI, then save
        the pool and all allocations together in a single atomic write."""
        self._refresh_pool_display()
        self._persist_state()

    def _persist_state(self):
        self.config.set("player", "temp_points", self._pool, save=False)
        for key, bar in self._bars.items():
            self.config.set_nested("player", "temp_allocations", key, bar.temp, save=False)
        self.config.save()

    def _reset_allocations(self):
        """Return every allocated point to the pool in one go."""
        if not any(bar.temp for bar in self._bars.values()):
            return
        for bar in self._bars.values():
            bar.release_all(commit=False)
        self._commit_state()

    def _refresh_pool_display(self):
        self._pool_lbl.setText(f"{self._pool:,}")
        colour = CYAN if self._pool else GRAY
        self._pool_icon.setStyleSheet(f"color: {colour}; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        self._pool_lbl.setStyleSheet(f"color: {colour}; font-size: 20px; font-weight: bold;")
        self._pool_hint.setText(
            "Available to allocate." if self._pool else "All points spent."
        )
        self._reset_btn.setEnabled(any(bar.temp for bar in self._bars.values()))
        for bar in self._bars.values():
            bar.set_pool_state(self._pool)

    def grant_skill_points(self, amount: int):
        amount = max(0, _as_int(amount))
        if amount <= 0:
            return
        self._pool += amount
        self._commit_state()

    def remove_skill_points(self, amount: int):
        amount = max(0, _as_int(amount))
        if amount <= 0:
            return
        self._pool = max(0, self._pool - amount)
        self._commit_state()

    def grant_xp(self, amount: int) -> int:
        """Award XP to the player, rolling over as many level-ups as the
        amount covers. Persists the result and refreshes the display.
        Returns the number of levels gained."""
        amount = _as_int(amount)
        if amount <= 0:
            return 0
        level = max(1, _as_int(self.config.get("player", "level", 1), 1))
        xp = max(0, _as_int(self.config.get("player", "xp", 0), 0)) + amount
        levels_gained = 0
        while xp >= xp_for_next_level(level):
            xp -= xp_for_next_level(level)
            level += 1
            levels_gained += 1
        self.config.set("player", "xp", xp, save=False)
        self.config.set("player", "level", level, save=False)
        self.config.save()
        self.refresh()
        return levels_gained

    def remove_xp(self, amount: int) -> int:
        """Remove previously awarded XP, reversing level-ups as needed.
        Returns the number of levels lost."""
        amount = max(0, _as_int(amount))
        if amount <= 0:
            return 0

        old_level = max(1, _as_int(self.config.get("player", "level", 1), 1))
        level = old_level
        xp = max(0, _as_int(self.config.get("player", "xp", 0), 0))
        total_xp = xp + sum(xp_for_next_level(lvl) for lvl in range(1, level))
        total_xp = max(0, total_xp - amount)

        level = 1
        while total_xp >= xp_for_next_level(level):
            total_xp -= xp_for_next_level(level)
            level += 1

        self.config.set("player", "xp", total_xp, save=False)
        self.config.set("player", "level", level, save=False)
        self.config.save()
        self.refresh()
        return old_level - level

    def _refresh_xp_display(self):
        lvl = self.config.get("player", "level", 1)
        xp = self.config.get("player", "xp", 0)
        need = xp_for_next_level(lvl)
        self._xp_bar.setRange(0, need)
        self._xp_bar.setValue(min(xp, need))
        self._xp_lbl.setText(f"EXP  {xp} / {need}")

    def refresh(self):
        rank = self.config.get("player", "rank", "E")
        level = self.config.get("player", "level", 1)
        self._badge.deleteLater()
        self._badge = LevelBadge(rank, level)
        self._badge_layout.insertWidget(
            0, self._badge, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        self._name_lbl.setText(self.config.get("player", "name", "Wanderer"))
        self._refresh_xp_display()
        for key, bar in self._bars.items():
            bar.temp = self.config.get_nested("player", "temp_allocations", key, default=0)
        self._pool = max(0, _as_int(self.config.get("player", "temp_points", 10), 10))
        self._refresh_pool_display()
