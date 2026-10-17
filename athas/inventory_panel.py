"""
Inventory Panel -- tabbed grid of Items (JSON) and Artifacts (DB).
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QWidget,
)
from PySide6.QtGui import QPixmap

from athas.styles import CYAN, WHITE, GOLD
from athas.inventory_manager import InventoryItem


RARITY_COLORS = {
    "Common": "#888888", "Uncommon": "#4caf50", "Rare": "#2196f3",
    "Epic": "#9c27b0", "Legendary": "#ff9800", "Mythic": GOLD,
}


def _rarity_border(rarity: str) -> str:
    return RARITY_COLORS.get(rarity, CYAN)


class InventoryCard(QFrame):
    def __init__(self, item: InventoryItem, on_click=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        col = _rarity_border(item.rarity)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(10,10,10,200);
                border: 1px solid {col}44;
                border-radius: 4px;
            }}
            QFrame:hover {{
                background-color: rgba(20,20,30,220);
                border: 1px solid {col};
            }}
        """)
        self.setMinimumSize(160, 200)
        self.setMaximumSize(200, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

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

        type_badge = QLabel(item.item_type.upper())
        type_badge.setStyleSheet(f"font-size: 9px; color: {col}; font-weight: bold; background: transparent;")
        type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(type_badge)

        name = QLabel(item.name)
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; background: transparent;")
        layout.addWidget(name)

        rar = QLabel(item.rarity)
        rar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rar.setStyleSheet(f"font-size: 10px; color: {col}; background: transparent;")
        layout.addWidget(rar)

        meta = QLabel(f"Lv.{item.level}  x{item.count}")
        meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta.setStyleSheet("font-size: 9px; color: #666; background: transparent;")
        layout.addWidget(meta)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.item)
        super().mousePressEvent(event)


class InventoryDetailView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{ background-color: rgba(5,5,8,245); border: 1px solid {CYAN}44; }}
            QLabel {{ background: transparent; border: none; color: {WHITE}; }}
            QPushButton {{
                background-color: {CYAN}11; border: 1px solid {CYAN}; color: {CYAN};
                padding: 6px 14px; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {CYAN}; color: #000; }}
        """)
        self.hide()
        self.item = None
        self._on_close = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        header = QHBoxLayout()
        self._img_label = QLabel()
        self._img_label.setFixedSize(120, 120)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setScaledContents(True)
        self._img_label.setStyleSheet("border: 2px solid #222; border-radius: 4px;")
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

        back = QPushButton("← BACK")
        back.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: 1px solid {CYAN}44;
                color: {CYAN}; padding: 4px 10px;
            }}
            QPushButton:hover {{ background-color: {CYAN}22; }}
        """)
        back.clicked.connect(self._close)
        header.addWidget(back)
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
        self._stats.setStyleSheet(f"font-size: 12px; color: {CYAN}; padding-top: 10px;")
        layout.addWidget(self._stats)

    def show_item(self, item, on_close):
        self.item = item
        self._on_close = on_close
        self._name.setText(item.name)
        cat_label = "Hand-Made Item" if item.category == "item" else "Auto-Generated Artifact"
        self._type.setText(f"Type: {item.item_type}  |  {cat_label}")
        self._rarity.setText(f"Rarity: {item.rarity}")
        self._meta.setText(f"Level {item.level}  |  Quantity: {item.count}")
        self._desc.setText(item.description or "No description.")
        self._story.setText(item.story or "")
        if item.stats:
            stats_str = "  |  ".join(f"{k.title()}: +{v}" for k, v in item.stats.items() if v)
            self._stats.setText(f"Stats: {stats_str}")
        else:
            self._stats.setText("Stats: None")

        if item.image_path and Path(item.image_path).exists():
            pix = QPixmap(item.image_path)
            if not pix.isNull():
                self._img_label.setPixmap(pix)
        else:
            self._img_label.setText("[image]")
        self.show()
        self.raise_()

    def _close(self):
        self.hide()
        if self._on_close:
            self._on_close()

class InventoryPanel(QWidget):
    """Tabbed inventory grid: Items | Artifacts."""
    def __init__(self, inv_manager, parent=None):
        super().__init__(parent)
        self.inv_manager = inv_manager
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
        self._detail = InventoryDetailView(self)
        self._detail.hide()

        title.setText("INVENTORY")
        self._switch_tab("items")

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
        else:
            items = self.inv_manager.get_artifacts() if self.inv_manager else []
            self._btn_items.setStyleSheet(inactive)
            self._btn_artifacts.setStyleSheet(active)

        while self._grid.count():
            it = self._grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not items:
            empty = QLabel("Nothing here yet.")
            empty.setStyleSheet("color: #555; font-size: 14px; padding: 20px;")
            self._grid.addWidget(empty, 0, 0)
            return

        cols = max(1, self.width() // 220)
        for i, itm in enumerate(items):
            card = InventoryCard(itm, on_click=self._open_detail)
            self._grid.addWidget(card, i // cols, i % cols)

    def _open_detail(self, item):
        self._detail.show_item(item, on_close=lambda: self._detail.hide())

