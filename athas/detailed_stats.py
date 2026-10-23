"""
Detailed Stats — the DASHBOARD details page.

Main stats (health, magic, attack, defense, speed, luck) come from the
player's config plus every owned artifact's bonuses. Detailed stats are
second-order values derived from those totals; artifacts can also grant
detailed stats directly, which stack on top of the derived value.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea,
)

from athas.styles import CYAN, WHITE, GOLD, GRAY
from athas.artifact_generator import (
    MAIN_STATS, DETAILED_STATS, PCT_DETAILED_STATS,
)
from athas.stats_widget import STAT_COLORS, TEXT_DIM


def _as_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


# Human labels for every stat shown on this page.
STAT_LABELS = {
    "health": "Health", "magic": "Magic", "attack": "Attack",
    "defense": "Defense", "speed": "Speed", "luck": "Luck",
    "crit_chance": "Crit Chance", "crit_damage": "Crit Damage",
    "dodge": "Dodge", "block": "Block",
    "armor_pen": "Armor Penetration", "magic_pen": "Magic Penetration",
    "hp_regen": "HP Regen", "mana_regen": "Mana Regen",
}

# Detailed stat key → (formula over main stat totals, readable formula text).
DETAILED_FORMULAS = {
    "crit_chance": (lambda t: 3 + 0.15 * t["speed"] + 0.30 * t["luck"],
                   "3% + Speed x 0.15% + Luck x 0.30%"),
    "crit_damage": (lambda t: 50 + 1.00 * t["attack"] + 0.50 * t["luck"],
                    "50% + Attack x 1% + Luck x 0.50%"),
    "dodge":       (lambda t: 1 + 0.10 * t["speed"] + 0.25 * t["luck"],
                    "1% + Speed x 0.10% + Luck x 0.25%"),
    "block":       (lambda t: 2 + 0.15 * t["defense"],
                    "2% + Defense x 0.15%"),
    "armor_pen":   (lambda t: t["attack"] * 0.5, "Attack x 0.5"),
    "magic_pen":   (lambda t: t["magic"] * 0.5, "Magic x 0.5"),
    "hp_regen":    (lambda t: 1 + 0.05 * t["health"], "1 + Health x 0.05"),
    "mana_regen":  (lambda t: 1 + 0.10 * t["magic"], "1 + Magic x 0.10"),
}

# Caps for percentage detailed stats (derived + direct bonuses combined).
PCT_CAPS = {"crit_chance": 75, "crit_damage": 300, "dodge": 50, "block": 60}


def collect_artifact_bonuses(artifacts):
    """Sum artifact stat bonuses into (main, detailed) buckets."""
    main = {key: 0 for key in MAIN_STATS}
    detailed = {key: 0 for key in DETAILED_STATS}
    for artifact in artifacts or []:
        for key, value in (artifact.stats or {}).items():
            value = _as_int(value)
            if value <= 0:
                continue
            if key in main:
                main[key] += value
            elif key in detailed:
                detailed[key] += value
    return main, detailed


def main_stat_totals(config, artifacts):
    """Per main stat: base+perm value, temp allocation, artifact bonus, total."""
    main_bonus, _ = collect_artifact_bonuses(artifacts)
    totals = {}
    for key in MAIN_STATS:
        base = _as_int(config.get("player", key, 0))
        temp = _as_int(config.get_nested("player", "temp_allocations", key, default=0))
        bonus = main_bonus.get(key, 0)
        totals[key] = {"base": base, "temp": temp, "artifact": bonus,
                       "total": base + temp + bonus}
    return totals


def detailed_stat_values(main_totals, artifacts):
    """Per detailed stat: derived value, direct artifact bonus, capped total."""
    _, direct = collect_artifact_bonuses(artifacts)
    flat_totals = {key: row["total"] for key, row in main_totals.items()}
    values = {}
    for key in DETAILED_STATS:
        formula, _ = DETAILED_FORMULAS[key]
        derived = formula(flat_totals)
        bonus = direct.get(key, 0)
        raw = derived + bonus
        capped = False
        cap = PCT_CAPS.get(key)
        if cap is not None and raw > cap:
            raw = cap
            capped = True
        values[key] = {"derived": derived, "artifact": bonus, "total": raw,
                       "pct": key in PCT_DETAILED_STATS, "capped": capped}
    return values


def _fmt(value, pct):
    if pct:
        return f"{value:.1f}%"
    return str(int(round(value)))


class DetailedStatsPanel(QWidget):
    """Dashboard sub-page: full breakdown of main and detailed stats."""

    def __init__(self, config, inv_manager=None, on_back=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.inv_manager = inv_manager
        self._on_back = on_back
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("DETAILED STATS")
        title.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {WHITE}; letter-spacing: 3px;")
        header.addWidget(title)
        header.addStretch()
        back = QPushButton("← BACK")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: 1px solid {CYAN}44;
                color: {CYAN}; padding: 4px 10px;
            }}
            QPushButton:hover {{ background-color: {CYAN}22; }}
        """)
        back.clicked.connect(self._back)
        header.addWidget(back)
        layout.addLayout(header)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        layout.addWidget(line)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_content = QWidget()
        self._body = QVBoxLayout(self._scroll_content)
        self._body.setContentsMargins(4, 4, 4, 4)
        self._body.setSpacing(16)
        scroll.setWidget(self._scroll_content)
        layout.addWidget(scroll, 1)

    def _back(self):
        if self._on_back:
            self._on_back()

    def _cell(self, text, color=WHITE, bold=False, align=Qt.AlignmentFlag.AlignRight):
        lbl = QLabel(text)
        lbl.setAlignment(align)
        weight = "bold" if bold else "normal"
        lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: {weight}; background: transparent;")
        return lbl

    def _section_frame(self, caption, headers):
        """Card with a caption row and right-aligned column headers.

        Returns (frame, grid); stat rows start at grid row 2, column 0 is
        the stat name and columns 1..N hold the header columns.
        """
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(16,16,22,200);
                border: 1px solid #232330;
                border-radius: 6px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        grid = QGridLayout(frame)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 2)
        for c in range(1, len(headers) + 1):
            grid.setColumnStretch(c, 1)
        cap = QLabel(caption)
        cap.setStyleSheet(f"color: {GRAY}; font-size: 11px; font-weight: bold; letter-spacing: 3px;")
        grid.addWidget(cap, 0, 0, 1, max(2, len(headers)))
        for c, text in enumerate(headers, start=1):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: #5d6373; font-size: 10px; letter-spacing: 1px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lbl, 1, c)
        return frame, grid

    def _build_main_section(self, totals):
        frame, grid = self._section_frame("MAIN STATS", ["BASE + TEMP", "ARTIFACTS", "TOTAL"])
        row = 2
        for key in MAIN_STATS:
            data = totals[key]
            color = STAT_COLORS.get(key, CYAN)
            name = QLabel(STAT_LABELS.get(key, key.title()))
            name.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent;")
            grid.addWidget(name, row, 0)
            base_txt = str(data["base"]) + (f" +{data['temp']}" if data["temp"] else "")
            grid.addWidget(self._cell(base_txt, TEXT_DIM), row, 1)
            bonus_color = GOLD if data["artifact"] else "#3a3a44"
            grid.addWidget(self._cell(f"+{data['artifact']}", bonus_color), row, 2)
            grid.addWidget(self._cell(f"= {data['total']}", WHITE, bold=True), row, 3)
            row += 1
        return frame

    def _build_detailed_section(self, values):
        frame, grid = self._section_frame("DETAILED STATS", ["FORMULA", "DERIVED", "ARTIFACTS", "TOTAL"])
        row = 2
        for key in DETAILED_STATS:
            data = values[key]
            name = QLabel(STAT_LABELS.get(key, key.replace("_", " ").title()))
            name.setStyleSheet(f"color: {WHITE}; font-size: 13px; font-weight: bold; background: transparent;")
            grid.addWidget(name, row, 0)
            _, formula_text = DETAILED_FORMULAS[key]
            grid.addWidget(self._cell(formula_text, "#5d6373", align=Qt.AlignmentFlag.AlignLeft), row, 1)
            grid.addWidget(self._cell(_fmt(data["derived"], data["pct"]), TEXT_DIM), row, 2)
            bonus_color = GOLD if data["artifact"] else "#3a3a44"
            grid.addWidget(self._cell(f"+{_fmt(data['artifact'], data['pct'])}", bonus_color), row, 3)
            total_txt = "= " + _fmt(data["total"], data["pct"])
            if data["capped"]:
                total_txt += " (capped)"
            grid.addWidget(self._cell(total_txt, WHITE, bold=True), row, 4)
            row += 1
        return frame

    def refresh(self):
        while self._body.count():
            it = self._body.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        artifacts = self.inv_manager.get_artifacts() if self.inv_manager else []
        totals = main_stat_totals(self.config, artifacts)
        detailed = detailed_stat_values(totals, artifacts)
        self._body.addWidget(self._build_main_section(totals))
        self._body.addWidget(self._build_detailed_section(detailed))
        note = QLabel(
            "Detailed stats are calculated from your main stat totals — base + temp points "
            "plus every owned artifact's bonuses. Artifacts can also roll detailed stats "
            "directly, and those stack on top of the derived value. Percentage stats are capped."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5d6373; font-size: 11px;")
        self._body.addWidget(note)
        self._body.addStretch()