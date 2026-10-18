"""Interactive constellation map with pan, zoom, and star-sign-based unlocking."""
import math
import random
from dataclasses import dataclass, field
from typing import List

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient

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
# --- LEO · The Lion (reversed / mirrored) ---------------------------------
# The sickle (head & mane) is on the RIGHT, tail on the LEFT so the Lion
# faces the centre of the sky.  Same real stellar names, just flipped.
NODES = [
    SkillNode("c_root", "Combat Focus", "Foundation of martial prowess.",
              300, 300, 5, 0, LEO_GOLD, [], "Regulus · the Lion's Heart"),
    SkillNode("c_pow", "Power Strike", "A devastating heavy blow.",
              440, 190, 5, 0, LEO_GOLD, ["c_root"], "Algieba · the Mane"),
    SkillNode("c_crit", "Critical Blow", "Increased critical hit chance.",
              520, 110, 3, 0, LEO_GOLD, ["c_pow"], "Adhafera · the Sickle"),
    SkillNode("c_ber", "Berserker", "Trade defense for raw damage.",
              560, 230, 3, 0, LEO_GOLD, ["c_pow"], "Algenubi · the Mane"),
    SkillNode("c_def", "Iron Skin", "Harden your body against blows.",
              160, 310, 5, 0, LEO_GOLD, ["c_root"], "Chertan · the Hip"),
    SkillNode("c_for", "Fortress", "Massively increase damage reduction.",
              140, 180, 3, 0, LEO_GOLD, ["c_def"], "Zosma · the Back"),
    SkillNode("c_shd", "Shield Slam", "Stun enemies with a bash.",
              30, 330, 3, 0, LEO_GOLD, ["c_def"], "Denebola · the Tail"),

    # --- LIBRA · The Scales -----------------------------------------------
    # A classic balance scale hanging from a single pivot at the top.
    # Two arms spread diagonally, each drops a chain to a pan below.
    SkillNode("a_root", "Arcane Focus", "Tap into the flow of magic.",
              900, 100, 5, 0, LIBRA_CYAN, [], "Zubeneschamali · the Beam"),
    SkillNode("a_man", "Mana Flow", "Accelerate mana regeneration.",
              1050, 240, 5, 0, LIBRA_CYAN, ["a_root"], "Zuben Elakrab · the East Arm"),
    SkillNode("a_men", "Mental Barrier", "Shield the mind from harm.",
              750, 240, 5, 0, LIBRA_CYAN, ["a_root"], "Zubenelgenubi · the West Arm"),
    SkillNode("a_shl", "Mind Shield", "Reflect psychic damage.",
              1120, 400, 3, 0, LIBRA_CYAN, ["a_man"], "Brachium · the East Chain"),
    SkillNode("a_psy", "Psychic Blast", "Unleash a wave of mental force.",
              680, 400, 3, 0, LIBRA_CYAN, ["a_men"], "Theta Librae · the West Chain"),
    SkillNode("a_sur", "Energy Surge", "Overcharge your next spell.",
              1190, 560, 3, 0, LIBRA_CYAN, ["a_shl"], "Upsilon Librae · the East Pan"),
    SkillNode("a_rif", "Elemental Rift", "Rip open a portal of raw elements.",
              610, 560, 3, 0, LIBRA_CYAN, ["a_psy"], "Tau Librae · the West Pan"),
]

# Faint extra stars that fill out the real constellations (non-interactive).
DECOR_STARS = {
    "leo": [(380, 300), (100, 130)],          # Rasalas, Eta Leonis
    "libra": [(900, 340), (900, 500)],        # Spica-pointers, decorative mid-stars
}

# Extra lines that complete each figure without being unlock paths.
DECOR_LINES = {
    "leo": [
        ((520, 110), (560, 230)),    # closes the sickle hook
        ((140, 180), (30, 330)),     # Zosma → Denebola (body edge)
        ((440, 190), (140, 180)),    # Algieba → Zosma (back)
    ],
    "libra": [
        ((680, 400), (1120, 400)),   # horizontal pan-joining bar
        ((610, 560), (1190, 560)),   # bottom crossbar (pans)
    ],
}

# Soft nebulas behind each figure.
GLOWS = [
    (300, 200, 380, LEO_GOLD),
    (900, 310, 420, LIBRA_CYAN),
]

# Watermark labels: key, zodiac glyph, spaced name, color, center x, top y.
CONSTELLATION_LABELS = [
    (LEO_GOLD, "♌", "L  E  O", 300, -85),
    (LIBRA_CYAN, "♎", "L  I  B  R  A", 900, -85),
]


class SkillMapCanvas(QWidget):
    constellation_changed = Signal(int)

    def __init__(self, nodes, config, parent=None):
        super().__init__(parent)
        self.nodes = {n.id: n for n in nodes}
        self.config = config
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
        for node in self.nodes.values():
            node.current_rank = min(
                self.config.get_nested("skills", node.id, default=0),
                node.max_rank,
            )

    def _save_ranks(self):
        for node in self.nodes.values():
            self.config.set_nested("skills", node.id, node.current_rank)

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
        self.scale = 1.0
        self.offset = QPointF(self.width() / 2 - cx, self.height() / 2 - cy)
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

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            wp = self._to_world(event.position())
            self._try_click(wp)

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
            self._update_tooltip()
            self.update()

    def _update_tooltip(self):
        if not self._hovered:
            self.setToolTip("")
            return
        n = self.nodes[self._hovered]
        state = ""
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
        self.setToolTip(
            f"{name_line}<br>{n.description}<br>"
            f"Rank {n.current_rank}/{n.max_rank}<br>{state}"
        )

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
        """Large faint zodiac glyphs and names behind each figure."""
        for color, glyph, name, cx, cy in CONSTELLATION_LABELS:
            glyph_c = QColor(color)
            glyph_c.setAlpha(70)
            font = QFont("Segoe UI Symbol")
            font.setPixelSize(40)
            painter.setFont(font)
            painter.setPen(glyph_c)
            painter.drawText(
                QRectF(cx - 200, cy, 400, 50),
                Qt.AlignmentFlag.AlignCenter, glyph,
            )
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

        pulse = 1.0 + 0.12 * math.sin(self._twinkle * 0.4) if is_unlocked else 1.0
        bright = QColor(node.color) if (is_unlocked or can_unlock) else QColor("#5a6070")

        # ---- outer halo (radial colour wash) ----
        for r, alpha in ((55, 24), (42, 40), (30, 70), (18, 120)):
            halo = QRadialGradient(QPointF(cx, cy), r * pulse)
            c0 = QColor(bright)
            c0.setAlpha(alpha if (is_unlocked or can_unlock) else int(alpha * 0.35))
            halo.setColorAt(0, c0)
            halo.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(halo))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), r * pulse, r * pulse)

        # ---- moon-white inner star (tiny disc) ----
        core_r = 6 * (1.2 if hover else 1.0)
        painter.setBrush(QColor(255, 255, 255) if (is_unlocked or can_unlock) else QColor(180, 185, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # ---- sparkle rays (sharp white / bright colour) ----
        if is_unlocked or can_unlock:
            w_rays = int(8 if hover else (6 if is_unlocked else 5))
            primary = QColor(255, 255, 255, 220)
            secondary = QColor(bright)
            secondary.setAlpha(180)
            _draw_star_rays(painter, cx, cy, node.color, w_rays)

        # ---- dim ring around inactive stars (needed for visiblity) ----
        if not (is_unlocked or can_unlock):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(ring_col, 1.5))
            painter.drawEllipse(cx - 13, cy - 13, 26, 26)

        # ---- Rank label (offset slightly so it doesn't sit on the core) ----
        rank_str = f"{node.current_rank}/{node.max_rank}"
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.setPen(QColor(node.color) if is_unlocked else QColor("#7a8194"))
        painter.drawText(cx - 20, cy + 10, 40, 16, Qt.AlignmentFlag.AlignCenter, rank_str)

        # ---- Star / skill name ----
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#e8ecf6"))
        painter.drawText(
            cx - 80, cy + 22, 160, 18,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            node.name,
        )



def _draw_star_rays(painter, cx, cy, color, num_rays):
    """Draw sharp multi-pointed rays like a bright star in the sky."""
    ray_long = 22
    ray_short = 8
    for i in range(num_rays):
        a = (math.tau * i) / num_rays
        # long main ray (white)
        x1 = cx + math.cos(a) * ray_long
        y1 = cy + math.sin(a) * ray_long
        x0 = cx - math.cos(a) * 3
        y0 = cy - math.sin(a) * 3
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
        painter.drawLine(int(x0), int(y0), int(x1), int(y1))
        # short colour ray in between
        a2 = a + (math.tau / (num_rays * 2))
        x2 = cx + math.cos(a2) * ray_short
        y2 = cy + math.sin(a2) * ray_short
        painter.setPen(QPen(QColor(color), 0.8))
        painter.drawLine(cx, cy, int(x2), int(y2))


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

    def _zoom_in(self):
        self._canvas.scale = min(3.0, self._canvas.scale * 1.2)
        self._canvas.update()

    def _zoom_out(self):
        self._canvas.scale = max(0.2, self._canvas.scale / 1.2)
        self._canvas.update()
