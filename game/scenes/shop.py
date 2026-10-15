"""Shop: item cards with buy buttons."""
import pygame

from .. import db
from ..core import Scene
from ..settings import Colors, get_font
from ..ui import Button, draw_panel
from .inventory import RARITY_COLORS


class ShopScene(Scene):
    ITEM_HEIGHT = 100
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
                    item_id, name, _desc, _type, rarity, price, quantity = item
                    if self.points < price or quantity <= 0:
                        self.message = "Not enough points!"
                        self.message_color = Colors.red
                        self.message_until = pygame.time.get_ticks() + 1200
                        return
                    success, message = db.purchase_item(item_id, price)
                    self.message = "Item purchased!" if success else message
                    self.message_color = Colors.green if success else Colors.red
                    self.message_until = pygame.time.get_ticks() + 1200
                    if success:
                        self.on_enter(app)
                    return

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
        medium, small = get_font(40), get_font(30)

        title = get_font(55).render("Shop", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, 20))
        points_text = medium.render(f"Points: {self.points}", True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - 20, 20))

        card_width = app.width - 100
        for card_rect, button_rect, item in self._cards(app):
            item_id, name, desc, type_, rarity, price, quantity = item
            draw_panel(screen, card_rect, (40, 40, 40, 230), radius=10)

            name_text = medium.render(name, True, RARITY_COLORS.get(rarity, Colors.white))
            screen.blit(name_text, (card_rect.x + self.PADDING, card_rect.y + 10))
            price_color = Colors.gold if self.points >= price else Colors.red
            price_text = medium.render(f"Price: {price} points", True, price_color)
            screen.blit(price_text, (card_rect.right - price_text.get_width() - self.PADDING,
                                     card_rect.y + 10))
            desc_text = small.render(desc, True, Colors.light_gray)
            screen.blit(desc_text, (card_rect.x + self.PADDING, card_rect.y + 45))
            info_text = small.render(f"Type: {type_} | Rarity: {rarity.capitalize()}",
                                     True, Colors.white)
            screen.blit(info_text, (card_rect.x + self.PADDING, card_rect.y + 70))

            can_buy = self.points >= price and quantity > 0
            pygame.draw.rect(screen, Colors.green if can_buy else Colors.red,
                             button_rect, border_radius=5)
            buy_text = small.render("Buy", True, Colors.white)
            screen.blit(buy_text, (button_rect.x + (button_rect.width - buy_text.get_width()) // 2,
                                   button_rect.y + (button_rect.height - buy_text.get_height()) // 2))
            stock_text = small.render(
                f"Stock: {quantity if quantity > 0 else 'Unlimited'}", True, Colors.white)
            screen.blit(stock_text, (card_rect.x + card_width - stock_text.get_width() - 20,
                                     card_rect.y + 45))

        if self.message and pygame.time.get_ticks() < self.message_until:
            message_surface = medium.render(self.message, True, self.message_color)
            screen.blit(message_surface,
                         (app.width // 2 - message_surface.get_width() // 2,
                          app.height // 2 - message_surface.get_height() // 2))
        elif self.message:
            self.message = None

        self.back_button.draw(app)
        self.draw_flash(app)
