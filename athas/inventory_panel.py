"""
Inventory Panel -- tabbed grid of Items (JSON) and Artifacts (DB), plus the
artifact workshop.

Artifacts no longer use pictures: their cards show the rolled stat lines
directly. Only EQUIPPED artifacts (5 slots) apply their stats to the
character. From the artifact detail view you can equip/unequip, UPGRADE
(a low/high roll into a random stat, max level 20), DOWNGRADE for a partial
gold refund, REROLL the stat types entirely, or reroll only where the
numbers went while keeping the stats.
"""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QWidget,
)
from PySide6.QtGui import QPixmap

try:
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # headless / test environments
    QSoundEffect = None

from athas.styles import CYAN, WHITE, GOLD
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

        meta_bits = [f"Lv.{item.level}"]
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

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.item)
        super().mousePressEvent(event)



class InventoryDetailView(QFrame):
    """Full overlay panel: item details plus the artifact workshop buttons."""

    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self.panel = panel
        self.setStyleSheet(f"""
            QFrame {{ background-color: rgba(5,5,8,245); border: 1px solid {CYAN}44; }}
            QLabel {{ background: transparent; border: none; color: {WHITE}; }}
            QPushButton {{
                background-color: {CYAN}11; border: 1px solid {CYAN}; color: {CYAN};
                padding: 6px 14px; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {CYAN}; color: #000; }}
            QPushButton:disabled {{ color: #555; border-color: #333; background: transparent; }}
        """)
        self.hide()
        self.item = None
        self._on_close = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self._img_label = QLabel()
        self._img_label.setFixedSize(120, 120)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setScaledContents(True)
        self._img_label.setStyleSheet("border: 2px solid #222; border-radius: 4px;")
        self._img_label.hide()
        header.addWidget(self._img_label)

        txt = QVBoxLayout()
        self._name = QLabel("")
        self._name.setStyleSheet("font-size: 24px; font-weight: bold; color: #fff;")
        txt.addWidget(self._name)
        self._type = QLabel("")
        self._type.setStyleSheet(f"font-size: 13px; color: {CYAN};")
        txt.addWidget(self._type)
        self._rarity = QLabel("")
        self._rarity.setStyleSheet("font-size: 12px; color: #aaa;")
        txt.addWidget(self._rarity)
        self._meta = QLabel("")
        self._meta.setStyleSheet("font-size: 11px; color: #777;")
        txt.addWidget(self._meta)
        header.addLayout(txt, 1)

        back = QPushButton("BACK")
        back.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: 1px solid {CYAN}44;
                color: {CYAN}; padding: 4px 10px;
            }}
            QPushButton:hover {{ background-color: {CYAN}22; }}
        """)
        back.clicked.connect(self._close)
        header.addWidget(back, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        layout.addWidget(line)

        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("font-size: 14px; color: #ccc; padding-top: 8px;")
        layout.addWidget(self._desc)

        self._story = QLabel("")
        self._story.setWordWrap(True)
        self._story.setStyleSheet("font-size: 14px; color: #bbb; padding-top: 8px;")
        layout.addWidget(self._story, 1)

        self._stats = QLabel("")
        self._stats.setWordWrap(True)
        self._stats.setStyleSheet(f"font-size: 12px; color: {CYAN}; padding-top: 10px;")
        layout.addWidget(self._stats)

        # --- workshop buttons (artifacts only) ---
        self._workshop = QWidget()
        self._workshop.setStyleSheet("background: transparent; border: none;")
        wl = QVBoxLayout(self._workshop)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(10)

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



    # --- showing an item ---
    def show_item(self, item, on_close):
        self.item = item
        self._on_close = on_close
        self._name.setText(item.name)
        if item.category == "item":
            cat_label = "Hand-Made Item"
        else:
            cat_label = {
                "mission": "Artifact - Mission Reward",
                "shop": "Artifact - Bought from the Shop",
                "forge": "Artifact - Forged from Sacrifice",
            }.get(item.source, "Artifact")
        self._type.setText(f"Type: {item.item_type}  |  {cat_label}")
        self._rarity.setText(f"Rarity: {item.rarity}")
        meta = f"Level {item.level}  |  Quantity: {item.count}"
        if item.category == "artifact":
            meta += f"  |  Upgrade +{item.upgrade_level}/{MAX_UPGRADE_LEVEL}"
        self._meta.setText(meta)
        self._desc.setText(item.description or "No description.")
        self._story.setText(item.story or "")
        if item.category == "artifact":
            self._stats.setText(_stat_lines(item))
            self._img_label.hide()
        else:
            self._stats.setText("")
            self._img_label.hide()
            if item.image_path and Path(item.image_path).exists():
                pix = QPixmap(item.image_path)
                if not pix.isNull():
                    self._img_label.setPixmap(pix)
                    self._img_label.show()
            if item.stats:
                self._stats.setText("Stats: " + "  |  ".join(
                    stat_display(k, v) for k, v in item.stats.items() if v
                ))
        self._configure_workshop(item)
        self.show()
        self.raise_()

    def _configure_workshop(self, item):
        """Update the workshop buttons for the shown artifact (or hide them)."""
        is_artifact = item.category == "artifact"
        self._workshop.setVisible(is_artifact)
        if not is_artifact:
            return
        panel = self.panel
        gold = panel._gold() if panel is not None else 0
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
        for btn in (self._btn_items, self._btn_artifacts):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {CYAN}44;
                    color: #aaa;
                    padding: 6px 20px;
                }}
                QPushButton:hover {{ color: {CYAN}; border-color: {CYAN}; }}
            """)
        self._btn_items.clicked.connect(lambda: self._switch_tab("items"))
        self._btn_artifacts.clicked.connect(lambda: self._switch_tab("artifacts"))
        tabs.addWidget(self._btn_items)
        tabs.addWidget(self._btn_artifacts)
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
        self._sacrifice_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {GOLD}44;
                color: #aaa;
                padding: 6px 20px;
            }}
            QPushButton:hover {{ color: {GOLD}; border-color: {GOLD}; }}
        """)
        self._sacrifice_btn.clicked.connect(self._toggle_sacrifice)

        forge_row.addWidget(self._sacrifice_btn)
        self._forge_lbl = QLabel(f"Fuse {SACRIFICE_PER_FUSION} artifacts of one rarity into 1 of the next rank.")
        self._forge_lbl.setStyleSheet("color: #888; font-size: 11px;")
        forge_row.addWidget(self._forge_lbl, 1)

        self._forge_btn = QPushButton("FORGE")
        self._forge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._forge_btn.setEnabled(False)
        self._forge_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {GOLD}11;
                border: 1px solid {GOLD}66;
                color: {GOLD};
                padding: 6px 20px;
                font-weight: bold;
                border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {GOLD}; color: #0a0a0a; }}
            QPushButton:disabled {{ color: #555; border-color: #333; background: transparent; }}
        """)
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

        self._sounds = {}
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

    # --- sounds (best effort) ---
    def _play_sound(self, filename: str):
        if QSoundEffect is None:
            return
        try:
            effect = self._sounds.get(filename)
            if effect is None:
                from PySide6.QtCore import QUrl
                path = Path(__file__).parent.parent / "sounds" / filename
                if not path.exists():
                    return
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(0.3)
                self._sounds[filename] = effect
            effect.play()
        except Exception:
            pass

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
        active = f"""
            QPushButton {{
                background-color: {CYAN}22;
                border: 1px solid {CYAN};
                color: {CYAN};
                padding: 6px 20px;
            }}
        """
        inactive = f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {CYAN}44;
                color: #aaa;
                padding: 6px 20px;
            }}
            QPushButton:hover {{ color: {CYAN}; border-color: {CYAN}; }}
        """

        if tab == "items":
            items = self.inv_manager.scan_items() if self.inv_manager else []
            self._btn_items.setStyleSheet(active)
            self._btn_artifacts.setStyleSheet(inactive)
            self._forge_bar.hide()
            self._equip_bar.hide()
            self._current_artifacts = []
            self._rebuild_equip_bar([])
        else:
            items = self.inv_manager.get_artifacts() if self.inv_manager else []
            self._btn_items.setStyleSheet(inactive)
            self._btn_artifacts.setStyleSheet(active)
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
            self._sacrifice_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {GOLD}22;
                    border: 1px solid {GOLD};
                    color: {GOLD};
                    padding: 6px 20px;
                }}
            """)
        else:
            self._sacrifice_btn.setText("SACRIFICE")
            self._sacrifice_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {GOLD}44;
                    color: #aaa;
                    padding: 6px 20px;
                }}
                QPushButton:hover {{ color: {GOLD}; border-color: {GOLD}; }}
            """)
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
            self._forge_lbl.setText(f"FORGED: {result.name} ({result.rarity}) - check your inventory.")


    # --- workshop actions (called by the detail view) ---
    def workshop_equip(self, item) -> str:
        aid = _artifact_id(item)
        if self.config is None or aid is None:
            return "Only artifacts can be equipped."
        if equip.is_equipped(self.config, aid):
            equip.unequip(self.config, aid)
            self.stats_changed.emit()
            self._switch_tab(self._tab)
            return "Unequipped - its stats no longer apply."
        if equip.equip(self.config, aid):
            self.stats_changed.emit()
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
        kind = "HIGH" if result["high"] else "low"
        self._play_sound("upgrade_artifact_sound.wav")
        status = f"+{result['amount']} {result['stat'].replace('_', ' ').title()} ({kind} roll) for {cost} gold."
        if result["item"] is not None and result["item"].upgrade_level >= MAX_UPGRADE_LEVEL:
            self._play_sound("upgrade_artifact_level_up.wav")
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
        if self.config is not None and equip.is_equipped(self.config, aid):
            self.stats_changed.emit()
        self._switch_tab(self._tab)
        return (
            f"Values re-rolled for {cost} gold - the stat types stayed, "
            f"upgrades were reset."
        )

