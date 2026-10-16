"""Missions: data-driven objectives that track themselves and pay out.

Definitions live in data/missions.txt (same content format as items,
artifacts and abilities). The database keeps progress and claimed state,
the game bumps progress from the places where things actually happen
(math rounds, artifact drops, level-ups, skill unlocks), and this scene
draws the list with progress bars and a Claim button for finished ones.
"""
import pygame

from .. import db
from ..core import Scene
from ..settings import Colors, get_font, scaled
from ..ui import Button, draw_panel, wrap_text


class MissionsScene(Scene):
    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.missions = []
        self.claim_rects = []          # [(rect, mission_key), ...]
        self.banner_heights = []       # filled by draw(), used for scrolling
        self.scroll_y = 0

    def on_enter(self, app):
        self.missions = db.get_missions()

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, key in self.claim_rects:
                if rect.collidepoint(event.pos):
                    ok, message = db.claim_mission(key)
                    self.flash(message, Colors.green if ok else Colors.red)
                    self.on_enter(app)
                    return
        if event.type == pygame.MOUSEWHEEL:
            padding = scaled(24)
            total_height = (sum(self.banner_heights)
                            + padding * max(0, len(self.banner_heights) - 1))
            min_scroll = min(0, -(total_height - app.height + scaled(170)))
            self.scroll_y = max(min_scroll, min(0, self.scroll_y + event.y * scaled(24)))

    def _reward_text(self, mission):
        parts = []
        if mission["reward_points"]:
            parts.append(f"+{mission['reward_points']} pts")
        if mission["reward_xp"]:
            parts.append(f"+{mission['reward_xp']} XP")
        if mission["reward_artifact_points"]:
            parts.append(f"+{mission['reward_artifact_points']} artifact pts")
        return "  ".join(parts)

    def draw(self, app):
        screen = app.screen
        small, medium = get_font(28), get_font(40)
        banner_width = app.width - scaled(100)
        padding = scaled(24)

        title = get_font(55).render("Missions", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, scaled(20)))

        self.claim_rects = []
        self.banner_heights = []
        y_pos = scaled(110) + self.scroll_y
        for mission in self.missions:
            lines = wrap_text(mission["description"] or "", small,
                              banner_width - scaled(300))[:2]
            banner_height = scaled(66) + len(lines) * scaled(26) + padding
            self.banner_heights.append(banner_height)
            if -banner_height <= y_pos <= app.height:
                rect = pygame.Rect(scaled(50), y_pos, banner_width, banner_height)
                complete = mission["progress"] >= mission["target"]
                border = ((*Colors.gold, 230)
                          if complete and not mission["claimed"] else None)
                draw_panel(screen, rect, (40, 40, 40, 230), radius=10, border=border)

                title_text = medium.render(mission["name"], True, Colors.gold)
                screen.blit(title_text, (rect.x + scaled(20), rect.y + scaled(12)))
                if mission["claimed"]:
                    status, status_color = "Claimed", Colors.green
                elif complete:
                    status, status_color = "Ready to claim!", Colors.gold
                else:
                    status, status_color = self._reward_text(mission), Colors.light_gray
                status_text = small.render(status, True, status_color)
                screen.blit(status_text,
                            (rect.right - status_text.get_width() - scaled(20),
                             rect.y + scaled(14)))

                y = rect.y + scaled(54)
                for line in lines:
                    screen.blit(small.render(line, True, Colors.white),
                                (rect.x + scaled(20), y))
                    y += small.get_height() + scaled(6)

                # Progress bar with the claim button beside it: the button
                # is placed first and the bar measured against it, so the
                # two can never overlap.
                bar_x = rect.x + scaled(20)
                bar_h = scaled(14)
                bar_y = rect.bottom - bar_h - scaled(14)
                claim_rect = None
                if complete and not mission["claimed"]:
                    claim_rect = pygame.Rect(
                        rect.right - scaled(20) - scaled(170),
                        bar_y - scaled(10), scaled(170), scaled(34))
                bar_w = ((claim_rect.left - scaled(16) - bar_x) if claim_rect
                         else banner_width - scaled(40))
                pygame.draw.rect(screen, (60, 60, 70),
                                 (bar_x, bar_y, bar_w, bar_h), border_radius=7)
                ratio = (min(1.0, mission["progress"] / mission["target"])
                         if mission["target"] else 0.0)
                if ratio > 0:
                    fill_color = Colors.green if mission["claimed"] else Colors.accent
                    pygame.draw.rect(screen, fill_color,
                                     (bar_x, bar_y, max(8, int(bar_w * ratio)), bar_h),
                                     border_radius=7)
                label = f"{min(mission['progress'], mission['target'])} / {mission['target']}"
                progress_text = small.render(label, True, Colors.light_gray)
                screen.blit(progress_text, (bar_x + bar_w - progress_text.get_width(),
                                           bar_y - progress_text.get_height() - 4))

                if claim_rect is not None:
                    pygame.draw.rect(screen, (0, 130, 60), claim_rect, border_radius=8)
                    claim_text = small.render("Claim", True, Colors.white)
                    screen.blit(claim_text,
                                (claim_rect.centerx - claim_text.get_width() // 2,
                                 claim_rect.centery - claim_text.get_height() // 2))
                    self.claim_rects.append((claim_rect, mission["key"]))
            y_pos += banner_height + padding

        self.back_button.draw(app)
        self.draw_flash(app)

