"""
Detailed Stats — the DASHBOARD details page.

Every regular stat (health, magic, attack, defense, speed) converts into a
simple, linear DG power rating — no real-world units involved. The stat's
total (base + temp points + every owned artifact's bonuses) is multiplied
by that stat's per-point DG rating, times the level multiplier:

    DG rating = stat total x per-point DG rating x level multiplier
    level multiplier = 1.05 ** (level - 1)    (x1.0 at level 1, x1.05 at 2)

Every stat currently awards 60 DG per point; tune STAT_DG_PER_POINT to
scale individual stats differently.

Artifacts can roll worth_<stat> bonuses: the bonus is added straight onto
that stat's per-point DG rating, and the level multiplier applies to the
whole thing — 1 point = (60 + bonus) DG, then × level multiplier (a
worth bonus of 5 makes a point worth 65 DG at level 1, 65 × 1.05 at
level 2, and so on).

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
    WORTH_PREFIX, TEMP_POINTS_KEY,
)
from athas.stats_widget import STAT_COLORS, TEXT_DIM, SURFACE, SURFACE_HI, EDGE, EDGE_HI
from athas import equip


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

# ── DG power ratings ─────────────────────────────────────────────────────────
# Every regular stat maps to a simple, linear DG power rating — no real-world
# units. Each stat currently awards 60 DG per point; change a stat's value
# here to scale it differently from the rest.
STAT_DG_PER_POINT = {
    "attack":  60.0,
    "health":  60.0,
    "magic":   60.0,
    "defense": 60.0,
    "speed":   60.0,
}

# What each stat's DG rating represents, shown under the stat name.
STAT_DG_DESCRIPTIONS = {
    "attack":  "Strike power",
    "health":  "Endurance reserve",
    "magic":   "Casting power",
    "defense": "Guard strength",
    "speed":   "Movement power",
}

LEVEL_GROWTH = 1.05   # multiplier growth for each level past the first

# (lower bound, upper bound, comparison). Bounds are lower-inclusive and
# upper-exclusive; use None for the final open-ended range.
# Bounds are in each stat's DG rating.
STAT_CAPABILITY_RANGES = {
    "attack": (
        (0, 1_000, "About as dangerous as a trained human. Effective against people, not armor."),
        (1_000, 10_000, "Breaks bones, doors and car panels. One clean hit ends most ordinary fights."),
        (10_000, 50_000, "Punches through brick and concrete. Can throw a grown man across a room."),
        (50_000, 100_000, "Brings down walls and guts small buildings in a handful of blows."),
        (100_000, 250_000, "Levels a house in one exchange and a larger building with sustained effort."),
        (250_000, 500_000, "Flattens large buildings. A single strike can clear a street."),
        (500_000, 1_000_000, "Destroys entire districts in a single sustained assault."),
        (1_000_000, 2_000_000, "Can wipe out a city. Unrestrained, the damage reaches well beyond it."),
        (2_000_000, 3_000_000, "Reshapes terrain across a whole region: mountains, coastlines, rivers."),
        (3_000_000, 4_000_000, "Force on a planetary scale. A full-strength blow puts the world at risk."),
        (4_000_000, None, "The upper limit of the scale. Very little anywhere hits harder."),
    ),
    "defense": (
        (0, 1_000, "Ordinary durability. Blades, bullets and bad falls are all serious threats."),
        (1_000, 10_000, "Shrugs off hits that would put an ordinary person in the hospital."),
        (10_000, 50_000, "Unhurt by blows that crack stone and bend steel."),
        (50_000, 100_000, "Walks away from collapsing walls and direct hits from heavy weapons."),
        (100_000, 250_000, "Can stand in a demolished building and keep fighting."),
        (250_000, 500_000, "Withstands attacks that flatten large structures."),
        (500_000, 1_000_000, "Survives assaults that tear through whole districts."),
        (1_000_000, 2_000_000, "Endures force that would destroy a city."),
        (2_000_000, 3_000_000, "Holds up against attacks that reshape the land around them."),
        (3_000_000, 4_000_000, "Can take hits of planetary magnitude without being broken."),
        (4_000_000, None, "Effectively impervious. Only the very strongest attacks leave a mark."),
    ),
    "speed": (
        (0, 1_000, "Human speed and human reflexes."),
        (1_000, 10_000, "Outpaces ordinary people and reacts before they can."),
        (10_000, 50_000, "Moves faster than the eye can follow. Ordinary people only see the aftermath."),
        (50_000, 100_000, "Crosses a battlefield before most opponents can react."),
        (100_000, 250_000, "Covers great distances in moments and dodges most attacks outright."),
        (250_000, 500_000, "Strong fighters lose track of them mid-fight."),
        (500_000, 1_000_000, "Only exceptional opponents can follow their movement at all."),
        (1_000_000, 2_000_000, "Faster than nearly any other fighter, even at point-blank range."),
        (2_000_000, 3_000_000, "Only a handful of top-tier opponents can keep pace."),
        (3_000_000, 4_000_000, "Acts before almost anyone has time to perceive a threat."),
        (4_000_000, None, "Near the limit of the scale. Only their closest rivals can match them."),
    ),
    "health": (
        (0, 1_000, "A few serious wounds are enough to kill."),
        (1_000, 10_000, "Can absorb a beating and keep going through exhaustion and pain."),
        (10_000, 50_000, "Survives injuries that would leave an ordinary person down for good."),
        (50_000, 100_000, "Fights on through wounds that would end most combatants."),
        (100_000, 250_000, "Holds out through long battles and repeated heavy injuries."),
        (250_000, 500_000, "Takes enormous punishment before going down."),
        (500_000, 1_000_000, "Outlasts battles that destroy lesser fighters."),
        (1_000_000, 2_000_000, "Wearing them down takes extraordinary, sustained force."),
        (2_000_000, 3_000_000, "Endures attacks that would overwhelm almost any other opponent."),
        (3_000_000, 4_000_000, "Survives damage that would be fatal to nearly everyone else."),
        (4_000_000, None, "Nearly unkillable without comparable power."),
    ),
    "magic": (
        (0, 1_000, "Minor spells with little use in a fight."),
        (1_000, 10_000, "Reliable combat magic. Can attack, defend and disrupt opponents."),
        (10_000, 50_000, "Strong enough to overwhelm groups and damage buildings."),
        (50_000, 100_000, "Can wreck structures and control the flow of a battlefield."),
        (100_000, 250_000, "Sustained casting can ruin a large area."),
        (250_000, 500_000, "One spell can devastate a city block or more."),
        (500_000, 1_000_000, "Capable of striking a whole city."),
        (1_000_000, 2_000_000, "Outclasses most magic users and can affect vast territories."),
        (2_000_000, 3_000_000, "Matches the strongest supernatural beings in the setting."),
        (3_000_000, 4_000_000, "Power on a scale that can change the fate of a world."),
        (4_000_000, None, "Beyond what almost anyone can counter."),
    ),
    # Overall might: the sum of every stat's DG rating.
    "total": (
        (0, 1_000, "An ordinary person with little to no fighting ability."),
        (1_000, 10_000, "A capable fighter, dangerous to ordinary people."),
        (10_000, 50_000, "A strong combatant, clearly beyond human limits."),
        (50_000, 150_000, "A superhuman fighter who can take on groups of ordinary opponents."),
        (150_000, 500_000, "A powerful warrior who can overwhelm elite fighters and armed forces."),
        (500_000, 750_000, "A major powerhouse, at the lower end of the high-tier roster."),
        (750_000, 1_000_000, "An elite powerhouse, closing in on the Kizaru and Naruto range."),
        (1_000_000, 1_250_000, "A top-tier fighter, in the range of Naruto and Akainu."),
        (1_250_000, 1_500_000, "An exceptional powerhouse, in the range of Momoshiki and Kaido."),
        (1_500_000, 1_750_000, "Among the strongest, in the range of Natsu and Sung Jinwoo."),
        (1_750_000, 2_000_000, "Just below the highest tier, in the range of Gojo, Sukuna and Tatsumaki."),
        (2_000_000, 2_500_000, "Top of the roster, in the range of Ulquiorra, Frieza and Gilgamesh."),
        (2_500_000, 3_000_000, "Among the very strongest, in the range of Aizen, Atomic and Rimuru."),
        (3_000_000, 3_500_000, "Above nearly everyone on the roster, nearing Yhwach."),
        (3_500_000, 4_000_000, "Just under the peak, past Yhwach's listed rating."),
        (4_000_000, 4_250_000, "At the top of the roster, around Raiden."),
        (4_250_000, 4_500_000, "Above Raiden, approaching Boros."),
        (4_500_000, 4_750_000, "On par with Boros and Sinbad."),
        (4_750_000, 5_000_000, "At the very top, around Milim."),
        (5_000_000, 5_500_000, "Beyond every character currently listed."),
        (5_500_000, 6_000_000, "Far past the current roster, a new benchmark for the strongest."),
        (6_000_000, None, "A level of power the existing scale doesn't cover."),
    ),
}


def level_multiplier(level) -> float:
    """Compounding level multiplier — x1.0 at level 1, x1.05 at level 2, ..."""
    return LEVEL_GROWTH ** (max(1, _as_int(level, 1)) - 1)


# Crit stat key → (formula over main stat totals, readable formula text).
DETAILED_FORMULAS = {
    "crit_chance": (lambda t: 3 + 0.45 * t["speed"],
                   "3% + Speed × 0.45%"),
    "crit_damage": (lambda t: 50 + 1.50 * t["attack"],
                    "50% + Attack × 1.50%"),
}

# Caps for the percentage crit stats (derived + direct bonuses combined).
PCT_CAPS = {"crit_chance": 75, "crit_damage": 300}

# What each crit stat actually does — shown as full readable text on its card.
CRIT_EXPLANATIONS = {
    "crit_chance": (
        "The chance that any given strike lands as a critical hit. It derives "
        "from your Speed total, and artifact bonuses add directly on top — the "
        "combined value caps at 75%."
    ),
    "crit_damage": (
        "The bonus damage a critical strike deals on top of a normal hit. It "
        "derives from your Attack total, and artifact bonuses add directly on "
        "top — the combined value caps at 300%."
    ),
}


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


def collect_worth_bonuses(artifacts):
    """Sum equipped artifacts' worth_<stat> bonuses: extra DG per point."""
    worth = {}
    for artifact in artifacts or []:
        for key, value in (artifact.stats or {}).items():
            if isinstance(key, str) and key.startswith(WORTH_PREFIX):
                stat = key[len(WORTH_PREFIX):]
                if stat in STAT_DG_PER_POINT:
                    worth[stat] = worth.get(stat, 0) + _as_int(value)
    return worth


def collect_temp_points(artifacts):
    """Total extra temp points granted by equipped artifacts."""
    total = 0
    for artifact in artifacts or []:
        total += _as_int((artifact.stats or {}).get(TEMP_POINTS_KEY))
    return max(0, total)


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


def measured_stat_values(main_totals, level, worth=None):
    """Per regular stat: point totals plus the linear DG power rating.

    `worth` maps a stat to the DG bonus granted by equipped artifacts
    (worth_<stat> bonuses): the bonus is added straight onto that stat's
    per-point DG rating, and the level multiplier then scales the whole
    thing — 1 point = (per-point DG + bonus) × level multiplier."""
    mult = level_multiplier(level)
    worth = worth or {}
    values = {}
    for key in MAIN_STATS:
        if key not in STAT_DG_PER_POINT:
            continue
        base_dg = STAT_DG_PER_POINT[key]
        worth_pts = max(0, worth.get(key, 0))
        dg = base_dg + worth_pts
        data = main_totals[key]
        total = data["total"]
        values[key] = {
            "base": data["base"], "temp": data["temp"],
            "artifact": data["artifact"], "total": total,
            "per_point": dg, "worth": worth_pts, "unit": "DG",
            "label": STAT_DG_DESCRIPTIONS.get(key, "Power rating"),
            "mult": mult, "value": total * dg * mult,
        }
    return values


def total_dg_rating(measured):
    """Sum of every stat's DG rating — overall might in one number."""
    return sum(row["value"] for row in measured.values())


def capability_comparison(stat_key, measurement):
    """Return the short reference description for a measured main stat."""
    for lower, upper, description in STAT_CAPABILITY_RANGES[stat_key]:
        if lower <= measurement and (upper is None or measurement < upper):
            return description
    return "Below the listed reference ranges."


def _fmt(value, pct):
    if pct:
        return f"{value:.1f}%"
    return str(int(round(value)))


def _fmt_measurement(value, unit):
    """Format a DG power rating (or any plain unit) for display."""
    if unit == "DG":
        return f"{value:,.0f} DG"
    return f"{value:,.1f} {unit}"


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

    # ── shared building blocks ─────────────────────────────────────────────

    def _card(self):
        """Surface card used by every section on this page."""
        frame = QFrame()
        frame.setObjectName("StatsCard")
        frame.setStyleSheet(f"""
            QFrame#StatsCard {{
                background-color: rgba(16,16,22,200);
                border: 1px solid {EDGE};
                border-radius: 8px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        return frame

    def _hline(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {EDGE}; border: none;")
        return line

    def _caption(self, text, hint=None):
        """Section caption row — bold label on the left, optional hint right."""
        row = QHBoxLayout()
        cap = QLabel(text)
        cap.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-weight: bold; letter-spacing: 3px;")
        row.addWidget(cap)
        row.addStretch()
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"color: #5d6373; font-size: 10px; letter-spacing: 1px;")
            row.addSpacing(12)
            row.addWidget(hint_lbl)
        return row

    def _build_level_card(self, level, equipped_count=0, temp_bonus=0):
        """Banner: current level and the compounding measurement multiplier."""
        frame = QFrame()
        frame.setObjectName("LevelCard")
        frame.setStyleSheet(f"""
            QFrame#LevelCard {{
                background-color: {SURFACE};
                border: 1px solid {EDGE};
                border-radius: 8px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        row = QHBoxLayout(frame)
        row.setContentsMargins(20, 12, 20, 12)
        left = QVBoxLayout()
        left.setSpacing(2)
        lvl_lbl = QLabel(f"LEVEL {level}")
        lvl_lbl.setStyleSheet(f"color: {WHITE}; font-size: 20px; font-weight: bold; letter-spacing: 2px;")
        left.addWidget(lvl_lbl)
        lvl_sub = QLabel(
            "×1.00 at level 1 · ×1.05 at level 2 · +5% compounding every level after"
        )
        lvl_sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; letter-spacing: 1px;")
        left.addWidget(lvl_sub)
        equip_bits = [f"EQUIPPED ARTIFACTS: {max(0, equipped_count)}/{equip.EQUIP_SLOTS}"]
        if temp_bonus:
            equip_bits.append(f"+{temp_bonus} temp points")
        equip_lbl = QLabel("  ·  ".join(equip_bits))
        equip_lbl.setStyleSheet(f"color: {GOLD}; font-size: 11px; letter-spacing: 1px;")
        left.addWidget(equip_lbl)
        row.addLayout(left)
        row.addStretch()
        right = QVBoxLayout()
        right.setSpacing(2)
        cap = QLabel("MEASUREMENT MULTIPLIER")
        cap.setAlignment(Qt.AlignmentFlag.AlignRight)
        cap.setStyleSheet(f"color: {GRAY}; font-size: 10px; font-weight: bold; letter-spacing: 2px;")
        right.addWidget(cap)
        mult = level_multiplier(level)
        mult_lbl = QLabel(f"×{mult:.2f}")
        mult_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        mult_lbl.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: bold;")
        right.addWidget(mult_lbl)
        row.addLayout(right)
        frame.setToolTip(
            "Level multiplier = 1.05^(level - 1): ×1.00 at level 1, ×1.05 at "
            "level 2, compounding an extra 5% for every level after that. "
            "It multiplies every DG rating shown below."
        )
        return frame

    def _build_power_section(self, measured):
        """One card per stat, two per row — the last card spans full width."""
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent; border: none;")
        col = QVBoxLayout(wrap)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        col.addLayout(self._caption(
            "POWER MEASUREMENTS", "stat total × per-point unit × level multiplier",
        ))

        keys = [k for k in MAIN_STATS if k in measured]
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for i, key in enumerate(keys):
            r, c = divmod(i, 2)
            if len(keys) % 2 == 1 and i == len(keys) - 1:
                grid.addWidget(self._power_card(key, measured[key]), r, 0, 1, 2)
            else:
                grid.addWidget(self._power_card(key, measured[key]), r, c)
        col.addLayout(grid)
        return wrap

    def _power_card(self, key, data):
        """A single stat card: name, numbers, and a full readable capability text."""
        color = STAT_COLORS.get(key, CYAN)
        card = self._card()
        col = QVBoxLayout(card)
        col.setContentsMargins(16, 12, 16, 12)
        col.setSpacing(8)

        # Header — stat name + what it measures, big measurement on the right.
        head = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(1)
        name = QLabel(STAT_LABELS.get(key, key.title()))
        name.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; letter-spacing: 1px;")
        left.addWidget(name)
        sub = QLabel(data["label"])
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        left.addWidget(sub)
        head.addLayout(left)
        head.addStretch()
        meas = QLabel(_fmt_measurement(data["value"], data["unit"]))
        meas.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        head.addWidget(meas)
        col.addLayout(head)

        # Point breakdown — base · temp · artifacts → total, then the formula.
        sep = f"<span style='color:#45454f;'> &nbsp;·&nbsp; </span>"
        parts = [f"<span style='color:{TEXT_DIM};'>{data['base']} base</span>"]
        if data["temp"]:
            parts.append(f"<span style='color:{TEXT_DIM};'>+{data['temp']} temp</span>")
        if data["artifact"]:
            parts.append(f"<span style='color:{GOLD};'>+{data['artifact']} artifacts</span>")
        if data.get("worth"):
            parts.append(
                f"<span style='color:{GOLD};'>+{data['worth']} point worth (+{data['worth']:g} DG/pt)</span>"
            )
        pts = QLabel(
            f"<span style='color:{WHITE}; font-weight:bold;'>{data['total']} pts</span>"
            + sep + sep.join(parts)
        )
        pts.setStyleSheet("font-size: 12px;")
        col.addWidget(pts)
        formula = QLabel(
            f"{data['total']} pts × {data['per_point']:g} DG/pt × {data['mult']:.2f} "
            f"= {data['value']:,.0f} DG"
        )
        formula.setStyleSheet(f"color: #5d6373; font-size: 10px; letter-spacing: 1px;")
        formula.setToolTip(
            f"{data['total']} stat points × {data['per_point']:g} DG per point "
            f"× level multiplier {data['mult']:.2f}"
            + (f" (includes +{data['worth']:g} DG per point of point worth "
               f"from equipped artifacts)"
               if data.get("worth") else "")
        )
        col.addWidget(formula)

        # What the resulting measurement can actually do — full readable text
        # that fills the remaining space in the card.
        col.addWidget(self._hline())
        desc = QLabel(
            f"<span style='color:{color}; font-weight:bold;'>≈ </span>"
            + capability_comparison(key, data["value"])
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        col.addWidget(desc, 1)
        return card

    def _build_crit_section(self, values):
        """Two side-by-side crit cards, with a caption like the power section."""
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent; border: none;")
        col = QVBoxLayout(wrap)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        col.addLayout(self._caption(
            "CRITICAL STATS", "derived from Speed / Attack · artifact rolls add on top",
        ))
        holder = QHBoxLayout()
        holder.setSpacing(12)
        for key in DETAILED_STATS:
            holder.addWidget(self._crit_card(key, values[key]), 1)
        col.addLayout(holder)
        return wrap

    def _crit_card(self, key, data):
        card = self._card()
        col = QVBoxLayout(card)
        col.setContentsMargins(16, 12, 16, 12)
        col.setSpacing(8)

        # Title row — stat name on the left, cap pill on the right.
        top = QHBoxLayout()
        name = QLabel(STAT_LABELS.get(key, key.replace("_", " ").title()).upper())
        name.setStyleSheet(f"color: {WHITE}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        top.addWidget(name)
        top.addStretch()
        cap = QLabel(f"CAP {PCT_CAPS.get(key, 0)}%")
        cap.setStyleSheet(f"""
            color: {TEXT_DIM}; font-size: 9px; font-weight: bold; letter-spacing: 1px;
            background-color: {SURFACE_HI}; border: 1px solid {EDGE_HI};
            border-radius: 8px; padding: 2px 8px;
        """)
        top.addWidget(cap)
        col.addLayout(top)

        # The derivation formula, shown as a quiet pill.
        _, formula_text = DETAILED_FORMULAS[key]
        pill = QLabel(formula_text)
        pill.setStyleSheet(f"""
            color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;
            background-color: {SURFACE_HI}; border: 1px solid {EDGE_HI};
            border-radius: 4px; padding: 3px 8px;
        """)
        pill.setToolTip(
            "Derived from your main stat totals; artifact crit rolls add directly on top."
        )
        col.addWidget(pill)

        # Mini table — DERIVED / ARTIFACTS / TOTAL.
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        for c, text in enumerate(("DERIVED", "ARTIFACTS", "TOTAL")):
            head = QLabel(text)
            head.setStyleSheet("color: #5d6373; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
            grid.addWidget(head, 0, c)
        derived = QLabel(_fmt(data["derived"], data["pct"]))
        derived.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px;")
        grid.addWidget(derived, 1, 0)
        bonus_color = GOLD if data["artifact"] else "#3a3a44"
        bonus = QLabel(f"+{_fmt(data['artifact'], data['pct'])}")
        bonus.setStyleSheet(f"color: {bonus_color}; font-size: 14px;")
        grid.addWidget(bonus, 1, 1)
        total_txt = _fmt(data["total"], data["pct"])
        if data["capped"]:
            total_txt += f"  <span style='color:{GOLD}; font-size:9px; font-weight:bold;'>CAPPED</span>"
        total = QLabel(total_txt)
        total.setStyleSheet(f"color: {WHITE}; font-size: 16px; font-weight: bold;")
        grid.addWidget(total, 1, 2)
        col.addLayout(grid)

        # What this crit stat actually does — full readable text filling the card.
        col.addWidget(self._hline())
        expl = QLabel(CRIT_EXPLANATIONS.get(key, ""))
        expl.setWordWrap(True)
        expl.setAlignment(Qt.AlignmentFlag.AlignTop)
        expl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        col.addWidget(expl, 1)
        return card

    def _build_total_section(self, measured):
        """Full-width card: every stat's DG combined into one overall rating."""
        total = total_dg_rating(measured)
        card = self._card()
        col = QVBoxLayout(card)
        col.setContentsMargins(16, 12, 16, 12)
        col.setSpacing(8)

        # Header — title on the left, the big gold total on the right.
        head = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(1)
        name = QLabel("TOTAL DG POWER")
        name.setStyleSheet(f"color: {WHITE}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        left.addWidget(name)
        sub = QLabel("every stat's DG combined — your overall might")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        left.addWidget(sub)
        head.addLayout(left)
        head.addStretch()
        total_lbl = QLabel(f"{total:,.0f} DG")
        total_lbl.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: bold;")
        head.addWidget(total_lbl)
        col.addLayout(head)

        # Each stat's contribution, labeled and colored per stat.
        sep = f"<span style='color:#45454f;'> &nbsp;·&nbsp; </span>"
        parts = []
        for key in MAIN_STATS:
            data = measured.get(key)
            if data is None:
                continue
            color = STAT_COLORS.get(key, CYAN)
            parts.append(
                f"{STAT_LABELS.get(key, key.title())} "
                f"<span style='color:{color}; font-weight:bold;'>{data['value']:,.0f}</span>"
            )
        contrib = QLabel(sep.join(parts))
        contrib.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        contrib.setWordWrap(True)
        col.addWidget(contrib)

        # What the combined rating says about the hero.
        col.addWidget(self._hline())
        desc = QLabel(
            f"<span style='color:{GOLD}; font-weight:bold;'>≈ </span>"
            + capability_comparison("total", total)
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        col.addWidget(desc, 1)
        return card

    def refresh(self):
        while self._body.count():
            it = self._body.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        # Only EQUIPPED artifacts apply their bonuses.
        equipped_ids = equip.equipped_ids(self.config)
        artifacts = self.inv_manager.get_equipped_artifacts(equipped_ids) if self.inv_manager else []
        level = max(1, _as_int(self.config.get("player", "level", 1), 1))
        totals = main_stat_totals(self.config, artifacts)
        worth = collect_worth_bonuses(artifacts)
        temp_bonus = collect_temp_points(artifacts)
        measured = measured_stat_values(totals, level, worth)
        detailed = detailed_stat_values(totals, artifacts)
        self._body.addWidget(self._build_level_card(level, len(artifacts), temp_bonus))
        self._body.addWidget(self._build_power_section(measured))
        self._body.addWidget(self._build_crit_section(detailed))
        self._body.addWidget(self._build_total_section(measured))
        mult = level_multiplier(level)
        footer = QLabel(
            f"Every stat converts into a linear DG power rating: your stat total "
            f"(base + temporary points + equipped artifact bonuses) × that stat's per-point "
            f"DG rating (60 for every stat right now, plus the point-worth bonus of "
            f"equipped artifacts) × the level multiplier — "
            f"×{mult:.2f} at your current level, compounding 5% for every level past "
            f"the first. Crit chance and crit damage derive from your Speed and "
            f"Attack totals; equipped artifact rolls add on top, capped at 75% and 300%. "
            f"Only equipped artifacts count — unequipped gear gives nothing."
        )
        footer.setWordWrap(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self._body.addWidget(footer)
        self._body.addStretch()