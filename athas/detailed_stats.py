"""
Detailed Stats — the DASHBOARD details page.

Every regular stat (health, magic, attack, defense, speed) converts into a
physical measurement: the stat's total — base + temp points + every owned
artifact's bonuses — times a per-point unit, times the level multiplier.

The level multiplier compounds 5% for every level past the first:

    level multiplier = 1.05 ** (level - 1)    (x1.0 at level 1, x1.05 at 2)

For example 1 ATK always equals 100 joules of kinetic energy per strike, so
energy per strike = ATK total x 100 J x level multiplier.

Crit chance and crit damage stay percentage stats derived from the main
stat totals; artifacts can also grant them directly, stacking on top.
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
from athas.stats_widget import STAT_COLORS, TEXT_DIM, SURFACE, EDGE


def _as_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


# Human labels for every stat shown on this page.
STAT_LABELS = {
    "health": "Health", "magic": "Magic", "attack": "Attack",
    "defense": "Defense", "speed": "Speed",
    "crit_chance": "Crit Chance", "crit_damage": "Crit Damage",
}

# ── Physical measurements ──────────────────────────────────────────────────
# Every regular stat maps to a real-world measurement through a per-point
# unit. The measurement scales with the compounding level multiplier below.
LEVEL_GROWTH = 1.05   # multiplier growth for each level past the first

# stat -> (per-point unit, unit symbol, what the measurement means)
STAT_MEASUREMENTS = {
    "attack":  (100.0, "J",   "Energy delivered per strike"),
    "defense": (200.0, "N",   "Impact force deflected per block"),
    "speed":   (0.5,   "m/s", "Top movement speed"),
    "health":  (0.25,  "kJ",  "Punishment absorbed before collapse"),
    "magic":   (50.0,  "W",   "Arcane power channelled while casting"),
}


def level_multiplier(level) -> float:
    """Compounding level multiplier — x1.0 at level 1, x1.05 at level 2, ..."""
    return LEVEL_GROWTH ** (max(1, _as_int(level, 1)) - 1)


# Crit stat key → (formula over main stat totals, readable formula text).
DETAILED_FORMULAS = {
    "crit_chance": (lambda t: 3 + 0.45 * t["speed"],
                   "3% + Speed x 0.45%"),
    "crit_damage": (lambda t: 50 + 1.50 * t["attack"],
                    "50% + Attack x 1.50%"),
}

# Caps for the percentage crit stats (derived + direct bonuses combined).
PCT_CAPS = {"crit_chance": 75, "crit_damage": 300}


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


def measured_stat_values(main_totals, level):
    """Per regular stat: point totals plus the physical measurement."""
    mult = level_multiplier(level)
    values = {}
    for key in MAIN_STATS:
        if key not in STAT_MEASUREMENTS:
            continue
        per_point, unit, label = STAT_MEASUREMENTS[key]
        data = main_totals[key]
        total = data["total"]
        values[key] = {
            "base": data["base"], "temp": data["temp"],
            "artifact": data["artifact"], "total": total,
            "per_point": per_point, "unit": unit, "label": label,
            "mult": mult, "value": total * per_point * mult,
        }
    return values


def _fmt(value, pct):
    if pct:
        return f"{value:.1f}%"
    return str(int(round(value)))


def _fmt_measurement(value, unit):
    if unit in ("m/s", "kJ"):
        return f"{value:,.1f} {unit}"
    return f"{int(round(value)):,} {unit}"


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

    def _build_level_card(self, level):
        """Banner: current level and the compounding measurement multiplier."""
        frame = QFrame()
        frame.setObjectName("LevelCard")
        frame.setStyleSheet(f"""
            QFrame#LevelCard {{ background-color: {SURFACE}; border: 1px solid {EDGE}; border-radius: 8px; }}
        """)
        row = QHBoxLayout(frame)
        row.setContentsMargins(20, 14, 20, 14)
        lvl_lbl = QLabel(f"LEVEL {level}")
        lvl_lbl.setStyleSheet(f"color: {WHITE}; font-size: 20px; font-weight: bold; letter-spacing: 2px;")
        row.addWidget(lvl_lbl)
        row.addStretch()
        cap = QLabel("MEASUREMENT MULTIPLIER")
        cap.setStyleSheet(f"color: {GRAY}; font-size: 10px; font-weight: bold; letter-spacing: 2px;")
        row.addWidget(cap)
        mult = level_multiplier(level)
        mult_lbl = QLabel(f"x1.05^({level}-1) = x{mult:.2f}")
        mult_lbl.setStyleSheet(f"color: {GOLD}; font-size: 20px; font-weight: bold;")
        row.addWidget(mult_lbl)
        return frame

    def _build_power_section(self, measured):
        frame, grid = self._section_frame(
            "POWER MEASUREMENTS",
            ["BASE + TEMP", "ARTIFACTS", "TOTAL", "FORMULA", "MEASUREMENT"],
        )
        legend = QLabel(
            "1 ATK = 100 J  ·  1 DEF = 200 N  ·  1 SPD = 0.5 m/s  ·  "
            "1 HP = 0.25 kJ  ·  1 MAG = 50 W"
        )
        legend.setStyleSheet("color: #5d6373; font-size: 10px; letter-spacing: 1px; background: transparent;")
        grid.addWidget(legend, 2, 0, 1, 6)
        row = 3
        for key in MAIN_STATS:
            data = measured.get(key)
            if data is None:
                continue
            color = STAT_COLORS.get(key, CYAN)
            name = QLabel(
                f"<span style='color:{color}; font-size:13px; font-weight:bold;'>"
                f"{STAT_LABELS.get(key, key.title())}</span>"
                f"<br><span style='color:#5d6373; font-size:10px;'>{data['label']}</span>"
            )
            name.setStyleSheet("background: transparent;")
            grid.addWidget(name, row, 0)
            base_txt = str(data["base"]) + (f" +{data['temp']}" if data["temp"] else "")
            grid.addWidget(self._cell(base_txt, TEXT_DIM), row, 1)
            bonus_color = GOLD if data["artifact"] else "#3a3a44"
            grid.addWidget(self._cell(f"+{data['artifact']}", bonus_color), row, 2)
            grid.addWidget(self._cell(f"= {data['total']}", WHITE, bold=True), row, 3)
            formula = f"{data['total']} x {data['per_point']:g} {data['unit']} x {data['mult']:.2f}"
            grid.addWidget(self._cell(formula, "#5d6373", align=Qt.AlignmentFlag.AlignLeft), row, 4)
            grid.addWidget(self._cell(_fmt_measurement(data["value"], data["unit"]), WHITE, bold=True), row, 5)
            row += 1
        return frame

    def _build_detailed_section(self, values):
        frame, grid = self._section_frame("CRIT STATS", ["FORMULA", "DERIVED", "ARTIFACTS", "TOTAL"])
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
        level = max(1, _as_int(self.config.get("player", "level", 1), 1))
        totals = main_stat_totals(self.config, artifacts)
        measured = measured_stat_values(totals, level)
        detailed = detailed_stat_values(totals, artifacts)
        self._body.addWidget(self._build_level_card(level))
        self._body.addWidget(self._build_power_section(measured))
        self._body.addWidget(self._build_detailed_section(detailed))
        note = QLabel(
            "Every regular stat converts into a physical measurement: total stat "
            "(base + temp points + artifact bonuses) x per-point unit x level "
            "multiplier — the multiplier is x1.05 at level 2 and compounds 5% for "
            "every level after that. Crit chance and crit damage are derived from "
            "your stat totals; artifacts that roll crit stats add directly on top. "
            "Crit chance is capped at 75% and crit damage at 300%."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5d6373; font-size: 11px;")
        self._body.addWidget(note)
        self._body.addStretch()