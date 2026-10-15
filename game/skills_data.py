"""Ability definitions loaded from data/abilities.txt.

The whole ability tree is data-driven: skill roots and upgrades live in
a plain text file (see data/abilities.txt for the format and a legend),
node positions are computed from the `requires` graph, and progress is
stored in the database. Adding or retuning an ability means editing a
text block - no layout code to touch.
"""
from dataclasses import dataclass
from typing import Dict, Tuple

from . import content, settings


@dataclass(frozen=True)
class UpgradeSpec:
    name: str
    level_req: int
    cost: int
    stat_boost: Dict[str, float]
    description: str
    requires: Tuple[str, ...] = ()      # upgrade names that must be unlocked first
    glyph: str = "mastery"              # key into the tree's glyph drawing code


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    base_stats: Dict[str, float]
    icon: str                           # filename inside icons/
    max_level: int = 10
    upgrades: Tuple[UpgradeSpec, ...] = ()


def _load_skills():
    entries = content.parse_named(settings.DATA_DIR, "abilities.txt")

    # upgrades first: `requires` is written with entry keys, but progress is
    # stored by display name, so keys must resolve to names.
    upgrade_specs = {}
    for key, entry in entries.items():
        if "upgrade_of" not in entry:
            continue
        upgrade = UpgradeSpec(
            name=content.as_str(entry, "name", key),
            level_req=content.as_int(entry, "level_req", 1),
            cost=content.as_int(entry, "cost", 50),
            stat_boost=content.as_stat_map(entry, "boost"),
            description=content.as_str(entry, "desc"),
            requires=content.as_list(entry, "requires"),
            glyph=content.as_str(entry, "glyph", "mastery"),
        )
        upgrade_specs[key] = upgrade

    def display_name(ref):
        spec = upgrade_specs.get(ref)
        return spec.name if spec else ref     # tolerate old name-based data

    upgrade_specs = {
        key: UpgradeSpec(u.name, u.level_req, u.cost, u.stat_boost, u.description,
                         tuple(display_name(r) for r in u.requires), u.glyph)
        for key, u in upgrade_specs.items()
    }

    skills = []
    for key, entry in entries.items():
        if "base" not in entry:
            continue
        upgrades = tuple(spec for ukey, spec in upgrade_specs.items()
                         if entries[ukey].get("upgrade_of") == key)
        skills.append(SkillSpec(
            name=content.as_str(entry, "name", key),
            description=content.as_str(entry, "desc"),
            base_stats=content.as_stat_map(entry, "base"),
            icon=content.as_str(entry, "icon"),
            upgrades=upgrades,
        ))
    return tuple(skills)


SKILLS = _load_skills()
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

    Level scaling plus multiplicative upgrade boosts, with special
    damage/mana stacking.
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

