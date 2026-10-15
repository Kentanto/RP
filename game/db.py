"""All database access for Athas.

One module, no circular imports. Every function opens a short-lived
connection via _connect(), so the rest of the code never touches sqlite3.

Skill progress is stored as JSON (the old code stored Python repr strings
and loaded them back with eval(), which was unsafe and fragile —
_parse_upgrade_names() tolerates both formats).
"""
import ast
import json
import os
import random
import sqlite3
import time
from contextlib import contextmanager

from . import settings


@contextmanager
def _connect():
    """Short-lived DB connection that always closes.

    Note: `with sqlite3.connect(...)` alone only manages the transaction —
    it never closes the connection, which leaked handles everywhere.
    """
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------- schema

def initialize_database():
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    with _connect() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    main_stat TEXT NOT NULL,
                    main_stat_value REAL NOT NULL,
                    sub_stat1 TEXT,
                    sub_stat1_value REAL,
                    sub_stat2 TEXT,
                    sub_stat2_value REAL,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    max_level INTEGER DEFAULT 20)""")

        c.execute("""CREATE TABLE IF NOT EXISTS stats
                     (id INTEGER PRIMARY KEY, level INTEGER, hp INTEGER,
                      atk INTEGER, def INTEGER, spd INTEGER, mana INTEGER)""")

        c.execute("""CREATE TABLE IF NOT EXISTS points
                     (id INTEGER PRIMARY KEY, points INTEGER, last_updated INTEGER,
                      artifact_points INTEGER DEFAULT 0)""")

        c.execute("""CREATE TABLE IF NOT EXISTS skills
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      level INTEGER DEFAULT 0,
                      active_upgrades TEXT,
                      unlocked_paths TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS equipped (
                    slot INTEGER PRIMARY KEY,
                    artifact_id INTEGER)""")
        for slot in range(1, 5):
            c.execute("SELECT COUNT(*) FROM equipped WHERE slot=?", (slot,))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO equipped (slot, artifact_id) VALUES (?, NULL)", (slot,))

        c.execute("""CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    acquired_date INTEGER DEFAULT (strftime('%s', 'now')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    buy_price INTEGER,
                    sell_price INTEGER,
                    stackable BOOLEAN DEFAULT 0,
                    max_stack INTEGER DEFAULT 1,
                    effects TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS shop_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    quantity INTEGER DEFAULT -1,
                    price INTEGER NOT NULL,
                    restock_time INTEGER,
                    FOREIGN KEY (item_id) REFERENCES items (id))""")

        c.execute("SELECT COUNT(*) FROM skills")
        if c.fetchone()[0] == 0:
            for skill_name in ("Fireball", "Ice Shard"):
                c.execute("INSERT INTO skills (name, level, active_upgrades, unlocked_paths) "
                          "VALUES (?, 0, '[]', '[]')", (skill_name,))

        c.execute("SELECT COUNT(*) FROM points")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO points (points, last_updated) VALUES (?, ?)",
                      (600, int(time.time())))


# --------------------------------------------------------------- points

def get_current_points():
    """Skill/mini-game points. Accrues +1 per minute offline, capped at 600."""
    with _connect() as conn:
        row = conn.execute("SELECT points, last_updated FROM points").fetchone()
        if row is None:
            return 600
        points, last_updated = row
        elapsed_minutes = (int(time.time()) - last_updated) // 60
        if elapsed_minutes > 0:
            points = min(600, points + elapsed_minutes)
            conn.execute("UPDATE points SET points = ?, last_updated = ?",
                         (points, int(time.time())))
            conn.commit()
        return points


def update_points(new_points):
    with _connect() as conn:
        conn.execute("UPDATE points SET points = ?, last_updated = ?",
                     (new_points, int(time.time())))
        conn.commit()


def add_points(amount):
    update_points(get_current_points() + amount)


def subtract_points(cost):
    """Spend points. Returns False (and changes nothing) if not enough."""
    with _connect() as conn:
        row = conn.execute("SELECT points FROM points").fetchone()
        current = row[0] if row else 0
        if current < cost:
            return False
        conn.execute("UPDATE points SET points = ?, last_updated = ?",
                     (current - cost, int(time.time())))
        conn.commit()
        return True


def get_artifact_points():
    with _connect() as conn:
        row = conn.execute("SELECT artifact_points FROM points").fetchone()
        return row[0] if row else 0


def update_artifact_points(points):
    with _connect() as conn:
        conn.execute("UPDATE points SET artifact_points = ?", (points,))
        conn.commit()


def spend_artifact_points(amount):
    current = get_artifact_points()
    if current >= amount:
        update_artifact_points(current - amount)
        return True
    return False


def add_artifact_points(amount):
    current = get_artifact_points()
    update_artifact_points(current + amount)
    return current + amount


# ---------------------------------------------------------------- skills

def _parse_upgrade_names(raw):
    """Tolerate both JSON and the old python-repr storage format."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        try:
            data = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return []
    names = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and "name" in item:
                names.append(item["name"])
            else:
                name = getattr(item, "name", None)
                if name:
                    names.append(name)
    return names


def load_skill_progress():
    """Return {skill_name: {"level": int, "upgrades": [upgrade names]}}."""
    progress = {}
    with _connect() as conn:
        rows = conn.execute("SELECT name, level, active_upgrades FROM skills").fetchall()
    for name, level, upgrades_raw in rows:
        progress[name] = {"level": level, "upgrades": _parse_upgrade_names(upgrades_raw)}
    return progress


def save_skill_progress(name, level, upgrade_names):
    payload = json.dumps(list(upgrade_names))
    with _connect() as conn:
        conn.execute(
            "UPDATE skills SET level = ?, active_upgrades = ?, unlocked_paths = ? WHERE name = ?",
            (level, payload, payload, name))
        conn.commit()


# ------------------------------------------------------------- equipped

def get_equipped_artifacts():
    with _connect() as conn:
        rows = conn.execute("SELECT slot, artifact_id FROM equipped ORDER BY slot").fetchall()
    return {slot: artifact_id for slot, artifact_id in rows}


def set_equipped_artifact(slot, artifact_id):
    with _connect() as conn:
        duplicate = conn.execute(
            "SELECT slot FROM equipped WHERE artifact_id=?", (artifact_id,)).fetchone()
        if duplicate and duplicate[0] != slot:
            return False
        conn.execute("UPDATE equipped SET artifact_id=? WHERE slot=?", (artifact_id, slot))
        conn.commit()
        return True


def remove_equipped_artifact(slot, artifact_id):
    with _connect() as conn:
        conn.execute("DELETE FROM equipped WHERE artifact_id=? AND slot=?", (artifact_id, slot))
        conn.commit()


# ----------------------------------------------------------- artifacts

def get_all_artifacts():
    with _connect() as conn:
        return conn.execute("SELECT * FROM artifacts").fetchall()


def get_artifact(artifact_id):
    with _connect() as conn:
        return conn.execute(
            "SELECT name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, "
            "sub_stat2, sub_stat2_value, level, exp, max_level "
            "FROM artifacts WHERE id=?", (artifact_id,)).fetchone()


def add_artifact(name, main_stat, main_stat_value,
                 sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO artifacts
               (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value,
                sub_stat2, sub_stat2_value)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value,
             sub_stat2, sub_stat2_value))
        conn.commit()


def roll_stat(stat_name):
    low = random.choice([True, False])
    if "Crit Rate%" in stat_name:
        value = random.uniform(1.0, 2.0) if low else random.uniform(1.8, 3.0)
        return round(value / 100.0, 4)
    if "%" in stat_name:
        value = random.uniform(1.0, 3.5) if low else random.uniform(3.5, 7.5)
        return round(value / 100, 4)
    return random.randint(10, 40) if low else random.randint(30, 100)


def get_artifact_stat_total(artifact, stat_name):
    total = 0
    found = False
    for stat_col, value_col in ((2, 3), (4, 5), (6, 7)):
        if artifact[stat_col] == stat_name and artifact[value_col] is not None:
            total += artifact[value_col]
            found = True
    return total if found else None


def format_stat_value(stat_name, value):
    if value is None:
        return "-"
    if "%" in stat_name:
        return f"{value * 100:.1f}%"
    return f"{int(value)}"


def level_up_artifact(artifact_id, feed_exp):
    """Feed EXP into an artifact, leveling it up and improving stats.

    Returns a result dict, or None when the artifact is missing or maxed.
    """
    with _connect() as conn:
        c = conn.cursor()
        c.execute("""SELECT level, exp, main_stat, main_stat_value,
                            sub_stat1, sub_stat1_value,
                            sub_stat2, sub_stat2_value, max_level
                     FROM artifacts WHERE id=?""", (artifact_id,))
        artifact = c.fetchone()
        if not artifact:
            return None
        (level, exp, main_stat, main_stat_value,
         sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value, max_level) = artifact
        if level >= max_level:
            return None

        exp += feed_exp
        exp_required = 100 + (level * 20)
        levels_gained = 0
        stats_improved = {}
        initial = (main_stat_value, sub_stat1_value, sub_stat2_value)

        while exp >= exp_required and level < max_level:
            exp -= exp_required
            level += 1
            levels_gained += 1
            exp_required = 100 + (level * 20)
            main_stat_value += roll_stat(main_stat)
            if level % 4 == 0:
                candidates = [(s, v) for s, v in
                              ((sub_stat1, "sub1"), (sub_stat2, "sub2")) if s]
                if candidates:
                    _, chosen = random.choice(candidates)
                    if chosen == "sub1":
                        sub_stat1_value += roll_stat(sub_stat1)
                    else:
                        sub_stat2_value += roll_stat(sub_stat2)

        if main_stat_value > initial[0]:
            stats_improved["main"] = ("main", main_stat, initial[0], main_stat_value)
        if sub_stat1 and sub_stat1_value and sub_stat1_value > initial[1]:
            stats_improved["sub1"] = ("sub1", sub_stat1, initial[1], sub_stat1_value)
        if sub_stat2 and sub_stat2_value and sub_stat2_value > initial[2]:
            stats_improved["sub2"] = ("sub2", sub_stat2, initial[2], sub_stat2_value)

        c.execute("""UPDATE artifacts
                     SET level=?, exp=?, main_stat_value=?, sub_stat1_value=?, sub_stat2_value=?
                     WHERE id=?""",
                  (level, exp, main_stat_value, sub_stat1_value, sub_stat2_value, artifact_id))
        conn.commit()

    return {
        "levels_gained": levels_gained,
        "stats_improved": list(stats_improved.values()),
        "new_level": level,
        "exp": exp,
        "exp_required": exp_required,
    }


# ---------------------------------------------- artifact name generation

_FALLBACK_ADJECTIVES = [
    "Ancient", "Blazing", "Cursed", "Dreadful", "Ethereal", "Feral", "Gleaming",
    "Hollow", "Infernal", "Jagged", "Keen", "Luminous", "Molten", "Noble",
    "Ominous", "Prismatic", "Quiet", "Runic", "Sacred", "Turbo", "Vengeful",
    "Whispering", "Zealous",
]
_FALLBACK_ITEM_TYPES = [
    "Amulet", "Band", "Charm", "Crown", "Emblem", "Fang", "Grasp", "Helm",
    "Idol", "Locket", "Pendant", "Ring", "Sigil", "Talisman", "Vestige", "Wraps",
]


def _load_wordlist(filename, fallback):
    path = os.path.join(settings.WORDLISTS_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        return words or fallback
    except OSError:
        return fallback


def generate_random_artifact_name():
    adjectives = _load_wordlist("adjectives.txt", _FALLBACK_ADJECTIVES)
    item_types = _load_wordlist("item_types.txt", _FALLBACK_ITEM_TYPES)
    adj = random.choice(adjectives)
    second_adj = random.choice(adjectives)
    item = random.choice(item_types)
    return random.choice([
        f"{adj} {second_adj} {item}",
        f"{item} of {adj} {second_adj}",
        f"{item} with {adj}",
        f"{item} of {adj}",
        f"{adj} {item} of {second_adj}",
    ])


def generate_artifact_by_level(level):
    stats = ["ATK", "DEF", "HP", "Crit Rate%", "SPD%", "Crit DMG%", "ATK%", "DEF%", "HP%"]
    name = generate_random_artifact_name()
    main_stat = random.choice(stats)
    if level == 1:
        return (name, main_stat, roll_stat(main_stat), None, None, None, None)
    if 2 <= level <= 7:
        sub_stat1 = random.choice([s for s in stats if s != main_stat])
        return (name, main_stat, roll_stat(main_stat), sub_stat1, roll_stat(sub_stat1), None, None)
    sub_stat1 = random.choice([s for s in stats if s != main_stat])
    sub_stat2 = random.choice([s for s in stats if s not in (main_stat, sub_stat1)])
    return (name, main_stat, roll_stat(main_stat), sub_stat1, roll_stat(sub_stat1),
            sub_stat2, roll_stat(sub_stat2))


# ------------------------------------------------------- inventory / shop

def get_inventory_items():
    with _connect() as conn:
        return conn.execute("""
            SELECT items.id, items.name, items.description, items.type, items.rarity,
                   inventory.quantity
            FROM inventory
            JOIN items ON inventory.item_id = items.id
            WHERE inventory.quantity > 0""").fetchall()


def get_shop_items():
    with _connect() as conn:
        return conn.execute("""
            SELECT items.id, items.name, items.description, items.type, items.rarity,
                   shop_inventory.price, shop_inventory.quantity
            FROM shop_inventory
            JOIN items ON shop_inventory.item_id = items.id
            WHERE shop_inventory.quantity > 0""").fetchall()


def purchase_item(item_id, price):
    """Atomically buy an item. Returns (success, message)."""
    with _connect() as conn:
        try:
            row = conn.execute("SELECT points FROM points").fetchone()
            current_points = row[0] if row else 0
            if current_points < price:
                return False, "Not enough points"
            conn.execute("UPDATE points SET points = points - ?", (price,))
            conn.execute("UPDATE shop_inventory SET quantity = quantity - 1 WHERE item_id = ?",
                         (item_id,))
            conn.execute("""
                INSERT INTO inventory (item_id, quantity) VALUES (?, 1)
                ON CONFLICT(item_id) DO UPDATE SET quantity = quantity + 1""", (item_id,))
            conn.commit()
            return True, "Purchase successful"
        except sqlite3.Error as e:
            conn.rollback()
            return False, str(e)



