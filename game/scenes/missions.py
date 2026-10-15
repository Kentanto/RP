"""Missions list (static for now, as in the original)."""
import pygame

from ..core import Scene
from ..settings import Colors, get_font
from ..ui import Button, draw_panel

MISSIONS = [
    {
        "title": "The Beginning",
        "description": "Survive the first raid \n Bonus: Kill an enemy",
        "reward": "100 points",
        "time_limit": "24 hours",
    }
]


class MissionsScene(Scene):
    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.scroll_y = 0

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if event.type == pygame.MOUSEWHEEL:
            padding = 20
            total_height = sum(m["banner_height"] + padding for m in MISSIONS
                               if "banner_height" in m) or 0
            min_scroll = -(total_height - app.height + 150)
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * 20))

    def draw(self, app):
        screen = app.screen
        banner_width = app.width - 100
        text_width = int(banner_width * 0.75)
        padding = 20
        small, medium = get_font(30), get_font(40)

        y_pos = 100 + self.scroll_y
        for mission in MISSIONS:
            lines = []
            for paragraph in mission["description"].split("\n"):
                current_line = []
                for word in paragraph.split():
                    test_line = " ".join(current_line + [word])
                    if small.size(test_line)[0] <= text_width:
                        current_line.append(word)
                    else:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))

            title_height = 60
            banner_height = title_height + len(lines) * 25 + padding * 2
            mission["banner_height"] = banner_height

            if -banner_height <= y_pos <= app.height:
                banner_rect = pygame.Rect(50, y_pos, banner_width, banner_height)
                draw_panel(screen, banner_rect, (40, 40, 40, 230), radius=10)

                stats_y = y_pos + 15
                reward_text = small.render(f"Reward: {mission['reward']}", True, Colors.green)
                time_text = small.render(f"Time: {mission['time_limit']}", True, Colors.light_blue)
                screen.blit(reward_text, (app.width // 2 - 100, stats_y + 10))
                screen.blit(time_text, (app.width // 2 + 180, stats_y + 10))

                title_text = medium.render(mission["title"], True, Colors.gold)
                screen.blit(title_text, (70, y_pos + 20))

                text_y = y_pos + title_height + 10
                for line in lines:
                    screen.blit(small.render(line, True, Colors.white), (70, text_y))
                    text_y += 25

            y_pos += banner_height + padding

        self.back_button.draw(app)
        self.draw_flash(app)
