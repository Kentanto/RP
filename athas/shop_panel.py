"""
Shop Panel — the System Shop.

Sells regular supplies (bandages, medkits, healing potions, ...) for
gold — a fixed catalogue that never rerolls, plus the bulk artifact
package. Owned supply counts live in the SQLite inventory database
(supplies table), so they persist and sync like the rest of the
inventory. Buying adds to the player's stash, shown in the inventory's
SUPPLIES tab.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea,
)

from athas import audio
from athas.styles import CYAN, WHITE, GOLD, button_style


class ShopCard(QFrame):
    """One shelf card: a supply for sale with its price and BUY button."""

    def __init__(self, entry: dict, owned: int, affordable: bool, on_buy, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(10,10,10,200);
                border: 1px solid {CYAN}44;
                border-radius: 4px;
            }}
            QFrame:hover {{
                background-color: rgba(20,20,30,220);
                border: 1px solid {CYAN};
            }}
        """)
        self.setMinimumSize(180, 220)
        self.setMaximumSize(220, 280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        type_badge = QLabel("SUPPLY")
        type_badge.setStyleSheet(
            f"font-size: 9px; color: {CYAN}; font-weight: bold; background: transparent; border: none;"
        )
        top.addWidget(type_badge)
        top.addStretch()
        owned_lbl = QLabel(f"OWNED x{owned}")
        owned_lbl.setStyleSheet("font-size: 9px; color: #666; background: transparent; border: none;")
        top.addWidget(owned_lbl)
        layout.addLayout(top)

        name = QLabel(entry.get("name", "Unknown"))
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #ffffff; background: transparent; border: none;"
        )
        layout.addWidget(name)

        desc = QLabel(entry.get("description", ""))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        desc.setStyleSheet("font-size: 10px; color: #aaa; background: transparent; border: none;")
        layout.addWidget(desc, 1)

        price = QLabel(f"{entry.get('price', 0)} GOLD")
        price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {GOLD}; background: transparent; border: none;"
        )
        layout.addWidget(price)

        buy = QPushButton("BUY")
        buy.setCursor(Qt.CursorShape.PointingHandCursor)
        buy.setStyleSheet(button_style(CYAN))
        buy.setEnabled(affordable)
        buy.clicked.connect(lambda _=False: on_buy(entry))
        layout.addWidget(buy)

class ShopPanel(QWidget):
    """Grid of for-sale supplies with a gold balance and the bulk package."""

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
        layout.addLayout(header_row)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        layout.addWidget(line)

        package = QFrame()
        package.setStyleSheet(f"""
            QFrame {{
                background-color: #14110a;
                border: 1px solid {GOLD}44;
                border-radius: 4px;
            }}
        """)
        pkg_layout = QHBoxLayout(package)
        pkg_layout.setContentsMargins(16, 10, 16, 10)
        pkg_layout.setSpacing(12)
        pkg_title = QLabel("PACKAGE")
        pkg_title.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        pkg_layout.addWidget(pkg_title)
        pkg_desc = QLabel("10 x Common Artifact — fresh random gear, straight to your inventory.")
        pkg_desc.setStyleSheet("color: #ccc; font-size: 12px;")
        pkg_layout.addWidget(pkg_desc, 1)
        self._pkg_price_lbl = QLabel("— GOLD")
        self._pkg_price_lbl.setStyleSheet(f"color: {GOLD}; font-size: 13px; font-weight: bold;")
        pkg_layout.addWidget(self._pkg_price_lbl)
        self._pkg_btn = QPushButton("BUY PACKAGE")
        self._pkg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pkg_btn.setEnabled(False)
        self._pkg_btn.setStyleSheet(button_style(GOLD))
        self._pkg_btn.clicked.connect(self._buy_package)
        pkg_layout.addWidget(self._pkg_btn)
        layout.addWidget(package)

        self._status = QLabel("Spend gold earned from missions on supplies for the road ahead.")
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
        price = self.inv_manager.PACKAGE_PRICE if self.inv_manager else 0
        self._pkg_price_lbl.setText(f"{price} GOLD")
        self._pkg_btn.setEnabled(self.inv_manager is not None and self._player_gold() >= price)

        catalogue = self.inv_manager.supply_catalog() if self.inv_manager else []
        owned = self.inv_manager.get_supply_counts() if self.inv_manager else {}
        gold = self._player_gold()

        while self._grid.count():
            it = self._grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not catalogue:
            empty = QLabel("The shop shelves are empty.")
            empty.setStyleSheet("color: #555; font-size: 14px; padding: 20px;")
            self._grid.addWidget(empty, 0, 0)
            return

        cols = max(1, self.width() // 240)
        for i, entry in enumerate(catalogue):
            try:
                affordable = gold >= int(entry.get("price", 0) or 0)
            except (TypeError, ValueError):
                affordable = False
            card = ShopCard(
                entry, owned=owned.get(entry.get("id"), 0),
                affordable=affordable, on_buy=self._buy,
            )
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
        item = self.inv_manager.buy_supply(entry.get("id"))
        if item is None:
            self._status.setText("That item is no longer stocked.")
            self.refresh()
            return
        self.config.set("player", "gold", gold - price)
        audio.play("buy")
        self._status.setText(
            f"Purchased {item.name} for {price} gold — you now own x{item.count}."
        )
        self.gold_changed.emit()
        self.refresh()

    def _buy_package(self):
        if self.inv_manager is None:
            return
        price = self.inv_manager.PACKAGE_PRICE
        gold = self._player_gold()
        if gold < price:
            self._status.setText(f"Not enough gold — the package costs {price} gold.")
            return
        items = self.inv_manager.buy_common_package(player_level=self._player_level())
        if not items:
            return
        self.config.set("player", "gold", gold - price)
        audio.play("buy")
        self._status.setText(f"Package opened — {len(items)} common artifacts added to your inventory.")
        self.gold_changed.emit()
        self.refresh()
