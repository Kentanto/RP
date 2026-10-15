"""Inventory grid with item tooltips."""
import pygame

from .. import db
from ..core import Scene
from ..settings import Colors, get_font
from ..ui import Button, draw_panel, truncate_text

RARITY_COLORS = {
    "common": Colors.white,
    "uncommon": Colors.green,
    "rare": Colors.purple,
    "epic": Colors.orange,
    "legendary": Colors.gold,
}


class InventoryScene(Scene):
    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.shop_button = Button("Shop", 0.92, 0.05, 0.1, 0.1, Colors.hover_color)
        self.items = []
        self.scroll_y = 0

    def on_enter(self, app):
        self.items = db.get_inventory_items()

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if self.shop_button.is_clicked(app, event):
            from .shop import ShopScene
            app.push_scene(ShopScene())
            return
        if event.type == pygame.MOUSEWHEEL:
            cell_size = max(48, int(app.width * 0.06))
            padding = max(6, int(app.width * 0.006))
            grid_rows = 6
            total_height = grid_rows * (cell_size + padding)
            min_scroll = -(total_height - app.height + 200)
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * 20))

    def draw(self, app):
        screen = app.screen
        padding = max(6, int(app.width * 0.006))
        cell_size = max(48, int(app.width * 0.06))
        grid_start_x = int(app.width * 0.08)
        grid_start_y = int(app.height * 0.15)
        grid_cols = max(4, min(12, (app.width - grid_start_x * 2) // (cell_size + padding)))
        grid_rows = 6
        small = get_font(30)

        title = get_font(55).render("Inventory", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, 20))

        mouse_pos = pygame.mouse.get_pos()
        hovered_item = None
        for row in range(grid_rows):
            for col in range(grid_cols):
                index = row * grid_cols + col
                x = grid_start_x + col * (cell_size + padding)
                y = grid_start_y + row * (cell_size + padding) + self.scroll_y
                rect = pygame.Rect(x, y, cell_size, cell_size)
                pygame.draw.rect(screen, Colors.dark_gray, rect, border_radius=5)
                pygame.draw.rect(screen, Colors.light_gray, rect, 2, border_radius=5)
                if index < len(self.items):
                    item = self.items[index]
                    name_text = small.render(
                        truncate_text(item[1], small, cell_size - 10),
                        True, RARITY_COLORS.get(item[4], Colors.white))
                    screen.blit(name_text, (x + (cell_size - name_text.get_width()) // 2,
                                            y + 6))
                    if item[5] and item[5] > 1:
                        quantity_text = small.render(str(item[5]), True, Colors.white)
                        screen.blit(quantity_text, (x + cell_size - quantity_text.get_width() - 5,
                                                    y + cell_size - quantity_text.get_height() - 5))
                    if rect.collidepoint(mouse_pos):
                        hovered_item = (rect, item)

        if hovered_item is not None:
            rect, item = hovered_item
            info_width, info_height = 200, 120
            draw_panel(screen, pygame.Rect(mouse_pos[0] + 10, mouse_pos[1] + 10,
                                           info_width, info_height))
            name_text = small.render(item[1], True, RARITY_COLORS.get(item[4], Colors.white))
            screen.blit(name_text, (mouse_pos[0] + 20, mouse_pos[1] + 20))
            desc_lines = item[2].split("\n") if item[2] else []
            for i, line in enumerate(desc_lines[:3]):
                desc_text = small.render(line, True, Colors.light_gray)
                screen.blit(desc_text, (mouse_pos[0] + 20, mouse_pos[1] + 50 + i * 25))

        self.back_button.draw(app)
        self.shop_button.draw(app)
        self.draw_flash(app)
