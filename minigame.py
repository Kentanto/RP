import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import secrets
import random
import sqlite3
import os
import pygame
import sys
DB_PATH = 'database\\artifacts.db'

pygame.init()
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
font_large = pygame.font.SysFont(None, 55)
font_medium = pygame.font.SysFont(None, 40)
font_small = pygame.font.SysFont(None, 30)

pygame.display.set_caption("Math Game Main Menu")

white = (255, 255, 255)
black = (0, 0, 0)
blue = (0, 0, 255)
dark_blue = (0, 0, 0)
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

        if is_hovered:
            hover_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, self.hover_color, hover_surface.get_rect())
            screen.blit(hover_surface, (self.x, self.y))

        text_surface = font.render(self.text, True, white)
        screen.blit(text_surface, (
            self.x + (self.width - text_surface.get_width()) // 2,
            self.y + (self.height - text_surface.get_height()) // 2
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
    
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS artifacts
                     (id INTEGER PRIMARY KEY, name TEXT, main_stat TEXT, sub_stat1 TEXT, sub_stat2 TEXT)''')
        conn.commit()
        conn.close()
        print("Database created successfully.")
    else:
        print("Database already exists.")


def add_artifact(name, main_stat, sub_stat1, sub_stat2):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO artifacts (name, main_stat, sub_stat1, sub_stat2) VALUES (?, ?, ?, ?)",
              (name, main_stat, sub_stat1, sub_stat2))
    conn.commit()
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
    running = True
    
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        # Get artifacts from database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM artifacts")
        artifacts = c.fetchall()
        conn.close()
        
        # Display artifacts in a scrollable list
        y_offset = 100
        for artifact in artifacts:
            name_text = font_small.render(f"{artifact[1]}", True, artifact_text_color)
            stats_text = font_small.render(f"Main: {artifact[2]} | Sub1: {artifact[3]} | Sub2: {artifact[4]}", True, artifact_text_color)
            screen.blit(name_text, (50, y_offset))
            screen.blit(stats_text, (50, y_offset + 30))
            y_offset += 80

        
        Back_Button.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if Back_Button.is_clicked(event):
                return True
        
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


def round_result(result, precision=0.001):
    return round(result / precision) * precision

def math_activity_menu():
    Easy_button = Button("Easy", screen_width // 2 - 165, screen_height // 2 - 140, 330, 50, hover_color)    
    Medium_button = Button("Medium", screen_width // 2 - 165, screen_height // 2 - 70, 330, 50, hover_color)
    Hard_button = Button("Hard", screen_width // 2 - 165, screen_height // 2 - 0, 330, 50, hover_color)
    Extreme_button = Button("Extreme", screen_width // 2 - 165, screen_height // 2 + 70, 330, 50, hover_color)
    Leave_button = Button("Leave", screen_width // 2 - 165, screen_height // 2 + 140, 330, 50, hover_color)
    
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        Easy_button.draw(screen)
        Medium_button.draw(screen)
        Hard_button.draw(screen)
        Extreme_button.draw(screen)
        Leave_button.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if Easy_button.is_clicked(event):
                math_game_window(1)
            
            elif Medium_button.is_clicked(event):
                math_game_window(5)
                
            elif Hard_button.is_clicked(event):
                math_game_window(10)

            elif Extreme_button.is_clicked(event):
                math_game_window(15)
            
            elif Leave_button.is_clicked(event):
                return True

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
        
        pygame.display.flip()
    
    return True

def math_game_window(math_difficulty):
    user_input = ""
    equation = generate_math_equation_easy(math_difficulty)
    leave_button = Button("Leave", 10, 10, 100, 40, hover_color)
    
    try:
        correct_answer = eval(equation)
        rounded_answer = round_result(correct_answer, precision=0.001)
    except Exception as e:
        print(f"Generated an invalid equation: {equation}")
        print("Error:", e)
        return True

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
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        user_answer = float(user_input)
                        if round_result(user_answer, precision=0.001) == rounded_answer:
                            screen.fill(white)
                            screen.blit(background_image, (0, 0))
                            result_color = (0, 255, 0)
                            
                            # "Correct!" message
                            result_text = "Correct!"
                            result_surface = font_large.render(result_text, True, (0, 255, 0))
                            screen.blit(result_surface, (screen_width // 2 - result_surface.get_width() // 2, 200))
                            
                            # Artifact name
                            artifact = generate_random_artifact()
                            name_surface = font_medium.render(f"You received: {artifact[0]}", True, black)
                            screen.blit(name_surface, (screen_width // 2 - name_surface.get_width() // 2, 280))
                            
                            # Stats
                            stats_text = f"Main: {artifact[1]}  |  Sub1: {artifact[2]}  |  Sub2: {artifact[3]}"
                            stats_surface = font_small.render(stats_text, True, black)
                            screen.blit(stats_surface, (screen_width // 2 - stats_surface.get_width() // 2, 330))
                            
                            pygame.display.flip()
                            pygame.time.wait(2000)  # Show reward for 2 seconds
                                                    
                            add_artifact(*artifact) 
                        else:
                            result_text = f"Incorrect. The correct answer is: {rounded_answer}"
                            result_color = (255, 0, 0)
                        
                        screen.fill(white)
                        result_surface = font.render(result_text, True, result_color)
                        
                        screen.blit(result_surface, (screen_width // 2 - result_surface.get_width() // 2, 300))
                        pygame.display.flip()
                        pygame.time.wait(1000)                        
                        equation = generate_math_equation_easy(math_difficulty)
                        try:
                            correct_answer = eval(equation)
                            rounded_answer = round_result(correct_answer, precision=0.001)
                        except Exception as e:
                            print(f"Generated an invalid equation: {equation}")
                            print("Error:", e)
                            equation = generate_math_equation_easy(math_difficulty)
                            correct_answer = eval(equation)
                            rounded_answer = round_result(correct_answer, precision=0.001)
                        
                        user_input = ""
                    except ValueError:
                        print("Invalid input. Please enter a numeric value.")
                        user_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                else:
                    user_input += event.unicode
            
            if leave_button.is_clicked(event):
                return True

        pygame.display.flip()

    return True

def minigames_menu():
    Math_Button = Button("Math", screen_width // 2 - 165, screen_height // 2 - 140, 330, 50, hover_color)    
    Back_Button = Button("Back", screen_width // 2 - 165, screen_height // 2 + 70, 330, 50, hover_color)
    
    while True:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        Math_Button.draw(screen)
        Back_Button.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if Math_Button.is_clicked(event):
                if not math_activity_menu():
                    return False
            
            if Back_Button.is_clicked(event):
                return True
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return True
        
        pygame.display.flip()



def status_window():
    Back_Button = Button("Back", 10, 10, 100, 40, hover_color)
    View_Artifacts = Button("Artifacts", screen_width - 150, 10, 140, 40, hover_color)
    
    stats = {
        "Level": 1,
        "HP": 8,
        "ATK": 0.3,
        "DEF": 0,
        "SPD": 0.1,
        "mana": 0,
    }
    
    running = True
    while running:
        screen.fill(white)
        screen.blit(background_image, (0, 0))
        
        # Display stats
        y_offset = 150
        for stat, value in stats.items():
            stat_text = font_medium.render(f"{stat}: {value}", True, stat_text_color)
            screen.blit(stat_text, (screen_width//2 - stat_text.get_width()//2, y_offset))
            y_offset += 60
        
        Back_Button.draw(screen)
        View_Artifacts.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if Back_Button.is_clicked(event):
                return True
            if View_Artifacts.is_clicked(event):
                view_artifacts()
        
        pygame.display.flip()

minigames = Button("Minigames", screen_width // 2 - 165, screen_height // 2 - 50, 330, 50, hover_color)
Math_Button = Button("Math", screen_width // 2 - 165, screen_height // 2 - 150, 330, 50, hover_color)

Stats_Menu = Button("Stats", screen_width // 2 - 165, screen_height // 2 + 50, 330, 50, hover_color)  

if __name__ == "__main__":
    initialize_database()
    running = True
    while running:
        screen.fill(black)
        screen.blit(background_image, (0, 0))
        minigames.draw(screen)
        Stats_Menu.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
              running = False
            if minigames.is_clicked(event):
                running = minigames_menu()
            
            if Stats_Menu.is_clicked(event):
                running = status_window()
        
        pygame.display.flip()


