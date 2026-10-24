"""
Artifact Generator — the engine behind every artifact in the System.

An artifact is rolled from three ingredients:
  * an item type  (Sword, Shield, Ring, ...) that biases which stats it rolls
  * a rarity      (Common .. Mythic)          that sets its power and price
  * a level       (scales the rolled stat values)

Rolled stats are either main stats (health, magic, attack, defense, speed)
or crit stats (crit chance, crit damage) granted directly — see the
DASHBOARD details page for how everything adds up.

The rarity can be pinned by the caller (a mission that promises a "Rare
Artifact") or rolled from the mission-difficulty loot table. The item type
list is read from library/item_types.txt when that file is filled in; the
built-in list below is the fallback so generation always works. An artifact
is named directly after its item type — no adjectives, no extra name pools.
"""
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Rarity tables ────────────────────────────────────────────────────────

RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]

# Chance of each rarity on a plain random roll (when nothing pins the rarity).
RARITY_WEIGHTS = [40, 25, 15, 10, 7, 3]

# Power multiplier applied to every rolled stat.
RARITY_MULTIPLIER = {
    "Common": 1, "Uncommon": 2, "Rare": 4,
    "Epic": 7, "Legendary": 12, "Mythic": 20,
}

# How many different stats an artifact of each rarity rolls.
RARITY_STAT_COUNTS = {
    "Common": 1, "Uncommon": 2, "Rare": 2,
    "Epic": 3, "Legendary": 4, "Mythic": 5,
}

# Shop price baseline (gold) before level scaling.
RARITY_BASE_PRICES = {
    "Common": 60, "Uncommon": 150, "Rare": 400,
    "Epic": 1000, "Legendary": 2500, "Mythic": 6000,
}

# Mission difficulty → (rarity, weight) table used when no rarity is pinned.
DIFFICULTY_LOOT_TABLE = {
    "E": [("Common", 60), ("Uncommon", 30), ("Rare", 10)],
    "D": [("Common", 40), ("Uncommon", 35), ("Rare", 20), ("Epic", 5)],
    "C": [("Uncommon", 30), ("Rare", 45), ("Epic", 20), ("Legendary", 5)],
    "B": [("Rare", 40), ("Epic", 35), ("Legendary", 20), ("Mythic", 5)],
    "A": [("Rare", 20), ("Epic", 40), ("Legendary", 30), ("Mythic", 10)],
    "S": [("Epic", 45), ("Legendary", 35), ("Mythic", 20)],
}

# What the shop stocks: almost always Common, sometimes Uncommon, rarely
# Rare — anything higher must be earned from missions or fused.
SHOP_RARITY_TABLE = [("Common", 85), ("Uncommon", 12), ("Rare", 3)]

# How many artifacts of one rarity must be sacrificed to forge a single
# artifact of the next rarity (on the inventory ARTIFACTS tab).
SACRIFICE_PER_FUSION = 3

# ── Stats ────────────────────────────────────────────────────────────────
# Main stats can be allocated with points and roll on artifacts.
MAIN_STATS = ["health", "magic", "attack", "defense", "speed"]

# Crit stats are second-order stats: each is derived from the main stat
# totals (see athas/detailed_stats.py), and artifacts can also grant them
# directly. Those direct rolls are added on top of the derived value.
DETAILED_STATS = ["crit_chance", "crit_damage"]

# Crit stats shown as percentages in the UI.
PCT_DETAILED_STATS = {"crit_chance", "crit_damage"}

# Direct detailed-stat rolls scale far more gently than main stats.
RARITY_DETAIL_SCALE = {
    "Common": 1, "Uncommon": 2, "Rare": 3,
    "Epic": 4, "Legendary": 5, "Mythic": 6,
}

# ── Special artifact stats ────────────────────────────────────────────────
# Besides plain stat bonuses, artifacts can roll two special stat kinds:
#   * worth_<stat>  — every point allocated into that stat is worth extra
#                     DG on the DASHBOARD details page (e.g. worth_attack
#                     raises the 60 DG each attack point normally grants).
#   * temp_points   — extra allocatable temporary points granted while the
#                     artifact is equipped.
WORTH_PREFIX = "worth_"
TEMP_POINTS_KEY = "temp_points"

# Relative weight of the special candidates inside an item type's stat pool.
WORTH_STAT_WEIGHT_FACTOR = 0.25   # worth_<stat> gets 25% of the stat's weight
TEMP_POINTS_WEIGHT = 0.8          # temp_points candidate weight for every type

# How high an artifact can be upgraded (baseline; tune freely).
MAX_UPGRADE_LEVEL = 20

# How many artifacts the player can equip at once.
EQUIP_SLOTS = 5

# Fraction of the gold an upgrade cost that an un-upgrade refunds.
UNUPGRADE_REFUND = 0.5


def is_worth_stat(key: str) -> bool:
    """True when the key is a worth_<main stat> bonus."""
    return (isinstance(key, str) and key.startswith(WORTH_PREFIX)
            and key[len(WORTH_PREFIX):] in MAIN_STATS)


def stat_display(key: str, value) -> str:
    """Human-readable one-line text for a stat entry, e.g. 'Health +12'."""
    value = value if isinstance(value, int) else int(value or 0)
    if is_worth_stat(key):
        stat = key[len(WORTH_PREFIX):].replace("_", " ").title()
        return f"{stat} Point Worth +{value} DG"
    if key == TEMP_POINTS_KEY:
        return f"Temp Points +{value}"
    label = key.replace("_", " ").title()
    return f"{label} +{value}{'%' if key in PCT_DETAILED_STATS else ''}"

# ── Item types ───────────────────────────────────────────────────────────
# type → stat bias (weight per player stat). Simple gear: weapons, armor,
# and a few accessories. The artifact is named after its item type.

ITEM_TYPES: Dict[str, Dict[str, float]] = {
    "Sword":      {"attack": 6, "speed": 2, "health": 1, "crit_chance": 2.5},
    "Greatsword": {"attack": 7, "health": 2, "defense": 1, "crit_damage": 1.5},
    "Axe":        {"attack": 6, "defense": 2, "health": 1, "crit_damage": 1.5},
    "Mace":       {"attack": 5, "defense": 3, "health": 1, "crit_damage": 1.5},
    "Spear":      {"attack": 5, "speed": 3, "health": 1, "crit_chance": 1.5},
    "Dagger":     {"speed": 5, "attack": 4, "magic": 1, "crit_chance": 2, "crit_damage": 1},
    "Bow":        {"attack": 5, "speed": 4, "crit_chance": 1.5, "crit_damage": 1},
    "Crossbow":   {"attack": 6, "speed": 2, "defense": 1, "crit_damage": 1.5},
    "Staff":      {"magic": 6, "health": 2, "crit_chance": 1.5},
    "Wand":       {"magic": 5, "speed": 3, "crit_chance": 1.5},
    "Shield":     {"defense": 6, "health": 3, "magic": 1},
    "Helmet":     {"defense": 4, "health": 3, "magic": 2.5},
    "Chestplate": {"defense": 5, "health": 5},
    "Gauntlets":  {"attack": 4, "defense": 4, "health": 1, "crit_damage": 1},
    "Leggings":   {"defense": 4, "health": 3, "speed": 3.5},
    "Boots":      {"speed": 6, "defense": 2, "health": 2},
    "Cloak":      {"speed": 3, "defense": 3, "magic": 3, "crit_chance": 2},
    "Ring":       {"magic": 4, "health": 3, "attack": 2, "crit_chance": 3},
    "Amulet":     {"health": 4, "magic": 3, "defense": 2, "crit_chance": 2, "crit_damage": 1},
}

# Bias used for custom item types added to library/item_types.txt that have
# no entry above.
GENERIC_BIAS: Dict[str, float] = {
    "attack": 3, "defense": 3, "magic": 3, "speed": 3, "health": 3,
}

# ── Flavour text ─────────────────────────────────────────────────────────

_DESCRIPTIONS: Dict[str, List[str]] = {
    "Common":    ["A plain {type} worn by countless adventurers before you.",
                  "A sturdy {type} — nothing more, nothing less."],
    "Uncommon":  ["A finely made {type} that carries a faint pulse of mana.",
                  "A well-crafted {type} that hums softly when held."],
    "Rare":      ["A remarkable {type} humming with condensed power.",
                  "A prized {type} that many adventurers would kill for."],
    "Epic":      ["A masterwork {type} that bends the air around it.",
                  "An awe-inspiring {type} forged by a long-lost hand."],
    "Legendary": ["A legendary {type} whose story is sung across the realms.",
                  "A {type} of legend; dungeons tremble where it is carried."],
    "Mythic":    ["A mythic {type} older than the System itself; reality strains around it.",
                  "A {type} that should not exist, and yet it chose you."],
}

_LORE: Dict[str, List[str]] = {
    "low": ["It was pulled from the dust of a nameless dungeon, still warm.",
            "A dealer swears it changed hands twelve times before reaching you.",
            "Its previous owner left no name — only claw marks on the strap."],
    "high": ["Scholars have written entire tomes trying to explain its origin.",
             "It is said the System itself once whispered its true purpose.",
             "Kings bankrupted kingdoms bidding for it at a shadow auction."],
}

class ArtifactGenerator:
    """Rolls artifacts from the type/rarity tables and library word pools."""

    def __init__(self, library_dir=None):
        self.library_dir = Path(library_dir) if library_dir else None
        self.item_types = self._read_types()

    # ── word pools ──
    def _read_pool(self, filename: str, fallback: List[str]) -> List[str]:
        if self.library_dir is not None:
            path = self.library_dir / filename
            if path.exists():
                try:
                    lines = [
                        ln.strip() for ln in
                        path.read_text(encoding="utf-8").splitlines()
                        if ln.strip()
                    ]
                except OSError:
                    lines = []
                if lines:
                    return lines
        return list(fallback)

    def _read_types(self) -> List[str]:
        """Item types come from library/item_types.txt when filled in.
        Unknown types simply fall back to the generic stat bias."""
        types = self._read_pool("item_types.txt", list(ITEM_TYPES))
        return [t.title() for t in types] or list(ITEM_TYPES)

    # ── rolls ──
    def roll_rarity(self, difficulty: Optional[str] = None) -> str:
        """Weighted rarity roll — from the difficulty loot table when a
        mission difficulty is given, otherwise from the base weights."""
        table = DIFFICULTY_LOOT_TABLE.get(str(difficulty or "").strip().upper())
        if table:
            rarities, weights = zip(*table)
            return random.choices(list(rarities), weights=list(weights))[0]
        return random.choices(RARITIES, weights=RARITY_WEIGHTS)[0]

    def roll_shop_rarity(self) -> str:
        """Shop shelves are almost always Common, sometimes Uncommon,
        rarely Rare — anything higher must be earned or fused."""
        rarities, weights = zip(*SHOP_RARITY_TABLE)
        return random.choices(list(rarities), weights=list(weights))[0]

    def price(self, rarity: str, level: int = 1) -> int:
        """Shop price in gold for a rarity/level combination."""
        base = RARITY_BASE_PRICES.get(rarity, 60)
        scale = 1 + 0.25 * (max(1, int(level)) - 1)
        return max(1, int(round(base * scale * random.uniform(0.9, 1.1))))

    def generate(self, rarity: Optional[str] = None, difficulty: Optional[str] = None,
                 level: int = 1) -> Dict[str, Any]:
        """Roll one complete artifact as a plain dict ready for storage.

        `rarity` wins when it names a known rarity; otherwise the rarity is
        rolled — from the difficulty loot table when a difficulty is given."""
        rarity = rarity if rarity in RARITIES else self.roll_rarity(difficulty)
        level = max(1, int(level))
        itype = random.choice(self.item_types)
        stats = self._roll_stats(itype, rarity, level)
        return {
            "name": itype,
            "item_type": itype,
            "rarity": rarity,
            "level": level,
            "stats": stats,
            "description": self._describe(rarity, itype),
            "story": self._lore(rarity),
        }

    def _roll_stats(self, itype: str, rarity: str, level: int) -> Dict[str, int]:
        """Roll the artifact's stat types and their starting values.

        The candidate pool is the item type's stat bias, extended by the
        special stat kinds: every main stat also offers a worth_<stat>
        candidate (a fraction of its weight) and every pool contains a
        temp_points candidate. Rarity decides how many different stats the
        artifact rolls at once."""
        bias = ITEM_TYPES.get(itype, GENERIC_BIAS)
        keys: List[str] = []
        weights: List[float] = []
        for stat, weight in bias.items():
            keys.append(stat)
            weights.append(float(weight))
            if stat in MAIN_STATS:
                keys.append(f"{WORTH_PREFIX}{stat}")
                weights.append(float(weight) * WORTH_STAT_WEIGHT_FACTOR)
        keys.append(TEMP_POINTS_KEY)
        weights.append(TEMP_POINTS_WEIGHT)

        count = min(RARITY_STAT_COUNTS.get(rarity, 1), len(keys))
        picked: List[str] = []
        for _ in range(count):
            stat = random.choices(keys, weights=weights)[0]
            picked.append(stat)
            index = keys.index(stat)
            keys.pop(index)
            weights.pop(index)
        return {stat: self.roll_stat_value(stat, rarity, level) for stat in picked}

    def roll_stat_value(self, stat: str, rarity: str, level: int) -> int:
        """Roll the starting value for one stat entry."""
        if is_worth_stat(stat):
            # Extra DG per point — gently scaling, ignores level.
            return max(1, random.randint(1, 2) * RARITY_DETAIL_SCALE.get(rarity, 1))
        if stat == TEMP_POINTS_KEY:
            return random.randint(1, RARITY_DETAIL_SCALE.get(rarity, 1))
        if stat in DETAILED_STATS:
            # Direct detailed rolls scale gently and ignore level.
            detail_mult = RARITY_DETAIL_SCALE.get(rarity, 1)
            return max(1, int(round(random.randint(1, 5) * detail_mult)))
        mult = RARITY_MULTIPLIER.get(rarity, 1)
        level_scale = 1 + 0.1 * (level - 1)
        return max(1, int(round(random.randint(1, 5) * mult * level_scale)))

    def reroll_stat_values(self, stats: Dict[str, int], rarity: str, level: int) -> Dict[str, int]:
        """Keep the same stat types but roll fresh starting numbers."""
        return {key: self.roll_stat_value(key, rarity, level) for key in stats}

    def upgrade_roll(self, stat: str, rarity: str) -> Dict[str, Any]:
        """One upgrade: a random amount (low or high roll) for one stat.

        Returns {'amount': int, 'high': bool}."""
        if is_worth_stat(stat):
            if random.random() < 0.5:
                return {"amount": random.randint(1, 2), "high": False}
            return {"amount": random.randint(2, 5), "high": True}
        if stat == TEMP_POINTS_KEY:
            if random.random() < 0.5:
                return {"amount": 1, "high": False}
            return {"amount": random.randint(1, 2), "high": True}
        if stat in DETAILED_STATS:
            scale = max(1, RARITY_DETAIL_SCALE.get(rarity, 1))
            if random.random() < 0.5:
                return {"amount": max(1, random.randint(1, max(1, scale // 2))), "high": False}
            return {"amount": random.randint(1, scale) * 2, "high": True}
        mult = RARITY_MULTIPLIER.get(rarity, 1)
        if random.random() < 0.5:
            return {"amount": max(1, random.randint(1, 2) * mult), "high": False}
        return {"amount": max(1, random.randint(3, 5) * mult), "high": True}

    # ── workshop prices ──
    def upgrade_cost(self, rarity: str, upgrade_level: int) -> int:
        """Gold price of the next upgrade (0-based: level 0 → first upgrade)."""
        base = RARITY_BASE_PRICES.get(rarity, 60)
        return max(1, int(round(base * (0.15 + 0.10 * max(0, int(upgrade_level))))))

    def unupgrade_refund(self, rarity: str, paid_cost: int) -> int:
        """Gold refunded when an upgrade is taken back off."""
        return max(1, int(round(max(0, int(paid_cost)) * UNUPGRADE_REFUND)))

    def reroll_stats_cost(self, rarity: str) -> int:
        """Gold price of rerolling the stat types entirely."""
        return max(1, int(round(RARITY_BASE_PRICES.get(rarity, 60) * 0.5)))

    def reroll_values_cost(self, rarity: str) -> int:
        """Gold price of rerolling the values while keeping the stat types.

        Deliberately expensive — and unlike upgrades, this gold is gone."""
        return max(1, int(round(RARITY_BASE_PRICES.get(rarity, 60) * 0.75)))


    def _describe(self, rarity: str, itype: str) -> str:
        template = random.choice(_DESCRIPTIONS.get(rarity, _DESCRIPTIONS["Common"]))
        return template.format(type=itype)

    def _lore(self, rarity: str) -> str:
        tier = "high" if rarity in ("Epic", "Legendary", "Mythic") else "low"
        return random.choice(_LORE[tier])