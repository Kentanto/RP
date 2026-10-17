"""
Solo Leveling System — Settings panel built dynamically from JSON config.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QCheckBox, QSlider, QTabWidget,
)

from solo_leveling_system.styles import CYAN, BLACK, WHITE


class HoverButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class SettingsPanel(QFrame):
    """
    A tabbed settings overlay.  Each config section becomes a tab,
    each key-value pair becomes a row with an appropriate control
    (checkbox for bool, slider for number, label for string).
    Changes are written back to ``ConfigManager.set`` immediately.
    """

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("SettingsPanel")
        self.setStyleSheet(f"""
            QFrame#SettingsPanel {{
                background-color: rgba(8,8,12,245);
                border: 2px solid {CYAN}44;
                border-radius: 6px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {WHITE};
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {CYAN}22;
                border: 1px solid {CYAN};
                color: {CYAN};
                padding: 6px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {CYAN};
                color: {BLACK};
            }}
            QCheckBox {{
                color: {WHITE};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {CYAN};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CYAN};
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: #333;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                background: {CYAN};
                border-radius: 8px;
                margin: -5px 0;
            }}
            QTabWidget::pane {{
                border: 1px solid {CYAN}44;
                background: rgba(5,5,8,180);
            }}
            QTabBar::tab {{
                background: {BLACK};
                color: {WHITE};
                padding: 8px 20px;
                border: 1px solid {CYAN}22;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {CYAN}22;
                color: {CYAN};
                border-bottom: 2px solid {CYAN};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)

        # Header row
        header_row = QHBoxLayout()
        header = QLabel("SYSTEM SETTINGS")
        header.setStyleSheet(
            f"color: {CYAN}; font-size: 20px; font-weight: bold; letter-spacing: 3px;"
        )
        header_row.addWidget(header)
        header_row.addStretch()

        close = HoverButton("CLOSE")
        close.clicked.connect(self.hide)
        header_row.addWidget(close)
        outer.addLayout(header_row)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        outer.addWidget(line)

        # Tabs
        tabs = QTabWidget()
        self._tabs = tabs
        self._widget_map: dict = {}

        for section, values in config.data.items():
            tab_w = QWidget()
            grid = QGridLayout(tab_w)
            grid.setContentsMargins(16, 16, 16, 16)
            grid.setSpacing(12)
            grid.setColumnStretch(1, 1)

            row = 0
            self._widget_map[section] = {}

            for key, default_val in values.items():
                label_txt = key.replace("_", " ").title()
                grid.addWidget(QLabel(label_txt), row, 0)

                val = config.get(section, key, default_val)
                ctrl = self._build_control(section, key, default_val, val)
                grid.addWidget(ctrl, row, 1)
                self._widget_map[section][key] = ctrl
                row += 1

            grid.setRowStretch(row, 1)
            tabs.addTab(tab_w, section.replace("_", " ").title())

        outer.addWidget(tabs)

    def _build_control(self, section, key, default, current):
        if isinstance(default, bool):
            cb = QCheckBox()
            cb.setChecked(bool(current))
            cb.stateChanged.connect(
                lambda _st, s=section, k=key, c=cb: self.config.set(s, k, c.isChecked())
            )
            return cb

        if isinstance(default, (int, float)):
            slider = QSlider(Qt.Orientation.Horizontal)
            is_ratio = "volume" in key or 0 <= default <= 1.0
            slider.setRange(0, 100)
            if current is not None:
                slider.setValue(int(current * 100) if is_ratio else int(current))
            slider.valueChanged.connect(
                lambda v, s=section, k=key, r=is_ratio: self.config.set(
                    s, k, round(v / 100.0, 2) if r else v
                )
            )
            return slider

        return QLabel(str(current))
