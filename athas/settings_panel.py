"""
Athas - Settings panel built dynamically from JSON config.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QCheckBox, QSlider, QTabWidget,
)

from athas.styles import CYAN, BLACK, WHITE


class HoverButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class SettingsPanel(QFrame):
    def __init__(self, config, audio_output=None, parent=None):
        super().__init__(parent)
        self.config = config
        self._audio_output = audio_output
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
                height: 8px;
                background: #333;
                border-radius: 4px;
            }}
            QSlider::sub-page:horizontal {{
                background: {CYAN};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                width: 18px;
                height: 18px;
                background: white;
                border: 2px solid {CYAN};
                border-radius: 9px;
                margin: -5px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {CYAN};
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

        tabs = QTabWidget()
        self._tabs = tabs
        self._widget_map = {}

        for section, values in config.data.items():
            if section == "player":
                continue

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
            return self._build_slider(section, key, default, current)

        lbl = QLabel(str(current))
        lbl.setStyleSheet(f"color: {CYAN}; font-size: 13px; font-weight: bold;")
        return lbl

    def _build_slider(self, section, key, default, current):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        slider = QSlider(Qt.Orientation.Horizontal)

        if "volume" in key.lower():
            _min, _max = 0, 100
            _is_ratio = True
            _suffix = "%"
            slider.setSingleStep(1)
        elif "duration_ms" in key.lower():
            _min, _max = 500, 30000
            _is_ratio = False
            _suffix = " ms"
            slider.setSingleStep(100)
        elif "interval_ms" in key.lower():
            _min, _max = 1000, 300000
            _is_ratio = False
            _suffix = " ms"
            slider.setSingleStep(1000)
        else:
            _min, _max = 0, 1000
            _is_ratio = False
            _suffix = ""
            slider.setSingleStep(10)

        slider.setRange(_min, _max)
        if current is not None:
            raw = int(current * 100) if _is_ratio else int(current)
            slider.setValue(max(_min, min(_max, raw)))

        value_lbl = QLabel()
        value_lbl.setStyleSheet(
            f"color: {CYAN}; font-size: 13px; font-weight: bold; min-width: 70px;"
        )
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def _update_label(v):
            if _is_ratio:
                value_lbl.setText(f"{v}%")
            else:
                value_lbl.setText(f"{v}{_suffix}")

        _update_label(slider.value())

        def _on_change(v, s=section, k=key):
            value = round(v / 100.0, 2) if _is_ratio else v
            self.config.set(s, k, value)
            _update_label(v)
            if "volume" in k.lower() and self._audio_output is not None:
                self._audio_output.setVolume(value)

        slider.valueChanged.connect(_on_change)
        layout.addWidget(slider, 1)
        layout.addWidget(value_lbl)
        return container
