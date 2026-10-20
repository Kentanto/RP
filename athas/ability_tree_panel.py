"""Interactive constellation map with pan, zoom, and star-sign-based unlocking."""
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QToolTip,
)
from PySide6.QtGui import (
    QCursor, QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QPixmap,
)

from athas.config import migrate_constellation_ranks
from athas.styles import CYAN, WHITE


@dataclass
class SkillNode:
    id: str
    name: str
    description: str
    x: float
    y: float
    max_rank: int
    current_rank: int
    color: str
    parent_ids: List[str] = field(default_factory=list)
    star: str = ""


LEO_GOLD = "#ffc44d"
LIBRA_CYAN = "#00e5ff"

# --- LEO · The Lion -------------------------------------------------------
# Stars are placed on Leo's real stick figure: the Sickle (head and mane)
# on the left, the hindquarter triangle (Zosma - Denebola - Chertan) on the
# right. Regulus, the Lion's Heart, is the branch's entry star.
NODES = [
    SkillNode("A_Prevalence", "Ceaseless prevalence", "An existence hard to end. Gain a body that revives once a day upon death.",
            449, 355, 1, 1, LEO_GOLD, [], "Regulus · the Lion's Heart"),
    SkillNode("A_temp0", "???", "???",
            347, 235, 1, 0, LEO_GOLD, ["A_Prevalence"], "Algieba · ???"),
    SkillNode("A_temp1", "???", "???",
            392, 125, 1, 0, LEO_GOLD, ["A_temp0"], "???"),
    SkillNode("A_temp2", "???", "???",
            327, 30, 1, 0, LEO_GOLD, ["A_temp1"], "???"),
    SkillNode("A_temp3", "???", "???",
            257, 140, 1, 0, LEO_GOLD, ["A_temp2"], "???"),
    SkillNode("A_temp4", "???", "???",
            187, 230, 1, 0, LEO_GOLD, ["A_temp3"], "???"),
    SkillNode("A_temp5", "???", "???",
            202, 335, 1, 0, LEO_GOLD, ["A_temp4"], "???"),
    SkillNode("A_temp6", "???", "???",
            72, 340, 1, 0, LEO_GOLD, ["A_temp5"], "???"),
    # --- LIBRA · The Scales -------------------------------------------------
    # Stars are placed on Libra's real figure: the beam held up by
    # Zubeneschamali with the two pans hanging from its arms.
    SkillNode("B_Scales", "Shifting Scales", "Tear open the scales of possibility, Once per day you can allocate temporary stat points between attributes.",
              840, 310, 1, 1, LIBRA_CYAN, [], "Zubeneschamali · The Scales"),
    SkillNode("B_Fortune", "Borrowed Fortune", "Access the weight of the scales. Multiply your base daily temporary stat points by (X+1), where X is the rank of this constellation.",
              900, 255, 5, 0, LIBRA_CYAN, ["B_Scales"], "Zubenelgenubi · The Weight"),
    SkillNode("B_temp1", "???", "???",
              950, 195, 1, 0, LIBRA_CYAN, ["B_Fortune"], "???"),
    SkillNode("B_temp2", "???", "???",
              880, 85, 1, 0, LIBRA_CYAN, ["B_temp1"], "???"),
    SkillNode("B_temp3", "???", "???",
              1030, 25, 1, 0, LIBRA_CYAN, ["B_temp2"], "???"),
    SkillNode("B_temp4", "???", "???",
              1190, 150, 1, 0, LIBRA_CYAN, ["B_temp3"], "???"),
    SkillNode("B_temp5", "???", "???",
              1135, 235, 1, 0, LIBRA_CYAN, ["B_temp4"], "???"),
    SkillNode("B_temp6", "???", "???",
              1200, 310, 1, 0, LIBRA_CYAN, ["B_temp5"], "???"),
]

# Faint extra stars that fill out the real constellations (non-interactive).
DECOR_STARS = {
    "leo": [
        (367, 160),   # Extra point along the Sickle
        (412, 240),   # Curvature of the mane
    ],        # Eta & Mu Leonis (the mane)
    "libra": [
        (965, 300), (1225, 260)
        ],    # Theta & 48 Librae (the cords)
}

# Extra lines that complete each figure without being unlock paths.
DECOR_LINES = {
    "leo": [
        ((72, 340), (187, 230)),
    ],
    "libra": [
        ((810, 380), (1230, 380)), # Brachium - Zuben Elakrab (closes the Scales)
    ],
}

# Soft nebulas behind each figure.
GLOWS = [
    (254, 250, 420, LEO_GOLD),
    (1030, 275, 420, LIBRA_CYAN),
]

# Watermark labels: icon key, spaced name, center x, top y.
CONSTELLATION_LABELS = [
    ("leo", "L  E  O", 327, -110),
    ("libra", "L  I  B  R  A", 1030, -110),
]


class SkillMapCanvas(QWidget):
    constellation_changed = Signal(int)

    def __init__(self, nodes, config, parent=None):
        super().__init__(parent)
        self.nodes = {n.id: n for n in nodes}
        self.config = config
        icon_dir = Path(__file__).resolve().parent.parent / "icons"
        self._constellation_icons = {
            key: QPixmap(str(icon_dir / f"{key}.png"))
            for key in ("leo", "libra")
        }
        for key, icon in self._constellation_icons.items():
            if icon.isNull():
                raise FileNotFoundError(
                    f"Could not load constellation icon: {icon_dir / f'{key}.png'}"
                )
        self._load_ranks()
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self._dragging = False
        self._last_mouse = QPoint()
        self._hovered = None
        self._flash_node = None
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

        # Fixed-seed background starfield so the sky never reshuffles.
        rng = random.Random(2026)
        self._bg_stars = [
            (
                rng.uniform(-450, 1500),
                rng.uniform(-380, 720),
                rng.uniform(0.7, 2.3),
                rng.uniform(0.0, math.tau),
            )
            for _ in range(150)
        ]
        self._twinkle = 0
        self._twinkle_timer = QTimer(self)
        self._twinkle_timer.timeout.connect(self._on_twinkle_tick)
        self._twinkle_timer.start(110)

    def _on_twinkle_tick(self):
        if self.isVisible():
            self._twinkle += 1
            self.update()

    def _load_ranks(self):
        migrate_constellation_ranks(self.config, self.nodes)
        for node in self.nodes.values():
            saved_rank = self.config.get_nested(
                "constellations", node.id, default=node.current_rank,
            )
            if not isinstance(saved_rank, int) or isinstance(saved_rank, bool):
                saved_rank = node.current_rank
            node.current_rank = max(0, min(saved_rank, node.max_rank))
            self.config.set_nested("constellations", node.id, node.current_rank, save=False)
        self.config.save()

    def _save_ranks(self):
        for node in self.nodes.values():
            self.config.set_nested("constellations", node.id, node.current_rank, save=False)
        self.config.save()

    def _can_unlock(self, node_id):
        node = self.nodes[node_id]
        if node.current_rank >= node.max_rank:
            return False
        if not node.parent_ids:
            return True
        return any(self.nodes[pid].current_rank > 0 for pid in node.parent_ids)

    def _constellation_points(self):
        return self.config.get("player", "constellation_points", 0)

    def _set_constellation_points(self, value):
        self.config.set("player", "constellation_points", max(0, value))
        self.constellation_changed.emit(max(0, value))

    def reset_view(self):
        xs = [n.x for n in self.nodes.values()]
        ys = [n.y for n in self.nodes.values()]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        self.scale = 0.8
        self.offset = QPointF(self.width() / 2 - cx * self.scale, self.height() / 2 - cy * self.scale)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.offset == QPointF(0, 0):
            self.reset_view()

    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        factor = 1.15 if zoom_in else 0.87
        new_scale = max(0.2, min(3.0, self.scale * factor))
        mouse_pos = event.position()
        world_before = self._to_world(mouse_pos)
        self.scale = new_scale
        self.offset.setX(mouse_pos.x() - world_before.x() * new_scale)
        self.offset.setY(mouse_pos.y() - world_before.y() * new_scale)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_mouse = event.pos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.pos() - self._last_mouse
            self.offset += QPointF(delta)
            self._last_mouse = event.pos()
            self.update()
        else:
            self._update_hover(self._to_world(event.position()))
            if self._hovered:
                self._update_tooltip()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            wp = self._to_world(event.position())
            self._try_click(wp)

    def leaveEvent(self, event):
        if self._hovered:
            self._hovered = None
            QToolTip.hideText()
            self.update()
        super().leaveEvent(event)

    def _to_world(self, screen_pos):
        return QPointF(
            (screen_pos.x() - self.offset.x()) / self.scale,
            (screen_pos.y() - self.offset.y()) / self.scale,
        )

    def _update_hover(self, world_pos):
        prev = self._hovered
        self._hovered = None
        for node in self.nodes.values():
            dx = world_pos.x() - node.x
            dy = world_pos.y() - node.y
            if (dx * dx + dy * dy) <= 36 * 36:
                self._hovered = node.id
                break
        if self._hovered != prev:
            self.update()

    def _update_tooltip(self):
        if not self._hovered:
            QToolTip.hideText()
            return

        n = self.nodes[self._hovered]
        if n.current_rank >= n.max_rank:
            state = "<span style=\"color:#ffd700\">MAXED</span>"
        elif self._can_unlock(n.id):
            state = (
                f"<span style=\"color:{CYAN}\">Click to unlock rank {n.current_rank + 1}</span> "
                f"({self._constellation_points()} points)"
            )
        else:
            state = "<span style=\"color:#666\">Locked — requires parent</span>"

        name_line = f"<b>{n.name}</b>"
        if n.star:
            name_line += f" · <i>{n.star}</i>"

        text = (
            f"{name_line}<br>{n.description}<br>"
            f"Rank {n.current_rank}/{n.max_rank}<br>{state}"
        )

        # Show immediately at the cursor with no auto-timeout so it
        # stays visible while we update position on every mouse move.
        QToolTip.showText(QCursor.pos(), text, self, QRect(), 0)

    def _try_click(self, world_pos):
        for node in self.nodes.values():
            dx = world_pos.x() - node.x
            dy = world_pos.y() - node.y
            if (dx * dx + dy * dy) > 36 * 36:
                continue
            if not self._can_unlock(node.id):
                self._flash_node = node.id
                from PySide6.QtCore import QTimer
                QTimer.singleShot(200, lambda: self._clear_flash())
                self.update()
                return
            if self._constellation_points() <= 0:
                self._flash_node = node.id
                from PySide6.QtCore import QTimer
                QTimer.singleShot(200, lambda: self._clear_flash())
                self.update()
                return
            node.current_rank += 1
            self._set_constellation_points(self._constellation_points() - 1)
            self._save_ranks()
            self._update_tooltip()
            self.update()
            return

    def _clear_flash(self):
        self._flash_node = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#04060c"))

        painter.save()
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)

        self._draw_nebulas(painter)
        self._draw_background_stars(painter)
        self._draw_decor(painter)
        self._draw_lines(painter)
        self._draw_constellation_labels(painter)

        for node in self.nodes.values():
            self._draw_node(painter, node)

        painter.restore()
        painter.end()

    def _draw_nebulas(self, painter):
        """Soft colored nebulas behind each constellation."""
        for gx, gy, gr, color in GLOWS:
            grad = QRadialGradient(gx, gy, gr)
            c0 = QColor(color)
            c0.setAlpha(16)
            c1 = QColor(color)
            c1.setAlpha(0)
            grad.setColorAt(0, c0)
            grad.setColorAt(1, c1)
            painter.fillRect(QRectF(gx - gr, gy - gr, gr * 2, gr * 2), QBrush(grad))

    def _draw_background_stars(self, painter):
        """Twinkling field of faint stars scattered across the sky."""
        for sx, sy, size, phase in self._bg_stars:
            tw = 0.55 + 0.45 * math.sin(self._twinkle * 0.35 + phase)
            alpha = int(40 + 90 * tw)
            painter.setPen(QPen(QColor(215, 224, 255, alpha), size))
            painter.drawPoint(int(sx), int(sy))

    def _draw_decor(self, painter):
        """Faint extra stars and dashed lines that complete each figure."""
        for key in ("leo", "libra"):
            color = LEO_GOLD if key == "leo" else LIBRA_CYAN
            star_c = QColor("#cdd6ee")
            star_c.setAlpha(150)
            painter.setPen(QPen(star_c, 2.2))
            for sx, sy in DECOR_STARS[key]:
                painter.drawPoint(int(sx), int(sy))
            line_c = QColor(color)
            line_c.setAlpha(70)
            pen = QPen(line_c, 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            for (x1, y1), (x2, y2) in DECOR_LINES[key]:
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_lines(self, painter):
        """Constellation lines between the stars (unlock paths)."""
        for node in self.nodes.values():
            for pid in node.parent_ids:
                p = self.nodes.get(pid)
                if not p:
                    continue
                active = node.current_rank > 0 and p.current_rank > 0
                if active:
                    glow = QColor(node.color)
                    glow.setAlpha(60)
                    painter.setPen(QPen(glow, 7))
                    painter.drawLine(int(p.x), int(p.y), int(node.x), int(node.y))
                    core = QColor(node.color)
                    core.setAlpha(220)
                    painter.setPen(QPen(core, 1.6))
                else:
                    painter.setPen(QPen(QColor("#2b3247"), 1.5))
                painter.drawLine(int(p.x), int(p.y), int(node.x), int(node.y))

    def _draw_constellation_labels(self, painter):
        """Large faint zodiac icons and names behind each figure."""
        for icon_key, name, cx, cy in CONSTELLATION_LABELS:
            painter.save()
            painter.setOpacity(0.2)
            painter.drawPixmap(
                QRectF(cx - 24, cy, 48, 48),
                self._constellation_icons[icon_key],
                QRectF(self._constellation_icons[icon_key].rect()),
            )
            painter.restore()

            name_c = QColor("#ffffff")
            name_c.setAlpha(36)
            font2 = QFont()
            font2.setPixelSize(16)
            font2.setBold(True)
            painter.setFont(font2)
            painter.setPen(name_c)
            painter.drawText(
                QRectF(cx - 220, cy + 50, 440, 24),
                Qt.AlignmentFlag.AlignCenter, name,
            )

    def _draw_node(self, painter, node):
        ring_r = 26
        hover = self._hovered == node.id
        flash = self._flash_node == node.id
        cx = int(node.x)
        cy = int(node.y)
        is_unlocked = node.current_rank > 0
        can_unlock = self._can_unlock(node.id)

        col = QColor(node.color) if (is_unlocked or can_unlock) else QColor("#4a4f5c")
        ring_col = QColor(node.color) if is_unlocked else (QColor("#8b93a8") if can_unlock else QColor("#333a48"))
        if flash:
            ring_col = QColor("#ff2222")

        # Soft stellar glow around the star.
        glow = QRadialGradient(QPointF(cx, cy), 60)
        g0 = QColor(col)
        g0.setAlpha(160 if is_unlocked else (90 if can_unlock else 30))
        if hover and (is_unlocked or can_unlock):
            g0 = g0.lighter(130)
        g1 = QColor(col)
        g1.setAlpha(0)
        glow.setColorAt(0, g0)
        glow.setColorAt(1, g1)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 60, 60)

        # Star body: a dark orb held in a thin ring.
        painter.setBrush(QColor(8, 10, 16, 190))
        painter.setPen(QPen(ring_col, 3 if hover else 2))
        painter.drawEllipse(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        # Rays around lit stars, longer on hover.
        if is_unlocked or (hover and can_unlock):
            ray_len = 13 if hover else 8
            painter.setPen(QPen(QColor(node.color).lighter(130), 2))
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                r0 = ring_r + 3
                r1 = ring_r + 3 + ray_len
                painter.drawLine(cx + dx * r0, cy + dy * r0, cx + dx * r1, cy + dy * r1)

        # Rank inside the star.
        rank_str = f"{node.current_rank}/{node.max_rank}"
        font_r = QFont()
        font_r.setPixelSize(11)
        font_r.setBold(True)
        painter.setFont(font_r)
        painter.setPen(QColor(node.color) if is_unlocked else QColor("#7a8194"))
        painter.drawText(cx - 20, cy - 8, 40, 16, Qt.AlignmentFlag.AlignCenter, rank_str)

        # Star name below.
        font = QFont()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#e8ecf6"))
        painter.drawText(
            cx - 70, cy + ring_r + 8, 140, 18,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            node.name,
        )



class AbilityTreePanel(QFrame):
    def __init__(self, config, on_back=None, parent=None):
        super().__init__(parent)
        self.on_back = on_back
        self._config = config
        self.setStyleSheet("background-color: #080808; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 12)
        title = QLabel("CONSTELLATIONS")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {WHITE}; letter-spacing: 3px;")
        top.addWidget(title)
        top.addStretch()

        self._cp_label = QLabel(f"✦ {config.get('player', 'constellation_points', 0)}")
        self._cp_label.setStyleSheet(f"color: {CYAN}; font-size: 14px; font-weight: bold; padding-right: 12px;")
        top.addWidget(self._cp_label)

        back = QPushButton("< BACK")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {CYAN}44;
                color: {CYAN};
                padding: 5px 14px;
                border-radius: 2px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {CYAN}22;
                border-color: {CYAN};
            }}
        """)
        back.clicked.connect(lambda: self.on_back() if self.on_back else None)
        top.addWidget(back)

        zoom_in = QPushButton("+")
        zoom_out = QPushButton("-")
        for btn in (zoom_in, zoom_out):
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #111111;
                    color: {CYAN};
                    border: 1px solid {CYAN};
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {CYAN};
                    color: #0a0a0a;
                }}
            """)
        zoom_in.clicked.connect(self._zoom_in)
        zoom_out.clicked.connect(self._zoom_out)
        top.addWidget(zoom_out)
        top.addWidget(zoom_in)

        top_bar = QFrame()
        top_bar.setLayout(top)
        top_bar.setStyleSheet("background-color: #0d0d0d; border-bottom: 1px solid #1a1a1a;")
        layout.addWidget(top_bar)

        self._canvas = SkillMapCanvas(NODES, config, parent=self)
        self._canvas.constellation_changed.connect(self._on_cp_changed)
        layout.addWidget(self._canvas, 1)

        hint = QLabel("Drag to pan · Scroll to zoom · Click a star to spend a constellation point · LEO the Lion · LIBRA the Scales")
        hint.setStyleSheet("color: #444444; font-size: 10px; padding: 4px 12px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def showEvent(self, event):
        super().showEvent(event)
        self._canvas.reset_view()
        self._cp_label.setText(f"✦ {self._config.get('player', 'constellation_points', 0)}")

    def _on_cp_changed(self, value):
        self._cp_label.setText(f"✦ {value}")

    def refresh_points(self):
        self._cp_label.setText(f"✦ {self._config.get('player', 'constellation_points', 0)}")

    def _zoom_in(self):
        self._canvas.scale = min(3.0, self._canvas.scale * 1.2)
        self._canvas.update()

    def _zoom_out(self):
        self._canvas.scale = max(0.2, self._canvas.scale / 1.2)
        self._canvas.update()
