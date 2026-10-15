"""Skill tree content and layout.

Skills and upgrades are declared as data with `requires` edges; node
positions are computed from the graph (BFS depth -> row), so adding a new
skill or upgrade never touches layout code. The old version hardcoded
pixel positions in a dict rebuilt every frame and carried a parallel
"unlocked_paths" list that duplicated the same information.
"""
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class UpgradeSpec:
    name: str
    level_req: int
    cost: int
    stat_boost: Dict[str, float]
    description: str
    requires: Tuple[str, ...] = ()      # upgrade names that must be unlocked first
    glyph: str = "mastery"              # key into the GLYPH drawing functions


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    base_stats: Dict[str, float]
    icon: str                           # filename inside icons/
    max_level: int = 10
    upgrades: Tuple[UpgradeSpec, ...] = ()


FIREBALL = SkillSpec(
    "Fireball", "Launches a ball of fire at enemies",
    {"damage": 5, "mana_cost": 50}, "fireball.png",
    upgrades=(
        UpgradeSpec("Fireball Mastery", 2, 50,
                    {"damage": 1.2, "mana_cost": 0.9},
                    "Master the basics of fire manipulation",
                    glyph="mastery"),
        UpgradeSpec("Inferno", 3, 100,
                    {"damage": 1.5, "burn_duration": 5, "burn_damage": 20},
                    "Transform fireball into a lingering inferno that burns enemies over time",
                    requires=("Fireball Mastery",), glyph="flame"),
        UpgradeSpec("Explosion", 3, 100,
                    {"damage": 1.3, "area": 2.0, "knockback": 5},
                    "Convert fireball into an explosive blast that knocks back enemies",
                    requires=("Fireball Mastery",), glyph="burst"),
        UpgradeSpec("True Fire", 5, 200,
                    {"damage": 2.0, "burn_damage": 40, "area": 3.0},
                    "All fire abilities double damage, your flame turns a hue of white",
                    requires=("Inferno",), glyph="star"),
        UpgradeSpec("Cluster", 5, 200,
                    {"damage": 1.8, "area": 3.0, "knockback": 8},
                    "Release a chain of explosions that ripple outward",
                    requires=("Explosion",), glyph="cluster"),
        UpgradeSpec("Meteor Shower", 9, 1200,
                    {"damage": 7.0, "area": 30, "knockback": 14},
                    "Call down a Meteor Shower that deals massive damage and knocks back enemies",
                    requires=("True Fire", "Cluster"), glyph="meteor"),
    ),
)

ICE_SHARD = SkillSpec(
    "Ice Shard", "Fires a piercing shard of ice",
    {"damage": 30, "mana_cost": 15}, "ice_shard.jpg",
    upgrades=(
        UpgradeSpec("Ice Shard Mastery", 2, 50,
                    {"damage": 1.2, "mana_cost": 0.9},
                    "Master the basics of ice manipulation",
                    glyph="mastery"),
        UpgradeSpec("Frost", 3, 100,
                    {"damage": 1.3, "freeze_chance": 0.3, "freeze_duration": 3},
                    "Add a chance to freeze enemies in place",
                    requires=("Ice Shard Mastery",), glyph="snow"),
        UpgradeSpec("Pierce", 3, 100,
                    {"damage": 1.4, "penetration": 3, "chain_hits": 2},
                    "Shard pierces through multiple enemies",
                    requires=("Ice Shard Mastery",), glyph="arrow"),
        UpgradeSpec("Glacial", 5, 200,
                    {"damage": 1.6, "freeze_chance": 0.5, "freeze_duration": 5, "area": 2.0},
                    "Create an expanding ice field that slows enemies",
                    requires=("Frost",), glyph="shield"),
        UpgradeSpec("Chain", 5, 200,
                    {"damage": 1.8, "penetration": 5, "chain_hits": 4, "chain_damage": 0.8},
                    "Shard bounces between multiple targets with increasing damage",
                    requires=("Pierce",), glyph="chain"),
        UpgradeSpec("Ice Age", 9, 1200,
                    {"damage": 7.0, "area": 30, "knockback": 1},
                    "Create an ice age that freezes all enemies in the area",
                    requires=("Glacial", "Chain"), glyph="wave"),
    ),
)

SKILLS = (FIREBALL, ICE_SHARD)

# -------------------------------------------------------------- layout

ROW_SPACING = 190.0      # vertical distance between tree rows
COL_SPACING = 280.0      # horizontal distance between nodes in a row
BRANCH_SPACING = 1300.0  # horizontal distance between skill roots


def upgrade_depths(skill):
    """Depth of every upgrade (0 for the mastery row, 1 for the next, ...)."""
    by_name = {u.name: u for u in skill.upgrades}
    depths = {}

    def depth(name, seen=()):
        if name in depths:
            return depths[name]
        if name in seen:          # guard against cycles in the data
            return 0
        upgrade = by_name.get(name)
        if upgrade is None or not upgrade.requires:
            depths[name] = 0
        else:
            depths[name] = 1 + max(depth(req, seen + (name,)) for req in upgrade.requires)
        return depths[name]

    for upgrade in skill.upgrades:
        depth(upgrade.name)
    return depths


def compute_layout():
    """World-space position of every node, keyed by name.

    Skill roots sit on a row; each upgrade row is centered under its skill.
    """
    positions = {}
    for index, skill in enumerate(SKILLS):
        root_x = (index - (len(SKILLS) - 1) / 2) * BRANCH_SPACING
        positions[skill.name] = (root_x, 0.0)

        depths = upgrade_depths(skill)
        rows = {}
        for upgrade in skill.upgrades:
            rows.setdefault(depths[upgrade.name], []).append(upgrade)

        for depth, upgrades in rows.items():
            count = len(upgrades)
            for i, upgrade in enumerate(upgrades):
                x = root_x + (i - (count - 1) / 2) * COL_SPACING
                positions[upgrade.name] = (x, (depth + 1) * ROW_SPACING)
    return positions


def edges():
    """All connector edges as (from_name, to_name) pairs.

    Upgrades without requirements connect to their skill root.
    """
    result = []
    for skill in SKILLS:
        for upgrade in skill.upgrades:
            sources = upgrade.requires or (skill.name,)
            for source in sources:
                result.append((source, upgrade.name))
    return result


def skill_by_name(name):
    for skill in SKILLS:
        if skill.name == name:
            return skill
    return None


def upgrade_owner(name):
    """Return (skill, upgrade) for an upgrade name, or (None, None)."""
    for skill in SKILLS:
        for upgrade in skill.upgrades:
            if upgrade.name == name:
                return skill, upgrade
    return None, None


# ------------------------------------------------- effective stat calculation

def current_stats(skill, level, active_names):
    """Effective stats of a skill at a level with the given active upgrades.

    Ported from the old Skill.get_current_stats(): level scaling plus
    multiplicative upgrade boosts, with special damage/mana stacking.
    """
    stats = dict(skill.base_stats)
    active = set(active_names)
    by_name = {u.name: u for u in skill.upgrades}

    level_multiplier = 1 + (level * 0.1)
    damage_multiplier = 1.0
    mana_multiplier = 1.0

    for name in active:
        upgrade = by_name.get(name)
        if upgrade is None:
            continue
        for stat, boost in upgrade.stat_boost.items():
            if "damage" in stat.lower():
                damage_multiplier += (boost - 1)
            elif "mana" in stat.lower():
                mana_multiplier *= max(0.5, boost)
            elif stat in stats:
                stats[stat] *= boost
            else:
                stats[stat] = boost          # brand new stat (area, knockback...)

    for stat in list(stats):
        if "damage" in stat.lower():
            stats[stat] *= level_multiplier * damage_multiplier
        elif "mana" in stat.lower():
            stats[stat] *= mana_multiplier
        else:
            stats[stat] *= level_multiplier
    return stats


