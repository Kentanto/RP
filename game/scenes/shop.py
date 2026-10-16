"""Shop: item cards drawn straight from the item definitions."""
import pygame

from .. import db
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font, scaled
from ..ui import Button, draw_panel, wrap_text
from .inventory import RARITY_COLORS, _parse_color, item_stat_lines


class ShopScene(Scene):
    ITEM_HEIGHT = 120          # design pixels, scaled at use
    PADDING = 20
    RIGHT_ZONE = 210           # room for price + stock + Buy button

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
            total_height = (len(self.shop_items)
                           * (scaled(self.ITEM_HEIGHT) + scaled(self.PADDING))
                           - scaled(self.PADDING))
            min_scroll = min(0, -(total_height - app.height + scaled(150)))
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * scaled(30)))
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
        """Card and Buy-button rects, shared by the click handler and draw."""
        cards = []
        pad = scaled(self.PADDING)
        card_width = app.width - scaled(100)
        card_height = scaled(self.ITEM_HEIGHT)
        y_pos = scaled(100) + self.scroll_y
        for item in self.shop_items:
            card_rect = pygame.Rect(scaled(50), y_pos, card_width, card_height)
            button_rect = pygame.Rect(card_rect.right - pad - scaled(100),
                                      card_rect.bottom - scaled(36),
                                      scaled(100), scaled(26))
            cards.append((card_rect, button_rect, item))
            y_pos += card_height + pad
        return cards

    def draw(self, app):
        screen = app.screen
        medium, small = get_font(40), get_font(28)
        pad = scaled(self.PADDING)

        title = get_font(55).render("Shop", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, scaled(20)))
        points_text = medium.render(f"Points: {self.points}", True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - scaled(20),
                                  scaled(20)))

        for card_rect, button_rect, item in self._cards(app):
            if card_rect.bottom < scaled(60) or card_rect.top > app.height:
                continue
            rarity_color = RARITY_COLORS.get(item["rarity"], Colors.white)
            special = item["category"] == "special"
            draw_panel(screen, card_rect, (40, 40, 40, 230), radius=10,
                       border=(*rarity_color, 230) if special else None)

            # Left column: icon, then text stacked by measured heights.
            icon = get_icon(item["icon"], _parse_color(item["color"]),
                            scaled(84), fallback_shape=item["type"])
            icon_x = card_rect.x + pad
            screen.blit(icon, (icon_x,
                               card_rect.y + (card_rect.height - icon.get_height()) // 2))
            text_x = icon_x + icon.get_width() + scaled(16)
            text_w = card_rect.right - scaled(self.RIGHT_ZONE) - pad - text_x

            name_text = medium.render(item["name"], True, rarity_color)
            screen.blit(name_text, (text_x, card_rect.y + scaled(10)))
            if special:
                tag = small.render("SPECIAL", True, Colors.gold)
                screen.blit(tag, (text_x + name_text.get_width() + scaled(10),
                                  card_rect.y + scaled(10)
                                  + (name_text.get_height() - tag.get_height()) // 2))

            stats_line = "  |  ".join(item_stat_lines(item))
            y = card_rect.y + scaled(10) + name_text.get_height() + scaled(4)
            if stats_line:
                stats_text = small.render(
                    wrap_text(stats_line, small, text_w)[0],
                    True, Colors.stat_text_color)
                screen.blit(stats_text, (text_x, y))
                y += stats_text.get_height() + scaled(4)
            desc_lines = wrap_text(item["description"] or "", small, text_w)[:1]
            if desc_lines:
                desc_text = small.render(desc_lines[0], True, Colors.light_gray)
                screen.blit(desc_text, (text_x, y))
                y += desc_text.get_height() + scaled(4)
            info_text = small.render(f"Type: {item['type'].capitalize()}",
                                     True, Colors.white)
            # Only show the type line if it still fits inside the card.
            if y + info_text.get_height() < card_rect.bottom - scaled(10):
                screen.blit(info_text, (text_x, y))

            # Right column: price, stock and Buy button, all right-aligned
            # so they cannot slide over the left text.
            right_x = card_rect.right - pad
            price_color = Colors.gold if self.points >= item["price"] else Colors.red
            price_text = medium.render(f"{item['price']} pts", True, price_color)
            screen.blit(price_text, (right_x - price_text.get_width(),
                                     card_rect.y + scaled(10)))
            stock = item["stock"]
            stock_label = "Unlimited" if stock < 0 else ("Sold out" if stock == 0
                                                          else f"Stock: {stock}")
            stock_text = small.render(stock_label, True, Colors.light_gray)
            screen.blit(stock_text, (right_x - stock_text.get_width(),
                                     card_rect.y + scaled(10)
                                     + price_text.get_height() + scaled(4)))

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

