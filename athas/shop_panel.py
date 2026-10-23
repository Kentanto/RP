"""
Shop Panel — the System Shop.

Sells auto-generated artifacts for gold. The stock lives in the SQLite
inventory database (shop_stock table), so it persists and syncs like the
rest of the inventory. Buying moves the artifact from the shelves into the
player's artifact inventory.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea,
)

from athas.styles import CYAN, WHITE, GOLD
from athas.inventory_panel import RARITY_COLORS


def _rarity_color(rarity: str) -> str:
    return RARITY_COLORS.get(rarity, CYAN)


class ShopCard(QFrame):
    """One shelf card: the artifact for sale with its price and BUY button."""

    def __init__(self, entry: dict, affordable: bool, on_buy, parent=None):
        super().__init__(parent)
        self.entry = entry
        col = _rarity_color(entry.get("rarity", ""))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.setMinimumSize(180, 240)
        self.setMaximumSize(220, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        type_badge = QLabel(entry.get("item_type", "Artifact").upper())
        type_badge.setStyleSheet(
            f"font-size: 9px; color: {col}; font-weight: bold; background: transparent; border: none;"
        )
        top.addWidget(type_badge)
        top.addStretch()
        lvl = QLabel(f"Lv.{entry.get('level', 1)}")
        lvl.setStyleSheet("font-size: 9px; color: #666; background: transparent; border: none;")
        top.addWidget(lvl)
        layout.addLayout(top)

        name = QLabel(entry.get("name", "Unknown"))
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #ffffff; background: transparent; border: none;"
        )
        layout.addWidget(name)

        rar = QLabel(entry.get("rarity", "Common"))
        rar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rar.setStyleSheet(f"font-size: 10px; color: {col}; background: transparent; border: none;")
        layout.addWidget(rar)

        stat_lines = [f"{k.title()} +{v}" for k, v in (entry.get("stats") or {}).items() if v]
        stats_lbl = QLabel("\n".join(stat_lines) if stat_lines else "No bonuses")
        stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_lbl.setStyleSheet(f"font-size: 10px; color: {CYAN}; background: transparent; border: none;")
        layout.addWidget(stats_lbl)

        layout.addStretch()

        price = QLabel(f"{entry.get('price', 0)} GOLD")
        price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {GOLD}; background: transparent; border: none;"
        )
        layout.addWidget(price)

        buy = QPushButton("BUY")
        buy.setCursor(Qt.CursorShape.PointingHandCursor)
        buy.setStyleSheet(f"""
            QPushButton {{
                background-color: {CYAN}11; border: 1px solid {CYAN}44;
                color: {CYAN}; padding: 6px; font-weight: bold; border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: {CYAN}33; }}
            QPushButton:disabled {{ color: #555; border-color: #333; background: transparent; }}
        """)
        buy.setEnabled(affordable)
        buy.clicked.connect(lambda _=False: on_buy(entry))
        layout.addWidget(buy)

class ShopPanel(QWidget):
    """Grid of for-sale artifacts with a gold balance and a restock button."""

    gold_changed = Signal()

    def __init__(self, config, inv_manager, parent=None):
        super().__init__(parent)
        self.config = config
        self.inv_manager = inv_manager
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header = QLabel("SYSTEM SHOP")
        header.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {WHITE}; letter-spacing: 3px;")
        header_row.addWidget(header)
        header_row.addStretch()

        self._gold_lbl = QLabel("GOLD 0")
        self._gold_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {GOLD};")
        header_row.addWidget(self._gold_lbl)

        restock = QPushButton("RESTOCK")
        restock.setCursor(Qt.CursorShape.PointingHandCursor)
        restock.setStyleSheet(f"""
            QPushButton {{
                background-color: {CYAN}11; border: 1px solid {CYAN};
                color: {CYAN}; padding: 8px 20px; border-radius: 2px;
                font-size: 12px; letter-spacing: 2px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {CYAN}; color: #0a0a0a; }}
        """)
        restock.clicked.connect(self._restock)
        header_row.addWidget(restock)
        layout.addLayout(header_row)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        layout.addWidget(line)

        self._status = QLabel("Spend gold earned from missions. RESTOCK rerolls the shelves.")
        self._status.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self._status)

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

    # ── helpers ──
    def _player_gold(self) -> int:
        try:
            return max(0, int(self.config.get("player", "gold", 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _player_level(self) -> int:
        try:
            return max(1, int(self.config.get("player", "level", 1) or 1))
        except (TypeError, ValueError):
            return 1

    def refresh_gold(self):
        self._gold_lbl.setText(f"GOLD {self._player_gold()}")

    def refresh(self):
        self.refresh_gold()
        stock = self.inv_manager.get_shop_stock() if self.inv_manager else []
        if not stock and self.inv_manager is not None:
            # First run — fill the shelves automatically.
            self.inv_manager.restock_shop(player_level=self._player_level())
            stock = self.inv_manager.get_shop_stock()
        gold = self._player_gold()

        while self._grid.count():
            it = self._grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not stock:
            empty = QLabel("The shop shelves are empty.")
            empty.setStyleSheet("color: #555; font-size: 14px; padding: 20px;")
            self._grid.addWidget(empty, 0, 0)
            return

        cols = max(1, self.width() // 240)
        for i, entry in enumerate(stock):
            try:
                affordable = gold >= int(entry.get("price", 0) or 0)
            except (TypeError, ValueError):
                affordable = False
            card = ShopCard(entry, affordable=affordable, on_buy=self._buy)
            self._grid.addWidget(card, i // cols, i % cols)

    def _buy(self, entry: dict):
        if self.inv_manager is None:
            return
        try:
            price = int(entry.get("price", 0) or 0)
        except (TypeError, ValueError):
            return
        gold = self._player_gold()
        if gold < price:
            self._status.setText(f"Not enough gold — {entry.get('name')} costs {price} gold.")
            return
        item = self.inv_manager.buy_from_shop(entry.get("id"))
        if item is None:
            self._status.setText("That item was already sold.")
            self.refresh()
            return
        self.config.set("player", "gold", gold - price)
        self._status.setText(f"Purchased {item.name} ({item.rarity}). Check your inventory.")
        self.gold_changed.emit()
        self.refresh()

    def _restock(self):
        if self.inv_manager is None:
            return
        self.inv_manager.restock_shop(player_level=self._player_level())
        self._status.setText("The shop restocked its shelves.")
        self.refresh()