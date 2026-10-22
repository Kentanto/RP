"""Per-skill upgrade tree in its own window, styled like the constellation map."""
import math
import random
from typing import Any

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QFont, QPainter, QPen, QRadialGradient,
)
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QToolTip, QVBoxLayout,
    QWidget,
)

from athas.ability_tree_panel import SkillNode
from athas.styles import CYAN, WHITE


def _nonnegative_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    return default


def _nodes_from_skill(skill: dict[str, Any]) -> dict[str, SkillNode]:
    """Turn a validated skill's 'upgrades' entries into tree nodes."""
    nodes: dict[str, SkillNode] = {}
    for entry in skill["upgrades"]:
        color = entry.get("color") or CYAN
        if not QColor(color).isValid():
            color = CYAN
        max_rank = entry["max_rank"]
        # Upgrade ranks live in the skill's own JSON file ('rank' per node).
        saved_rank = max(0, min(_nonnegative_int(entry.get("rank")), max_rank))
        nodes[entry["id"]] = SkillNode(
            id=entry["id"],
            name=entry["title"],
            description=entry["description"],
            x=float(entry["x"]),
            y=float(entry["y"]),
            max_rank=max_rank,
            current_rank=saved_rank,
            color=color,
            parent_ids=list(entry.get("parents", [])),
        )
    return nodes


class SkillTreeCanvas(QWidget):
    """Pan/zoom star map of one skill's upgrades, like the constellation map."""

    points_changed = Signal(int)

    def __init__(self, skill: dict[str, Any], config, skills_manager, parent=None):
        super().__init__(parent)
        self._skill_id = skill["id"]
        # SkillManager validates upgrade_cost as a positive integer.
        self._cost_per_rank = max(1, _nonnegative_int(skill.get("upgrade_cost"), default=1))
        self.nodes = _nodes_from_skill(skill)
        self.config = config
        self.skills_manager = skills_manager
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self._dragging = False
        self._last_mouse = QPoint()
        self._hovered = None
        self._flash_node = None
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

        xs = [node.x for node in self.nodes.values()] or [0.0]
        ys = [node.y for node in self.nodes.values()] or [0.0]
        self._center_x = (min(xs) + max(xs)) / 2
        self._center_y = (min(ys) + max(ys)) / 2
        self._glow_radius = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.45 + 160

        # Fixed-seed background starfield so the sky never reshuffles.
        rng = random.Random(2026)
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        self._bg_stars = [
            (
                rng.uniform(self._center_x - span_x / 2 - 420, self._center_x + span_x / 2 + 420),
                rng.uniform(self._center_y - span_y / 2 - 340, self._center_y + span_y / 2 + 340),
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

    def _save_ranks(self):
        self.skills_manager.save_ranks(
            self._skill_id,
            {node.id: node.current_rank for node in self.nodes.values()},
        )

    def _skill_points(self):
        return _nonnegative_int(self.config.get("player", "skill_points", 0))

    def _set_skill_points(self, value):
        self.config.set("player", "skill_points", max(0, value))
        self.points_changed.emit(max(0, value))

    def _can_unlock(self, node_id):
        node = self.nodes[node_id]
        if node.current_rank >= node.max_rank:
            return False
        if not node.parent_ids:
            return True
        return any(self.nodes[pid].current_rank > 0 for pid in node.parent_ids)

    def reset_view(self):
        """Fit the whole tree comfortably in the canvas."""
        if not self.nodes:
            return
        xs = [node.x for node in self.nodes.values()]
        ys = [node.y for node in self.nodes.values()]
        pad = 90  # breathing room for glows and node names
        bounds_w = (max(xs) - min(xs)) + pad * 2
        bounds_h = (max(ys) - min(ys)) + pad * 2
        width = max(1, self.width())
        height = max(1, self.height())
        self.scale = min(width / bounds_w, height / bounds_h, 1.6)
        center_x = (min(xs) + max(xs)) / 2
        center_y = (min(ys) + max(ys)) / 2
        self.offset = QPointF(
            width / 2 - center_x * self.scale,
            height / 2 - center_y * self.scale,
        )
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
            self._try_click(self._to_world(event.position()))

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

        node = self.nodes[self._hovered]
        if node.current_rank >= node.max_rank:
            state = "<span style=\"color:#ffd700\">MAXED</span>"
        elif self._can_unlock(node.id):
            state = (
                f"<span style=\"color:{CYAN}\">Click to unlock rank {node.current_rank + 1}</span> "
                f"({self._skill_points()} SP)"
            )
        else:
            state = "<span style=\"color:#666\">Locked — requires parent</span>"

        text = (
            f"<b>{node.name}</b><br>{node.description}<br>"
            f"Rank {node.current_rank}/{node.max_rank} · "
            f"{self._cost_per_rank} SP per rank<br>{state}"
        )

        # Show immediately at the cursor with no auto-timeout so it stays
        # visible while we update position on every mouse move.
        QToolTip.showText(QCursor.pos(), text, self, QRect(), 0)

    def _try_click(self, world_pos):
        for node in self.nodes.values():
            dx = world_pos.x() - node.x
            dy = world_pos.y() - node.y
            if (dx * dx + dy * dy) <= 36 * 36:
                self.try_unlock_node(node.id)
                return

    def try_unlock_node(self, node_id: str) -> bool:
        """Spend skill points to raise one node's rank; True when it worked."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        if not self._can_unlock(node_id) or self._skill_points() < self._cost_per_rank:
            self._flash_node = node_id
            QTimer.singleShot(200, self._clear_flash)
            self.update()
            return False
        node.current_rank += 1
        self._set_skill_points(self._skill_points() - self._cost_per_rank)
        self._save_ranks()
        self._update_tooltip()
        self.update()
        return True

    def _clear_flash(self):
        self._flash_node = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#04060c"))

        painter.save()
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)

        self._draw_nebula(painter)
        self._draw_background_stars(painter)
        self._draw_lines(painter)

        for node in self.nodes.values():
            self._draw_node(painter, node)

        painter.restore()
        painter.end()

    def _draw_nebula(self, painter):
        """One soft glow behind the tree, tinted with the skill's colour."""
        grad = QRadialGradient(self._center_x, self._center_y, self._glow_radius)
        c0 = QColor(CYAN)
        c0.setAlpha(16)
        c1 = QColor(CYAN)
        c1.setAlpha(0)
        grad.setColorAt(0, c0)
        grad.setColorAt(1, c1)
        painter.fillRect(
            QRectF(
                self._center_x - self._glow_radius,
                self._center_y - self._glow_radius,
                self._glow_radius * 2,
                self._glow_radius * 2,
            ),
            QBrush(grad),
        )

    def _draw_background_stars(self, painter):
        """Twinkling field of faint stars scattered across the sky."""
        for sx, sy, size, phase in self._bg_stars:
            tw = 0.55 + 0.45 * math.sin(self._twinkle * 0.35 + phase)
            alpha = int(40 + 90 * tw)
            painter.setPen(QPen(QColor(215, 224, 255, alpha), size))
            painter.drawPoint(int(sx), int(sy))

    def _draw_lines(self, painter):
        """Lines between the nodes (unlock paths)."""
        for node in self.nodes.values():
            for pid in node.parent_ids:
                parent = self.nodes.get(pid)
                if not parent:
                    continue
                active = node.current_rank > 0 and parent.current_rank > 0
                if active:
                    glow = QColor(node.color)
                    glow.setAlpha(60)
                    painter.setPen(QPen(glow, 7))
                    painter.drawLine(int(parent.x), int(parent.y), int(node.x), int(node.y))
                    core = QColor(node.color)
                    core.setAlpha(220)
                    painter.setPen(QPen(core, 1.6))
                else:
                    painter.setPen(QPen(QColor("#2b3247"), 1.5))
                painter.drawLine(int(parent.x), int(parent.y), int(node.x), int(node.y))

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

        # Node name below.
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

class SkillTreeDialog(QDialog):
    """A skill's upgrade tree in its own window."""

    def __init__(self, skill: dict[str, Any], config, skills_manager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(f"{skill['title']} — UPGRADES")
        self.setModal(True)
        self.resize(900, 640)
        self.setStyleSheet("QDialog { background-color: #080808; border: none; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 12)
        title = QLabel(f"{skill['title'].upper()} · UPGRADE TREE")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {WHITE}; letter-spacing: 3px;")
        top.addWidget(title)
        top.addStretch()

        self._sp_label = QLabel(
            f"✦ {_nonnegative_int(config.get('player', 'skill_points', 0))} SP"
        )
        self._sp_label.setStyleSheet(
            f"color: {CYAN}; font-size: 14px; font-weight: bold; padding-right: 12px;"
        )
        top.addWidget(self._sp_label)

        close = QPushButton("✕ CLOSE")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(f"""
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
        close.clicked.connect(self.close)
        top.addWidget(close)

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

        self._canvas = SkillTreeCanvas(skill, config, skills_manager, parent=self)
        self._canvas.points_changed.connect(self._on_points_changed)
        layout.addWidget(self._canvas, 1)

        hint = QLabel("Drag to pan · Scroll to zoom · Click a node to spend a skill point")
        hint.setStyleSheet("color: #444444; font-size: 10px; padding: 4px 12px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def showEvent(self, event):
        super().showEvent(event)
        self._canvas.reset_view()
        self._refresh_points()

    def _on_points_changed(self, value):
        self._sp_label.setText(f"✦ {value} SP")

    def _refresh_points(self):
        points = _nonnegative_int(self._config.get("player", "skill_points", 0))
        self._sp_label.setText(f"✦ {points} SP")

    def _zoom_in(self):
        self._canvas.scale = min(3.0, self._canvas.scale * 1.2)
        self._canvas.update()

    def _zoom_out(self):
        self._canvas.scale = max(0.2, self._canvas.scale / 1.2)
        self._canvas.update()