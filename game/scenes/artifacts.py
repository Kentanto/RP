"""Artifact collection: sortable list and the detail/level-up screen."""
import pygame

from .. import audio, db
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font, scaled
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
        self._sync_controls(app)

    def _sync_controls(self, app):
        """Keep the sort controls anchored to the window: they follow
        resizes instead of staying stuck at construction-time pixels."""
        self.dropdown.x = int(app.width * 0.05)
        self.dropdown.y = scaled(70)
        self.dropdown.width = scaled(180)
        self.dropdown.height = scaled(35)
        self.checkbox.x = self.dropdown.x + self.dropdown.width + scaled(12)
        self.checkbox.y = self.dropdown.y + scaled(8)
        self.checkbox.size = scaled(22)

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
            self.scroll_y += event.y * scaled(20)
            row_step = scaled(160) + scaled(20)
            max_rows = (len(self.artifacts) + self.items_per_row - 1) // self.items_per_row
            min_scroll = -((max_rows * row_step) - app.height + scaled(150))
            self.scroll_y = max(min_scroll, min(0, self.scroll_y))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for box, artifact_id in self._boxes(app):
                if box.collidepoint(event.pos):
                    app.push_scene(ArtifactDetailScene(
                        artifact_id, equip_slot=self.equip_slot, remove_slot=self.remove_slot))
                    return

    def _boxes(self, app):
        box_w, box_h = scaled(220), scaled(160)
        padding = scaled(20)
        result = []
        start_x = (app.width - (box_w * self.items_per_row
                                + padding * (self.items_per_row - 1))) // 2
        start_y = scaled(100) + self.scroll_y
        for i, artifact in enumerate(self._sorted_artifacts()):
            row, col = divmod(i, self.items_per_row)
            x = start_x + col * (box_w + padding)
            y = start_y + row * (box_h + padding)
            result.append((pygame.Rect(x, y, box_w, box_h), artifact[0]))
        return result

    def draw(self, app):
        screen = app.screen
        mouse_pos = pygame.mouse.get_pos()
        self._sync_controls(app)

        title = get_font(55).render("Artifacts", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, scaled(30)))
        points_text = get_font(40).render(f"Artifact Points: {self.artifact_points}",
                                          True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - scaled(20),
                                  scaled(20)))

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
            icon = get_icon(icon_key, icon_color, scaled(64))
            screen.blit(icon, (box.right - icon.get_width() - scaled(8),
                               box.y + scaled(8)))

            rarity_color = (RARITY_COLORS.get(archetype["rarity"], Colors.gold)
                            if archetype else Colors.gold)
            name_display = truncate_text(artifact[1], small, box.width - scaled(80))
            name_text = small.render(name_display, True, rarity_color)
            screen.blit(name_text, (box.x + scaled(10), box.y + scaled(10)))
            level_text = small.render(f"Lv.{artifact[8]}/{artifact[10]}",
                                      True, Colors.artifact_text_color)
            screen.blit(level_text, (box.x + box.width // 2 - level_text.get_width() // 2,
                                     box.y + box.height - scaled(30)))
            main_stat_text = small.render(
                f"{artifact[2]}: +{db.format_stat_value(artifact[2], artifact[3])}",
                True, Colors.white)
            sub1_text = small.render(
                f"{artifact[4]}: +{db.format_stat_value(artifact[4], artifact[5])}"
                if artifact[4] else "", True, Colors.light_gray)
            sub2_text = small.render(
                f"{artifact[6]}: +{db.format_stat_value(artifact[6], artifact[7])}"
                if artifact[6] else "", True, Colors.light_gray)
            # Stat lines stacked by measured height, below the name.
            stats_y = box.y + scaled(10) + name_text.get_height() + scaled(10)
            for stat_text in (main_stat_text, sub1_text, sub2_text):
                if stat_text.get_width():
                    screen.blit(stat_text, (box.x + scaled(10), stats_y))
                stats_y += stat_text.get_height() + scaled(6)

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
        self.last_slider_y = None
        self.upgrade_start = 0
        self.upgrade_duration = 2000

    def on_enter(self, app):
        # Refresh once here instead of querying the DB every frame.
        self.artifact = db.get_artifact(self.artifact_id)
        self.artifact_points = db.get_artifact_points()
        self.artifact_def = (db.get_artifact_def(self.artifact[10])
                             if self.artifact else None)

    def _slider_geometry(self, app):
        """Return slider rectangle. When last_slider_y is cached from draw(),
        use that so hit-testing stays aligned with the rendered slider."""
        slider_width = int(app.width * 0.25)
        slider_height = int(app.height * 0.015)
        slider_x = (app.width - slider_width) // 2
        if _is_original_window(app) and self.last_slider_y is not None:
            slider_y = self.last_slider_y
        else:
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
        if app.height < 500:
            # At very low resolutions, keep the panel within the safe vertical
            # strip between the top buttons and the bottom Level Up button.
            panel_y = 36
            panel_height = max(160, int(app.height * 0.62))
            # Clamp so the panel never overlaps bottom buttons (~y=app.height*0.78)
            panel_height = min(panel_height, int(app.height * 0.72) - panel_y)
        elif app.height < 900:
            panel_height = int(app.height * 0.65)
            panel_y = scaled(30)
        else:
            panel_height = int(app.height * 0.6)
            panel_y = scaled(50)
        panel_x = (app.width - panel_width) // 2
        draw_panel(screen, pygame.Rect(panel_x, panel_y, panel_width, panel_height))

        rarity_color = (RARITY_COLORS.get(self.artifact_def["rarity"], Colors.gold)
                        if self.artifact_def else Colors.gold)
        name_font = fit_text_to_box(name, panel_width - scaled(40), scaled(60))
        name_text = name_font.render(name, True, rarity_color)
        name_y = panel_y + scaled(20)
        screen.blit(name_text, (panel_x + (panel_width - name_text.get_width()) // 2,
                                name_y))
        medium, small = get_font(40), get_font(30)
        if self.artifact_def:
            subtitle = small.render(
                f"{self.artifact_def['rarity'].capitalize()} "
                f"{self.artifact_def['name']}", True, Colors.light_gray)
        else:
            subtitle = small.render("Relic", True, Colors.light_gray)
        subtitle_y = name_y + name_text.get_height() + scaled(6)
        screen.blit(subtitle, (panel_x + (panel_width - subtitle.get_width()) // 2,
                               subtitle_y))
        if self.artifact_def:
            is_compact = app.height < 500
            if is_compact:
                icon_size = scaled(55)
                max_lore = 0
                lore_width = 0
            elif app.height < 900:
                icon_size = scaled(110)
                max_lore = 3
                lore_width = scaled(170)
            else:
                icon_size = scaled(130)
                max_lore = 4
                lore_width = scaled(190)
            icon = get_icon(self.artifact_def["icon"],
                            _parse_color(self.artifact_def["color"]), icon_size)
            icon_y = subtitle_y + subtitle.get_height() + (scaled(6) if is_compact else scaled(10))
            screen.blit(icon, (panel_x + scaled(20), icon_y))
            if max_lore > 0:
                lore_lines = wrap_text(self.artifact_def["lore"] or "", small, lore_width)
                for i, line in enumerate(lore_lines[:max_lore]):
                    screen.blit(small.render(line, True, Colors.light_gray),
                                (panel_x + scaled(20),
                                 icon_y + icon_size
                                 + i * (small.get_height() + scaled(6))))
                icon_bottom = icon_y + icon_size + len(lore_lines[:max_lore]) * (small.get_height() + scaled(6)) + scaled(8)
            else:
                icon_bottom = icon_y + icon_size + scaled(4)
        else:
            icon_bottom = subtitle_y + subtitle.get_height() + scaled(10)

        # Compact mode places stats to the right of the icon to save
        # vertical space at very low resolutions.
        is_compact = app.height < 500
        if is_compact:
            stat_x = panel_x + icon_size + scaled(25)
            value_x = panel_x + panel_width - scaled(10)
            level_y = icon_y + scaled(2)
            spacing = scaled(22)
        else:
            stat_x = panel_x + scaled(200)
            value_x = panel_x + panel_width - scaled(30)
            level_y = max(panel_y + scaled(80), icon_bottom)
            spacing = scaled(50)
        level_text = medium.render(f"Level: {level}/{max_level}", True, Colors.white)
        screen.blit(level_text, (stat_x, level_y))

        stat_y = level_y + level_text.get_height() + scaled(14)
        screen.blit(medium.render(f"Main Stat: {main_stat}", True, Colors.gold),
                    (stat_x, stat_y))
        main_value = medium.render(
            f"+{db.format_stat_value(main_stat, main_stat_value)}", True, Colors.gold)
        screen.blit(main_value, (value_x - main_value.get_width(), stat_y))
        if sub_stat1 and sub_stat1_value is not None:
            screen.blit(small.render(f"Sub Stat: {sub_stat1}", True, Colors.white),
                        (stat_x, stat_y + spacing))
            sub1_value = small.render(
                f"+{db.format_stat_value(sub_stat1, sub_stat1_value)}",
                True, Colors.white)
            screen.blit(sub1_value, (value_x - sub1_value.get_width(),
                                    stat_y + spacing))
        if sub_stat2 and sub_stat2_value is not None:
            screen.blit(small.render(f"Sub Stat: {sub_stat2}", True, Colors.white),
                        (stat_x, stat_y + spacing * 2))
            sub2_value = small.render(
                f"+{db.format_stat_value(sub_stat2, sub_stat2_value)}",
                True, Colors.white)
            screen.blit(sub2_value, (value_x - sub2_value.get_width(),
                                     stat_y + spacing * 2))

        # Compute where stats ended so we can place the EXP bar & slider
        # dynamically rather than using fixed panel-relative positions.
        stat_bottom = stat_y + scaled(14)  # base line after main stat
        if sub_stat1 and sub_stat1_value is not None:
            stat_bottom = stat_y + spacing + small.get_height()
        if sub_stat2 and sub_stat2_value is not None:
            stat_bottom = stat_y + spacing * 2 + small.get_height()

        # Reserve about 12 % of panel height for the EXP bar + slider area at
        # the bottom of the panel.  Position the bar inside that reserve so
        # that even when stat_bottom comes down low there is still room.
        reserve = int(panel_height * 0.12)
        bottom_zone = panel_y + panel_height - reserve

        bar_width = panel_width - scaled(60)
        bar_height = scaled(16 if app.height < 500 else 25)
        bar_x = panel_x + scaled(30)
        bar_y = max(stat_bottom + scaled(10), bottom_zone + scaled(2))
        # Ensure the whole bar + slider + labels block fits inside the panel.
        slider_height = int(app.height * 0.015)
        exp_block = bar_height + scaled(10) + slider_height
        max_bar_y = panel_y + panel_height - exp_block
        bar_y = min(bar_y, max_bar_y)

        exp_required = 100 + (level * 20)
        exp_ratio = min(exp / exp_required, 1.0)
        pygame.draw.rect(screen, (80, 80, 80),
                         (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        pygame.draw.rect(screen, (100, 150, 255),
                         (bar_x, bar_y, int(bar_width * exp_ratio), bar_height),
                         border_radius=5)

        points_text = medium.render(f"Artifact Points: {self.artifact_points}",
                                    True, Colors.white)
        screen.blit(points_text, (app.width - points_text.get_width() - scaled(20),
                                  scaled(20)))

        slider_width = int(app.width * 0.25)
        slider_height = int(app.height * 0.015)
        slider_x = (app.width - slider_width) // 2
        slider_y = bar_y + bar_height + scaled(10)
        # Cache the computed slider Y for consistent hit-testing.
        self.last_slider_y = slider_y
        if level < max_level:
            pygame.draw.rect(screen, (80, 80, 80),
                             (slider_x, slider_y, slider_width, slider_height), border_radius=5)
            position = slider_x + ((self.current_invest - self.MIN_INVEST) /
                                   (self.MAX_INVEST - self.MIN_INVEST)) * slider_width
            handle_radius = int(app.height * 0.02)
            pygame.draw.circle(screen, (150, 150, 255),
                               (int(position), slider_y + slider_height // 2), handle_radius)

            if app.height < 500:
                # Compact: one combined label above slider; EXP text inside the bar
                bar_y_center = bar_y + bar_height // 2
                exp_text = small.render(f"EXP {exp}/{exp_required}", True, Colors.white)
                screen.blit(exp_text, (bar_x + (bar_width - exp_text.get_width()) // 2,
                                       bar_y_center - exp_text.get_height() // 2))
                invest_text = small.render(
                    f"Invest {self.current_invest} pts  (+{self.current_invest * 4} XP)",
                    True, Colors.white)
                screen.blit(invest_text,
                            (slider_x + (slider_width - invest_text.get_width()) // 2,
                             slider_y - scaled(28)))
            else:
                exp_text = small.render(f"EXP: {exp}/{exp_required}", True, Colors.white)
                screen.blit(exp_text, (bar_x + (bar_width - exp_text.get_width()) // 2,
                                       bar_y + bar_height + scaled(8)))
                invest_text = small.render(f"Investment: {self.current_invest} points",
                                           True, Colors.white)
                screen.blit(invest_text, (slider_x + (slider_width - invest_text.get_width()) // 2,
                                          slider_y - scaled(34)))
                gain_text = small.render(f"XP Gain: {self.current_invest * 4}", True, Colors.white)
                screen.blit(gain_text, (slider_x + (slider_width - gain_text.get_width()) // 2,
                                       slider_y + slider_height + scaled(12)))
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
        draw_panel(screen, pygame.Rect(app.width // 2 - scaled(200),
                                       app.height // 2 - scaled(150),
                                       scaled(400), scaled(300)),
                   (0, 0, 0, 180), radius=10)
        medium, small = get_font(40), get_font(30)
        level_text = medium.render(f"Level Up! +{self.upgrade_info['levels_gained']}",
                                   True, Colors.gold)
        screen.blit(level_text, (app.width // 2 - level_text.get_width() // 2,
                                app.height // 2 - scaled(120)))
        y_offset = app.height // 2 - scaled(60)
        for stat_type, stat_name, old_value, new_value in self.upgrade_info["stats_improved"]:
            current_value = old_value + (new_value - old_value) * progress
            label = "Main Stat" if stat_type == "main" else "Sub Stat"
            stat_text = small.render(f"{label}: {stat_name}",
                                     True, Colors.gold if stat_type == "main" else Colors.white)
            value_text = small.render(f"{old_value:.1f} -> {current_value:.1f}",
                                     True, Colors.green)
            screen.blit(stat_text, (app.width // 2 - scaled(180), y_offset))
            screen.blit(value_text, (app.width // 2 + scaled(50), y_offset))
            y_offset += small.get_height() + scaled(16)





