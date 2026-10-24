"""
Athas — visual styles / QSS strings.
"""

# ── Colour Palette ──
BLACK = "#0a0a0a"
DARK = "#111111"
DARKER = "#0d0d0d"
CYAN = "#00f0ff"
CYAN_GLOW = "#00f0ff88"
WHITE = "#e0e0e0"
GRAY = "#888888"
DANGER = "#ff2a2a"
GOLD = "#ffd700"

DIFF_COLOURS = {
    "E": "#888888",
    "D": "#4caf50",
    "C": "#2196f3",
    "B": "#9c27b0",
    "A": "#ff9800",
    "S": CYAN,
}


def panel_style(bg: str = DARK, border: str = CYAN) -> str:
    return f"""
        QWidget {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 4px;
        }}
    """


def button_style(accent: str = CYAN, active: bool = True) -> str:
    """A clearly defined button: solid dark fill, crisp accent border,
    visible hover / pressed / disabled states. Used for the shop and
    inventory buttons so they always read as buttons."""
    if active:
        return f"""
            QPushButton {{
                background-color: {DARK};
                border: 1px solid {accent};
                color: {accent};
                padding: 6px 20px;
                font-weight: bold;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {accent};
                border: 1px solid {accent};
                color: {BLACK};
            }}
            QPushButton:pressed {{
                background-color: {accent};
                border: 1px solid {WHITE};
                color: {BLACK};
            }}
            QPushButton:disabled {{
                background-color: {DARKER};
                border: 1px solid #333;
                color: #555;
            }}
        """
    return f"""
        QPushButton {{
            background-color: {DARK};
            border: 1px solid #3a4a52;
            color: {GRAY};
            padding: 6px 20px;
            border-radius: 2px;
        }}
        QPushButton:hover {{
            background-color: {DARK};
            border: 1px solid {accent};
            color: {accent};
        }}
        QPushButton:disabled {{
            background-color: {DARKER};
            border: 1px solid #333;
            color: #555;
        }}
    """


def mission_card_style(difficulty: str = "E", completed: bool = False) -> str:
    col = DIFF_COLOURS.get(difficulty.upper(), CYAN)
    if completed:
        bg = "rgba(10,10,10,140)"
        hover_bg = "rgba(10,10,10,160)"
        border_col = "#555555"
    else:
        bg = "rgba(10,10,10,210)"
        hover_bg = "rgba(20,30,40,230)"
        border_col = col
    return f"""
        QFrame#MissionCard {{
            background-color: {bg};
            border-left: 4px solid {border_col};
            border-top: 1px solid #222;
            border-right: 1px solid #222;
            border-bottom: 1px solid #222;
            border-radius: 0px;
            padding: 8px;
        }}
        QFrame#MissionCard:hover {{
            background-color: {hover_bg};
            border-left: 4px solid {border_col};
            border-top: 1px solid {border_col};
            border-right: 1px solid {border_col};
            border-bottom: 1px solid {border_col};
        }}
        QLabel {{
            background: transparent;
            border: none;
        }}
    """


MAIN_QSS = f"""
QMainWindow {{
    background-color: {BLACK};
}}
QWidget {{
    font-family: "Segoe UI", "Roboto Mono", sans-serif;
    font-size: 14px;
    color: {WHITE};
}}
QPushButton {{
    background-color: {DARK};
    border: 1px solid {CYAN};
    color: {CYAN};
    padding: 8px 18px;
    border-radius: 2px;
}}
QPushButton:hover {{
    background-color: {CYAN};
    color: {BLACK};
}}
QPushButton:pressed {{
    background-color: {CYAN_GLOW};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {DARKER};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {CYAN};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {WHITE};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
