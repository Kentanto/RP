"""
Inventory Panel -- tabbed grid of Items (JSON), Artifacts (DB), and
Supplies (shop consumables), plus the artifact workshop.

Artifacts no longer use pictures: their cards show the rolled stat lines
directly. Only EQUIPPED artifacts (5 slots) apply their stats to the
character. From the artifact detail view you can equip/unequip, UPGRADE
(a low/high roll into a random stat, max level 20), DOWNGRADE for a partial
gold refund, REROLL the stat types entirely (resets the upgrades), or
reroll only where the numbers went while keeping the stat types and the
upgrade level — every upgrade is applied again with fresh low/high rolls.
Supplies bought in the shop show up on the SUPPLIES tab with their counts
and can be used from their detail view.
"""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

from athas import audio
from athas.styles import CYAN, WHITE, GOLD, button_style
from athas.artifact_generator import (
    PCT_DETAILED_STATS, RARITIES, SACRIFICE_PER_FUSION,
    MAX_UPGRADE_LEVEL, EQUIP_SLOTS, stat_display,
)
from athas.inventory_manager import InventoryItem
from athas import equip


RARITY_COLORS = {
    "Common": "#888888", "Uncommon": "#4caf50", "Rare": "#2196f3",
    "Epic": "#9c27b0", "Legendary": "#ff9800", "Mythic": GOLD,
}


def _rarity_border(rarity: str) -> str:
    return RARITY_COLORS.get(rarity, CYAN)


def _artifact_id(item):
    """The numeric db id behind an 'artifact:<id>' uid (None otherwise)."""
    if item is None or not str(getattr(item, "uid", "")).startswith("artifact:"):
        return None
    try:
        return int(str(item.uid).split(":", 1)[1])
    except (IndexError, ValueError):
        return None


def _stat_lines(item) -> str:
    """The artifact's stats as readable lines."""
    lines = [stat_display(k, v) for k, v in (item.stats or {}).items() if v]
    return "\n".join(lines) if lines else "No stat bonuses"


class InventoryCard(QFrame):
    def __init__(self, item: InventoryItem, on_click=None, parent=None,
                 selected: bool = False, equipped: bool = False):
        super().__init__(parent)
        self.item = item
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        col = _rarity_border(item.rarity)
        rest_border = f"2px solid {GOLD}" if selected else f"1px solid {col}44"
        hover_border = f"2px solid {GOLD}" if selected else f"1px solid {col}"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(10,10,10,200);
                border: {rest_border};
                border-radius: 4px;
            }}
            QFrame:hover {{
                background-color: rgba(20,20,30,220);
                border: {hover_border};
            }}
        """)
        self.setMinimumSize(160, 200)
        self.setMaximumSize(200, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        if item.category == "item":
            # Hand-made JSON items keep their picture.
            img_label = QLabel()
            img_label.setFixedSize(140, 100)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setScaledContents(True)
            img_label.setStyleSheet("background: transparent; border: none;")
            if item.image_path and Path(item.image_path).exists():
                pix = QPixmap(item.image_path)
                if not pix.isNull():
                    img_label.setPixmap(pix)
            else:
                img_label.setText("[ no image ]")
                img_label.setStyleSheet(f"color: #444; font-size: 10px; background: transparent; border: 1px dashed {col}44;")
            layout.addWidget(img_label, alignment=Qt.AlignmentFlag.AlignCenter)

        top = QHBoxLayout()
        type_badge = QLabel(item.item_type.upper())
        type_badge.setStyleSheet(f"font-size: 9px; color: {col}; font-weight: bold; background: transparent; border: none;")
        top.addWidget(type_badge)
        top.addStretch()
        if equipped:
            badge = QLabel("EQUIPPED")
            badge.setStyleSheet(f"font-size: 9px; color: {GOLD}; font-weight: bold; background: transparent; border: none;")
            top.addWidget(badge)
        elif item.category == "artifact" and item.upgrade_level:
            badge = QLabel(f"+{item.upgrade_level}")
            badge.setStyleSheet(f"font-size: 9px; color: {GOLD}; font-weight: bold; background: transparent; border: none;")
            top.addWidget(badge)
        layout.addLayout(top)

        name = QLabel(("V " if selected else "") + item.name)
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; background: transparent; border: none;")
        layout.addWidget(name)

        rar = QLabel(item.rarity)
        rar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rar.setStyleSheet(f"font-size: 10px; color: {col}; background: transparent; border: none;")
        layout.addWidget(rar)

        meta_bits = [] if item.category == "supply" else [f"Lv.{item.level}"]
        if item.category == "artifact" and item.upgrade_level:
            meta_bits.append(f"+{item.upgrade_level} UP")
        meta_bits.append(f"x{item.count}")
        meta = QLabel("  ".join(meta_bits))
        meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta.setStyleSheet("font-size: 9px; color: #666; background: transparent; border: none;")
        layout.addWidget(meta)

        if item.category == "artifact":
            stats_lbl = QLabel(_stat_lines(item))
            stats_lbl.setWordWrap(True)
            stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stats_lbl.setStyleSheet(f"font-size: 10px; color: {CYAN}; background: transparent; border: none;")
            layout.addWidget(stats_lbl, 1)
        elif item.category == "supply":
            desc_lbl = QLabel(item.description or "")
            desc_lbl.setWordWrap(True)
            desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_lbl.setStyleSheet("font-size: 10px; color: #aaa; background: transparent; border: none;")
            layout.addWidget(desc_lbl, 1)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.item)
        super().mousePressEvent(event)



class _DetailCard(QFrame):
    """The centered detail card. It paints its own dark background and
    rarity-coloured border/glow, so it always renders — even when a
    parent stylesheet would leave it transparent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.border_color = CYAN
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(36)
        glow.setOffset(0, 0)
        glow.setColor(QColor(CYAN))
        self.setGraphicsEffect(glow)
        self._glow = glow

    def set_theme(self, color: str):
        """Border + glow follow the shown item's rarity colour."""
        self.border_color = color or CYAN
        self._glow.setColor(QColor(self.border_color))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(QColor(self.border_color), 2))
        painter.setBrush(QColor(8, 9, 13, 250))
        painter.drawRoundedRect(rect, 8, 8)


class InventoryDetailView(QFrame):
    """Full overlay panel: a centered, rarity-lit detail card for the
    clicked item, artifact, or supply — plus the artifact workshop."""

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.panel = panel
        self.item = None
        self._on_close = None
        self.setObjectName("InventoryDetail")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(f"""
            QFrame#InventoryDetail {{ background: transparent; border: none; }}
            QLabel {{ background: transparent; border: none; color: {WHITE}; }}
        """ + button_style(CYAN))
        self.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 28, 36, 28)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setStyleSheet("background: transparent; border: none;")
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addStretch()
        scroll.setWidget(holder)

        self._card = _DetailCard()
        self._card.setMaximumWidth(940)
        self._card.setMinimumWidth(720)
        holder_layout.addWidget(self._card, 1)
        holder_layout.addStretch()
        outer.addWidget(scroll)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        # --- header: caption / name / rarity / meta + CLOSE ---
        header = QHBoxLayout()
        header.setSpacing(16)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._type_caption = QLabel("")
        self._type_caption.setStyleSheet(
            f"font-size: 10px; color: {CYAN}; font-weight: bold; letter-spacing: 2px;"
        )
        title_col.addWidget(self._type_caption)
        self._name = QLabel("")
        self._name.setWordWrap(True)
        self._name.setStyleSheet("font-size: 26px; font-weight: bold; color: #ffffff;")
        title_col.addWidget(self._name)
        self._rarity = QLabel("")
        self._rarity.setStyleSheet("font-size: 12px; font-weight: bold;")
        title_col.addWidget(self._rarity)
        self._meta = QLabel("")
        self._meta.setStyleSheet("font-size: 11px; color: #777;")
        title_col.addWidget(self._meta)
        header.addLayout(title_col, 1)

        back = QPushButton("CLOSE")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self._close)
        header.addWidget(back, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {CYAN}44; border: none;")
        layout.addWidget(line)


        # --- body: description/lore (left) + bonuses/history (right) ---
        body = QHBoxLayout()
        body.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(6)
        self._img_label = QLabel()
        self._img_label.setFixedSize(180, 140)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setScaledContents(True)
        self._img_label.hide()
        left.addWidget(self._img_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self._desc_caption = QLabel("DESCRIPTION")
        self._desc_caption.setStyleSheet(
            f"color: {CYAN}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        left.addWidget(self._desc_caption)
        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("font-size: 13px; color: #ccc;")
        left.addWidget(self._desc)
        self._lore_caption = QLabel("LORE")
        self._lore_caption.setStyleSheet(
            f"color: {GOLD}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        self._lore_caption.hide()
        left.addWidget(self._lore_caption)
        self._story = QLabel("")
        self._story.setWordWrap(True)
        self._story.setStyleSheet("font-size: 12px; color: #9a9a9a; font-style: italic;")
        left.addWidget(self._story, 1)
        body.addLayout(left, 1)

        self._bonus_panel = QFrame()
        self._bonus_panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0,240,255,12);
                border: 1px solid {CYAN}33;
                border-radius: 4px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        self._bonus_panel.setMinimumWidth(300)
        self._bonus_panel.setMaximumWidth(340)
        bonus_layout = QVBoxLayout(self._bonus_panel)
        bonus_layout.setContentsMargins(14, 12, 14, 12)
        bonus_layout.setSpacing(6)
        self._bonus_caption = QLabel("BONUSES")
        self._bonus_caption.setStyleSheet(
            f"color: {CYAN}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        bonus_layout.addWidget(self._bonus_caption)
        self._stats_box = QVBoxLayout()
        self._stats_box.setSpacing(4)
        bonus_layout.addLayout(self._stats_box)
        self._history_caption = QLabel("UPGRADE HISTORY")
        self._history_caption.setStyleSheet(
            f"color: {GOLD}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        self._history_caption.hide()
        bonus_layout.addWidget(self._history_caption)
        self._history_box = QVBoxLayout()
        self._history_box.setSpacing(3)
        bonus_layout.addLayout(self._history_box)
        bonus_layout.addStretch()
        body.addWidget(self._bonus_panel)
        layout.addLayout(body, 1)

        # --- supply bar (supplies only): USE + owned count ---
        self._supply_bar = QWidget()
        self._supply_bar.setStyleSheet("background: transparent; border: none;")
        sb = QVBoxLayout(self._supply_bar)
        sb.setContentsMargins(0, 6, 0, 0)
        sb.setSpacing(8)
        sb_row = QHBoxLayout()
        self._use_btn = QPushButton("USE ONE")
        self._use_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._use_btn.clicked.connect(self._on_use_supply)
        sb_row.addWidget(self._use_btn)
        self._supply_owned = QLabel("")
        self._supply_owned.setStyleSheet("font-size: 12px; color: #888;")
        sb_row.addWidget(self._supply_owned)
        sb_row.addStretch()
        sb.addLayout(sb_row)
        self._supply_status = QLabel("")
        self._supply_status.setWordWrap(True)
        self._supply_status.setStyleSheet("font-size: 12px; color: #aaa;")
        sb.addWidget(self._supply_status)
        layout.addWidget(self._supply_bar)

        # --- workshop (artifacts only) ---
        self._workshop = QWidget()
        self._workshop.setStyleSheet("background: transparent; border: none;")
        wl = QVBoxLayout(self._workshop)
        wl.setContentsMargins(0, 6, 0, 0)
        wl.setSpacing(10)

        workshop_head = QHBoxLayout()
        self._workshop_title = QLabel("ARTIFACT WORKSHOP")
        self._workshop_title.setStyleSheet(
            f"color: {GOLD}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )
        workshop_head.addWidget(self._workshop_title)
        workshop_head.addStretch()
        self._workshop_gold = QLabel("")
        self._workshop_gold.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: bold;")
        workshop_head.addWidget(self._workshop_gold)
        wl.addLayout(workshop_head)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self._equip_btn = QPushButton("EQUIP")
        self._equip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._equip_btn.clicked.connect(self._on_equip)
        row1.addWidget(self._equip_btn, 1)
        self._upgrade_btn = QPushButton("UPGRADE")
        self._upgrade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upgrade_btn.clicked.connect(self._on_upgrade)
        row1.addWidget(self._upgrade_btn, 1)
        self._downgrade_btn = QPushButton("DOWNGRADE")
        self._downgrade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._downgrade_btn.clicked.connect(self._on_downgrade)
        row1.addWidget(self._downgrade_btn, 1)
        wl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self._reroll_stats_btn = QPushButton("REROLL STATS")
        self._reroll_stats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reroll_stats_btn.clicked.connect(self._on_reroll_stats)
        row2.addWidget(self._reroll_stats_btn, 1)
        self._reroll_values_btn = QPushButton("REROLL VALUES")
        self._reroll_values_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reroll_values_btn.clicked.connect(self._on_reroll_values)
        row2.addWidget(self._reroll_values_btn, 1)
        wl.addLayout(row2)

        self._workshop_status = QLabel("")
        self._workshop_status.setWordWrap(True)
        self._workshop_status.setStyleSheet("font-size: 12px; color: #aaa;")
        wl.addWidget(self._workshop_status)
        layout.addWidget(self._workshop)

    def paintEvent(self, event):
        """Dim whatever is behind the overlay, painted by hand so it
        always renders."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(3, 4, 7, 215))

    # --- showing an item ---
    def show_item(self, item, on_close):
        self.item = item
        self._on_close = on_close
        col = _rarity_border(item.rarity)
        self._card.set_theme(col)
        self._name.setText(item.name)
        if item.category == "item":
            cat_label = "HAND-MADE ITEM"
        elif item.category == "supply":
            cat_label = "SUPPLY"
        else:
            cat_label = {
                "mission": "ARTIFACT — MISSION REWARD",
                "shop": "ARTIFACT — BOUGHT FROM THE SHOP",
                "forge": "ARTIFACT — FORGED FROM SACRIFICE",
                "drop": "ARTIFACT — SYSTEM DROP",
            }.get(item.source, "ARTIFACT")
        self._type_caption.setText(f"{item.item_type.upper()}  |  {cat_label}")
        self._rarity.setText(item.rarity.upper())
        self._rarity.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {col};")
        if item.category == "artifact":
            # Artifacts have no level — only their upgrade level matters.
            meta = f"Upgrade +{item.upgrade_level}/{MAX_UPGRADE_LEVEL}  |  Quantity: x{item.count}"
        else:
            meta = f"Level {item.level}  |  Quantity: x{item.count}"
        self._meta.setText(meta)

        # Hand-made items keep their picture.
        if item.category == "item" and item.image_path and Path(item.image_path).exists():
            pix = QPixmap(item.image_path)
            if not pix.isNull():
                self._img_label.setPixmap(pix)
                self._img_label.show()
            else:
                self._img_label.hide()
        else:
            self._img_label.hide()

        self._desc.setText(item.description or "No description.")
        story = (item.story or "").strip()
        self._lore_caption.setVisible(bool(story))
        self._story.setText(story)

        # Bonuses panel: stats + upgrade history for artifacts.
        if item.category == "artifact":
            self._bonus_panel.show()
            self._fill_stats(item)
            self._fill_history(item)
        elif getattr(item, "stats", None):
            self._bonus_panel.show()
            self._fill_stats(item)
            self._clear_layout(self._history_box)
            self._history_caption.hide()
        else:
            self._bonus_panel.hide()

        # Supply bar (use / owned count).
        self._supply_bar.setVisible(item.category == "supply")
        if item.category == "supply":
            self._supply_owned.setText(f"Owned: x{item.count}")
            self._use_btn.setEnabled(item.count > 0)
            self._supply_status.setText("")

        self._configure_workshop(item)
        self.show()
        self.raise_()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _fill_stats(self, item):
        self._clear_layout(self._stats_box)
        stats = {k: v for k, v in (item.stats or {}).items() if v}
        if not stats:
            empty = QLabel("No bonuses.")
            empty.setStyleSheet("color: #555; font-size: 11px;")
            self._stats_box.addWidget(empty)
            return
        for key, value in stats.items():
            row = QLabel(stat_display(key, value))
            row.setStyleSheet(f"color: {CYAN}; font-size: 12px;")
            self._stats_box.addWidget(row)

    def _fill_history(self, item):
        self._clear_layout(self._history_box)
        log = [e for e in (item.upgrade_log or []) if isinstance(e, dict)]
        if not log:
            self._history_caption.hide()
            return
        self._history_caption.show()
        for i, entry in enumerate(log, start=1):
            stat = str(entry.get("stat", "")).replace("_", " ").title()
            amount = int(entry.get("amount", 0) or 0)
            cost = int(entry.get("cost", 0) or 0)
            kind = str(entry.get("tier") or ("high" if entry.get("high") else "low"))
            color = GOLD if kind == "high" else ("#b8a04a" if kind == "mid" else "#888888")
            row = QLabel(f"+{i}  {stat} +{amount}  ({kind} roll, {cost}g)")
            row.setStyleSheet(f"color: {color}; font-size: 10px;")
            self._history_box.addWidget(row)


    def _configure_workshop(self, item):
        """Update the workshop buttons for the shown artifact (or hide them)."""
        is_artifact = item.category == "artifact"
        self._workshop.setVisible(is_artifact)
        if not is_artifact:
            return
        panel = self.panel
        gold = panel._gold() if panel is not None else 0
        self._workshop_gold.setText(f"YOUR GOLD: {gold}")
        aid = _artifact_id(item)
        equipped = panel._is_equipped(aid) if panel is not None else False
        slots_used = len(equip.equipped_ids(panel.config)) if panel is not None else 0

        if equipped:
            self._equip_btn.setText("UNEQUIP")
        else:
            self._equip_btn.setText(f"EQUIP  ({slots_used}/{EQUIP_SLOTS} slots used)")
        self._equip_btn.setEnabled(True)

        gen = panel.inv_manager.generator if panel is not None and panel.inv_manager else None
        cost = gen.upgrade_cost(item.rarity, item.upgrade_level) if gen else 0
        if item.upgrade_level >= MAX_UPGRADE_LEVEL:
            self._upgrade_btn.setText("UPGRADE (MAX)")
            self._upgrade_btn.setEnabled(False)
        else:
            self._upgrade_btn.setText(f"UPGRADE  -  {cost} GOLD")
            self._upgrade_btn.setEnabled(gold >= cost)

        if item.upgrade_level > 0 and item.upgrade_log:
            last_cost = int((item.upgrade_log[-1] or {}).get("cost", 0))
            refund = gen.unupgrade_refund(item.rarity, last_cost) if gen else 0
            self._downgrade_btn.setText(f"DOWNGRADE  -  +{refund} GOLD")
            self._downgrade_btn.setEnabled(True)
        else:
            self._downgrade_btn.setText("DOWNGRADE")
            self._downgrade_btn.setEnabled(False)

        reroll_cost = gen.reroll_stats_cost(item.rarity) if gen else 0
        values_cost = gen.reroll_values_cost(item.rarity) if gen else 0
        self._reroll_stats_btn.setText(f"REROLL STATS  -  {reroll_cost} GOLD")
        self._reroll_stats_btn.setEnabled(gold >= reroll_cost)
        self._reroll_values_btn.setText(f"REROLL VALUES  -  {values_cost} GOLD")
        self._reroll_values_btn.setEnabled(gold >= values_cost)
        self._workshop_status.setText("")

    def _reload_item(self, status: str):
        """Refresh the view with the artifact's fresh db state."""
        panel = self.panel
        if panel is None or panel.inv_manager is None:
            return
        aid = _artifact_id(self.item)
        fresh = panel.inv_manager.get_artifact_by_id(aid) if aid is not None else None
        if fresh is None:
            self._close()
            return
        self.show_item(fresh, self._on_close)
        self._workshop_status.setText(status)

    def _reload_supply(self, status: str):
        """Refresh the view after using a supply; close it when the
        stash entry ran out."""
        panel = self.panel
        if panel is None or panel.inv_manager is None:
            return
        uid = str(getattr(self.item, "uid", ""))
        fresh = None
        if uid.startswith("supply:"):
            fresh = panel.inv_manager.get_supply(uid.split(":", 1)[1])
        if fresh is None or fresh.count <= 0:
            self._close()
            return
        self.show_item(fresh, self._on_close)
        self._supply_status.setText(status)

    # --- workshop actions (delegated to the panel) ---
    def _on_equip(self):
        if self.panel is not None:
            self._reload_item(self.panel.workshop_equip(self.item))

    def _on_upgrade(self):
        if self.panel is not None:
            self._reload_item(self.panel.workshop_upgrade(self.item))

    def _on_downgrade(self):
        if self.panel is not None:
            self._reload_item(self.panel.workshop_downgrade(self.item))

    def _on_reroll_stats(self):
        if self.panel is not None:
            self._reload_item(self.panel.workshop_reroll_stats(self.item))

    def _on_reroll_values(self):
        if self.panel is not None:
            self._reload_item(self.panel.workshop_reroll_values(self.item))

    def _on_use_supply(self):
        if self.panel is not None:
            self._reload_supply(self.panel.workshop_use_supply(self.item))

    def _close(self):
        self.hide()
        if self._on_close:
            self._on_close()


class InventoryPanel(QWidget):
    """Tabbed inventory grid: Items | Artifacts, with the equip bar and
    the artifact workshop."""

    gold_changed = Signal()
    stats_changed = Signal()

    def __init__(self, inv_manager, config=None, parent=None):
        super().__init__(parent)
        self.inv_manager = inv_manager
        self.config = config
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("")
        title.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {WHITE}; letter-spacing: 3px;")
        layout.addWidget(title)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        layout.addWidget(line)

        tabs = QHBoxLayout()
        tabs.setSpacing(12)
        self._btn_items = QPushButton("ITEMS")
        self._btn_artifacts = QPushButton("ARTIFACTS")
        self._btn_supplies = QPushButton("SUPPLIES")
        for btn in (self._btn_items, self._btn_artifacts, self._btn_supplies):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(button_style(CYAN, active=False))
        self._btn_items.clicked.connect(lambda: self._switch_tab("items"))
        self._btn_artifacts.clicked.connect(lambda: self._switch_tab("artifacts"))
        self._btn_supplies.clicked.connect(lambda: self._switch_tab("supplies"))
        tabs.addWidget(self._btn_items)
        tabs.addWidget(self._btn_artifacts)
        tabs.addWidget(self._btn_supplies)
        tabs.addStretch()
        layout.addLayout(tabs)

        # --- equip bar (artifacts tab only): the 5 equipment slots ---
        self._equip_bar = QWidget()
        self._equip_bar.setStyleSheet("background: transparent; border: none;")
        equip_layout = QVBoxLayout(self._equip_bar)
        equip_layout.setContentsMargins(0, 0, 0, 0)
        equip_layout.setSpacing(8)
        self._equip_caption = QLabel("EQUIPPED")
        self._equip_caption.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: bold; letter-spacing: 3px;")
        equip_layout.addWidget(self._equip_caption)
        self._equip_row = QHBoxLayout()
        self._equip_row.setSpacing(10)
        equip_layout.addLayout(self._equip_row)
        self._equip_hint = QLabel("Click a slot to unequip. Only equipped artifacts apply their stats.")
        self._equip_hint.setStyleSheet("color: #666; font-size: 10px;")
        equip_layout.addWidget(self._equip_hint)
        layout.addWidget(self._equip_bar)

        # --- sacrifice / forge bar (artifacts tab only) ---
        self._sacrifice_mode = False
        self._selected_uids: set = set()
        self._current_artifacts: list = []

        forge_row = QHBoxLayout()
        forge_row.setSpacing(12)
        self._sacrifice_btn = QPushButton("SACRIFICE")
        self._sacrifice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sacrifice_btn.setStyleSheet(button_style(GOLD, active=False))
        self._sacrifice_btn.clicked.connect(self._toggle_sacrifice)

        forge_row.addWidget(self._sacrifice_btn)
        self._forge_lbl = QLabel(f"Fuse {SACRIFICE_PER_FUSION} artifacts of one rarity into 1 of the next rank.")
        self._forge_lbl.setStyleSheet("color: #888; font-size: 11px;")
        forge_row.addWidget(self._forge_lbl, 1)

        self._forge_btn = QPushButton("FORGE")
        self._forge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._forge_btn.setEnabled(False)
        self._forge_btn.setStyleSheet(button_style(GOLD))
        self._forge_btn.clicked.connect(self._forge_selected)
        forge_row.addWidget(self._forge_btn)

        self._forge_bar = QWidget()
        self._forge_bar.setLayout(forge_row)
        layout.addWidget(self._forge_bar)


        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, 1)

        self._tab = "items"
        self._detail = InventoryDetailView(self, self)
        self._detail.hide()

        title.setText("INVENTORY")
        self._switch_tab("items")

    # --- gold / equip state ---
    def _gold(self) -> int:
        try:
            return max(0, int(self.config.get("player", "gold", 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _add_gold(self, amount: int):
        if self.config is not None:
            self.config.set("player", "gold", max(0, self._gold() + int(amount)))
            self.gold_changed.emit()

    def _is_equipped(self, artifact_id) -> bool:
        return self.config is not None and equip.is_equipped(self.config, artifact_id)

    def _equipped_ids(self) -> list:
        return equip.equipped_ids(self.config) if self.config is not None else []

    def setGeometry(self, x, y, w, h):
        super().setGeometry(x, y, w, h)
        self._detail.setGeometry(0, 0, w, h)

    def resizeEvent(self, event):
        self._detail.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def refresh(self):
        self._switch_tab(self._tab)

    def _switch_tab(self, tab: str):
        self._tab = tab
        active = button_style(CYAN)
        inactive = button_style(CYAN, active=False)

        if tab == "supplies":
            items = [
                s for s in (self.inv_manager.get_supplies() if self.inv_manager else [])
                if s.count > 0
            ]
            self._btn_items.setStyleSheet(inactive)
            self._btn_artifacts.setStyleSheet(inactive)
            self._btn_supplies.setStyleSheet(active)
            self._forge_bar.hide()
            self._equip_bar.hide()
            self._current_artifacts = []
            self._rebuild_equip_bar([])
        elif tab == "items":
            items = self.inv_manager.scan_items() if self.inv_manager else []
            self._btn_items.setStyleSheet(active)
            self._btn_artifacts.setStyleSheet(inactive)
            self._btn_supplies.setStyleSheet(inactive)
            self._forge_bar.hide()
            self._equip_bar.hide()
            self._current_artifacts = []
            self._rebuild_equip_bar([])
        else:
            items = self.inv_manager.get_artifacts() if self.inv_manager else []
            self._btn_items.setStyleSheet(inactive)
            self._btn_artifacts.setStyleSheet(active)
            self._btn_supplies.setStyleSheet(inactive)
            self._forge_bar.show()
            self._equip_bar.show()
            self._current_artifacts = items
            self._prune_equipped(items)
            self._rebuild_equip_bar(self._equipped_items())

        while self._grid.count():
            it = self._grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not items:
            empty = QLabel("Nothing here yet.")
            empty.setStyleSheet("color: #555; font-size: 14px; padding: 20px;")
            self._grid.addWidget(empty, 0, 0)
            self._update_forge_state()
            return

        equipped = set(self._equipped_ids())
        cols = max(1, self.width() // 220)
        for i, itm in enumerate(items):
            selected = self._sacrifice_mode and itm.uid in self._selected_uids
            aid = _artifact_id(itm)
            card = InventoryCard(
                itm, on_click=self._open_detail, selected=selected,
                equipped=aid is not None and aid in equipped,
            )
            self._grid.addWidget(card, i // cols, i % cols)
        self._update_forge_state()


    # --- equipment slots ---
    def _equipped_items(self) -> list:
        if self.inv_manager is None:
            return []
        return self.inv_manager.get_equipped_artifacts(self._equipped_ids())

    def _prune_equipped(self, items):
        """Drop equipped ids that no longer exist (revoked mission rewards)."""
        if self.config is None or self.inv_manager is None:
            return
        existing = [_artifact_id(it) for it in items]
        existing = [aid for aid in existing if aid is not None]
        equip.prune_equipped(self.config, existing)

    def _rebuild_equip_bar(self, equipped_items):
        while self._equip_row.count():
            it = self._equip_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        used_ids = [_artifact_id(it) for it in equipped_items]
        by_id = {aid: it for aid, it in zip(used_ids, equipped_items)}
        for slot in range(EQUIP_SLOTS):
            box = QPushButton()
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            box.setMinimumHeight(44)
            aid = used_ids[slot] if slot < len(used_ids) else None
            item = by_id.get(aid)
            if item is not None:
                col = _rarity_border(item.rarity)
                box.setText(f"{slot + 1}. {item.name} ({item.rarity})")
                box.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {col}18;
                        border: 1px solid {col};
                        color: {WHITE};
                        font-size: 11px;
                        border-radius: 4px;
                        padding: 4px 8px;
                        text-align: left;
                    }}
                    QPushButton:hover {{ border: 2px solid {GOLD}; }}
                """)
                box.clicked.connect(lambda _=False, a=aid: self._unequip_id(a))
            else:
                box.setText(f"{slot + 1}. EMPTY SLOT")
                box.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(16,16,22,160);
                        border: 1px dashed #333;
                        color: #555;
                        font-size: 11px;
                        border-radius: 4px;
                        padding: 4px 8px;
                    }
                """)
                box.setEnabled(False)
            self._equip_row.addWidget(box, 1)
        self._equip_caption.setText(f"EQUIPPED  {len(equipped_items)}/{EQUIP_SLOTS}")

    def _unequip_id(self, artifact_id):
        if self.config is not None:
            equip.unequip(self.config, artifact_id)
            self.stats_changed.emit()
        self._switch_tab(self._tab)

    def _open_detail(self, item):
        if self._sacrifice_mode and self._tab == "artifacts":
            self._toggle_select(item)
            return
        self._detail.show_item(item, on_close=lambda: self._detail.hide())


    # --- sacrifice / forge ---
    def _toggle_sacrifice(self):
        self._sacrifice_mode = not self._sacrifice_mode
        self._selected_uids.clear()
        if self._sacrifice_mode:
            self._sacrifice_btn.setText("CANCEL")
            self._sacrifice_btn.setStyleSheet(button_style(GOLD))
        else:
            self._sacrifice_btn.setText("SACRIFICE")
            self._sacrifice_btn.setStyleSheet(button_style(GOLD, active=False))
        self._switch_tab(self._tab)

    def _toggle_select(self, item):
        if item.uid in self._selected_uids:
            self._selected_uids.discard(item.uid)
        else:
            self._selected_uids.add(item.uid)
        self._switch_tab(self._tab)

    def _update_forge_state(self):
        by_uid = {it.uid: it for it in self._current_artifacts}
        chosen = [by_uid[u] for u in self._selected_uids if u in by_uid]
        rarities = {it.rarity for it in chosen}
        valid = False
        if (self._sacrifice_mode and len(chosen) == SACRIFICE_PER_FUSION
                and len(rarities) == 1):
            if next(iter(rarities)) != RARITIES[-1]:
                valid = True
        self._forge_btn.setEnabled(valid)
        if not self._sacrifice_mode:
            self._forge_lbl.setText(
                f"Fuse {SACRIFICE_PER_FUSION} artifacts of one rarity into 1 of the next rank."
            )
        elif not chosen:
            self._forge_lbl.setText(f"Select {SACRIFICE_PER_FUSION} artifacts of the same rarity.")
        elif len(rarities) == 1:
            rarity = next(iter(rarities))
            suffix = " - Mythic cannot be fused." if rarity == RARITIES[-1] else ""
            self._forge_lbl.setText(
                f"Selected {len(chosen)}/{SACRIFICE_PER_FUSION} - {rarity}{suffix}"
            )
        else:
            self._forge_lbl.setText("All sacrificed artifacts must share one rarity.")

    def _forge_selected(self):
        if self.inv_manager is None:
            return
        ids = []
        for uid in self._selected_uids:
            if uid.startswith("artifact:"):
                try:
                    ids.append(int(uid.split(":", 1)[1]))
                except ValueError:
                    pass
        # Forged artifacts are consumed - take them off the loadout first.
        if self.config is not None:
            for aid in ids:
                equip.unequip(self.config, aid)
            if ids:
                self.stats_changed.emit()
        result = self.inv_manager.sacrifice_artifacts(ids)
        self._selected_uids.clear()
        self._switch_tab(self._tab)
        if result is None:
            self._forge_lbl.setText("Forge failed - need 3 of one non-Mythic rarity.")
        else:
            audio.play("forge")
            self._forge_lbl.setText(f"FORGED: {result.name} ({result.rarity}) - check your inventory.")


    # --- workshop actions (called by the detail view) ---
    def workshop_equip(self, item) -> str:
        aid = _artifact_id(item)
        if self.config is None or aid is None:
            return "Only artifacts can be equipped."
        if equip.is_equipped(self.config, aid):
            equip.unequip(self.config, aid)
            self.stats_changed.emit()
            audio.play("equip")
            self._switch_tab(self._tab)
            return "Unequipped - its stats no longer apply."
        if equip.equip(self.config, aid):
            self.stats_changed.emit()
            audio.play("equip")
            self._switch_tab(self._tab)
            return f"Equipped ({len(self._equipped_ids())}/{EQUIP_SLOTS} slots)."
        return f"No free slot - only {EQUIP_SLOTS} artifacts can be equipped at once."

    def workshop_upgrade(self, item) -> str:
        aid = _artifact_id(item)
        if self.inv_manager is None or aid is None:
            return "Upgrades only apply to artifacts."
        fresh = self.inv_manager.get_artifact_by_id(aid)
        if fresh is None:
            return "Artifact not found."
        if fresh.upgrade_level >= MAX_UPGRADE_LEVEL:
            return f"Already at the maximum upgrade level (+{MAX_UPGRADE_LEVEL})."
        cost = self.inv_manager.generator.upgrade_cost(fresh.rarity, fresh.upgrade_level)
        if self._gold() < cost:
            return f"Not enough gold - this upgrade costs {cost} gold."
        result = self.inv_manager.upgrade_artifact(aid)
        if result is None:
            return "Upgrade failed."
        self._add_gold(-cost)
        kind = str(result.get("tier") or ("high" if result.get("high") else "low"))
        audio.play("upgrade")
        status = f"+{result['amount']} {result['stat'].replace('_', ' ').title()} ({kind} roll) for {cost} gold."
        if result["item"] is not None and result["item"].upgrade_level >= MAX_UPGRADE_LEVEL:
            audio.play("upgrade_max")
            status += f"  MAX upgrade level (+{MAX_UPGRADE_LEVEL}) reached!"
        if self.config is not None and equip.is_equipped(self.config, aid):
            self.stats_changed.emit()
        self._switch_tab(self._tab)
        return status

    def workshop_downgrade(self, item) -> str:
        aid = _artifact_id(item)
        if self.inv_manager is None or aid is None:
            return "Upgrades only apply to artifacts."
        result = self.inv_manager.unupgrade_artifact(aid)
        if result is None:
            return "Nothing to take back off."
        self._add_gold(result["refund"])
        audio.play("refund")
        if self.config is not None and equip.is_equipped(self.config, aid):
            self.stats_changed.emit()
        self._switch_tab(self._tab)
        return f"Last upgrade removed - {result['refund']} gold refunded."

    def workshop_reroll_stats(self, item) -> str:
        aid = _artifact_id(item)
        if self.inv_manager is None or aid is None:
            return "Rerolls only apply to artifacts."
        fresh = self.inv_manager.get_artifact_by_id(aid)
        if fresh is None:
            return "Artifact not found."
        cost = self.inv_manager.generator.reroll_stats_cost(fresh.rarity)
        if self._gold() < cost:
            return f"Not enough gold - rerolling the stats costs {cost} gold."
        if self.inv_manager.reroll_artifact_stats(aid) is None:
            return "Reroll failed."
        self._add_gold(-cost)
        audio.play("reroll")
        if self.config is not None and equip.is_equipped(self.config, aid):
            self.stats_changed.emit()
        self._switch_tab(self._tab)
        return f"Stat types fully rerolled for {cost} gold - upgrades were reset."

    def workshop_reroll_values(self, item) -> str:
        aid = _artifact_id(item)
        if self.inv_manager is None or aid is None:
            return "Rerolls only apply to artifacts."
        fresh = self.inv_manager.get_artifact_by_id(aid)
        if fresh is None:
            return "Artifact not found."
        cost = self.inv_manager.generator.reroll_values_cost(fresh.rarity)
        if self._gold() < cost:
            return f"Not enough gold - rerolling the values costs {cost} gold."
        if self.inv_manager.reroll_artifact_values(aid) is None:
            return "Reroll failed."
        self._add_gold(-cost)
        audio.play("reroll")
        if self.config is not None and equip.is_equipped(self.config, aid):
            self.stats_changed.emit()
        self._switch_tab(self._tab)
        return (
            f"Values re-rolled for {cost} gold - the stat types and upgrade level "
            f"(+{fresh.upgrade_level}) stayed, every upgrade was rolled fresh."
        )

    def workshop_use_supply(self, item) -> str:
        """Consume one unit of a supply from the stash."""
        if self.inv_manager is None:
            return "Supplies are unavailable."
        uid = str(getattr(item, "uid", ""))
        if not uid.startswith("supply:"):
            return "Only supplies can be used."
        supply_id = uid.split(":", 1)[1]
        name = getattr(item, "name", "The supply")
        fresh = self.inv_manager.consume_supply(supply_id)
        self._switch_tab(self._tab)
        audio.play("click")
        if fresh is None or fresh.count <= 0:
            return f"{name} used - none left."
        return f"{name} used - x{fresh.count} remaining."

