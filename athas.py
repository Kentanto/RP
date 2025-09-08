import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from librarby.helper import *
import pygame
import secrets
import random
import sqlite3
import sys
import time
import threading
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = 'icons'
DB_PATH = os.path.join(base_path, 'database', 'artifacts.db')


pygame.init()
pygame.display.set_caption("Athas system")

screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
font_large = pygame.font.SysFont(None, 55)
font_medium = pygame.font.SysFont(None, 40)
font_small = pygame.font.SysFont(None, 30)
font = pygame.font.SysFont(None, 55)

ui_hover_sound = None
ui_click_sound = None
ui_back_sound = None


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
    

def initial_startup():
    fade_in()
    send_launcher_back()
    main_menu()

def send_launcher_back():
    launcher_path = os.path.join(base_path, "launcher.exe")
    if os.path.exists(launcher_path):
        parent_dir = os.path.dirname(base_path)
        destination = os.path.join(parent_dir, "launcher.exe")
        try:
            os.replace(launcher_path, destination)
        except OSError:
            try:
                import shutil
                shutil.move(launcher_path, destination)
            except:
                pass

    
def organize_files():
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.ico')
    sound_extensions = ('.wav', '.mp3', '.ogg', '.flac', '.m4a')
    icons_path = os.path.join(base_path, "icons")
    sounds_path = os.path.join(base_path, "sounds")

    
    if not os.path.exists(icons_path):
        os.makedirs(icons_path)
        
    for file in os.listdir(base_path):
        if file.lower().endswith(image_extensions):
            source = os.path.join(base_path, file)
            destination = os.path.join(icons_path, file)
            try:
                if not os.path.exists(destination):
                    os.rename(source, destination)
            except:
                os.mkdir(icons_path)
                if not os.path.exists(destination):
                    os.rename(source, destination)
        elif file.lower().endswith(sound_extensions):
            source = os.path.join(base_path, file)
            destination = os.path.join(sounds_path, file)
            try:
                if not os.path.exists(destination):
                    os.rename(source, destination)
            except:
                os.mkdir(sounds_path)
                if not os.path.exists(destination):
                    os.rename(source, destination)



def fade_out_music():
    if not pygame.mixer.get_init():
        return 
    def fade():
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 13000:
            if not pygame.get_init():
                return
            current_time = (pygame.time.get_ticks() - start_time) / 1000
            if current_time >= 10:
                volume = 0.1 * (1 - (current_time - 10) / 3)
                pygame.mixer.music.set_volume(max(0, volume))
            pygame.time.delay(100)

        if pygame.get_init():
            pygame.mixer.music.stop()

    threading.Thread(target=fade, daemon=True).start()

def fade_in():
    screen.fill(black)
    screen.blit(background_image, (0, 0))    
    bar_width = 400
    bar_height = 30
    bar_x = (screen_width - bar_width) // 2
    bar_y = screen_height - 100
    loading_time = 2700
    fade_surface = pygame.Surface((screen_width, screen_height))
    fade_surface.fill(black)
    song_durations = {
        "feelGood.mp3": 53,
        "haldis.mp3": 73,
        "spell.mp3": 62,
        "mortals.mp3": 44,
        "worldBurn.mp3": 59,
        "shakeDown.mp3": 53,
        "disconnected.mp3": 47,
        "noSound.mp3": 73,
        "mySide.mp3": 50,
        "bornForThis.mp3": 56,
        "theEdge.mp3": 50,
        "invisible.mp3": 85,
        "myHeart.mp3": 68,
        "nekozilla.mp3": 47,
        "linked.mp3": 50,
        "ark.mp3": 53,
        "matafaka.mp3": 54,
        "whereWeStarted.mp3": 62,
        "fearless.mp3": 62,
        "brass.mp3": 55,
        "erika.mp3": 45,
        "departure.mp3": 47,
        "watchTheMoon.mp3": 61,
    }

    if pygame.mixer.get_init() is None:
        print("no audio sorry")
    else:
            pygame.mixer.init()
            music_playlist = ["feelGood.mp3",
                            "haldis.mp3",
                            "spell.mp3",
                            "mortals.mp3",
                            "worldBurn.mp3",
                            "shakeDown.mp3",
                            "disconnected.mp3",
                            "noSound.mp3",
                            "mySide.mp3",
                            "bornForThis.mp3",
                            "theEdge.mp3",
                            "invisible.mp3",
                            "myHeart.mp3",
                            "nekozilla.mp3",
                            "linked.mp3",
                            "ark.mp3",
                            "matafaka.mp3",
                            "whereWeStarted.mp3",
                            "fearless.mp3",
                            "brass.mp3",
                            "erika.mp3",
                            "departure.mp3",
                            "watchTheMoon.mp3"]
            
            random_song = random.choice(music_playlist)
            chosen_song = random_song
            loading_time = song_durations.get(chosen_song, 12) * 100
            
            if getattr(sys, 'frozen', False):
                song_path = os.path.join(os.path.dirname(sys.executable), "songs", chosen_song)
            else:
                song_path = os.path.join(os.path.dirname(__file__), "songs", chosen_song)
                
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.set_volume(0.1)
            pygame.mixer.music.play(1)



    start_time = pygame.time.get_ticks()
    last_reported_progress = -1
    running = True
    while running:
        if pygame.event.get(pygame.QUIT):
            running = False
            get_current_points()
            cleanup()
            pygame.quit()
            sys.exit()
        pygame.event.pump()
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - start_time
        progress = min(elapsed_time / loading_time, 1)
        
        current_progress = int(progress * 100)
        if current_progress != last_reported_progress and current_progress % 10 == 0:
            last_reported_progress = current_progress
        elapsed_time = current_time - start_time
        progress = min(elapsed_time / loading_time, 1)

        if progress >= 1:
            running = False

        fade_surface.set_alpha(int(255 * (1 - progress)))
        screen.blit(background_image, (0, 0))
        screen.blit(fade_surface, (0, 0))

        fill_width = int(progress * bar_width)
        pygame.draw.rect(screen, white, (bar_x, bar_y, bar_width, bar_height), 2)
        pygame.draw.rect(screen, gold, (bar_x + 2, bar_y + 2, fill_width - 4, bar_height - 4))

        loading_text = font_medium.render(f"Loading... {int(progress * 100)}%", True, white)
        text_rect = loading_text.get_rect(center=(screen_width // 2, bar_y - 30))
        screen.blit(loading_text, text_rect)

        pygame.display.flip()

background_image_path = os.path.join(base_path, "icons\\background_menu.png")
background_image = pygame.image.load(background_image_path)
background_image = pygame.transform.scale(background_image, (screen_width, screen_height))


class Button:
    def __init__(self, text, x, y, width, height, hover_color=(255, 255, 255, 128), is_back_button=False):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.hover_color = hover_color
        self.was_hovered = False  # Track previous hover state
        self.is_back_button = is_back_button  # Flag for back/leave buttons

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.is_hovered(mouse_pos)
        
        # Play hover sound when first hovering
        if is_hovered and not self.was_hovered and ui_hover_sound:
            ui_hover_sound.play()
        
        self.was_hovered = is_hovered
        
        text_surface = font.render(self.text, True, white)
        text_width = text_surface.get_width()
        text_height = text_surface.get_height()
        
        hover_width = text_width + 20
        hover_x = self.x + (self.width - hover_width) // 2

        if is_hovered:
            hover_surface = pygame.Surface((hover_width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, self.hover_color, hover_surface.get_rect())
            screen.blit(hover_surface, (hover_x, self.y))

        screen.blit(text_surface, (
            self.x + (self.width - text_width) // 2,
            self.y + (self.height - text_height) // 2
        ))

    def is_hovered(self, mouse_pos):
        return self.x <= mouse_pos[0] <= self.x + self.width and self.y <= mouse_pos[1] <= self.y + self.height

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered(pygame.mouse.get_pos()):
                # Play appropriate click sound
                if self.is_back_button and ui_back_sound:
                    ui_back_sound.play()
                elif ui_click_sound:
                    ui_click_sound.play()
                return True
        return False

def initialize_database():    
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS artifacts (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 main_stat TEXT NOT NULL,
                 main_stat_value REAL NOT NULL,
                 sub_stat1 TEXT NOT NULL,
                 sub_stat1_value REAL NOT NULL,
                 sub_stat2 TEXT NOT NULL,
                 sub_stat2_value REAL NOT NULL,
                 level INTEGER DEFAULT 0,
                 exp INTEGER DEFAULT 0,
                 max_level INTEGER DEFAULT 20
                 )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY, level INTEGER, hp INTEGER, atk INTEGER, def INTEGER, spd INTEGER, mana INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS points
                 (id INTEGER PRIMARY KEY, points INTEGER, last_updated INTEGER, artifact_points INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS skills
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  level INTEGER DEFAULT 0,
                  active_upgrades TEXT,
                  unlocked_paths TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS equipped (
        id INTEGER PRIMARY KEY,
        artifact_id INTEGER
    )''')
    c.execute("SELECT COUNT(*) FROM equipped")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO equipped (artifact_id) VALUES (NULL)")
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM skills")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO skills (name, level, active_upgrades, unlocked_paths) VALUES (?, ?, ?, ?)",
                 ("Fireball", 0, "[]", "[]"))
        c.execute("INSERT INTO skills (name, level, active_upgrades, unlocked_paths) VALUES (?, ?, ?, ?)",
                 ("Ice Shard", 0, "[]", "[]"))
        conn.commit()

    c.execute("SELECT COUNT(*) FROM points")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO points (points, last_updated) VALUES (?, ?)", (600, int(time.time())))
        print("Database initialized.")
        conn.commit()
        conn.close()
    else:
        print("No Changes needed.")
        conn.close()


def get_current_points():
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


def generate_random_artifact():
    artifact_names = ["Wooden Sword", "Leather Armor", "Iron Shield", "Bronze Helmet", "Cloth Robe"]
    stats = ["ATK", "DEF", "HP", "Crit Rate%", "SPD%", "Crit DMG%", "ATK%", "DEF%", "HP%"]
    
    name = random.choice(artifact_names)
    main_stat = random.choice(stats)
    sub_stat1 = random.choice([s for s in stats if s != main_stat])
    sub_stat2 = random.choice([s for s in stats if s not in [main_stat, sub_stat1]])

    main_stat_value = roll_stat(main_stat)
    sub_stat1_value = roll_stat(sub_stat1)
    sub_stat2_value = roll_stat(sub_stat2)
    
    return (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value)

def roll_stat(stat_name):
    if "%" in stat_name:
        return round(random.uniform(3.0, 7.5), 1)
    else:
        return random.randint(30, 100)

def add_artifact(name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO artifacts (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value))
        conn.commit()

def level_up_artifact(artifact_id, feed_exp):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT level, exp, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value, max_level FROM artifacts WHERE id=?", (artifact_id,))
        artifact = c.fetchone()
        
        if not artifact:
            return False
            
        level, exp, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value, max_level = artifact
        
        if level >= max_level:
            return False
        
        initial_main_value = main_stat_value
        initial_sub1_value = sub_stat1_value
        initial_sub2_value = sub_stat2_value
        
        exp += feed_exp
        exp_required = 100 + (level * 20)
        levels_gained = 0
        stats_improved = {}
        
        while exp >= exp_required and level < max_level:
            exp -= exp_required
            level += 1
            levels_gained += 1
            exp_required = 100 + (level * 20)

            if "%" in main_stat:
                main_stat_value += round(random.uniform(1.5, 3), 1)
            else:
                main_stat_value += random.randint(9, 20)

            if level % 4 == 0:
                chosen_sub = random.choice(["sub_stat1", "sub_stat2"])
                if chosen_sub == "sub_stat1":
                    if "%" in sub_stat1:
                        sub_stat1_value += round(random.uniform(4, 10), .1)
                    else:
                        sub_stat1_value += random.randint(20, 35)
                else:
                    if "%" in sub_stat2:
                        sub_stat2_value += round(random.uniform(4, 10), .1)
                    else:
                        sub_stat2_value += random.randint(20, 35)
        
        if main_stat_value > initial_main_value:
            stats_improved["main"] = ("main", main_stat, initial_main_value, main_stat_value)
        
        if sub_stat1_value > initial_sub1_value:
            stats_improved["sub1"] = ("sub1", sub_stat1, initial_sub1_value, sub_stat1_value)
            
        if sub_stat2_value > initial_sub2_value:
            stats_improved["sub2"] = ("sub2", sub_stat2, initial_sub2_value, sub_stat2_value)
        
        c.execute('''UPDATE artifacts
                    SET level=?, exp=?, main_stat_value=?, sub_stat1_value=?, sub_stat2_value=?
                    WHERE id=?''',
                (level, exp, main_stat_value, sub_stat1_value, sub_stat2_value, artifact_id))
        conn.commit()
    
    return {
        "levels_gained": levels_gained,
        "stats_improved": list(stats_improved.values()),
        "new_level": level,
        "exp": exp,
        "exp_required": exp_required
    }

def draw_text(text, font, color, surface, x, y):
    textobj = font.render(text, True, color)
    surface.blit(textobj, (x, y))

def get_artifact_points():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT artifact_points FROM points")
        return c.fetchone()[0]
    
def update_artifact_points(points):
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

def open_artifact_detail(artifact_id):
    running = True
    back_button = Button("Back", 10, 10, 100, 40, hover_color, is_back_button=True)
    
    min_invest = 50
    max_invest = 500
    current_invest = min_invest
    invest_step = 50
    
    slider_width = 300
    slider_height = 20
    slider_x = screen_width // 2 - slider_width // 2
    slider_y = screen_height - 150 
    slider_dragging = False
    
    level_button = Button("Level Up", screen_width // 2 - 100, screen_height - 100, 200, 50, (0, 150, 0, 200))
    
    showing_upgrade = False
    upgrade_info = None
    upgrade_start_time = 0
    upgrade_duration = 2000
    
    while running:
        current_time = pygame.time.get_ticks()
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value, level, exp, max_level FROM artifacts WHERE id=?", (artifact_id,))
            artifact = c.fetchone()

        if not artifact:
            return

        name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value, level, exp, max_level = artifact
        
        artifact_points = get_artifact_points()

        panel_width = int(screen_width * 0.7)
        panel_height = int(screen_height * 0.6)
        panel_x = (screen_width - panel_width) // 2
        panel_y = 50
        
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (40, 40, 40, 230), panel_surface.get_rect(), border_radius=15)
        screen.blit(panel_surface, (panel_x, panel_y))
        
        name_text = font_large.render(f"{name}", True, gold)
        screen.blit(name_text, (panel_x + (panel_width - name_text.get_width()) // 2, panel_y + 20))
        
        level_text = font_medium.render(f"Level: {level}/{max_level}", True, white)
        screen.blit(level_text, (panel_x + 30, panel_y + 80))
        
        stat_y = panel_y + 130
        stat_spacing = 50 

        main_stat_text = font_medium.render(f"Main Stat: {main_stat}", True, gold)
        main_value_text = font_medium.render(f"+{main_stat_value:.1f}", True, gold)
        screen.blit(main_stat_text, (panel_x + 30, stat_y))
        screen.blit(main_value_text, (panel_x + panel_width - 150, stat_y))
        
        sub1_stat_text = font_small.render(f"Sub Stat: {sub_stat1}", True, white)
        sub1_value_text = font_small.render(f"+{sub_stat1_value:.1f}", True, white)
        screen.blit(sub1_stat_text, (panel_x + 30, stat_y + stat_spacing))
        screen.blit(sub1_value_text, (panel_x + panel_width - 150, stat_y + stat_spacing))
        
        sub2_stat_text = font_small.render(f"Sub Stat: {sub_stat2}", True, white)
        sub2_value_text = font_small.render(f"+{sub_stat2_value:.1f}", True, white)
        screen.blit(sub2_stat_text, (panel_x + 30, stat_y + stat_spacing * 2))
        screen.blit(sub2_value_text, (panel_x + panel_width - 150, stat_y + stat_spacing * 2))
        
        exp_required = 100 + (level * 20)
        exp_ratio = min(exp / exp_required, 1.0)
        bar_width = panel_width - 60
        bar_height = 25
        bar_x = panel_x + 30
        bar_y = panel_y + panel_height - 80
        
        pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        pygame.draw.rect(screen, (100, 150, 255), (bar_x, bar_y, bar_width * exp_ratio, bar_height), border_radius=5)
        
        exp_text = font_small.render(f"EXP: {exp}/{exp_required}", True, white)
        screen.blit(exp_text, (bar_x + (bar_width - exp_text.get_width()) // 2, bar_y + 30))
        
        points_text = font_medium.render(f"Artifact Points: {artifact_points}", True, white)
        screen.blit(points_text, (screen_width - points_text.get_width() - 20, 20))
        
        if level < max_level:
            pygame.draw.rect(screen, (80, 80, 80), (slider_x, slider_y, slider_width, slider_height), border_radius=5)
            
            slider_position = slider_x + ((current_invest - min_invest) / (max_invest - min_invest)) * slider_width
            
            pygame.draw.circle(screen, (150, 150, 255), (int(slider_position), slider_y + slider_height // 2), 15)
            
            invest_text = font_small.render(f"Investment: {current_invest} points", True, white)
            screen.blit(invest_text, (slider_x + (slider_width - invest_text.get_width()) // 2, slider_y - 30))
            
            xp_gain_text = font_small.render(f"XP Gain: {current_invest * 4}", True, white)
            screen.blit(xp_gain_text, (slider_x + (slider_width - xp_gain_text.get_width()) // 2, slider_y + 30))
            
            cost_text = font_small.render(f"Cost: {current_invest} points", True, 
                                        green if artifact_points >= current_invest else red)
            screen.blit(cost_text, (level_button.x + level_button.width + 10, level_button.y + 15))
            
            level_button.draw(screen)
        else:
            max_level_text = font_medium.render("Maximum Level Reached!", True, gold)
            screen.blit(max_level_text, (screen_width // 2 - max_level_text.get_width() // 2, slider_y))

        back_button.draw(screen)
        
        if showing_upgrade and upgrade_info:
            progress = min(1.0, (current_time - upgrade_start_time) / upgrade_duration)
            
            if progress < 1.0:
                upgrade_panel = pygame.Surface((400, 300), pygame.SRCALPHA)
                pygame.draw.rect(upgrade_panel, (0, 0, 0, 180), upgrade_panel.get_rect(), border_radius=10)
                screen.blit(upgrade_panel, (screen_width // 2 - 200, screen_height // 2 - 150))
                
                level_up_text = font_medium.render(f"Level Up! +{upgrade_info['levels_gained']}", True, gold)
                screen.blit(level_up_text, (screen_width // 2 - level_up_text.get_width() // 2, screen_height // 2 - 120))
                
                y_offset = screen_height // 2 - 60
                for stat_type, stat_name, old_value, new_value in upgrade_info['stats_improved']:
                    current_value = old_value + (new_value - old_value) * progress
                    
                    if stat_type == "main":
                        stat_text = font_small.render(f"Main Stat: {stat_name}", True, gold)
                    elif stat_type == "sub1":
                        stat_text = font_small.render(f"Sub Stat: {stat_name}", True, white)
                    else:
                        stat_text = font_small.render(f"Sub Stat: {stat_name}", True, white)
                    
                    value_text = font_small.render(f"{old_value:.1f} → {current_value:.1f}", True, green)
                    
                    screen.blit(stat_text, (screen_width // 2 - 180, y_offset))
                    screen.blit(value_text, (screen_width // 2 + 50, y_offset))
                    
                    y_offset += 40
            else:
                showing_upgrade = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()

                    if level < max_level and slider_x <= mx <= slider_x + slider_width and slider_y - 10 <= my <= slider_y + slider_height + 10:
                        slider_dragging = True
                    
                    if level_button.is_hovered((mx, my)) and level < max_level:
                        if spend_artifact_points(current_invest):
                            xp_gain = current_invest * 4
                            upgrade_result = level_up_artifact(artifact_id, xp_gain)
                            
                            if pygame.mixer.get_init():
                                try:
                                    if upgrade_result and upgrade_result["levels_gained"] > 0:
                                        upgrade_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "upgrade_artifact_level_up.wav"))
                                        showing_upgrade = True
                                        upgrade_info = upgrade_result
                                        upgrade_start_time = current_time
                                    else:
                                        upgrade_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "upgrade_artifact_sound.wav"))
                                    
                                    upgrade_sound.play()
                                except:
                                    pass

                    if back_button.is_hovered((mx, my)):
                        running = False
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    slider_dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if slider_dragging and level < max_level:
                    mx, my = pygame.mouse.get_pos()
                    if mx < slider_x:
                        current_invest = min_invest
                    elif mx > slider_x + slider_width:
                        current_invest = max_invest
                    else:
                        ratio = (mx - slider_x) / slider_width
                        current_invest = min_invest + int((max_invest - min_invest) * ratio)
                        current_invest = int(round(current_invest / invest_step)) * invest_step
            
            elif event.type == pygame.KEYDOWN:
                if level < max_level:
                    if event.key == pygame.K_LEFT:
                        current_invest = max(min_invest, current_invest - invest_step)
                    elif event.key == pygame.K_RIGHT:
                        current_invest = min(max_invest, current_invest + invest_step)
                    elif event.key == pygame.K_RETURN:
                        if spend_artifact_points(current_invest):
                            xp_gain = current_invest * 4
                            upgrade_result = level_up_artifact(artifact_id, xp_gain)
                            
                            if pygame.mixer.get_init():
                                try:
                                    if upgrade_result and upgrade_result["levels_gained"] > 0:
                                        upgrade_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "upgrade_artifact_level_up.wav"))
                                        showing_upgrade = True
                                        upgrade_info = upgrade_result
                                        upgrade_start_time = current_time
                                    else:
                                        upgrade_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "upgrade_artifact_sound.wav"))
                                    
                                    upgrade_sound.play()
                                except:
                                    pass

            if level < max_level:
                min_label = font_small.render(f"{min_invest}", True, light_gray)
                max_label = font_small.render(f"{max_invest}", True, light_gray)
                screen.blit(min_label, (slider_x - 10, slider_y + 25))
                screen.blit(max_label, (slider_x + slider_width - 10, slider_y + 25))
                
                for i in range(min_invest, max_invest + 1, invest_step * 2):
                    tick_x = slider_x + ((i - min_invest) / (max_invest - min_invest)) * slider_width
                    tick_height = 8 if i % 100 == 0 else 5
                    pygame.draw.line(screen, light_gray, (tick_x, slider_y + slider_height + 2), 
                                    (tick_x, slider_y + slider_height + 2 + tick_height), 2)

            pygame.display.update()




def view_artifacts():
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color, is_back_button=True)
    scroll_y = 0
    scroll_speed = 20
    items_per_row = 3
    box_width = 220
    box_padding = 20
    box_height = 160

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM artifacts")
    artifacts = c.fetchall()
    conn.close()
    
    artifact_boxes = []

    hovered_box_index = -1
    last_hovered_box_index = -1
    
    artifact_points = get_artifact_points()

    while True:
        screen.fill(white)
        screen.blit(background_image, (0, 0))

        title_text = font_large.render("Artifacts", True, gold)
        screen.blit(title_text, (screen_width // 2 - title_text.get_width() // 2, 30))
        
        points_text = font_medium.render(f"Artifact Points: {artifact_points}", True, white)
        screen.blit(points_text, (screen_width - points_text.get_width() - 20, 20))

        start_x = (screen_width - (box_width * items_per_row + box_padding * (items_per_row-1))) // 2
        start_y = 100 + scroll_y

        artifact_boxes.clear()
        
        # Get current mouse position for hover detection
        mouse_pos = pygame.mouse.get_pos()
        hovered_box_index = -1

        for i, artifact in enumerate(artifacts):
            row = i // items_per_row
            col = i % items_per_row
            x = start_x + col * (box_width + box_padding)
            y = start_y + row * (box_height + box_padding)
            box = pygame.Rect(x, y, box_width, box_height)
            artifact_boxes.append((box, artifact[0]))
            
            # Check if this box is being hovered
            is_hovered = box.collidepoint(mouse_pos)
            if is_hovered:
                hovered_box_index = i
            
            # Draw a nicer box with gradient and border
            box_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            
            # Change background color when hovered
            if is_hovered:
                pygame.draw.rect(box_surface, (70, 70, 70, 220), box_surface.get_rect(), border_radius=10)
                pygame.draw.rect(box_surface, (100, 150, 255, 150), box_surface.get_rect(), width=3, border_radius=10)
            else:
                pygame.draw.rect(box_surface, (50, 50, 50, 200), box_surface.get_rect(), border_radius=10)
                pygame.draw.rect(box_surface, (80, 80, 80, 100), box_surface.get_rect(), width=2, border_radius=10)
            
            screen.blit(box_surface, (x, y))

            main_stat_value = artifact[3]
            sub_stat1_value = artifact[5]
            sub_stat2_value = artifact[7]
            
            if isinstance(main_stat_value, float):
                main_stat_value = f"{main_stat_value:.1f}"
            if isinstance(sub_stat1_value, float):
                sub_stat1_value = f"{sub_stat1_value:.1f}"
            if isinstance(sub_stat2_value, float):
                sub_stat2_value = f"{sub_stat2_value:.1f}"

            name_text = font_small.render(f"{artifact[1]}", True, gold)
            level_text = font_small.render(f"Lv.{artifact[8]}/{artifact[10]}", True, artifact_text_color)
            main_stat_text = font_small.render(f"{artifact[2]}: +{main_stat_value}", True, white)
            sub_stat1_text = font_small.render(f"{artifact[4]}: +{sub_stat1_value}", True, light_gray)
            sub_stat2_text = font_small.render(f"{artifact[6]}: +{sub_stat2_value}", True, light_gray)

            screen.blit(name_text, (x + 10, y + 10))
            screen.blit(level_text, (x + box_width - level_text.get_width() - 10, y + 10))
            screen.blit(main_stat_text, (x + 10, y + 40))
            screen.blit(sub_stat1_text, (x + 10, y + 70))
            screen.blit(sub_stat2_text, (x + 10, y + 95)) 
            
            # Add a small "click to view" hint
            hint_text = font_small.render("Click to view", True, (150, 150, 150))
            screen.blit(hint_text, (x + (box_width - hint_text.get_width()) // 2, y + box_height - 30))

        # Play hover sound when first hovering over an artifact box
        if hovered_box_index != -1 and hovered_box_index != last_hovered_box_index and ui_hover_sound:
            ui_hover_sound.play()
        
        last_hovered_box_index = hovered_box_index

        Back_Button.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEWHEEL:
                scroll_y += event.y * scroll_speed
                max_rows = (len(artifacts) + items_per_row - 1) // items_per_row
                min_scroll = -((max_rows * (box_height + box_padding)) - screen_height + 150)
                scroll_y = max(min_scroll, min(0, scroll_y))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                for box, artifact_id in artifact_boxes:
                    if box.collidepoint(pos):
                        # Play click sound for artifacts
                        if ui_click_sound:
                            ui_click_sound.play()
                        
                        open_artifact_detail(artifact_id)
                        # Refresh artifact points after returning from detail view
                        artifact_points = get_artifact_points()
                        # Refresh artifacts list in case they were upgraded
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT * FROM artifacts")
                        artifacts = c.fetchall()
                        conn.close()
                        break
            if Back_Button.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                status_window()

        pygame.display.flip()





def generate_math_equation_easy(equation_length):
    equation_length+=2
    math_numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    math_operators = ["*", "-", "+", "/"]
    final_equation = []    
    i = 0
    num_of_open_parens = 0
    
    while i < equation_length:
        if i % 2 == 0:
            number = secrets.choice(math_numbers)
            
            if random.random() > 0.9:
                exponent = str(random.randint(2, 4))
                final_equation.append(f"{number}**{exponent}")
            else:
                final_equation.append(number)
            
            if random.random() > 0.8 and i < equation_length - 2:
                final_equation.insert(-1, "(")
                num_of_open_parens += 1
                
        else:
            if num_of_open_parens > 0 and random.random() > 0.8 and i < equation_length - 1:
                final_equation.append(")")
                num_of_open_parens -= 1
                
            operator = secrets.choice(math_operators)
            
            if (final_equation and final_equation[-1] in math_operators):
                operator = secrets.choice(["+", "-"])
            
            final_equation.append(operator)
        
        i += 1
        
    if num_of_open_parens > 0:
        final_equation.append(")")
    while final_equation and final_equation[-1] in math_operators:
        final_equation.pop()
    
    equation = "".join(final_equation)
    
    return equation


def round_result(result, precision=0.1):
    return round(result / precision) * precision

def update_points(new_points):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE points SET points = ?, last_updated = ?", (new_points, int(time.time())))
        conn.commit()

def insufficient_points_message():
    message = font_medium.render("Not enough points!", True, red)
    screen.blit(message, (screen_width//2 - message.get_width()//2, screen_height - 100))
    pygame.display.flip()
    pygame.time.wait(1500)
    screen.fill(white)
    screen.blit(background_image, (0, 0))
    pygame.display.flip()
    minigames_menu()

def subtract_points(point_cost):
    current_points = get_current_points()
    if current_points >= point_cost:
        update_points(current_points - point_cost)
    else:
        insufficient_points_message()
        return 0

def add_points(point_reward):
    current_points = get_current_points()
    update_points(current_points + point_reward)

def math_activity_menu():
    current_points = get_current_points()
    
    Easy_button = Button("Easy", screen_width // 2 - 165, screen_height // 2 - 140, 330, 50, hover_color)    
    Medium_button = Button("Locked-Medium-Locked LV: 8", screen_width // 2 - 165, screen_height // 2 - 70, 330, 50, hover_color)
    Hard_button = Button("Locked-Hard-Locked Lv: 15", screen_width // 2 - 165, screen_height // 2 - 0, 330, 50, hover_color)
    Extreme_button = Button("Locked-Extreme-Locked LV: 25", screen_width // 2 - 165, screen_height // 2 + 70, 330, 50, hover_color)
    Leave_button = Button("Leave", screen_width // 2 - 165, screen_height // 2 + 140, 330, 50, hover_color, is_back_button=True)
    
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        points_text = font_medium.render(f"Points: {current_points}/{20}", True, white)
        screen.blit(points_text, (screen_width - 200, 50))
        
        Easy_button.draw(screen)
        Medium_button.draw(screen)
        Hard_button.draw(screen)
        Extreme_button.draw(screen)
        Leave_button.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
                pygame.quit()
                sys.exit()
                
            match event:
                case _ if Easy_button.is_clicked(event):
                    if current_points >= 20:
                        subtract_points(20)                        
                        math_game_window(1)
                        
                case _ if Medium_button.is_clicked(event):
                    pass
                    
                case _ if Hard_button.is_clicked(event):
                    pass
                    
                case _ if Extreme_button.is_clicked(event):
                    pass
                    
                case _ if Leave_button.is_clicked(event):
                    screen.fill(white)
                    screen.blit(background_image, (0, 0))
                    pygame.display.flip()
                    minigames_menu()
                    
                case _ if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    screen.fill(white)
                    screen.blit(background_image, (0, 0))
                    pygame.display.flip()
                    minigames_menu()
        
        pygame.display.flip()
    
    return True

def math_game_window(math_difficulty):
    mathed = math_difficulty
    user_input = ""
    equation = generate_math_equation_easy(math_difficulty)
    leave_button = Button("Leave", 10, 10, 100, 40, hover_color, is_back_button=True)
    
    try:
        correct_answer = eval(equation)
        rounded_answer = round_result(correct_answer, precision=0.1)
    except Exception as e:
        print(f"Generated an invalid equation: {equation}")
        print("Error:", e)
        math_game_window(math_difficulty)

    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        equation_surface = font.render(f"Solve: {equation}", True, white)
        screen.blit(equation_surface, (screen_width // 2 - equation_surface.get_width() // 2, 150))

        user_input_surface = font.render(user_input, True, white)
        screen.blit(user_input_surface, (screen_width // 2 - user_input_surface.get_width() // 2, 300))

        leave_button.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                add_points(20)
                cleanup()
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        user_answer = float(user_input)
                        if round_result(user_answer, precision=0.1) == rounded_answer:
                            screen.fill(white)
                            screen.blit(background_image, (0, 0))
                            
                            artifact = generate_random_artifact()
                            add_artifact(*artifact)
                            
                            artifact_points_reward = 100
                            add_artifact_points(artifact_points_reward)
                            
                            panel_width = 600
                            panel_height = 350
                            panel_x = (screen_width - panel_width) // 2
                            panel_y = 120
                            
                            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
                            pygame.draw.rect(panel_surface, (40, 40, 40, 230), panel_surface.get_rect(), border_radius=15)
                            screen.blit(panel_surface, (panel_x, panel_y))
                            
                            result_text = "Correct!"
                            result_surface = font_large.render(result_text, True, (0, 255, 0))
                            screen.blit(result_surface, (screen_width // 2 - result_surface.get_width() // 2, panel_y + 30))
                            
                            name_surface = font_medium.render(f"You received: {artifact[0]}", True, gold)
                            screen.blit(name_surface, (screen_width // 2 - name_surface.get_width() // 2, panel_y + 100))
                            
                            main_stat_text = font_small.render(f"Main Stat: {artifact[1]} +{artifact[2]}", True, white)
                            screen.blit(main_stat_text, (screen_width // 2 - main_stat_text.get_width() // 2, panel_y + 150))
                            
                            sub1_text = font_small.render(f"Sub Stat: {artifact[3]} +{artifact[4]}", True, light_gray)
                            screen.blit(sub1_text, (screen_width // 2 - sub1_text.get_width() // 2, panel_y + 180))
                            
                            sub2_text = font_small.render(f"Sub Stat: {artifact[5]} +{artifact[6]}", True, light_gray)
                            screen.blit(sub2_text, (screen_width // 2 - sub2_text.get_width() // 2, panel_y + 210))
                            
                            points_text = font_medium.render(f"+{artifact_points_reward} Artifact Points", True, green)
                            screen.blit(points_text, (screen_width // 2 - points_text.get_width() // 2, panel_y + 250))
                            
                            hint_text = font_small.render("Press any key to continue...", True, white)
                            screen.blit(hint_text, (screen_width // 2 - hint_text.get_width() // 2, panel_y + 300))
                            
                            pygame.display.flip()
                            
                            waiting = True
                            while waiting:
                                for evt in pygame.event.get():
                                    if evt.type == pygame.QUIT:
                                        get_current_points()
                                        cleanup()
                                        pygame.quit()
                                        sys.exit()
                                    if evt.type == pygame.KEYDOWN or evt.type == pygame.MOUSEBUTTONDOWN:
                                        waiting = False
                        else:
                            panel_width = 600
                            panel_height = 200
                            panel_x = (screen_width - panel_width) // 2
                            panel_y = 200
                            
                            screen.fill(white)
                            screen.blit(background_image, (0, 0))
                            
                            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
                            pygame.draw.rect(panel_surface, (40, 40, 40, 230), panel_surface.get_rect(), border_radius=15)
                            screen.blit(panel_surface, (panel_x, panel_y))
                            
                            result_text = "Incorrect!"
                            result_surface = font_large.render(result_text, True, red)
                            screen.blit(result_surface, (screen_width // 2 - result_surface.get_width() // 2, panel_y + 30))
                            
                            answer_text = f"The correct answer is: {rounded_answer}"
                            answer_surface = font_medium.render(answer_text, True, white)
                            screen.blit(answer_surface, (screen_width // 2 - answer_surface.get_width() // 2, panel_y + 90))
                            
                            hint_text = font_small.render("Press any key to continue...", True, white)
                            screen.blit(hint_text, (screen_width // 2 - hint_text.get_width() // 2, panel_y + 150))
                            
                            pygame.display.flip()
                            
                            waiting = True
                            while waiting:
                                for evt in pygame.event.get():
                                    if evt.type == pygame.QUIT:
                                        get_current_points()
                                        cleanup()
                                        pygame.quit()
                                        sys.exit()
                                    if evt.type == pygame.KEYDOWN or evt.type == pygame.MOUSEBUTTONDOWN:
                                        waiting = False

                        screen.fill(white)
                        screen.blit(background_image, (0, 0))
                        pygame.display.flip()
                        subtract_points(20)
                        math_game_window(mathed)
                                       
                    except ValueError:
                        print("Invalid input. Please enter a numeric value.")
                        user_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                else:
                    user_input += event.unicode
            
            if leave_button.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                add_points(20)
                math_activity_menu()

        pygame.display.flip()

    return True

def minigames_menu():
    current_points = get_current_points()
    Math_Button = Button("Math", screen_width // 2 - 165, screen_height // 2 - 140, 330, 50, hover_color)    
    Back_Button = Button("Back", screen_width // 2 - 165, screen_height // 2 + 70, 330, 50, hover_color, is_back_button=True)
    points_text = font_medium.render(f"Points: {current_points}", True, white)
    
    while True:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        Math_Button.draw(screen)
        Back_Button.draw(screen)
        screen.blit(points_text, (screen_width - 200, 50))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
                pygame.quit()
                sys.exit()
            
            if Math_Button.is_clicked(event):
                if not math_activity_menu():
                    screen.fill(white)
                    screen.blit(background_image, (0, 0))
                    pygame.display.flip()
                    main_menu()
            
            if Back_Button.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                main_menu()
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                main_menu()
        
        pygame.display.flip()



def status_window():
    global equipped_artifact_id
    equipped_artifact_id = get_equipped_artifact()

    Back_Button = Button("Back", 10, 10, 100, 40, hover_color, is_back_button=True)
    View_Artifacts = Button("Artifacts", screen_width - 160, 10, 140, 40, hover_color)
    Skill_menu = Button("Skills", screen_width//2 - 70, 10, 140, 40, hover_color)
    
    # Equip slot area
    equip_slot_rect = pygame.Rect(screen_width//2 - 100, 500, 200, 60)
    
    Kenji = "Kenji Mizuki"
    base_stats = {
        "Level": 1,
        "CON": 10,
        "ATK": 5,
        "DEF": 10,
        "SPD": 5,
        "mana": 0,
    }
    
    artifact_points = get_artifact_points()
    
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))        
        
        # --- Calculate artifact bonus ---
        artifact_bonus = {"ATK": 0, "DEF": 0, "SPD": 0, "CON": 0, "mana": 0}
        artifact_name = None
        if equipped_artifact_id:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value FROM artifacts WHERE id=?", (equipped_artifact_id,))
                result = c.fetchone()
            if result:
                artifact_name, main_stat, main_stat_value, sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value = result
                # Map artifact stats to base stats
                stat_map = {
                    "ATK": "ATK", "DEF": "DEF", "SPD": "SPD", "HP": "CON", "mana": "mana",
                    "ATK%": "ATK", "DEF%": "DEF", "SPD%": "SPD", "HP%": "CON",
                    "Crit Rate%": "ATK", "Crit DMG%": "ATK"
                }
                for stat, value in [(main_stat, main_stat_value), (sub_stat1, sub_stat1_value), (sub_stat2, sub_stat2_value)]:
                    key = stat_map.get(stat.replace("%", ""), None)
                    if key and key in artifact_bonus:
                        artifact_bonus[key] += int(value) if not isinstance(value, float) else int(round(value))
        
        # --- Draw stats (base + artifact bonus) ---
        stat_y = 150
        for stat, base_value in base_stats.items():
            total_value = base_value + artifact_bonus.get(stat, 0)
            stat_text = font_medium.render(f"{stat}: {total_value}", True, stat_text_color)
            screen.blit(stat_text, (screen_width // 2 - 100, stat_y))
            stat_y += 40

        # Draw equip slot
        pygame.draw.rect(screen, light_gray, equip_slot_rect, border_radius=10)
        equip_text = font_medium.render("Equip Artifact", True, gray)
        screen.blit(equip_text, (equip_slot_rect.x + 20, equip_slot_rect.y + 10))
        
        # Show equipped artifact name
        if artifact_name:
            name_text = font_small.render(f"Equipped: {artifact_name}", True, gold)
            screen.blit(name_text, (equip_slot_rect.x + 20, equip_slot_rect.y + 40))

        Back_Button.draw(screen)
        Skill_menu.draw(screen)
        View_Artifacts.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
                pygame.quit()
                sys.exit()
            if Back_Button.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                main_menu()
            if View_Artifacts.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                view_artifacts()
            if Skill_menu.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                skill_tree_menu()
            # Handle equip slot click
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if equip_slot_rect.collidepoint(pygame.mouse.get_pos()):
                    selected_id = select_artifact_window()
                    if selected_id:
                        set_equipped_artifact(selected_id)
                        equipped_artifact_id = selected_id  # Update for immediate display
        
        pygame.display.flip()

def select_artifact_window():
    # Simple selection window for artifacts
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM artifacts")
    artifacts = c.fetchall()
    conn.close()
    
    selected_id = None
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        title_text = font_large.render("Select Artifact", True, gold)
        screen.blit(title_text, (screen_width // 2 - title_text.get_width() // 2, 30))
        
        for i, (artifact_id, name) in enumerate(artifacts):
            y = 100 + i * 50
            box = pygame.Rect(screen_width//2 - 150, y, 300, 40)
            pygame.draw.rect(screen, light_gray, box, border_radius=8)
            name_text = font_small.render(name, True, black)
            screen.blit(name_text, (box.x + 20, box.y + 8))
            if box.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(screen, hover_color, box, 3, border_radius=8)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if box.collidepoint(event.pos):
                        selected_id = artifact_id
                        running = False
        pygame.display.flip()
    return selected_id


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

        
@dataclass
class SkillUpgrade:
    name: str
    level_req: int
    cost: int
    stat_boost: Dict[str, float]
    description: str
    unlocks: Optional[str] = None
    requires: Optional[str] = None

@dataclass
class SkillPosition:
    position: Tuple[int, int]
    upgrade_positions: Dict[str, Tuple[int, int]]
    icons: Dict[str, str]

@dataclass
class Skill:
    name: str
    description: str
    base_stats: Dict[str, int]
    icon_path: Optional[str] = None
    level: int = 0
    max_level: int = 10
    upgrades: List[SkillUpgrade] = field(default_factory=list)
    active_upgrades: List[Dict] = field(default_factory=list)
    unlocked_paths: List[str] = field(default_factory=list)

    def get_current_stats(self):
        stats = self.base_stats.copy()
        
        level_multiplier = 1 + (self.level * 0.1)
        
        damage_multiplier = 1.0
        mana_multiplier = 1.0
        
        for upgrade in self.active_upgrades:
            stat_boost = upgrade.stat_boost if isinstance(upgrade, SkillUpgrade) else upgrade["stat_boost"]
            for stat, boost in stat_boost.items():
                if "damage" in stat.lower():
                    damage_multiplier += (boost - 1)
                elif "mana" in stat.lower():
                    mana_multiplier *= max(0.5, boost)
                elif stat in stats:
                    stats[stat] *= boost

        for stat in stats:
            if "damage" in stat.lower():
                stats[stat] *= level_multiplier * damage_multiplier
            elif "mana" in stat.lower():
                stats[stat] *= mana_multiplier
            else:
                stats[stat] *= level_multiplier

        return stats




def save_skill_progress(skill_name, level, active_upgrades, unlocked_paths):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""UPDATE skills 
                    SET level = ?, active_upgrades = ?, unlocked_paths = ?
                    WHERE name = ?""", 
                (level, str(active_upgrades), str(unlocked_paths), skill_name))
        conn.commit()

def load_skill_progress(skill_name):
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

def create_circular_icon(image_path, size):
    icon = pygame.image.load(image_path)
    icon = pygame.transform.scale(icon, (size, size))
    
    circle_surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(circle_surface, (255, 255, 255), (size//2, size//2), size//2)
    
    masked_icon = pygame.Surface((size, size), pygame.SRCALPHA)
    masked_icon.blit(icon, (0, 0))
    masked_icon.blit(circle_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    
    return masked_icon


def skill_tree_menu():
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color, is_back_button=True)
    tree_center_x = screen_width // 2
    tree_center_y = 200
    node_radius = 30
    node_spacing = 120
    last_clicked_skill = None
    last_click_time = 0
    double_click_threshold = 500
    selected_skill = None 
    camera_offset = [0, 0]
    dragging = False
    drag_start = None
    start_offset = None
    any_node_clicked = False
    zoom_level = 1.0
    min_zoom = 0.5
    max_zoom = 2.0

    branch_points = {
        "Fireball": {
            "position": (tree_center_x, tree_center_y),
            "upgrade_positions": {
                "Fireball Mastery": (tree_center_x, tree_center_y + node_spacing),
                "Inferno": (tree_center_x - node_spacing, tree_center_y + node_spacing),
                "Explosion": (tree_center_x + node_spacing, tree_center_y + node_spacing),
                "True Fire": (tree_center_x - node_spacing, tree_center_y + node_spacing * 2),
                "Cluster": (tree_center_x + node_spacing, tree_center_y + node_spacing * 2),
                "Meteor Shower": (tree_center_x, tree_center_y + node_spacing * 3),
            },
            "icons": {
                "Fireball Mastery": "⚔️",
                "Inferno": "🔥",
                "Explosion": "💥", 
                "True Fire": "☄️",
                "Cluster": "⭐",
                "Meteor Shower": "🌠",
            },
            "connections": {
                "Fireball Mastery": ["Inferno", "Explosion"],
                "Inferno": ["True Fire"],
                "Explosion": ["Cluster"],
                "True Fire": ["Meteor Shower"],
                "Cluster": ["Meteor Shower"],
                "Meteor Shower": [""],
            }
        },
        "Ice Shard": {
            "position": (tree_center_x + node_spacing * 2, tree_center_y),
            "upgrade_positions": {
                "Ice Shard Mastery": (tree_center_x + node_spacing * 2, tree_center_y + node_spacing),
                "Frost": (tree_center_x + node_spacing * 3, tree_center_y + node_spacing),
                "Pierce": (tree_center_x + node_spacing, tree_center_y + node_spacing),
                "Glacial": (tree_center_x + node_spacing * 3, tree_center_y + node_spacing * 2),
                "Chain": (tree_center_x + node_spacing, tree_center_y + node_spacing * 2),
                "ice age": (tree_center_x + node_spacing * 2, tree_center_y + node_spacing * 3),
            },
            "icons": {
                "Ice Shard Mastery": "❄️",
                "Frost": "🌨️",
                "Pierce": "⚡",
                "Glacial": "🌡️",
                "Chain": "⛓️",
                "ice age": "🌊",
            },
            "connections": {
                "Ice Shard Mastery": ["Frost", "Pierce"],
                "Frost": ["Glacial"],
                "Pierce": ["Chain"],
                "Glacial": ["ice age"],
                "Chain": ["ice age"],
                "ice age": [""]
            }
        }
    }
    fireball = Skill(
        "Fireball",
        "Launches a ball of fire at enemies",
        {"damage": 5, "mana_cost": 50},
        icon_path=os.path.join(base_path, "icons", "fireball.png"),
        upgrades=[
            SkillUpgrade("Fireball Mastery", 2, 2, 
                {"damage": 1.2, "mana_cost": 0.9},
                unlocks="flame_mastery_branch",
                description="Master the basics of fire manipulation"),
            SkillUpgrade("Inferno", 3, 100, 
                {"damage": 1.5, "burn_duration": 5, "burn_damage": 20},
                unlocks="inferno_branch",
                requires="flame_mastery_branch",
                description="Transform fireball into a lingering inferno that burns enemies over time"),
            SkillUpgrade("Explosion", 3, 100, 
                {"damage": 1.3, "area": 2.0, "knockback": 5},
                unlocks="explosion_branch",
                requires="flame_mastery_branch",
                description="Convert fireball into an explosive blast that knocks back enemies"),
            SkillUpgrade("True Fire", 5, 200, 
                {"damage": 2.0, "burn_damage": 40, "area": 3.0},
                unlocks="True_Fire",
                requires="inferno_branch",
                description="all fire abilities double damage, your flame turns a hue of white"),
            SkillUpgrade("Cluster", 5, 200, 
                {"damage": 1.8, "area": 3.0, "knockback": 8},
                unlocks="Cluster",
                requires="explosion_branch",
                description="Release a chain of explosions that ripple outward"),
            SkillUpgrade("Meteor Shower", 9, 1200,
            {"damage": 7.0, "area": 30, "knockback": 14},
            requires=["True_Fire", "Cluster"],
            description="Call down a Meteor Shower that deals massive damage and knocks back enemies")
        ]
    )
    
    ice_shard = Skill(
        "Ice Shard",
        "Fires a piercing shard of ice",
        {"damage": 30, "mana_cost": 15},
        icon_path=os.path.join(base_path, "icons", "ice_shard.jpg"),
        upgrades=[
            SkillUpgrade("Ice Shard Mastery", 2, 50,
                {"damage": 1.2, "mana_cost": 0.9},
                unlocks="ice_mastery_branch",
                description="Master the basics of ice manipulation"),
            SkillUpgrade("Frost", 3, 100,
                {"damage": 1.3, "freeze_chance": 0.3, "freeze_duration": 3},
                requires="ice_mastery_branch",
                unlocks="frost_branch",
                description="Add a chance to freeze enemies in place"),
            SkillUpgrade("Pierce", 3, 100,
                {"damage": 1.4, "penetration": 3, "chain_hits": 2},
                requires="ice_mastery_branch",
                unlocks="pierce_branch", 
                description="Shard pierces through multiple enemies"),
            SkillUpgrade("Glacial", 5, 200,
                {"damage": 1.6, "freeze_chance": 0.5, "freeze_duration": 5, "area": 2.0},
                unlocks="glacial_branch",
                requires="frost_branch",
                description="Create an expanding ice field that slows enemies"),
            SkillUpgrade("Chain", 5, 200,
                {"damage": 1.8, "penetration": 5, "chain_hits": 4, "chain_damage": 0.8},
                unlocks="chain_branch",
                requires="pierce_branch",
                description="Shard bounces between multiple targets with increasing damage"),
            SkillUpgrade("ice age", 9, 1200,
                {"damage": 4532.543, "area": 30, "knockback": 1},
                requires=["glacial_branch", "chain_branch"],
                description="Create an ice age that freezes all enemies in the area")

                         
    ]
)
    
    
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT name, level, active_upgrades, unlocked_paths FROM skills")
        skill_data = c.fetchall()  
    
    skills = [fireball, ice_shard]
    for skill in skills:
        progress = load_skill_progress(skill.name)
        if progress:
            skill.level = progress["level"]
            skill.active_upgrades = progress["active_upgrades"]
            skill.unlocked_paths = progress["unlocked_paths"]
    
    skill_points = 100000
    selected_skill = None
    
    while True:
        current_time = pygame.time.get_ticks()
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        Back_Button.draw(screen)
        
        points_text = font_medium.render(f"Skill Points: {skill_points}", True, gold)
        screen.blit(points_text, (screen_width // 2 - points_text.get_width() // 2, 10))

        mouse_pos = pygame.mouse.get_pos()
                            
                            
        if skills:
            for skill in skills:    
                skill_data = branch_points[skill.name]
                skill_pos = ((skill_data["position"][0] * zoom_level) + camera_offset[0], 
                             (skill_data["position"][1] * zoom_level) + camera_offset[1])
                                                
                skill_hovered = ((mouse_pos[0] - skill_pos[0])**2 + (mouse_pos[1] - skill_pos[1])**2 <= (node_radius * zoom_level)**2)
                node_color = gray if skill_hovered else black
                pygame.draw.circle(screen, node_color, skill_pos, (node_radius * zoom_level) + 2.5)
                
                icon_size = (node_radius * 2) * zoom_level
                if skill.icon_path and os.path.exists(skill.icon_path):
                    circular_icon = create_circular_icon(skill.icon_path, icon_size)
                    icon_rect = circular_icon.get_rect(center=skill_pos)
                    screen.blit(circular_icon, icon_rect)
                    
                name_text = font_small.render(skill.name, True, white)
                level_text = font_small.render(f"Lv.{skill.level}", True, white)
                name_y = skill_pos[1] - (icon_size//2 + name_text.get_height() + 5)
                level_y = skill_pos[1] + (icon_size//2 + 5)
                
                screen.blit(name_text, (skill_pos[0] - name_text.get_width()//2, name_y))
                screen.blit(level_text, (skill_pos[0] - level_text.get_width()//2, level_y))
                
                if selected_skill and selected_skill.name == skill.name:    
                    core_name = f"{skill.name} Mastery"
                    core_pos = ((skill_data["upgrade_positions"][core_name][0] * zoom_level) + camera_offset[0],
                                (skill_data["upgrade_positions"][core_name][1] * zoom_level) + camera_offset[1])

                    start, end = get_edge_points(skill_pos, core_pos, node_radius, zoom_level)
                    core_unlocked = any(u.name == core_name if isinstance(u, SkillUpgrade) else u["name"] == core_name 
                                    for u in selected_skill.active_upgrades)
                    color = green if core_unlocked else gray
                    pygame.draw.line(screen, color, start, end, max(2, int(3 * zoom_level)))
                            
                    for source, targets in skill_data["connections"].items():
                        if source in skill_data["upgrade_positions"]:
                            source_pos = ((skill_data["upgrade_positions"][source][0] * zoom_level) + camera_offset[0],
                                          (skill_data["upgrade_positions"][source][1] * zoom_level) + camera_offset[1])
                            source_unlocked = any(u.name == source if isinstance(u, SkillUpgrade) else u["name"] == source 
                                            for u in selected_skill.active_upgrades)

                            
                            for target in targets:
                                if target in skill_data["upgrade_positions"]:
                                    target_pos = ((skill_data["upgrade_positions"][target][0] * zoom_level) + camera_offset[0],
                                                  (skill_data["upgrade_positions"][target][1] * zoom_level) + camera_offset[1])
                                    target_unlocked = any(u.name == target if isinstance(u, SkillUpgrade) else u["name"] == target 
                                                        for u in selected_skill.active_upgrades)
                                    
                                    start, end = get_edge_points(source_pos, target_pos, node_radius, zoom_level)
                                    if source_unlocked and target_unlocked:
                                        color = green
                                    elif source_unlocked:
                                        color = gold
                                    else:
                                        color = gray
                                        
                                    pygame.draw.line(screen, color, start, end, max(1, int(3 * zoom_level)))

                    for upgrade in selected_skill.upgrades:
                        upgrade_name = upgrade.name if isinstance(upgrade, SkillUpgrade) else upgrade["name"]
                        if upgrade_name in skill_data["upgrade_positions"]:
                            upgrade_pos = ((skill_data["upgrade_positions"][upgrade_name][0] * zoom_level) + camera_offset[0],
                                           (skill_data["upgrade_positions"][upgrade_name][1] * zoom_level) + camera_offset[1])
                            upgrade_unlocked = upgrade in selected_skill.active_upgrades
                            can_buy = can_purchase_upgrade(selected_skill, upgrade, skill_points)
                            upgrade_hovered = ((mouse_pos[0] - upgrade_pos[0])**2 + (mouse_pos[1] - upgrade_pos[1])**2 <= (node_radius * zoom_level)**2)
                            
                            if upgrade_unlocked:
                                node_color = dark_green if upgrade_hovered else green
                            elif can_buy:
                                node_color = gold
                            else:
                                node_color = dark_red if upgrade_hovered else red
                            
                            pygame.draw.circle(screen, node_color, upgrade_pos, (node_radius * zoom_level) - 5)
                            icon_text = font_small.render(skill_data["icons"][upgrade_name], True, white)
                            icon_pos = (upgrade_pos[0] - icon_text.get_width()//2, 
                                    upgrade_pos[1] - icon_text.get_height()//2)
                            screen.blit(icon_text, icon_pos)

                            if upgrade_hovered:
                                draw_upgrade_info(skill, upgrade, upgrade_pos, skill_points)

                    if skill_hovered:
                        draw_skill_info(selected_skill, skill_pos, skill_points)
                
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    get_current_points()
                    cleanup()
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button not in (4,5):
                    if Back_Button.is_clicked(event):
                        screen.fill(black)
                        screen.blit(background_image, (0, 0))
                        status_window()

                    clicked_skill = None
                    clicked_upgrade = None
                    any_node_clicked = False

                    for skill in skills:
                        skill_pos = ((branch_points[skill.name]["position"][0] * zoom_level) + camera_offset[0],
                                     (branch_points[skill.name]["position"][1] * zoom_level) + camera_offset[1])
                        if ((mouse_pos[0] - skill_pos[0])**2 + (mouse_pos[1] - skill_pos[1])**2 <= node_radius**2):
                            any_node_clicked = True
                            clicked_skill = skill

                            if clicked_skill == last_clicked_skill and current_time - last_click_time < double_click_threshold:
                                if skill.level < skill.max_level and skill_points > 0:
                                    skill.level += 1
                                    skill_points -= 1
                                    save_skill_progress(skill.name, skill.level, skill.active_upgrades, skill.unlocked_paths)
                                last_clicked_skill = None
                            else:
                                last_clicked_skill = clicked_skill
                                last_click_time = current_time
                            break

                    if selected_skill and not clicked_skill:
                        skill_data = branch_points[selected_skill.name]
                        for upgrade in selected_skill.upgrades:
                            upgrade_name = upgrade.name if isinstance(upgrade, SkillUpgrade) else upgrade["name"]
                            if upgrade_name in skill_data["upgrade_positions"]:
                                upgrade_pos = ((skill_data["upgrade_positions"][upgrade_name][0] * zoom_level) + camera_offset[0],
                                               (skill_data["upgrade_positions"][upgrade_name][1] * zoom_level) + camera_offset[1])
                                if ((mouse_pos[0] - upgrade_pos[0])**2 + (mouse_pos[1] - upgrade_pos[1])**2 <= node_radius**2):
                                    any_node_clicked = True
                                    clicked_upgrade = upgrade
                                    break

                    if clicked_skill:
                        if selected_skill == clicked_skill:
                            if not clicked_upgrade:
                                selected_skill = None
                        else:
                            selected_skill = clicked_skill

                    elif clicked_upgrade:
                        if can_purchase_upgrade(selected_skill, clicked_upgrade, skill_points):
                            selected_skill.active_upgrades.append(clicked_upgrade)
                            if isinstance(clicked_upgrade, SkillUpgrade) and clicked_upgrade.unlocks:
                                selected_skill.unlocked_paths.append(clicked_upgrade.unlocks)
                            elif isinstance(clicked_upgrade, dict) and "unlocks" in clicked_upgrade:
                                selected_skill.unlocked_paths.append(clicked_upgrade["unlocks"])
                            skill_points -= clicked_upgrade.cost if isinstance(clicked_upgrade, SkillUpgrade) else clicked_upgrade["cost"]
                            save_skill_progress(selected_skill.name, selected_skill.level, selected_skill.active_upgrades, selected_skill.unlocked_paths)

                    if event.button == 1 and not any_node_clicked:
                        dragging = True
                        drag_start = pygame.mouse.get_pos()
                        start_offset = camera_offset.copy()

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        dragging = False
                        
                elif event.type == pygame.MOUSEMOTION:
                    if dragging:
                        current_pos = pygame.mouse.get_pos()
                        dx = current_pos[0] - drag_start[0]
                        dy = current_pos[1] - drag_start[1]
                        camera_offset[0] = start_offset[0] + dx
                        camera_offset[1] = start_offset[1] + dy
                        
                elif event.type == pygame.MOUSEWHEEL:
                    old_zoom = zoom_level
                    zoom_change = 0.1 * event.y
                    zoom_level = max(min_zoom, min(max_zoom, zoom_level + zoom_change))
                    
                    mouse_x = mouse_pos[0] - camera_offset[0]
                    mouse_y = mouse_pos[1] - camera_offset[1]
                    
                    camera_offset[0] += mouse_x * (1 - zoom_level/old_zoom)
                    camera_offset[1] += mouse_y * (1 - zoom_level/old_zoom)

                pygame.display.flip()
        else:
            screen.fill(black)
            screen.blit(background_image, (0, 0))
            status_window()
            break
            




def draw_upgrade_info(skill, upgrade, pos, skill_points):
    padding = 20
    min_width = 250
    line_height = 25
    
    upgrade_name = upgrade.name if hasattr(upgrade, 'name') else upgrade.get("name", "Unknown")
    upgrade_cost = upgrade.cost if hasattr(upgrade, 'cost') else upgrade.get("cost", 0)
    description = upgrade.description if hasattr(upgrade, 'description') else upgrade.get("description", "")
    stat_boosts = upgrade.stat_boost if hasattr(upgrade, 'stat_boost') else upgrade.get("stat_boost", {})
    
    current_stats = skill.get_current_stats()
    
    stat_lines = []
    for stat, value in stat_boosts.items():
        if "percentage" in stat.lower():
            stat_text = f"{stat}: {value:+.0f}%"
        elif "damage" in stat.lower():
            current_damage = current_stats.get(stat, 0)
            final_damage = current_damage * value
            stat_text = f"{stat}: {final_damage:.0f}"
        else:
            stat_text = f"{stat}: {value}"
        stat_lines.append(stat_text)
    
    name_width = font_small.size(upgrade_name)[0]
    cost_text = f"Cost: {upgrade_cost} SP"
    cost_width = font_small.size(cost_text)[0]
    desc_lines = wrap_text(description, font_small, min_width - padding * 2)
    
    info_width = max(min_width, name_width + padding * 2, cost_width + padding * 2)
    info_height = padding * 2 + line_height * (len(desc_lines) + len(stat_lines) + 2)
    
    info_x = max(padding, min(pos[0] - info_width//2, screen_width - info_width - padding))
    info_y = max(padding, min(pos[1] - info_height - 40, screen_height - info_height - padding))
    
    info_surface = pygame.Surface((info_width, info_height), pygame.SRCALPHA)
    pygame.draw.rect(info_surface, (40, 40, 40, 240), info_surface.get_rect(), border_radius=10)
    screen.blit(info_surface, (info_x, info_y))
    
    current_y = info_y + padding
    name_text = font_small.render(upgrade_name, True, gold)
    cost_text = font_small.render(f"Cost: {upgrade_cost}", True, 
                                green if skill_points >= upgrade_cost else red)
    screen.blit(name_text, (info_x + padding, current_y))
    current_y += line_height
    screen.blit(cost_text, (info_x + padding, current_y))
    current_y += line_height
    
    for stat_line in stat_lines:
        stat_text = font_small.render(stat_line, True, stat_text_color)
        screen.blit(stat_text, (info_x + padding, current_y))
        current_y += line_height
    
    current_y += line_height // 2
    for line in desc_lines:
        desc_text = font_small.render(line, True, white)
        screen.blit(desc_text, (info_x + padding, current_y))
        current_y += line_height



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

def draw_skill_info(skill, pos, skill_points):
    padding = 20
    line_height = 25
    min_width = 400
    
    name_width = font_medium.size(skill.name)[0]
    level_text = f"Level {skill.level}/{skill.max_level}"
    level_width = font_small.size(level_text)[0]
    desc_lines = wrap_text(skill.description, font_small, min_width - padding * 2)
    
    stat_lines = []
    max_stat_width = 0
    for stat, value in skill.get_current_stats().items():
        stat_text = f"{stat}: {value:.1f}"
        stat_width = font_small.size(stat_text)[0]
        max_stat_width = max(max_stat_width, stat_width)
        stat_lines.append(stat_text)
    
    info_width = max(min_width, name_width + level_width + padding * 3, max_stat_width + padding * 2)
    info_height = padding * 2 + line_height * (len(desc_lines) + len(stat_lines) + 1)
    
    info_x = max(padding, min(pos[0] - info_width//2, screen_width - info_width - padding))
    info_y = max(padding, min(pos[1] + 60, screen_height - info_height - padding))
    
    info_surface = pygame.Surface((info_width, info_height), pygame.SRCALPHA)
    pygame.draw.rect(info_surface, (40, 40, 40, 230), info_surface.get_rect(), border_radius=15)
    screen.blit(info_surface, (info_x, info_y))
    
    current_y = info_y + padding
    name_text = font_medium.render(skill.name, True, gold)
    level_info = font_small.render(level_text, True, white)
    screen.blit(name_text, (info_x + padding, current_y))
    screen.blit(level_info, (info_x + info_width - level_width - padding, current_y))
    current_y += line_height
    
    for line in desc_lines:
        desc_text = font_small.render(line, True, white)
        screen.blit(desc_text, (info_x + padding, current_y))
        current_y += line_height
    
    current_y += line_height // 2
    for stat_text in stat_lines:
        stat_rendered = font_small.render(stat_text, True, stat_text_color)
        screen.blit(stat_rendered, (info_x + padding, current_y))
        current_y += line_height


def can_purchase_upgrade(skill, upgrade, skill_points):
    level_req = upgrade.level_req if isinstance(upgrade, SkillUpgrade) else upgrade["level_req"]
    cost = upgrade.cost if isinstance(upgrade, SkillUpgrade) else upgrade["cost"]
    requires = upgrade.requires if isinstance(upgrade, SkillUpgrade) else upgrade.get("requires")
    
    if isinstance(requires, list):
        requirements_met = all(req in skill.unlocked_paths for req in requires)
    else:
        requirements_met = not requires or requires in skill.unlocked_paths
        
    return (
        skill.level >= level_req and 
        skill_points >= cost and
        requirements_met and
        upgrade not in skill.active_upgrades
    )

def cleanup():
    try:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except pygame.error:
        pass
    pygame.quit()
    sys.exit()

def missions_window():
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color, is_back_button=True)
    scroll_y = 0
    banner_width = screen_width - 100
    text_width = int(banner_width * 0.75)
    padding = 20
    
    missions = [
        {
            "title": "The Beginning",
            "description": "Survive the first raid \n Bonus: Kill an enemy",
            "reward": "100 points", 
            "time_limit": "24 hours",
        }
    ]

    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
                pygame.quit()
                sys.exit()
            if Back_Button.is_clicked(event):
                main_menu()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                main_menu()
                return
            if event.type == pygame.MOUSEWHEEL:
                scroll_y += event.y * 20
                total_height = sum(mission["banner_height"] + padding for mission in missions)
                min_scroll = -(total_height - screen_height + 150)
                scroll_y = max(min_scroll, min(0, scroll_y))

        screen.fill(white)
        screen.blit(background_image, (0, 0))
        Back_Button.draw(screen)

        y_pos = 100 + scroll_y
        for mission in missions:
            paragraphs = mission["description"].split('\n')
            lines = []
            
            for paragraph in paragraphs:
                words = paragraph.split()
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    if font_small.size(test_line)[0] <= text_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                else:
                    test_line = ' '.join(current_line + [word])
                    if font_small.size(test_line)[0] <= text_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]

            title_height = 60
            text_height = len(lines) * 25
            banner_height = title_height + text_height + padding * 2
            mission["banner_height"] = banner_height

            if -banner_height <= y_pos <= screen_height:
                banner_rect = pygame.Rect(50, y_pos, banner_width, banner_height)
                pygame.draw.rect(screen, (40, 40, 40, 230), banner_rect, border_radius=10)
                
                stats_y = y_pos + 15
                reward_text = font_small.render(f"Reward: {mission['reward']}", True, green)
                time_text = font_small.render(f"Time: {mission['time_limit']}", True, light_blue)
                screen.blit(reward_text, (screen_width // 2 -100 , stats_y + 10))
                screen.blit(time_text, (screen_width // 2 +180, stats_y + 10))
                try:
                    progress_text = font_small.render(f"Progress: {mission['progress']}", True, gold)
                    screen.blit(progress_text, (screen_width // 2 +180, stats_y + banner_height - 40))  
                except KeyError:
                    pass
                    
                
                title_text = font_medium.render(mission["title"], True, gold)
                screen.blit(title_text, (70, y_pos + 20))
                
                text_y = y_pos + title_height + 10
                for line in lines:
                    text = font_small.render(line, True, white)
                    screen.blit(text, (70, text_y))
                    text_y += 25
            
            y_pos += banner_height + padding

        pygame.display.flip()





minigames = Button("Minigames", screen_width // 2 - 165, screen_height // 2 - 100, 330, 50, hover_color)
Missions_Menu = Button("Missions", screen_width // 2 - 165, screen_height // 2, 330, 50, hover_color) 
Stats_Menu = Button("Stats", screen_width // 2 - 165, screen_height // 2 + 100, 330, 50, hover_color)
fadeInComplete = False
running_threads = []
def main_menu():
    global fadeInComplete, running_threads
    
    while True:
        screen.fill(black)
        screen.blit(background_image, (0, 0))
        minigames.draw(screen)
        Missions_Menu.draw(screen)
        Stats_Menu.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
            if minigames.is_clicked(event):
                minigames_menu()
            if Missions_Menu.is_clicked(event):
                missions_window()
            if Stats_Menu.is_clicked(event):
                status_window()

        
        pygame.display.flip()
        if not fadeInComplete:
            fade_thread = threading.Thread(target=fade_out_music, daemon=True)
            running_threads.append(fade_thread)
            fade_thread.start()
            fadeInComplete = True

if __name__ == "__main__":
    initialize_database()
    organize_files()
    try:
        if pygame.mixer.get_init():
            ui_hover_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "hover_sound.wav"))
            ui_hover_sound.set_volume(0.3)
            ui_click_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "click_sound.wav"))
            ui_back_sound = pygame.mixer.Sound(os.path.join(base_path, "sounds", "back_sound.wav"))
    except:
        print("Could not load UI sound effects")
    initial_startup()

