"""Inventory: category tabs, auto-drawn icons and rich tooltips.

Items come from the item definitions (data/items.txt via the database),
including the 'special' category that gets its own tab.
"""
import json

import pygame

from .. import db
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font, scaled
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
        self.cell_rects = []         # [(rect, item), ...] filled by draw()

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

    def _tab_layout(self, app):
        """Tab rects flowing left to right, wrapping to a new row when they
        would run off the window. Returns (rects, bottom_y)."""
        small = get_font(30)
        height = max(scaled(30), int(app.height * 0.05))
        gap = scaled(12)
        left = int(app.width * 0.08)
        max_x = app.width - left
        x, y = left, int(app.height * 0.10)
        rects = []
        for label, _selector in TYPE_TABS:
            width = small.size(label)[0] + scaled(30)
            if rects and x + width > max_x:      # wrap instead of overflowing
                x = left
                y += height + scaled(6)
            rects.append(pygame.Rect(x, y, width, height))
            x += width + gap
        return rects, y + height

    def _grid(self, app):
        padding = max(scaled(6), int(app.width * 0.006))
        cell = max(scaled(56), int(app.width * 0.075))
        start_x = int(app.width * 0.08)
        _rects, tabs_bottom = self._tab_layout(app)
        start_y = tabs_bottom + scaled(16)
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
            for rect, item in self.cell_rects:
                if rect.collidepoint(event.pos):
                    app.push_scene(ItemActionScene(item))
                    return
        if event.type == pygame.MOUSEWHEEL:
            padding, cell, start_x, start_y, cols, _rows = self._grid(app)
            total = len(self._visible_items())
            grid_rows = max(1, -(-total // cols))     # ceil division
            max_height = grid_rows * (cell + padding)
            min_scroll = min(0, -(max_height - (app.height - start_y - scaled(20))))
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * scaled(20)))

    def _draw_tabs(self, app):
        small = get_font(30)
        self.tab_rects, _bottom = self._tab_layout(app)
        for index, (rect, (label, _selector)) in enumerate(zip(self.tab_rects, TYPE_TABS)):
            active = index == self.active_tab
            surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(surface, (70, 130, 220, 235) if active else (50, 50, 58, 220),
                             surface.get_rect(), border_radius=8)
            pygame.draw.rect(surface, Colors.accent if active else (90, 90, 100, 255),
                             surface.get_rect(), width=2, border_radius=8)
            app.screen.blit(surface, rect.topleft)
            text = small.render(label, True, Colors.white if active else Colors.light_gray)
            app.screen.blit(text, (rect.x + (rect.width - text.get_width()) // 2,
                                   rect.y + (rect.height - text.get_height()) // 2))

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
        self.cell_rects = []

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
                if y + cell < start_y:
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
                self.cell_rects.append((rect, item))
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
        width = scaled(360)
        stats = item_stat_lines(item)
        desc_lines = wrap_text(item["description"] or "", small, width - scaled(40))[:3]
        line_h = small.get_height()
        height = (scaled(16) + line_h + scaled(14) + line_h + scaled(10)
                  + (line_h + scaled(8)) * len(stats)
                  + (line_h + scaled(6)) * len(desc_lines) + scaled(16))

        x = rect.right + scaled(12)
        if x + width > app.width:
            x = rect.x - width - scaled(12)
        x = max(scaled(10), x)
        y = max(scaled(10), min(rect.y, app.height - height - scaled(10)))
        draw_panel(screen, pygame.Rect(x, y, width, height))

        name = small.render(item["name"], True, rarity_color)
        screen.blit(name, (x + scaled(15), y + scaled(12)))
        kind = item["type"].capitalize()
        if item["category"] == "special":
            kind += "  * Special *"
        kind_text = small.render(f"{kind} | {item['rarity'].capitalize()}",
                                 True, Colors.light_gray)
        screen.blit(kind_text, (x + scaled(15),
                               y + scaled(12) + name.get_height() + scaled(8)))
        offset = (y + scaled(12) + name.get_height() + scaled(8)
                  + kind_text.get_height() + scaled(10))
        for line in stats:
            stat_text = small.render(line, True, Colors.stat_text_color)
            screen.blit(stat_text, (x + scaled(15), offset))
            offset += line_h + scaled(8)
        for line in desc_lines:
            desc_text = small.render(line, True, Colors.light_gray)
            screen.blit(desc_text, (x + scaled(15), offset))
            offset += line_h + scaled(6)


class ItemActionScene(Scene):
    """Overlay with the actions for one inventory item: use, sell, equip.

    Closing the overlay re-enters the inventory scene, so quantities
    and the grid refresh automatically.
    """

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.action_rects = []          # [(rect, action_name), ...]

    def _panel_rect(self, app):
        width, height = int(app.width * 0.44), int(app.height * 0.52)
        return pygame.Rect((app.width - width) // 2, (app.height - height) // 2,
                           width, height)

    def _actions(self):
        """(action, label) pairs this item supports."""
        item = self.item
        actions = []
        if item["type"] == "consumable":
            actions.append(("use", "Use"))
        if item["sell_price"] > 0:
            actions.append(("sell", f"Sell  (+{item['sell_price']} pts)"))
        if item["slot"]:
            actions.append(("equip", f"Equip  ({item['slot'].capitalize()})"))
        return actions

    def handle_event(self, app, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action in self.action_rects:
                if rect.collidepoint(event.pos):
                    self._run(app, action)
                    return
            if not self._panel_rect(app).collidepoint(event.pos):
                app.pop_scene()

    def _run(self, app, action):
        key = self.item["key"]
        if action == "use":
            ok, message = db.use_item(key)
        elif action == "sell":
            ok, message = db.sell_item(key)
        else:                                   # equip
            ok = db.equip_gear(self.item["slot"], key)
            message = "Equipped!" if ok else "Can't equip that"
        if ok:
            app.pop_scene()
            if app.scene is not None:            # flash it on the inventory below
                app.scene.flash(message, Colors.green)
        else:
            self.flash(message, Colors.red)

    def draw(self, app):
        screen = app.screen
        panel = self._panel_rect(app)
        veil = pygame.Surface((app.width, app.height), pygame.SRCALPHA)
        veil.fill((8, 8, 16, 170))
        screen.blit(veil, (0, 0))
        draw_panel(screen, panel, (30, 30, 38, 245), radius=14,
                   border=(*Colors.accent, 200))

        name = get_font(36).render(
            self.item["name"], True,
            RARITY_COLORS.get(self.item["rarity"], Colors.white))
        screen.blit(name, (panel.x + scaled(24), panel.y + scaled(18)))
        small = get_font(26)
        sub = f"{self.item['type'].capitalize()}  |  x{self.item['quantity']}"
        screen.blit(small.render(sub, True, Colors.light_gray),
                    (panel.x + scaled(24),
                     panel.y + scaled(18) + name.get_height() + scaled(8)))

        y = panel.y + scaled(18) + name.get_height() + scaled(8) \
            + small.get_height() + scaled(14)
        for line in wrap_text(self.item["description"] or "", small,
                              panel.width - scaled(48))[:3]:
            screen.blit(small.render(line, True, Colors.light_gray),
                        (panel.x + scaled(24), y))
            y += small.get_height() + scaled(6)

        self.action_rects = []
        y += scaled(14)
        button_h = max(scaled(44), small.get_height() + scaled(18))
        for action, label in self._actions():
            rect = pygame.Rect(panel.x + scaled(24), y,
                               panel.width - scaled(48), button_h)
            color = (0, 130, 60) if action in ("use", "equip") else (150, 110, 30)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, Colors.light_gray, rect, 1, border_radius=8)
            text = small.render(label, True, Colors.white)
            screen.blit(text, (rect.x + (rect.width - text.get_width()) // 2,
                               rect.y + (rect.height - text.get_height()) // 2))
            self.action_rects.append((rect, action))
            y += button_h + scaled(8)

        if not self.action_rects:
            screen.blit(small.render("Nothing you can do with this yet.",
                                     True, Colors.gray), (panel.x + scaled(24), y))

        hint = small.render("Click outside to close", True, Colors.gray)
        screen.blit(hint, (panel.centerx - hint.get_width() // 2,
                           panel.bottom - scaled(38)))
        self.draw_flash(app)

