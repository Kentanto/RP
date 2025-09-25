import sqlite3
import pygame
import sys
import math
import random
import time

def get_equipped_artifacts():
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT slot, artifact_id FROM equipped ORDER BY slot")
        return {slot: artifact_id for slot, artifact_id in c.fetchall()}

def set_equipped_artifact(slot, artifact_id):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE equipped SET artifact_id=? WHERE slot=?", (artifact_id, slot))
        conn.commit()

def cleanup():
    try:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except pygame.error:
        pass
    pygame.quit()
    sys.exit()

def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def create_circular_icon(image_path, size):
    icon = pygame.image.load(image_path)
    icon = pygame.transform.scale(icon, (size, size))
    
    circle_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(circle_surface, (255, 255, 255), (size//2, size//2), size//2)
    
    masked_icon = pygame.Surface((size, size), pygame.SRCALPHA)
    masked_icon.blit(icon, (0, 0))
    masked_icon.blit(circle_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    
    return masked_icon

def save_skill_progress(skill_name, level, active_upgrades, unlocked_paths):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""UPDATE skills 
                    SET level = ?, active_upgrades = ?, unlocked_paths = ?
                    WHERE name = ?""", 
                (level, str(active_upgrades), str(unlocked_paths), skill_name))
        conn.commit()

def load_skill_progress(skill_name):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT level, active_upgrades, unlocked_paths FROM skills WHERE name = ?", (skill_name,))
        result = c.fetchone()
    
    if result:
        return {
            "level": result[0],
            "active_upgrades": eval(result[1]),
            "unlocked_paths": eval(result[2])
        }
    return None

def get_edge_points(start_pos, end_pos, radius, zoom_level):
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]
    angle = math.atan2(dy, dx)
    
    scaled_radius = (radius * zoom_level)
    
    start_x = start_pos[0] + math.cos(angle) * scaled_radius
    start_y = start_pos[1] + math.sin(angle) * scaled_radius
    end_x = end_pos[0] - math.cos(angle) * scaled_radius
    end_y = end_pos[1] - math.sin(angle) * scaled_radius
    
    return (start_x, start_y), (end_x, end_y)

def round_result(result, precision=0.1):
    return round(result / precision) * precision

def update_points(new_points):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE points SET points = ?, last_updated = ?", (new_points, int(time.time())))
        conn.commit()

def draw_text(text, font, color, surface, x, y):
    textobj = font.render(text, True, color)
    surface.blit(textobj, (x, y))

def get_artifact_points():
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT artifact_points FROM points")
        return c.fetchone()[0]
    
def update_artifact_points(points):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()    
        c.execute("UPDATE points SET artifact_points = ?", (points,))
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

def get_current_points():
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("SELECT points, last_updated FROM points")
        result = c.fetchone()
        
        if result is None:
            return 600

        current_points, last_updated = result
        elapsed_seconds = int(time.time()) - last_updated
        elapsed_minutes = elapsed_seconds // 60

        if elapsed_minutes > 0:
            new_points = min(600, current_points + elapsed_minutes)
            last_updated = int(time.time())

            c.execute("UPDATE points SET points = ?, last_updated = ?", (new_points, last_updated))
            conn.commit()
            return new_points
        
        return current_points

def generate_random_artifact_name():
    import os
    import random

    # Load names and adjectives from txt files
    base_dir = os.path.dirname(__file__)
    names_path = os.path.join(base_dir, "Artifact_names.txt")
    adjectives_path = os.path.join(base_dir, "adjectives.txt")
    items_path = os.path.join(base_dir, "item_types.txt")

    with open(names_path, encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip()]
    with open(adjectives_path, encoding="utf-8") as f:
        adjectives = [line.strip() for line in f if line.strip()]
    with open(items_path, encoding="utf-8") as f:
        item_types = [line.strip() for line in f if line.strip()]
    fillers = ["of", "the", "from", "with", "for"]

    # Try generating a name that fits the length constraint
    for _ in range(10):  # Try up to 10 times
        name = random.choice(names)
        adj = random.choice(adjectives)
        item = random.choice(item_types)
        filler = random.choice(fillers)
        # Randomly choose a pattern
        patterns = [
            f"{name}'s {adj} {item}",
            f"{adj} {item} of {name}",
            f"{item} of {adj} {name}",
            f"{name}'s {item} of {adj}",
            f"{adj} {item} {filler} {name}"
        ]
        result = random.choice(patterns)
        if len(result) <= 55:
            return result
    # Fallback: just return a short pattern
    return f"{random.choice(names)}'s {random.choice(item_types)}"

# Example usage:
# artifact_name = generate_random_artifact_name()


def generate_artifact_by_level(level):
    stats = ["ATK", "DEF", "HP", "Crit Rate%", "SPD%", "Crit DMG%", "ATK%", "DEF%", "HP%"]
    name = generate_random_artifact_name()
    main_stat = random.choice(stats)

    # Level 1: Only main stat, lower roll
    if level == 1:
        main_stat_value = roll_stat(main_stat, low=True)
        return (name, main_stat, main_stat_value, None, None, None, None)
    # Level 2: Main stat (higher roll), one substat
    elif 2 <= level <= 7 :
        main_stat_value = roll_stat(main_stat, low=False)
        sub_stat1 = random.choice([s for s in stats if s != main_stat])
        sub_stat1_value = roll_stat(sub_stat1, low=True)
        return (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, None, None)
    # Level 3: Full artifact (existing logic)
    else:
        sub_stat1 = random.choice([s for s in stats if s != main_stat])
        sub_stat2 = random.choice([s for s in stats if s not in [main_stat, sub_stat1]])
        main_stat_value = roll_stat(main_stat, low=False)
        sub_stat1_value = roll_stat(sub_stat1, low=False)
        sub_stat2_value = roll_stat(sub_stat2, low=False)
        return (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value)

def roll_stat(stat_name, low=False):
    if "%" in stat_name:
        if low:
            return round(random.uniform(1.0, 3.5), 1)
        else:
            return round(random.uniform(3.0, 7.5), 1)
    else:
        if low:
            return random.randint(10, 40)
        else:
            return random.randint(30, 100)

def add_artifact(name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value):
    from athas import DB_PATH
    sub_stat1 = sub_stat1 if sub_stat1 is not None else None
    sub_stat1_value = sub_stat1_value if sub_stat1_value is not None else None
    sub_stat2 = sub_stat2 if sub_stat2 is not None else None
    sub_stat2_value = sub_stat2_value if sub_stat2_value is not None else None
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO artifacts (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value))
        conn.commit()