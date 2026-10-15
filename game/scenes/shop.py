"""Shop: item cards drawn straight from the item definitions."""
import pygame

from .. import db
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font
from ..ui import Button, draw_panel, wrap_text
from .inventory import RARITY_COLORS, _parse_color, item_stat_lines


class ShopScene(Scene):
    ITEM_HEIGHT = 120
    PADDING = 20

    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.shop_items = []
        self.points = 0
        self.scroll_y = 0
        self.message = None
        self.message_color = Colors.green
        self.message_until = 0

    def on_enter(self, app):
        self.shop_items = db.get_shop_items()
        self.points = db.get_current_points()

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if event.type == pygame.MOUSEWHEEL:
            total_height = len(self.shop_items) * (self.ITEM_HEIGHT + self.PADDING) - self.PADDING
            min_scroll = min(0, -(total_height - app.height + 150))
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * 30))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for card_rect, button_rect, item in self._cards(app):
                if button_rect.collidepoint(event.pos):
                    self._buy(app, item)
                    return

    def _buy(self, app, item):
        if self.points < item["price"] or item["stock"] == 0:
            self._flash("Not enough points!", Colors.red)
            return
        success, message = db.purchase_item(item["key"])
        if success:
            self._flash("Item purchased!", Colors.green)
        else:
            self._flash(message, Colors.red)
        self.on_enter(app)

    def _flash(self, text, color):
        self.message = text
        self.message_color = color
        self.message_until = pygame.time.get_ticks() + 1200

    def _cards(self, app):
        cards = []
        card_width = app.width - 100
        y_pos = 100 + self.scroll_y
        for item in self.shop_items:
            card_rect = pygame.Rect(50, y_pos, card_width, self.ITEM_HEIGHT)
            button_rect = pygame.Rect(card_width - 120 + 50,
                                      y_pos + self.ITEM_HEIGHT - 35, 100, 25)
            cards.append((card_rect, button_rect, item))
            y_pos += self.ITEM_HEIGHT + self.PADDING
        return cards

    def draw(self, app):
        screen = app.screen
        medium, small = get_font(40), get_font(28)

        title = get_font(55).render("Shop", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, 20))
        points_text = medium.render(f"Points: {self.points}", True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - 20, 20))

        for card_rect, button_rect, item in self._cards(app):
            if card_rect.bottom < 60 or card_rect.top > app.height:
                continue
            rarity_color = RARITY_COLORS.get(item["rarity"], Colors.white)
            special = item["category"] == "special"
            draw_panel(screen, card_rect, (40, 40, 40, 230), radius=10,
                       border=(*rarity_color, 230) if special else None)

            icon = get_icon(item["icon"], _parse_color(item["color"]),
                            84, fallback_shape=item["type"])
            screen.blit(icon, (card_rect.x + self.PADDING,
                              card_rect.y + (self.ITEM_HEIGHT - icon.get_height()) // 2))

            name_text = medium.render(item["name"], True, rarity_color)
            screen.blit(name_text, (card_rect.x + 120, card_rect.y + 10))
            if special:
                tag = small.render("SPECIAL", True, Colors.gold)
                screen.blit(tag, (card_rect.x + 130 + name_text.get_width(),
                                  card_rect.y + 18))

            stats_line = "  |  ".join(item_stat_lines(item))
            if stats_line:
                screen.blit(small.render(stats_line, True, Colors.stat_text_color),
                            (card_rect.x + 120, card_rect.y + 50))
            desc_lines = wrap_text(item["description"] or "", small,
                                   card_rect.width - 360)[:1]
            if desc_lines:
                screen.blit(small.render(desc_lines[0], True, Colors.light_gray),
                            (card_rect.x + 120, card_rect.y + 80))
            info_text = small.render(f"Type: {item['type'].capitalize()}",
                                     True, Colors.white)
            screen.blit(info_text, (card_rect.x + 120,
                                    card_rect.y + self.ITEM_HEIGHT - 32))

            price_color = Colors.gold if self.points >= item["price"] else Colors.red
            price_text = medium.render(f"{item['price']} pts", True, price_color)
            screen.blit(price_text, (card_rect.right - price_text.get_width() - self.PADDING,
                                     card_rect.y + 10))
            stock = item["stock"]
            stock_label = "Unlimited" if stock < 0 else ("Sold out" if stock == 0
                                                         else f"Stock: {stock}")
            screen.blit(small.render(stock_label, True, Colors.light_gray),
                        (card_rect.right - 160, card_rect.y + 52))

            can_buy = self.points >= item["price"] and stock != 0
            pygame.draw.rect(screen, Colors.green if can_buy else Colors.red,
                             button_rect, border_radius=5)
            buy_text = small.render("Buy", True, Colors.white)
            screen.blit(buy_text, (button_rect.x + (button_rect.width - buy_text.get_width()) // 2,
                                  button_rect.y + (button_rect.height - buy_text.get_height()) // 2))

        if self.message and pygame.time.get_ticks() < self.message_until:
            message_surface = medium.render(self.message, True, self.message_color)
            screen.blit(message_surface,
                        (app.width // 2 - message_surface.get_width() // 2,
                         app.height // 2 - message_surface.get_height() // 2))
        elif self.message:
            self.message = None

        self.back_button.draw(app)
        self.draw_flash(app)

