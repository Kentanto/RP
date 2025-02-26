import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import secrets
import random
import sqlite3
import os
import pygame #type: ignore
import sys
import time
import threading
DB_PATH = 'database\\artifacts.db'
base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songs")

pygame.init()

def initial_startup():
    fade_in()
    main_menu()

def fade_out_music():
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
                      "departure.mp3"]

    pygame.mixer.init()
    
    random_song = random.choice(music_playlist)
    chosen_song = random_song
    
    # Track song path resolution
    if getattr(sys, 'frozen', False):
        song_path = os.path.join(os.path.dirname(sys.executable), "songs", chosen_song)
    else:
        song_path = os.path.join(os.path.dirname(__file__), "songs", chosen_song)
    
    song_durations = {
        "feelGood.mp3": 53,
        "haldis.mp3": 73,
        "spell.mp3": 57,
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
    }

    
    loading_time = song_durations.get(chosen_song, 12) * 100
    
    last_reported_progress = -1
    start_time = pygame.time.get_ticks()
    
    pygame.mixer.music.load(song_path)
    pygame.mixer.music.set_volume(0.1)
    pygame.mixer.music.play(1)

    fade_surface = pygame.Surface((screen_width, screen_height))
    fade_surface.fill(black)

    bar_width = 400
    bar_height = 30
    bar_x = (screen_width - bar_width) // 2
    bar_y = screen_height - 100

    start_time = pygame.time.get_ticks()

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




screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
font_large = pygame.font.SysFont(None, 55)
font_medium = pygame.font.SysFont(None, 40)
font_small = pygame.font.SysFont(None, 30)

pygame.display.set_caption("Athas system")

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


font = pygame.font.SysFont(None, 55)


if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

background_image_path = os.path.join("background_menu.png")
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
    
    # Check if skills need initialization
    c.execute("SELECT COUNT(*) FROM skills")
    if c.fetchone()[0] == 0:
        # Initialize default skills
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
        
        
class Skill:
    def __init__(self, name, description, base_stats, icon_path=None, level=0, max_level=10, upgrades=None):
        self.name = name
        self.description = description
        self.base_stats = base_stats
        self.icon_path = icon_path
        self.level = level
        self.max_level = max_level
        self.upgrades = upgrades or []
        self.active_upgrades = []
        self.unlocked_paths = []
        
    def add_upgrade(self, upgrade):
        self.upgrades.append(upgrade)
        
    def get_current_stats(self):
        stats = self.base_stats.copy()
        multiplier = 1 + (self.level * 0.1)
        
        # Apply upgrade bonuses
        for upgrade in self.active_upgrades:
            for stat, boost in upgrade["stat_boost"].items():
                if stat in stats:
                    multiplier *= boost
                
        return {stat: value * multiplier for stat, value in stats.items()}



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


def skill_tree_menu():
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color)
    info_width = 400
    info_height = 300
    
    # Example skill definitions with upgrade paths and requirements
    fireball = Skill(
        "Fireball",
        "Launches a ball of fire at enemies",
        {"damage": 50, "mana_cost": 20},
        icon_path="icons/fireball.png",
        upgrades=[
            {"name": "Core: Flame Mastery", "level_req": 2, "cost": 50, "stat_boost": {"damage": 1.2, "mana_cost": 0.9}},
            {"name": "Path: Inferno", "level_req": 3, "cost": 100, "stat_boost": {"damage": 1.5}, "unlocks": "inferno_branch"},
            {"name": "Path: Explosion", "level_req": 3, "cost": 100, "stat_boost": {"area": 1.5}, "unlocks": "explosion_branch"},
            {"name": "Inferno: Meteor", "level_req": 5, "cost": 200, "stat_boost": {"damage": 2.0}, "requires": "inferno_branch"},
            {"name": "Explosion: Shockwave", "level_req": 5, "cost": 200, "stat_boost": {"area": 2.0}, "requires": "explosion_branch"}
        ]
    )
    
    ice_shard = Skill(
        "Ice Shard",
        "Fires a piercing shard of ice",
        {"damage": 30, "mana_cost": 15},
        icon_path="icons/ice_shard.png",
        upgrades=[
            {"name": "Core: Ice Mastery", "level_req": 2, "cost": 50, "stat_boost": {"damage": 1.2, "mana_cost": 0.9}},
            {"name": "Path: Frost", "level_req": 3, "cost": 100, "stat_boost": {"freeze": 1.5}, "unlocks": "frost_branch"},
            {"name": "Path: Pierce", "level_req": 3, "cost": 100, "stat_boost": {"penetration": 1.5}, "unlocks": "pierce_branch"},
            {"name": "Frost: Glacial", "level_req": 5, "cost": 200, "stat_boost": {"freeze": 2.0}, "requires": "frost_branch"},
            {"name": "Pierce: Chain", "level_req": 5, "cost": 200, "stat_boost": {"penetration": 2.0}, "requires": "pierce_branch"}
        ]
    )
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, level, active_upgrades, unlocked_paths FROM skills")
    skill_data = c.fetchall()
    conn.close()
    
    for data in skill_data:
        name, level, active_upgrades, unlocked_paths = data
        for skill in [fireball, ice_shard]:
            if skill.name == name:
                skill.level = level
                skill.active_upgrades = eval(active_upgrades)
                skill.unlocked_paths = eval(unlocked_paths)
    
    skills = [fireball, ice_shard]
    skill_points = 10
    selected_skill = None
    
    while True:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        Back_Button.draw(screen)
        
        points_text = font_medium.render(f"Skill Points: {skill_points}", True, gold)
        screen.blit(points_text, (screen_width - 200, 20))
        
        icon_size = 80
        grid_spacing = 100
        start_x = (screen_width - (len(skills) * grid_spacing)) // 2
        icon_y = 150
        
        for i, skill in enumerate(skills):
            icon_x = start_x + (i * grid_spacing)
            
            pygame.draw.rect(screen, dark_gray, (icon_x, icon_y, icon_size, icon_size), border_radius=15)
            level_text = font_small.render(f"Lv.{skill.level}", True, white)
            screen.blit(level_text, (icon_x + 5, icon_y + icon_size - 25))
            
            icon_text = font_medium.render(skill.name[0], True, gold)
            text_x = icon_x + (icon_size - icon_text.get_width()) // 2
            text_y = icon_y + (icon_size - icon_text.get_height()) // 2
            screen.blit(icon_text, (text_x, text_y))
            
            mouse_pos = pygame.mouse.get_pos()
            is_hovered = (icon_x <= mouse_pos[0] <= icon_x + icon_size and 
                         icon_y <= mouse_pos[1] <= icon_y + icon_size)
            
            if is_hovered or selected_skill == skill:
                info_x = max(10, min(icon_x - (info_width - icon_size) // 2, 
                                   screen_width - info_width - 10))
                info_y = icon_y + icon_size + 20
                
                info_surface = pygame.Surface((info_width, info_height), pygame.SRCALPHA)
                opacity = 255 if selected_skill == skill else 180
                pygame.draw.rect(info_surface, (40, 40, 40, opacity), 
                               info_surface.get_rect(), border_radius=15)
                screen.blit(info_surface, (info_x, info_y))
                
                name_text = font_medium.render(skill.name, True, gold)
                level_info = font_small.render(f"Level {skill.level}/{skill.max_level}", True, white)
                desc_text = font_small.render(skill.description, True, white)
                
                screen.blit(name_text, (info_x + 20, info_y + 20))
                screen.blit(level_info, (info_x + info_width - 120, info_y + 20))
                screen.blit(desc_text, (info_x + 20, info_y + 60))
                
                stats_y = info_y + 100
                current_stats = skill.get_current_stats()
                for stat, value in current_stats.items():
                    stat_text = font_small.render(f"{stat}: {value:.1f}", True, stat_text_color)
                    screen.blit(stat_text, (info_x + 20, stats_y))
                    stats_y += 30
                
                upgrade_y = info_y + 180
                for upgrade in skill.upgrades:
                    if skill.level >= upgrade["level_req"]:
                        color = green if skill_points >= upgrade["cost"] else red
                        upgrade_text = font_small.render(
                            f"{upgrade['name']} - Cost: {upgrade['cost']} SP", 
                            True, color
                        )
                        screen.blit(upgrade_text, (info_x + 20, upgrade_y))
                        upgrade_y += 30
                
                if skill.level < skill.max_level and skill_points > 0:
                    level_up_rect = pygame.Rect(info_x + info_width - 120, 
                                              info_y + info_height - 50, 100, 30)
                    pygame.draw.rect(screen, green, level_up_rect, border_radius=5)
                    level_text = font_small.render("Level Up", True, white)
                    screen.blit(level_text, (level_up_rect.centerx - level_text.get_width()//2, 
                                           level_up_rect.centery - level_text.get_height()//2))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                get_current_points()
                cleanup()
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                clicked_skill = None
                for i, skill in enumerate(skills):
                    icon_x = start_x + (i * grid_spacing)
                    if (icon_x <= event.pos[0] <= icon_x + icon_size and 
                        icon_y <= event.pos[1] <= icon_y + icon_size):
                        clicked_skill = skill
                
                if clicked_skill:
                    if selected_skill == clicked_skill:
                        selected_skill = None
                    else:
                        selected_skill = clicked_skill
                elif selected_skill:
                    info_rect = pygame.Rect(info_x, info_y, info_width, info_height)
                    if not info_rect.collidepoint(event.pos):
                        selected_skill = None
                    
                        if selected_skill and selected_skill.level < selected_skill.max_level:
                            if level_up_rect.collidepoint(event.pos) and skill_points > 0:
                                selected_skill.level += 1
                                skill_points -= 1
            if Back_Button.is_clicked(event):
                screen.fill(white)
                screen.blit(background_image, (0, 0))
                pygame.display.flip()
                status_window()
                
                
            if selected_skill:
                for upgrade in selected_skill.upgrades:
                    if (selected_skill.level >= upgrade["level_req"] and 
                        skill_points >= upgrade["cost"]):
                        if "requires" in upgrade and upgrade["requires"] not in selected_skill.unlocked_paths:
                            continue
                            
                        upgrade_rect = pygame.Rect(info_x + 20, upgrade_y, 300, 25)
                        if upgrade_rect.collidepoint(event.pos):
                            selected_skill.active_upgrades.append(upgrade)
                            if "unlocks" in upgrade:
                                selected_skill.unlocked_paths.append(upgrade["unlocks"])
                            skill_points -= upgrade["cost"]
                            
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute("""
                                UPDATE skills 
                                SET active_upgrades = ?, unlocked_paths = ?
                                WHERE name = ?
                            """, (str(selected_skill.active_upgrades), 
                                str(selected_skill.unlocked_paths), 
                                selected_skill.name))
                            conn.commit()
                            conn.close()


        pygame.display.flip()

def cleanup():
    pygame.mixer.music.stop()
    pygame.mixer.quit()
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

