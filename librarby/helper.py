import sqlite3
import pygame
import sys
import math
import random
import time

class WindowState:
    def __init__(self):
        self.width, self.height = 800, 600
    
    def update(self):
        surface = pygame.display.get_surface()
        if surface is None:
            return
        new_w, new_h = surface.get_width(), surface.get_height()
        if (new_w, new_h) != (self.width, self.height):
            self.width, self.height = new_w, new_h
class Colors:    
    white = (255, 255, 255)
    black = (0, 0, 0)
    blue = (0, 0, 255)
    purple = (128, 0, 128)
    gold = (255, 215, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    orange = (255, 165, 0)
    brown = (139, 69, 19)
    gray = (128, 128, 128)
    light_gray = (200, 200, 200)
    dark_gray = (50, 50, 50)
    dark_green = (0, 100, 0)
    light_green = (150, 255, 150)
    dark_red = (139, 0, 0)
    light_red = (255, 150, 150)
    dark_yellow = (128, 128, 0)
    light_yellow = (255, 255, 150)
    dark_blue = (0, 0, 125)
    light_blue = (100, 100, 255)
    hover_color = (0, 150, 255)
    stat_text_color = (218, 165, 32)
    artifact_text_color = (147, 112, 219)

def get_equipped_artifacts():
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("SELECT slot, artifact_id FROM equipped ORDER BY slot")
        return {slot: artifact_id for slot, artifact_id in cur.fetchall()}

def set_equipped_artifact(slot, artifact_id):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        
        cur.execute("SELECT slot FROM equipped WHERE artifact_id=?", (artifact_id,))
        duplicate = cur.fetchone()
        
        if duplicate and duplicate[0] != slot:
            print(f"⚠️ Artifact {artifact_id} is already equipped in slot {duplicate[0]}.")
            return False
        
        # ✅ Safe to equip
        cur.execute("UPDATE equipped SET artifact_id=? WHERE slot=?", (artifact_id, slot))
        c.commit()
        return True

def remove_equipped_artifact(slot, artifact_id):
    from athas import DB_PATH
    with sqlite3.connect(DB_PATH) as c:
        cur = c.cursor()
        cur.execute("DELETE FROM equipped WHERE artifact_id=? AND slot=?", (artifact_id, slot))
        c.commit()

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

    base_dir = os.path.dirname(__file__)
    adjectives_path = os.path.join(base_dir, "adjectives.txt")
    items_path = os.path.join(base_dir, "item_types.txt")

    with open(adjectives_path, encoding="utf-8") as f:
        adjectives = [line.strip() for line in f if line.strip()]
    with open(items_path, encoding="utf-8") as f:
        item_types = [line.strip() for line in f if line.strip()]

    for _ in range(10):
        adj = random.choice(adjectives)
        second_adj = random.choice(adjectives)
        item = random.choice(item_types)
        patterns = [
            f"{adj} {second_adj} {item}",
            f"{item} of {adj} {second_adj}",
            f"{item} with {adj}",
            f"{item} of {adj}",
            f"{adj} {item} of {second_adj}"
        ]
        result = random.choice(patterns)
        return result

def generate_artifact_by_level(level):
    stats = ["ATK", "DEF", "HP", "Crit Rate%", "SPD%", "Crit DMG%", "ATK%", "DEF%", "HP%"]
    name = generate_random_artifact_name()
    main_stat = random.choice(stats)

    # Level 1: Only main stat, lower roll
    if level == 1:
        main_stat_value = roll_stat(main_stat)
        return (name, main_stat, main_stat_value, None, None, None, None)
    # Level 2: Main stat (higher roll), one substat
    elif 2 <= level <= 7 :
        main_stat_value = roll_stat(main_stat)
        sub_stat1 = random.choice([s for s in stats if s != main_stat])
        sub_stat1_value = roll_stat(sub_stat1)
        return (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, None, None)
    # Level 3: Full artifact
    else:
        sub_stat1 = random.choice([s for s in stats if s != main_stat])
        sub_stat2 = random.choice([s for s in stats if s not in [main_stat, sub_stat1]])
        main_stat_value = roll_stat(main_stat)
        sub_stat1_value = roll_stat(sub_stat1)
        sub_stat2_value = roll_stat(sub_stat2)
        return (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value)

def roll_stat(stat_name):
    low = random.choice([True, False])
    if "Crit Rate%" in stat_name:
        value = random.uniform(1.0, 2.0) if low else random.uniform(1.8, 3.0)
        return round(value / 100.0, 4)
    elif "%" in stat_name:
        value = random.uniform(1.0, 3.5) if low else random.uniform(3.5, 7.5)
        return round(value / 100, 4)
    else:
        return random.randint(10, 40) if low else random.randint(30, 100)

def format_stat_value(stat_name, value):
    if value is None:
        return "-"
    if "%" in stat_name:
        return f"{value * 100:.1f}%"
    else:
        return f"{int(value)}" 

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

def truncate_text(text, font, max_width):
    if font.size(text)[0] <= max_width:
        return text
    while font.size(text + "...")[0] > max_width and len(text) > 0:
        text = text[:-1]
    return text + "..."

def fit_text_to_box(text, box_width, box_height, font_name="None", max_size=55, min_size=18):
    for size in range(max_size, min_size - 1, -2):
        font = pygame.font.SysFont(font_name, size)
        text_width, text_height = font.size(text)
        if text_width <= box_width and text_height <= box_height:
            return font
    return pygame.font.SysFont(font_name, min_size)

class DropdownMenu:
    def __init__(self, options, x, y, width, height, font, selected=0):
        self.options = options
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.selected = selected
        self.open = False

    def draw(self, screen):
        pygame.draw.rect(screen, Colors.light_gray, (self.x, self.y, self.width, self.height), border_radius=5)
        text = self.font.render(self.options[self.selected], True, Colors.black)
        screen.blit(text, (self.x + 10, self.y + 5))
        if self.open:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(self.x, self.y + self.height + i * self.height, self.width, self.height)
                is_hovered = option_rect.collidepoint((mouse_x, mouse_y))
                color = Colors.light_blue if i == self.selected or is_hovered else Colors.white
                pygame.draw.rect(screen, color, option_rect, border_radius=3)
                option_text = self.font.render(option, True, Colors.black)
                screen.blit(option_text, (option_rect.x + 10, option_rect.y + 5))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            main_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if main_rect.collidepoint((mx, my)):
                self.open = not self.open
                return True
            elif self.open:
                for i, option in enumerate(self.options):
                    option_rect = pygame.Rect(self.x, self.y + self.height + i * self.height, self.width, self.height)
                    if option_rect.collidepoint((mx, my)):
                        self.selected = i
                        self.open = False
                        return True
                self.open = False
        return False

    def get_selected(self):
        return self.selected

class Checkbox:
    def __init__(self, x, y, size, checked=False, label="", font=None):
        self.x = x
        self.y = y
        self.size = size
        self.checked = checked
        self.label = label
        self.font = font

    def draw(self, screen):
        rect = pygame.Rect(self.x, self.y, self.size, self.size)
        pygame.draw.rect(screen, Colors.light_gray, rect, border_radius=3)
        if self.checked:
            pygame.draw.line(screen, Colors.green, (self.x+4, self.y+self.size//2), (self.x+self.size//2, self.y+self.size-4), 3)
            pygame.draw.line(screen, Colors.green, (self.x+self.size//2, self.y+self.size-4), (self.x+self.size-4, self.y+4), 3)
        if self.label and self.font:
            label_text = self.font.render(self.label, True, Colors.black)
            screen.blit(label_text, (self.x + self.size + 8, self.y + self.size//2 - label_text.get_height()//2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            rect = pygame.Rect(self.x, self.y, self.size, self.size)
            if rect.collidepoint((mx, my)):
                self.checked = not self.checked
                return True
        return False

    def is_checked(self):
        return self.checked

def get_artifact_stat_total(artifact, stat_name):
    total = 0
    found = False
    # main stat
    if artifact[2] == stat_name and artifact[3] is not None:
        total += artifact[3]
        found = True
    # sub stat 1
    if artifact[4] == stat_name and artifact[5] is not None:
        total += artifact[5]
        found = True
    # sub stat 2
    if artifact[6] == stat_name and artifact[7] is not None:
        total += artifact[7]
        found = True
    return total if found else None