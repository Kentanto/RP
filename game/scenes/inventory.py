"""Inventory: category tabs, auto-drawn icons and rich tooltips.

Items come from the item definitions (data/items.txt via the database),
including the 'special' category that gets its own tab.
"""
import json

import pygame

from .. import db
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font
from ..ui import Button, draw_panel, wrap_text

RARITY_COLORS = {
    "common": Colors.white,
    "uncommon": Colors.green,
    "rare": Colors.purple,
    "epic": Colors.orange,
    "legendary": Colors.gold,
}

# (tab label, filter) - filter None = all, "special" = category, else types
TYPE_TABS = [
    ("All", None),
    ("Weapons", ("weapon",)),
    ("Armor", ("armor",)),
    ("Consumables", ("consumable",)),
    ("Materials", ("material",)),
    ("Quest", ("quest",)),
    ("Special", "special"),
]


def _parse_color(text):
    try:
        return tuple(int(part) for part in text.split(","))
    except (ValueError, AttributeError):
        return (200, 200, 200)


def _format_stat(name, value):
    label = name.replace("_", " ").upper()
    if isinstance(value, float) and 0 < value < 1:
        return f"{label} +{value * 100:.1f}%"
    if isinstance(value, float) and value == int(value):
        return f"{label} +{int(value)}"
    return f"{label} +{value:g}"


def item_stat_lines(item):
    """Pretty stat lines for tooltips and cards."""
    try:
        stats = json.loads(item["stats"] or "{}")
    except ValueError:
        stats = {}
    return [_format_stat(name, value) for name, value in stats.items()]


class InventoryScene(Scene):
    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.shop_button = Button("Shop", 0.92, 0.05, 0.1, 0.1, Colors.hover_color)
        self.items = []
        self.scroll_y = 0
        self.active_tab = 0
        self.tab_rects = []

    def on_enter(self, app):
        self.items = db.get_inventory_items()
        self.scroll_y = 0

    def _visible_items(self):
        label, selector = TYPE_TABS[self.active_tab]
        if selector is None:
            return self.items
        if selector == "special":
            return [item for item in self.items if item["category"] == "special"]
        return [item for item in self.items if item["type"] in selector]

    def _grid(self, app):
        padding = max(6, int(app.width * 0.006))
        cell = max(56, int(app.width * 0.075))
        start_x = int(app.width * 0.08)
        start_y = int(app.height * 0.18)
        cols = max(4, min(12, (app.width - start_x * 2) // (cell + padding)))
        rows = 6
        return padding, cell, start_x, start_y, cols, rows

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if self.shop_button.is_clicked(app, event):
            from .shop import ShopScene
            app.push_scene(ShopScene())
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.tab_rects):
                if rect.collidepoint(event.pos):
                    self.active_tab = index
                    self.scroll_y = 0
                    return
        if event.type == pygame.MOUSEWHEEL:
            padding, cell, _x, _y, cols, _rows = self._grid(app)
            total = len(self._visible_items())
            grid_rows = max(1, -(-total // cols))     # ceil division
            max_height = grid_rows * (cell + padding)
            min_scroll = min(0, -(max_height - app.height + 220))
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * 20))

    def _draw_tabs(self, app):
        small = get_font(30)
        self.tab_rects = []
        x = int(app.width * 0.08)
        y = int(app.height * 0.10)
        height = int(app.height * 0.05)
        for index, (label, _selector) in enumerate(TYPE_TABS):
            width = small.size(label)[0] + 30
            rect = pygame.Rect(x, y, width, height)
            active = index == self.active_tab
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(surface, (70, 130, 220, 235) if active else (50, 50, 58, 220),
                             surface.get_rect(), border_radius=8)
            pygame.draw.rect(surface, Colors.accent if active else (90, 90, 100, 255),
                             surface.get_rect(), width=2, border_radius=8)
            app.screen.blit(surface, rect.topleft)
            text = small.render(label, True, Colors.white if active else Colors.light_gray)
            app.screen.blit(text, (x + (width - text.get_width()) // 2,
                                   y + (height - text.get_height()) // 2))
            self.tab_rects.append(rect)
            x += width + 12

    def draw(self, app):
        screen = app.screen
        padding, cell, start_x, start_y, cols, rows = self._grid(app)
        small = get_font(26)

        title = get_font(55).render("Inventory", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, 20))

        self._draw_tabs(app)
        items = self._visible_items()
        mouse_pos = pygame.mouse.get_pos()
        hovered = None

        index = 0
        for row in range(rows * 4):          # the grid can scroll deep
            done = False
            for col in range(cols):
                if index >= len(items):
                    done = True
                    break
                item = items[index]
                x = start_x + col * (cell + padding)
                y = start_y + row * (cell + padding) + self.scroll_y
                if y > app.height:           # fully below the screen: stop
                    done = True
                    break
                rect = pygame.Rect(x, y, cell, cell)
                if y + cell < int(app.height * 0.17):
                    index += 1
                    continue
                rarity_color = RARITY_COLORS.get(item["rarity"], Colors.white)
                special = item["category"] == "special"

                surface = pygame.Surface((cell, cell), pygame.SRCALPHA)
                pygame.draw.rect(surface, (50, 50, 58, 230), surface.get_rect(),
                                 border_radius=8)
                pygame.draw.rect(surface, (*rarity_color, 200 if special else 120),
                                 surface.get_rect(), width=3 if special else 2,
                                 border_radius=8)
                screen.blit(surface, rect.topleft)

                icon = get_icon(item["icon"], _parse_color(item["color"]),
                                int(cell * 0.72), fallback_shape=item["type"])
                screen.blit(icon, (x + (cell - icon.get_width()) // 2,
                                  y + (cell - icon.get_height()) // 2))

                if item["quantity"] > 1:
                    quantity = small.render(str(item["quantity"]), True, Colors.white)
                    badge = pygame.Surface((quantity.get_width() + 10,
                                            quantity.get_height() + 4), pygame.SRCALPHA)
                    pygame.draw.rect(badge, (0, 0, 0, 170), badge.get_rect(),
                                     border_radius=6)
                    badge.blit(quantity, (5, 2))
                    screen.blit(badge, (x + cell - badge.get_width() - 4,
                                        y + cell - badge.get_height() - 4))

                if special:
                    pygame.draw.circle(screen, Colors.gold, (x + 12, y + 12), 6)
                    pygame.draw.circle(screen, (60, 40, 0), (x + 12, y + 12), 2)

                if rect.collidepoint(mouse_pos):
                    hovered = (rect, item)
                index += 1
            if done:
                break

        if hovered is not None:
            self._draw_tooltip(app, hovered[0], hovered[1])

        self.back_button.draw(app)
        self.shop_button.draw(app)
        self.draw_flash(app)

    def _draw_tooltip(self, app, rect, item):
        screen = app.screen
        small = get_font(26)
        rarity_color = RARITY_COLORS.get(item["rarity"], Colors.white)
        width = 340
        stats = item_stat_lines(item)
        desc_lines = wrap_text(item["description"] or "", small, width - 40)
        height = 110 + 28 * len(stats) + 26 * min(3, len(desc_lines))

        x = rect.right + 12
        if x + width > app.width:
            x = rect.x - width - 12
        y = max(10, min(rect.y, app.height - height - 10))
        draw_panel(screen, pygame.Rect(x, y, width, height))

        name = small.render(item["name"], True, rarity_color)
        screen.blit(name, (x + 15, y + 10))
        kind = item["type"].capitalize()
        if item["category"] == "special":
            kind += "  * Special *"
        kind_text = small.render(f"{kind} | {item['rarity'].capitalize()}",
                                 True, Colors.light_gray)
        screen.blit(kind_text, (x + 15, y + 42))
        offset = y + 74
        for line in stats:
            stat_text = small.render(line, True, Colors.stat_text_color)
            screen.blit(stat_text, (x + 15, offset))
            offset += 28
        for line in desc_lines[:3]:
            desc_text = small.render(line, True, Colors.light_gray)
            screen.blit(desc_text, (x + 15, offset))
            offset += 26

