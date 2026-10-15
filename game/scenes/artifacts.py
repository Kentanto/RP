"""Artifact collection: sortable list and the detail/level-up screen."""
import pygame

from .. import audio, db
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font
from ..ui import (Button, Checkbox, DropdownMenu, draw_panel,
                  fit_text_to_box, truncate_text, wrap_text)
from .inventory import RARITY_COLORS, _parse_color

SORT_OPTIONS = [
    "Recent", "Level", "ATK", "ATK%", "DEF", "DEF%", "HP", "HP%",
    "SPD%", "Crit Rate%", "Crit DMG%",
]


class ArtifactsScene(Scene):
    """Grid of owned artifacts with sorting, scrolling and hover info."""

    def __init__(self, equip_slot=None, remove_slot=None):
        super().__init__()
        self.equip_slot = equip_slot
        self.remove_slot = remove_slot
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.artifacts = []
        self.artifact_points = 0
        self.scroll_y = 0
        self.items_per_row = 3
        self.box_width = 220
        self.box_height = 160
        self.box_padding = 20
        self.dropdown = None
        self.checkbox = None
        self.hovered_box_index = -1
        self.last_hovered_box_index = -1

    def on_enter(self, app):
        self.artifacts = db.get_all_artifacts()
        self.artifact_defs = {d["key"]: d for d in db.get_artifact_defs()}
        self.artifact_points = db.get_artifact_points()
        if self.dropdown is None:
            small = get_font(30)
            self.dropdown = DropdownMenu(SORT_OPTIONS, 40, 70, 180, 35, small)
            self.checkbox = Checkbox(230, 78, 22, checked=True, label="Descending", font=small)

    def _sorted_artifacts(self):
        selected_sort = self.dropdown.get_selected()
        descending = self.checkbox.is_checked()
        if selected_sort == "Recent":
            return sorted(self.artifacts, key=lambda a: a[0], reverse=descending)
        if selected_sort == "Level":
            return sorted(self.artifacts, key=lambda a: (a[8], a[3]), reverse=descending)
        filtered = [a for a in self.artifacts
                    if db.get_artifact_stat_total(a, selected_sort) is not None]
        return sorted(filtered,
                      key=lambda a: (db.get_artifact_stat_total(a, selected_sort), a[3]),
                      reverse=descending)

    def handle_event(self, app, event):
        dropdown_handled = self.dropdown.handle_event(event)
        self.checkbox.handle_event(event)
        if self.dropdown.open or dropdown_handled:
            return
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y += event.y * 20
            max_rows = (len(self.artifacts) + self.items_per_row - 1) // self.items_per_row
            min_scroll = -((max_rows * (self.box_height + self.box_padding)) - app.height + 150)
            self.scroll_y = max(min_scroll, min(0, self.scroll_y))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for box, artifact_id in self._boxes(app):
                if box.collidepoint(event.pos):
                    app.push_scene(ArtifactDetailScene(
                        artifact_id, equip_slot=self.equip_slot, remove_slot=self.remove_slot))
                    return

    def _boxes(self, app):
        result = []
        start_x = (app.width - (self.box_width * self.items_per_row +
                                self.box_padding * (self.items_per_row - 1))) // 2
        start_y = 100 + self.scroll_y
        for i, artifact in enumerate(self._sorted_artifacts()):
            row, col = divmod(i, self.items_per_row)
            x = start_x + col * (self.box_width + self.box_padding)
            y = start_y + row * (self.box_height + self.box_padding)
            result.append((pygame.Rect(x, y, self.box_width, self.box_height), artifact[0]))
        return result

    def draw(self, app):
        screen = app.screen
        mouse_pos = pygame.mouse.get_pos()

        title = get_font(55).render("Artifacts", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, 30))
        points_text = get_font(40).render(f"Artifact Points: {self.artifact_points}",
                                          True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - 20, 20))

        small = get_font(30)
        boxes = self._boxes(app)
        self.hovered_box_index = -1
        artifacts = self._sorted_artifacts()

        for i, (box, _artifact_id) in enumerate(boxes):
            artifact = artifacts[i]
            is_hovered = box.collidepoint(mouse_pos)
            if is_hovered:
                self.hovered_box_index = i

            box_surface = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
            if is_hovered:
                pygame.draw.rect(box_surface, (70, 70, 70, 220), box_surface.get_rect(),
                                 border_radius=10)
                pygame.draw.rect(box_surface, (100, 150, 255, 150), box_surface.get_rect(),
                                 width=3, border_radius=10)
            else:
                pygame.draw.rect(box_surface, (50, 50, 50, 200), box_surface.get_rect(),
                                 border_radius=10)
                pygame.draw.rect(box_surface, (80, 80, 80, 100), box_surface.get_rect(),
                                 width=2, border_radius=10)
            screen.blit(box_surface, box.topleft)

            archetype = self.artifact_defs.get(artifact[11])
            icon_key = archetype["icon"] if archetype else "gem"
            icon_color = _parse_color(archetype["color"]) if archetype else (160, 160, 170)
            icon = get_icon(icon_key, icon_color, 64)
            screen.blit(icon, (box.right - icon.get_width() - 8, box.y + 8))

            rarity_color = (RARITY_COLORS.get(archetype["rarity"], Colors.gold)
                            if archetype else Colors.gold)
            name_display = truncate_text(artifact[1], small, box.width - 80)
            name_text = small.render(name_display, True, rarity_color)
            screen.blit(name_text, (box.x + 10, box.y + 10))
            level_text = small.render(f"Lv.{artifact[8]}/{artifact[10]}",
                                      True, Colors.artifact_text_color)
            screen.blit(level_text, (box.x + box.width // 2 - level_text.get_width() // 2,
                                     box.y + box.height - 30))
            main_stat_text = small.render(
                f"{artifact[2]}: +{db.format_stat_value(artifact[2], artifact[3])}",
                True, Colors.white)
            sub1_text = small.render(
                f"{artifact[4]}: +{db.format_stat_value(artifact[4], artifact[5])}"
                if artifact[4] else "", True, Colors.light_gray)
            sub2_text = small.render(
                f"{artifact[6]}: +{db.format_stat_value(artifact[6], artifact[7])}"
                if artifact[6] else "", True, Colors.light_gray)
            screen.blit(main_stat_text, (box.x + 10, box.y + 40))
            screen.blit(sub1_text, (box.x + 10, box.y + 70))
            screen.blit(sub2_text, (box.x + 10, box.y + 95))

        if (self.hovered_box_index != -1
                and self.hovered_box_index != self.last_hovered_box_index):
            audio.play(app, "hover")
        self.last_hovered_box_index = self.hovered_box_index

        self.back_button.draw(app)
        self.dropdown.draw(screen)
        self.checkbox.draw(screen)
        self.draw_flash(app)


class ArtifactDetailScene(Scene):
    """Single artifact: stats, EXP investment slider, equip/remove."""

    MIN_INVEST = 50
    MAX_INVEST = 500
    INVEST_STEP = 50

    def __init__(self, artifact_id, equip_slot=None, remove_slot=None):
        super().__init__()
        self.artifact_id = artifact_id
        self.equip_slot = equip_slot
        self.remove_slot = remove_slot
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.level_button = Button("Level Up", 0.8, 0.78, 0.2, 0.1, (0, 150, 0, 200))
        if equip_slot is not None:
            self.equip_button = Button(f"Equip to Slot {equip_slot}", 0.25, 0.96, 0.3, 0.1,
                                       Colors.hover_color)
            self.remove_button = Button(f"Remove Artifact {remove_slot}", 0.65, 0.96, 0.5, 0.1,
                                        Colors.hover_color)
        self.artifact = None
        self.artifact_points = 0
        self.current_invest = self.MIN_INVEST
        self.slider_dragging = False
        self.showing_upgrade = False
        self.upgrade_info = None
        self.upgrade_start = 0
        self.upgrade_duration = 2000

    def on_enter(self, app):
        # Refresh once here instead of querying the DB every frame.
        self.artifact = db.get_artifact(self.artifact_id)
        self.artifact_points = db.get_artifact_points()
        self.artifact_def = (db.get_artifact_def(self.artifact[10])
                             if self.artifact else None)

    def _slider_geometry(self, app):
        slider_width = int(app.width * 0.25)
        slider_height = int(app.height * 0.015)
        slider_x = (app.width - slider_width) // 2
        slider_y = int(app.height * 0.82)
        return slider_x, slider_y, slider_width, slider_height

    def _level_up(self, app):
        if not db.spend_artifact_points(self.current_invest):
            self.flash("Not enough artifact points!", Colors.red)
            return
        result = db.level_up_artifact(self.artifact_id, self.current_invest * 4)
        self.artifact = db.get_artifact(self.artifact_id)
        self.artifact_points = db.get_artifact_points()
        if result and result["levels_gained"] > 0:
            audio.play(app, "artifact_level_up")
            self.showing_upgrade = True
            self.upgrade_info = result
            self.upgrade_start = pygame.time.get_ticks()
        else:
            audio.play(app, "artifact_upgrade")

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            if self.equip_slot is not None:
                from .status import StatusScene
                app.pop_to_scene(StatusScene)
            else:
                app.pop_scene()
            return
        if self.equip_slot is not None and self.equip_button.is_clicked(app, event):
            db.set_equipped_artifact(self.equip_slot, self.artifact_id)
            from .status import StatusScene
            app.pop_to_scene(StatusScene)
            return
        if self.equip_slot is not None and self.remove_button.is_clicked(app, event):
            db.remove_equipped_artifact(self.remove_slot, self.artifact_id)
            from .status import StatusScene
            app.pop_to_scene(StatusScene)
            return
        if not self.artifact:
            return
        level, max_level = self.artifact[7], self.artifact[9]
        slider_x, slider_y, slider_width, slider_height = self._slider_geometry(app)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if level < max_level and self.level_button.is_clicked(app, event):
                self._level_up(app)
                return
            if (level < max_level and slider_x <= mx <= slider_x + slider_width
                    and slider_y - 10 <= my <= slider_y + slider_height + 10):
                self.slider_dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.slider_dragging = False
        elif event.type == pygame.MOUSEMOTION and self.slider_dragging:
            if level >= max_level:
                return
            mx = event.pos[0]
            if mx < slider_x:
                self.current_invest = self.MIN_INVEST
            elif mx > slider_x + slider_width:
                self.current_invest = self.MAX_INVEST
            else:
                ratio = (mx - slider_x) / slider_width
                invest = self.MIN_INVEST + int((self.MAX_INVEST - self.MIN_INVEST) * ratio)
                self.current_invest = int(round(invest / self.INVEST_STEP)) * self.INVEST_STEP
        elif event.type == pygame.KEYDOWN and level < max_level:
            if event.key == pygame.K_LEFT:
                self.current_invest = max(self.MIN_INVEST,
                                         self.current_invest - self.INVEST_STEP)
            elif event.key == pygame.K_RIGHT:
                self.current_invest = min(self.MAX_INVEST,
                                          self.current_invest + self.INVEST_STEP)
            elif event.key == pygame.K_RETURN:
                self._level_up(app)

    def draw(self, app):
        screen = app.screen
        if not self.artifact:
            self.back_button.draw(app)
            return
        (name, main_stat, main_stat_value, sub_stat1, sub_stat1_value,
         sub_stat2, sub_stat2_value, level, exp, max_level, _def_key) = self.artifact

        panel_width = int(app.width * 0.7)
        panel_height = int(app.height * 0.6)
        panel_x = (app.width - panel_width) // 2
        panel_y = 50
        draw_panel(screen, pygame.Rect(panel_x, panel_y, panel_width, panel_height))

        rarity_color = (RARITY_COLORS.get(self.artifact_def["rarity"], Colors.gold)
                        if self.artifact_def else Colors.gold)
        name_font = fit_text_to_box(name, panel_width - 40, 60)
        name_text = name_font.render(name, True, rarity_color)
        screen.blit(name_text, (panel_x + (panel_width - name_text.get_width()) // 2,
                               panel_y + 20))
        medium, small = get_font(40), get_font(30)
        if self.artifact_def:
            subtitle = small.render(
                f"{self.artifact_def['rarity'].capitalize()} "
                f"{self.artifact_def['name']}", True, Colors.light_gray)
        else:
            subtitle = small.render("Relic", True, Colors.light_gray)
        screen.blit(subtitle, (panel_x + (panel_width - subtitle.get_width()) // 2,
                               panel_y + 75))
        if self.artifact_def:
            icon = get_icon(self.artifact_def["icon"],
                            _parse_color(self.artifact_def["color"]), 130)
            screen.blit(icon, (panel_x + 30, panel_y + 110))
            lore_lines = wrap_text(self.artifact_def["lore"] or "", small, 190)
            for i, line in enumerate(lore_lines[:4]):
                screen.blit(small.render(line, True, Colors.light_gray),
                            (panel_x + 30, panel_y + 250 + i * 32))

        stat_x = panel_x + 200
        level_text = medium.render(f"Level: {level}/{max_level}", True, Colors.white)
        screen.blit(level_text, (stat_x, panel_y + 80))

        stat_y = panel_y + 130
        spacing = 50
        screen.blit(medium.render(f"Main Stat: {main_stat}", True, Colors.gold),
                    (stat_x, stat_y))
        screen.blit(medium.render(f"+{db.format_stat_value(main_stat, main_stat_value)}",
                                  True, Colors.gold), (panel_x + panel_width - 150, stat_y))
        if sub_stat1 and sub_stat1_value is not None:
            screen.blit(small.render(f"Sub Stat: {sub_stat1}", True, Colors.white),
                        (stat_x, stat_y + spacing))
            screen.blit(small.render(f"+{db.format_stat_value(sub_stat1, sub_stat1_value)}",
                                     True, Colors.white),
                        (panel_x + panel_width - 150, stat_y + spacing))
        if sub_stat2 and sub_stat2_value is not None:
            screen.blit(small.render(f"Sub Stat: {sub_stat2}", True, Colors.white),
                        (stat_x, stat_y + spacing * 2))
            screen.blit(small.render(f"+{db.format_stat_value(sub_stat2, sub_stat2_value)}",
                                     True, Colors.white),
                        (panel_x + panel_width - 150, stat_y + spacing * 2))

        exp_required = 100 + (level * 20)
        exp_ratio = min(exp / exp_required, 1.0)
        bar_width = panel_width - 60
        bar_x, bar_y = panel_x + 30, panel_y + panel_height - 80
        pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_width, 25), border_radius=5)
        pygame.draw.rect(screen, (100, 150, 255),
                         (bar_x, bar_y, int(bar_width * exp_ratio), 25), border_radius=5)

        points_text = medium.render(f"Artifact Points: {self.artifact_points}",
                                    True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - 20, 20))

        slider_x, slider_y, slider_width, slider_height = self._slider_geometry(app)
        if level < max_level:
            pygame.draw.rect(screen, (80, 80, 80),
                             (slider_x, slider_y, slider_width, slider_height), border_radius=5)
            position = slider_x + ((self.current_invest - self.MIN_INVEST) /
                                   (self.MAX_INVEST - self.MIN_INVEST)) * slider_width
            handle_radius = int(app.height * 0.02)
            pygame.draw.circle(screen, (150, 150, 255),
                               (int(position), slider_y + slider_height // 2), handle_radius)
            exp_text = small.render(f"EXP: {exp}/{exp_required}", True, Colors.white)
            screen.blit(exp_text, (bar_x + (bar_width - exp_text.get_width()) // 2,
                                   bar_y + int(app.height * 0.04)))
            invest_text = small.render(f"Investment: {self.current_invest} points",
                                       True, Colors.white)
            screen.blit(invest_text, (slider_x + (slider_width - invest_text.get_width()) // 2,
                                      slider_y - int(app.height * 0.04)))
            gain_text = small.render(f"XP Gain: {self.current_invest * 4}", True, Colors.white)
            screen.blit(gain_text, (slider_x + (slider_width - gain_text.get_width()) // 2,
                                    slider_y + int(app.height * 0.03)))
            self.level_button.draw(app)
        else:
            max_text = medium.render("Maximum Level Reached!", True, Colors.gold)
            screen.blit(max_text, (app.width // 2 - max_text.get_width() // 2, slider_y))

        self._draw_upgrade_flash(app)
        self.back_button.draw(app)
        if self.equip_slot is not None:
            self.equip_button.draw(app)
            self.remove_button.draw(app)
        self.draw_flash(app)

    def _draw_upgrade_flash(self, app):
        if not self.showing_upgrade or not self.upgrade_info:
            return
        screen = app.screen
        progress = min(1.0, (pygame.time.get_ticks() - self.upgrade_start)
                       / self.upgrade_duration)
        if progress >= 1.0:
            self.showing_upgrade = False
            return
        draw_panel(screen, pygame.Rect(app.width // 2 - 200, app.height // 2 - 150,
                                       400, 300), (0, 0, 0, 180), radius=10)
        medium, small = get_font(40), get_font(30)
        level_text = medium.render(f"Level Up! +{self.upgrade_info['levels_gained']}",
                                   True, Colors.gold)
        screen.blit(level_text, (app.width // 2 - level_text.get_width() // 2,
                                app.height // 2 - 120))
        y_offset = app.height // 2 - 60
        for stat_type, stat_name, old_value, new_value in self.upgrade_info["stats_improved"]:
            current_value = old_value + (new_value - old_value) * progress
            label = "Main Stat" if stat_type == "main" else "Sub Stat"
            stat_text = small.render(f"{label}: {stat_name}",
                                     True, Colors.gold if stat_type == "main" else Colors.white)
            value_text = small.render(f"{old_value:.1f} -> {current_value:.1f}",
                                     True, Colors.green)
            screen.blit(stat_text, (app.width // 2 - 180, y_offset))
            screen.blit(value_text, (app.width // 2 + 50, y_offset))
            y_offset += 40





