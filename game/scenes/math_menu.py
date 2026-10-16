"""Math Arena: difficulty selection with enforced level locks.

The old menu showed "Locked LV: 8" labels but never locked anything, and
its points readout was a stray "x/20". Now the character level actually
gates the harder tiers, the entry fee is charged per tier (and refunded
when leaving mid-round), and correct answers pay skill points back, so
the arena is a real point source instead of a pure sink.
"""
import pygame

from .. import db
from ..core import Scene
from ..settings import Colors, get_font, scaled
from ..ui import Button, draw_panel, truncate_text


class Tier:
    """One arena difficulty: entry fee, math hardness, level gate, payout."""

    def __init__(self, name, fee, difficulty, level_req, reward):
        self.name = name
        self.fee = fee
        self.difficulty = difficulty
        self.level_req = level_req
        self.reward = reward        # skill points per correct answer


TIERS = (
    Tier("Easy", 20, 1, 1, 10),
    Tier("Medium", 50, 7, 8, 30),
    Tier("Hard", 200, 14, 15, 120),
    Tier("Extreme", 600, 20, 25, 400),
)


def tier_for(difficulty):
    for tier in TIERS:
        if tier.difficulty == difficulty:
            return tier
    return TIERS[0]


class MathMenuScene(Scene):
    def __init__(self):
        super().__init__()
        self.leave_button = Button("Leave", 0.1, 0.1, 0.1, 0.1, is_back_button=True)
        self.points = 0
        self.level = 1
        self.row_rects = []           # [(rect, Tier), ...]

    def on_enter(self, app):
        self.points = db.get_current_points()
        self.level = db.get_base_stats()["level"]

    def handle_event(self, app, event):
        if self.leave_button.is_clicked(app, event):
            app.pop_scene()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, tier in self.row_rects:
                if rect.collidepoint(event.pos):
                    self._pick(app, tier)
                    return

    def _pick(self, app, tier):
        if self.level < tier.level_req:
            self.flash(f"{tier.name} requires level {tier.level_req}!", Colors.red)
            return
        if not db.subtract_points(tier.fee):
            self.flash("Not enough points!", Colors.red)
            return
        from .minigames import MathGameScene
        app.push_scene(MathGameScene(tier.difficulty))

    def draw(self, app):
        screen = app.screen
        medium, small = get_font(40), get_font(28)

        # Title and status header stacked (measured) so they never collide,
        # whatever the window width.
        title = get_font(55).render("Math Arena", True, Colors.gold)
        title_y = scaled(14)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, title_y))
        header = medium.render(f"Level {self.level}    Points: {self.points}",
                               True, Colors.white)
        header_y = title_y + title.get_height() + scaled(6)
        screen.blit(header, (app.width // 2 - header.get_width() // 2,
                             header_y))

        rows = len(TIERS)
        top = header_y + header.get_height() + scaled(16)
        bottom_margin = scaled(70) + small.get_height() + scaled(12)
        available = app.height - top - bottom_margin
        row_height = max(scaled(56),
                         (available - scaled(12) * (rows - 1)) // rows)
        width = int(app.width * 0.66)
        x = app.width // 2 - width // 2
        pad = scaled(16)

        self.row_rects = []
        for index, tier in enumerate(TIERS):
            y = top + index * (row_height + scaled(12))
            rect = pygame.Rect(x, y, width, row_height)
            locked = self.level < tier.level_req
            affordable = self.points >= tier.fee
            if locked:
                color = (50, 50, 58, 235)
            elif affordable:
                color = (0, 120, 60, 235)
            else:
                color = (120, 60, 30, 235)
            border = (90, 90, 100, 255) if locked else (*Colors.accent, 220)
            draw_panel(screen, rect, color, radius=10, border=border)
            self.row_rects.append((rect, tier))

            name_font = get_font(34)
            name_text = name_font.render(tier.name, True,
                                         Colors.gray if locked else Colors.gold)
            name_x = rect.x + pad
            screen.blit(name_text,
                        (name_x,
                         rect.y + (rect.height - name_text.get_height()) // 2))

            # Right column: right-aligned against the row edge and truncated
            # to the space left of the tier name, so nothing can overlap.
            avail = rect.right - pad - (name_x + name_text.get_width() + pad)
            right_x = rect.right - pad
            top_line = (f"Requires level {tier.level_req}" if locked
                        else f"Entry: {tier.fee} pts")
            fee_color = Colors.red if locked else (
                Colors.light_gray if affordable else Colors.red)
            fee_text = small.render(truncate_text(top_line, small, avail),
                                    True, fee_color)
            screen.blit(fee_text, (right_x - fee_text.get_width(),
                                   rect.y + scaled(10)))

            reward_text = small.render(
                truncate_text(f"Per solve: +{tier.reward} pts, "
                              f"+100 artifact pts", small, avail),
                True, Colors.stat_text_color)
            screen.blit(reward_text, (right_x - reward_text.get_width(),
                                      rect.bottom - scaled(10)
                                      - reward_text.get_height()))

        hint = small.render("Entry fee is refunded when you leave mid-round. "
                            "Streaks boost artifact points!",
                            True, Colors.light_gray)
        hint_y = min(app.height - hint.get_height() - scaled(8),
                     top + rows * (row_height + scaled(12)) + scaled(4))
        screen.blit(hint, (app.width // 2 - hint.get_width() // 2, hint_y))

        self.leave_button.draw(app)
        self.draw_flash(app)

