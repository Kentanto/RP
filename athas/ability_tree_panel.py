"""Interactive skill-tree map with pan, zoom, and constellation-based unlocking."""
from dataclasses import dataclass, field
from typing import List

from PySide6.QtCore import Qt, QPoint, QPointF, Signal
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


NODES = [
    SkillNode("c_root", "Combat Focus", "Foundation of martial prowess.", 0, 0, 5, 0, "#ff4444"),
    SkillNode("c_pow", "Power Strike", "A devastating heavy blow.", 200, -160, 5, 0, "#ff4444", ["c_root"]),
    SkillNode("c_crit", "Critical Blow", "Increased critical hit chance.", 400, -240, 3, 0, "#ff4444", ["c_pow"]),
    SkillNode("c_ber", "Berserker", "Trade defense for raw damage.", 400, -80, 3, 0, "#ff4444", ["c_pow"]),
    SkillNode("c_def", "Iron Skin", "Harden your body against blows.", 200, 160, 5, 0, "#ff4444", ["c_root"]),
    SkillNode("c_for", "Fortress", "Massively increase damage reduction.", 400, 240, 3, 0, "#ff4444", ["c_def"]),
    SkillNode("c_shd", "Shield Slam", "Stun enemies with a bash.", 400, 80, 3, 0, "#ff4444", ["c_def"]),
    SkillNode("a_root", "Arcane Focus", "Tap into the flow of magic.", 700, 0, 5, 0, "#00e5ff"),
    SkillNode("a_man", "Mana Flow", "Accelerate mana regeneration.", 900, -160, 5, 0, "#00e5ff", ["a_root"]),
    SkillNode("a_sur", "Energy Surge", "Overcharge your next spell.", 1100, -240, 3, 0, "#00e5ff", ["a_man"]),
    SkillNode("a_rif", "Elemental Rift", "Rip open a portal of raw elements.", 1100, -80, 3, 0, "#00e5ff", ["a_man"]),
    SkillNode("a_men", "Mental Barrier", "Shield the mind from harm.", 900, 160, 5, 0, "#00e5ff", ["a_root"]),
    SkillNode("a_shl", "Mind Shield", "Reflect psychic damage.", 1100, 240, 3, 0, "#00e5ff", ["a_men"]),
    SkillNode("a_psy", "Psychic Blast", "Unleash a wave of mental force.", 1100, 80, 3, 0, "#00e5ff", ["a_men"]),
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
        self.setToolTip(
            f"<b>{n.name}</b><br>{n.description}<br>"
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
        painter.fillRect(self.rect(), QColor("#080808"))

        pen_line = QPen(QColor("#333333"), 3)
        pen_active = QPen(QColor("#555555"), 3)
        painter.save()
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)

        for node in self.nodes.values():
            for pid in node.parent_ids:
                p = self.nodes.get(pid)
                if not p:
                    continue
                active = node.current_rank > 0 and p.current_rank > 0
                painter.setPen(pen_active if active else pen_line)
                painter.drawLine(int(p.x), int(p.y), int(node.x), int(node.y))

        for node in self.nodes.values():
            self._draw_node(painter, node)

        painter.restore()
        painter.end()

    def _draw_node(self, painter, node):
        r = 32
        hover = self._hovered == node.id
        flash = self._flash_node == node.id
        cx = int(node.x)
        cy = int(node.y)
        is_unlocked = node.current_rank > 0
        can_unlock = self._can_unlock(node.id)

        col = QColor(node.color) if is_unlocked else (QColor(node.color) if can_unlock else QColor("#444444"))
        ring_col = QColor(node.color) if is_unlocked else (QColor("#888888") if can_unlock else QColor("#333333"))
        if flash:
            ring_col = QColor("#ff0000")

        grad = QRadialGradient(cx, cy, r * 2, cx, cy)
        if hover and can_unlock:
            grad.setColorAt(0, QColor(node.color).lighter(150))
            grad.setColorAt(1, QColor("#000000"))
        else:
            inner = col.lighter(120) if is_unlocked else col
            grad.setColorAt(0, inner)
            grad.setColorAt(1, QColor("#000000"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(ring_col, 3 if hover else 2))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        font = QFont()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            cx - 60, cy + r + 6, 120, 20,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            node.name,
        )

        rank_str = f"{node.current_rank}/{node.max_rank}"
        painter.setPen(QColor(node.color) if is_unlocked else QColor("#666666"))
        font_r = QFont()
        font_r.setPixelSize(11)
        font_r.setBold(True)
        painter.setFont(font_r)
        painter.drawText(cx - 20, cy - 8, 40, 16, Qt.AlignmentFlag.AlignCenter, rank_str)



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
        title = QLabel("SKILL TREE")
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

        hint = QLabel("Drag to pan · Scroll to zoom · Click node to spend constellation point")
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
