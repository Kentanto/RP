import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
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
import shutil
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
    organize_image_files()
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

    
def organize_image_files():
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.ico')
    icons_dir = 'icons'
    icons_path = os.path.join(base_path, icons_dir)
    
    if not os.path.exists(icons_path):
        os.makedirs(icons_path)
        
    for file in os.listdir(base_path):
        if file.lower().endswith(image_extensions):
            source = os.path.join(base_path, file)
            destination = os.path.join(icons_path, file)
            if not os.path.exists(destination):
                os.rename(source, destination)



organize_image_files()

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

    if pygame.mixer.get_init() is None:
        print("no audio sorry")
    else:
        try:
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
        except:
            print("Audio system unavailable - running without sound")


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
    def __init__(self, text, x, y, width, height, hover_color=(255, 255, 255, 128)):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.hover_color = hover_color

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.is_hovered(mouse_pos)
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
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self.is_hovered(pygame.mouse.get_pos())
        return False


def initialize_database():    
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS artifacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  main_stat TEXT NOT NULL,
                  sub_stat1 TEXT NOT NULL,
                  sub_stat2 TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY, level INTEGER, hp INTEGER, atk INTEGER, def INTEGER, spd INTEGER, mana INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS points
                 (id INTEGER PRIMARY KEY, points INTEGER, last_updated INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS skills
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  level INTEGER DEFAULT 0,
                  active_upgrades TEXT,
                  unlocked_paths TEXT)''')
    
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
    conn = sqlite3.connect(DB_PATH)
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
        conn.close()
        return new_points
    
    conn.close()
    return current_points




def add_artifact(name, main_stat, sub_stat1, sub_stat2):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO artifacts (name, main_stat, sub_stat1, sub_stat2) VALUES (?, ?, ?, ?)",
                 (name, main_stat, sub_stat1, sub_stat2))
        conn.commit()
    finally:
        if conn:
            conn.close()

def generate_random_artifact():
    artifact_names = ["Wooden Sword", "Leather Armor", "Iron Shield", "Bronze Helmet", "Cloth Robe"]
    stats = ["ATK", "DEF", "HP", "Crit Rate%", "SPD%", "Crit DMG%", "ATK%", "DEF%", "HP%"]
    
    name = random.choice(artifact_names)
    main_stat = random.choice(stats)
    sub_stat1 = random.choice([s for s in stats if s != main_stat])
    sub_stat2 = random.choice([s for s in stats if s not in [main_stat, sub_stat1]])
    
    return name, main_stat, sub_stat1, sub_stat2

def view_artifacts():
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color)
    scroll_y = 0
    scroll_speed = 20
    items_per_row = 3
    box_width = 220
    box_padding = 20
    box_height = 100
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM artifacts")
    artifacts = c.fetchall()
    conn.close()
    
    while True:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        start_x = (screen_width - (box_width * items_per_row + box_padding * (items_per_row-1))) // 2
        start_y = 100 + scroll_y
        
        for i, artifact in enumerate(artifacts):
            row = i // items_per_row
            col = i % items_per_row
            x = start_x + col * (box_width + box_padding)
            y = start_y + row * (box_height + box_padding)
            
            pygame.draw.rect(screen, (50, 50, 50, 128), (x, y, box_width, box_height), border_radius=10)
            
            name_text = font_small.render(artifact[1], True, artifact_text_color)
            stats_text = font_small.render(f"{artifact[2]}", True, artifact_text_color)
            sub_stats = font_small.render(f"{artifact[3]} | {artifact[4]}", True, artifact_text_color)
            
            screen.blit(name_text, (x + 10, y + 10))
            screen.blit(stats_text, (x + 10, y + 35))
            screen.blit(sub_stats, (x + 10, y + 60))
        
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE points SET points = ?, last_updated = ?", (new_points, int(time.time())))
    conn.commit()
    conn.close()

def insufficient_points_message():
    message = font_medium.render("Not enough points!", True, red)
    screen.blit(message, (screen_width//2 - message.get_width()//2, screen_height - 100))
    pygame.display.flip()
    pygame.time.wait(1500)
    screen.fill(white)
    screen.blit(background_image, (0, 0))
    pygame.display.flip()
    minigames_menu()

def math_activity_menu():
    current_points = get_current_points()
    point_cost = 20
    
    Easy_button = Button("Easy (20 points)", screen_width // 2 - 165, screen_height // 2 - 140, 330, 50, hover_color)    
    Medium_button = Button("Locked-Medium-Locked LV: 8", screen_width // 2 - 165, screen_height // 2 - 70, 330, 50, hover_color)
    Hard_button = Button("Locked-Hard-Locked Lv: 15", screen_width // 2 - 165, screen_height // 2 - 0, 330, 50, hover_color)
    Extreme_button = Button("Locked-Extreme-Locked LV: 25", screen_width // 2 - 165, screen_height // 2 + 70, 330, 50, hover_color)
    Leave_button = Button("Leave", screen_width // 2 - 165, screen_height // 2 + 140, 330, 50, hover_color)
    
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        points_text = font_medium.render(f"Points: {current_points}/{point_cost}", True, white)
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
                    if current_points >= point_cost:
                        current_points -= point_cost
                        update_points(current_points)
                        math_game_window(1)
                    else:
                        insufficient_points_message()
                        
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
    user_input = ""
    equation = generate_math_equation_easy(math_difficulty)
    leave_button = Button("Leave", 10, 10, 100, 40, hover_color)
    
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
                get_current_points()
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
                            
                            result_text = "Correct!"
                            result_surface = font_large.render(result_text, True, (0, 255, 0))
                            screen.blit(result_surface, (screen_width // 2 - result_surface.get_width() // 2, 200))
                            
                            name_surface = font_medium.render(f"You received: {artifact[0]}", True, purple)
                            screen.blit(name_surface, (screen_width // 2 - name_surface.get_width() // 2, 280))
                            
                            stats_text = f"Main: {artifact[1]}  |  Sub1: {artifact[2]}  |  Sub2: {artifact[3]}"
                            stats_surface = font_small.render(stats_text, True, gold)
                            screen.blit(stats_surface, (screen_width // 2 - stats_surface.get_width() // 2, 330))
                            
                            pygame.display.flip()
                            pygame.time.wait(2000) 
                        else:
                            result_text = f"Incorrect. The correct answer is: {rounded_answer}"
                            result_color = (255, 0, 0)

                            screen.fill(white)
                            screen.blit(background_image, (0, 0))
                            result_surface = font.render(result_text, True, result_color)
                            screen.blit(result_surface, (screen_width // 2 - result_surface.get_width() // 2, 300))
                            pygame.display.flip()
                            pygame.time.wait(2000)

                        pygame.display.flip()
                        screen.fill(white)
                        screen.blit(background_image, (0, 0))
                        pygame.display.flip()
                        math_activity_menu()
                        
                                       
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
                math_activity_menu()

        pygame.display.flip()

    return True

def minigames_menu():
    current_points = get_current_points()
    Math_Button = Button("Math", screen_width // 2 - 165, screen_height // 2 - 140, 330, 50, hover_color)    
    Back_Button = Button("Back", screen_width // 2 - 165, screen_height // 2 + 70, 330, 50, hover_color)
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
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color)
    View_Artifacts = Button("Artifacts", screen_width - 160, 10, 140, 40, hover_color)
    Skill_menu = Button("Skills", screen_width//2 - 70, 10, 140, 40, hover_color)
    
    Kenji = "Kenji Mizuki"
    stats = {
        "Level": 1,
        "CON": 10,
        "ATK": 5,
        "DEF": 10,
        "SPD": 5,
        "mana": 0,
    }
    
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))        
        
        name_text = font_large.render(Kenji, True, black)
        screen.blit(name_text, (screen_width//2 - name_text.get_width()//2, 80))
        
        y_offset = 133
        for stat, value in stats.items():
            stat_text = font_medium.render(f"{stat}: {value}", True, stat_text_color)
            screen.blit(stat_text, (screen_width//2 - stat_text.get_width()//2, y_offset))
            y_offset += 60
        
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
        
        pygame.display.flip()
        
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
        
        # Base level scaling (more controlled growth)
        level_multiplier = 1 + (self.level * 0.1)  # 10% increase per level
        
        # Separate multipliers for different stat types
        damage_multiplier = 1.0
        mana_multiplier = 1.0
        
        for upgrade in self.active_upgrades:
            stat_boost = upgrade.stat_boost if isinstance(upgrade, SkillUpgrade) else upgrade["stat_boost"]
            for stat, boost in stat_boost.items():
                if "damage" in stat.lower():
                    # Additive stacking for damage boosts
                    damage_multiplier += (boost - 1)
                elif "mana" in stat.lower():
                    # Diminishing returns for mana cost reduction
                    mana_multiplier *= max(0.5, boost)  # Cap at 50% reduction
                elif stat in stats:
                    # Other stats get normal scaling
                    stats[stat] *= boost

        # Apply final multipliers
        for stat in stats:
            if "damage" in stat.lower():
                stats[stat] *= level_multiplier * damage_multiplier
            elif "mana" in stat.lower():
                stats[stat] *= mana_multiplier
            else:
                stats[stat] *= level_multiplier

        return stats




def save_skill_progress(skill_name, level, active_upgrades, unlocked_paths):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""UPDATE skills 
                 SET level = ?, active_upgrades = ?, unlocked_paths = ?
                 WHERE name = ?""", 
              (level, str(active_upgrades), str(unlocked_paths), skill_name))
    conn.commit()
    conn.close()

def load_skill_progress(skill_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT level, active_upgrades, unlocked_paths FROM skills WHERE name = ?", (skill_name,))
    result = c.fetchone()
    conn.close()
    
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
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color)
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
    
    
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, level, active_upgrades, unlocked_paths FROM skills")
    skill_data = c.fetchall()
    conn.close()  
    
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
                    
                    # Get mouse position relative to camera
                    mouse_x = mouse_pos[0] - camera_offset[0]
                    mouse_y = mouse_pos[1] - camera_offset[1]
                    
                    # Adjust camera offset to zoom towards cursor
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


minigames = Button("Minigames", screen_width // 2 - 165, screen_height // 2 - 50, 330, 50, hover_color)
Stats_Menu = Button("Stats", screen_width // 2 - 165, screen_height // 2 + 50, 330, 50, hover_color)
fadeInComplete = False
running_threads = []
def main_menu():
    global fadeInComplete, running_threads
    
    while True:
        screen.fill(black)
        screen.blit(background_image, (0, 0))
        minigames.draw(screen)
        Stats_Menu.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
            if minigames.is_clicked(event):
                minigames_menu()
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
    initial_startup()

