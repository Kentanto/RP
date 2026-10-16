"""
Solo Leveling System — visual styles / QSS strings.
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


def mission_card_style(difficulty: str = "E") -> str:
    col = DIFF_COLOURS.get(difficulty.upper(), CYAN)
    return f"""
        QFrame#MissionCard {{
            background-color: rgba(10,10,10,210);
            border-left: 4px solid {col};
            border-top: 1px solid #222;
            border-right: 1px solid #222;
            border-bottom: 1px solid #222;
            border-radius: 0px;
            padding: 8px;
        }}
        QFrame#MissionCard:hover {{
            background-color: rgba(20,30,40,230);
            border-left: 4px solid {col};
            border-top: 1px solid {col};
            border-right: 1px solid {col};
            border-bottom: 1px solid {col};
        }}
        QLabel {{
            background: transparent;
            border: none;
            color: {WHITE};
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
