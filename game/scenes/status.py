"""Character page: level/XP, live stat totals, gear and artifact slots.

All numbers come from stats_model.sheet() — one module computes base
stats, equipped gear and equipped artifacts into final totals. This
scene only draws the result and routes the equip flows.
"""
import pygame

from .. import db, skills_data, stats_model
from ..core import Scene
from ..icons import get_icon
from ..settings import Colors, get_font, scaled
from ..ui import Button, draw_panel, truncate_text
from .inventory import RARITY_COLORS, _parse_color, item_stat_lines


class StatusScene(Scene):
    def __init__(self):
        super().__init__()
        # Button ratios are kept stable — tests click "Skills" at (0.5, 0.05).
        self.back_button = Button("Back", 0.08, 0.05, 0.2, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.artifacts_button = Button("Artifacts", 0.85, 0.05, 0.3, 0.1,
                                       Colors.hover_color)
        self.skills_button = Button("Skills", 0.5, 0.05, 0.2, 0.1, Colors.hover_color)
        self.sheet = None
        self.gear_items = {}            # slot -> item def row or None
        self.equipped = {}              # artifact slot -> artifact id
        self.equipped_names = [None] * 4
        self.artifact_icons = [None] * 4
        self.skill_levels = {}

    def on_enter(self, app):
        # Everything is read once here, not per frame.
        self.sheet = stats_model.sheet()
        self.equipped = db.get_equipped_artifacts()
        equipped_gear = db.get_equipped_gear()
        self.gear_items = {
            slot: (db.get_item_def(equipped_gear[slot])
                   if slot in equipped_gear else None)
            for slot in stats_model.GEAR_SLOTS}

        self.equipped_names = [None] * 4
        self.artifact_icons = [None] * 4
        by_id = {row["id"]: row for row in db.get_artifacts_by_ids(
            [aid for aid in self.equipped.values() if aid])}
        for slot in range(1, 5):
            row = by_id.get(self.equipped.get(slot))
            if row is None:
                continue
            self.equipped_names[slot - 1] = row["name"]
            def_row = db.get_artifact_def(row["def_key"])
            if def_row is not None:
                self.artifact_icons[slot - 1] = (def_row["icon"],
                                                  _parse_color(def_row["color"]))

        progress = db.load_skill_progress()
        self.skill_levels = {
            skill.name: progress.get(skill.name, {}).get("level", 0)
            for skill in skills_data.SKILLS}

    # ------------------------------------------------------------- input

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if self.artifacts_button.is_clicked(app, event):
            from .artifacts import ArtifactsScene
            app.push_scene(ArtifactsScene())
            return
        if self.skills_button.is_clicked(app, event):
            from .skill_tree import SkillTreeScene
            app.push_scene(SkillTreeScene())
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for slot, rect in zip(stats_model.GEAR_SLOTS, self._gear_rects(app)):
                if rect.collidepoint(event.pos):
                    app.push_scene(GearPickerScene(slot))
                    return
            for index, rect in enumerate(self._artifact_rects(app)):
                if rect.collidepoint(event.pos):
                    artifact_id = self.equipped.get(index + 1)
                    if artifact_id:
                        from .artifacts import ArtifactDetailScene
                        app.push_scene(ArtifactDetailScene(
                            artifact_id, equip_slot=index + 1, remove_slot=index + 1))
                    else:
                        from .artifacts import ArtifactsScene
                        app.push_scene(ArtifactsScene(equip_slot=index + 1,
                                                      remove_slot=index + 1))
                    return

    # ---------------------------------------------------------- geometry

    def _gear_rects(self, app):
        panel_x = int(app.width * 0.62)
        panel_w = int(app.width * 0.33)
        row_h = scaled(62)
        gap = scaled(10)
        y = int(app.height * 0.24)
        return [pygame.Rect(panel_x, y + i * (row_h + gap), panel_w, row_h)
                for i in range(4)]

    def _gear_bottom(self, app):
        rects = self._gear_rects(app)
        return rects[-1].bottom if rects else int(app.height * 0.72)

    def _artifact_top(self, app):
        """Artifacts sit below whichever column is taller, so the
        stats grid, gear list and artifact section never overlap."""
        stats_bottom = (getattr(self, "_stats_bottom", None)
                        or int(app.height * 0.72))
        return max(stats_bottom, self._gear_bottom(app)) + scaled(12)

    def _artifact_rects(self, app):
        slot_w, slot_h = int(app.width * 0.11), int(app.height * 0.14)
        spacing = int(slot_w * 0.3)
        total = 4 * slot_w + 3 * spacing
        x = (app.width - total) // 2
        small = get_font(30)
        y = (self._artifact_top(app) + small.get_height() + scaled(10))
        return [pygame.Rect(x + i * (slot_w + spacing), y, slot_w, slot_h)
                for i in range(4)]

    # -------------------------------------------------------------- draw

    def _draw_xp_bar(self, app):
        screen = app.screen
        medium, small = get_font(40), get_font(26)
        level = self.sheet["level"]
        xp, needed = self.sheet["xp"], self.sheet["needed"]
        level_text = medium.render(f"Level {level}", True, Colors.gold)
        screen.blit(level_text, (app.width // 2 - level_text.get_width() // 2,
                                 int(app.height * 0.13)))
        bar_w, bar_h = int(app.width * 0.5), scaled(18)
        bar_x = (app.width - bar_w) // 2
        bar_y = int(app.height * 0.185)
        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_w, bar_h),
                         border_radius=9)
        ratio = min(1.0, xp / needed) if needed else 1.0
        if ratio > 0:
            pygame.draw.rect(screen, Colors.accent,
                             (bar_x, bar_y, max(8, int(bar_w * ratio)), bar_h),
                             border_radius=9)
        xp_text = small.render(f"{xp} / {needed} XP", True, Colors.light_gray)
        screen.blit(xp_text, (app.width // 2 - xp_text.get_width() // 2,
                              bar_y + bar_h + 4))
        # Anchor for the resource bars: right below the XP readout.
        self._resource_bar_top = bar_y + bar_h + 4 + xp_text.get_height() + scaled(10)

    def _draw_resource_bars(self, app):
        """Live HP/mana pools: regenerating, spent and restored by items."""
        screen = app.screen
        small = get_font(22)
        hp = self.sheet["hp_current"]
        hp_max = self.sheet["stats"]["HP"]["total"]
        mp = self.sheet["mana_current"]
        mp_max = self.sheet["stats"]["Mana"]["total"]
        bar_w = int(app.width * 0.22)
        bar_h = max(scaled(14), small.get_height() + scaled(2))
        gap = int(app.width * 0.06)
        y = getattr(self, "_resource_bar_top", int(app.height * 0.26))
        hp_x = app.width // 2 - bar_w - gap // 2
        mp_x = app.width // 2 + gap // 2
        for x, value, maximum, color, label in (
                (hp_x, hp, hp_max, (170, 60, 60), f"HP {hp}/{hp_max}"),
                (mp_x, mp, mp_max, (70, 110, 220), f"MP {mp}/{mp_max}")):
            pygame.draw.rect(screen, (60, 60, 70), (x, y, bar_w, bar_h),
                             border_radius=8)
            ratio = min(1.0, value / maximum) if maximum else 0.0
            if ratio > 0:
                pygame.draw.rect(screen, color,
                                 (x, y, max(8, int(bar_w * ratio)), bar_h),
                                 border_radius=8)
            text = small.render(label, True, Colors.white)
            screen.blit(text, (x + (bar_w - text.get_width()) // 2,
                               y + (bar_h - text.get_height()) // 2))
        # Anchor for the stats grid: below the resource bars.
        self._stats_top = y + bar_h + scaled(12)

    def _draw_stats(self, app):
        screen = app.screen
        value_font, small = get_font(36), get_font(22)
        col1 = ("HP", "ATK", "DEF", "SPD")
        col2 = ("Mana", "Crit Rate", "Crit DMG")
        x1, x2 = int(app.width * 0.07), int(app.width * 0.33)
        y = getattr(self, "_stats_top", int(app.height * 0.30))
        # Rows tall enough for value + breakdown at the current scale.
        row_h = max(scaled(59), value_font.get_height() + small.get_height()
                    + scaled(12))

        for column, x in ((col1, x1), (col2, x2)):
            for i, key in enumerate(column):
                entry = self.sheet["stats"][key]
                base_y = y + i * row_h
                label = value_font.render(key, True, Colors.light_gray)
                value = value_font.render(
                    stats_model.format_stat(key, entry["total"]), True,
                    Colors.stat_text_color)
                screen.blit(label, (x, base_y))
                screen.blit(value, (x + int(app.width * 0.13), base_y))
                breakdown = small.render(stats_model.breakdown_text(entry),
                                         True, (150, 150, 160))
                screen.blit(breakdown, (x, base_y + value_font.get_height() + 2))
        self._stats_bottom = y + len(col1) * row_h

    def _draw_gear(self, app):
        screen = app.screen
        small = get_font(26)
        panel_x = int(app.width * 0.62)
        title = get_font(30).render("Gear", True, Colors.light_gray)
        screen.blit(title, (panel_x, int(app.height * 0.195)))
        gear_rows = [self.gear_items.get(s) for s in stats_model.GEAR_SLOTS]
        for slot, rect, item in zip(stats_model.GEAR_SLOTS, self._gear_rects(app),
                                    gear_rows):
            draw_panel(screen, rect, (40, 40, 40, 220), radius=10)
            if item is None:
                icon = get_icon(slot, (120, 120, 130), scaled(46),
                                fallback_shape="gem")
                label = small.render(f"{stats_model.GEAR_LABELS[slot]}: Empty",
                                     True, Colors.gray)
                screen.blit(icon, (rect.x + scaled(8), rect.y + scaled(8)))
                screen.blit(label, (rect.x + scaled(62),
                                   rect.y + (rect.height - label.get_height()) // 2))
            else:
                color = RARITY_COLORS.get(item["rarity"], Colors.white)
                icon = get_icon(item["icon"], _parse_color(item["color"]), scaled(46))
                label = small.render(
                    truncate_text(item["name"], small, rect.width - scaled(70)),
                    True, color)
                stats_line = "  ".join(item_stat_lines(item))
                stats_surf = get_font(20).render(
                    truncate_text(stats_line, get_font(20), rect.width - scaled(70)),
                    True, Colors.stat_text_color)
                screen.blit(icon, (rect.x + scaled(8), rect.y + scaled(8)))
                screen.blit(label, (rect.x + scaled(62), rect.y + scaled(6)))
                screen.blit(stats_surf, (rect.x + scaled(62),
                                        rect.y + scaled(6)
                                        + label.get_height() + scaled(6)))

    def _draw_artifact_slots(self, app):
        screen = app.screen
        small = get_font(26)
        title = get_font(30).render("Artifacts", True, Colors.light_gray)
        screen.blit(title, (int(app.width * 0.06), self._artifact_top(app)))
        for index, rect in enumerate(self._artifact_rects(app)):
            draw_panel(screen, rect, (40, 40, 40, 220), radius=10)
            if self.equipped_names[index] is None:
                icon = get_icon("gem", (110, 110, 120), int(rect.width * 0.55))
                screen.blit(icon, (rect.x + (rect.width - icon.get_width()) // 2,
                                   rect.y + scaled(6)))
                label = small.render("Empty", True, Colors.gray)
            else:
                icon_key, icon_color = self.artifact_icons[index] or ("gem", (160, 160, 170))
                icon = get_icon(icon_key, icon_color, int(rect.width * 0.55))
                screen.blit(icon, (rect.x + (rect.width - icon.get_width()) // 2,
                                   rect.y + scaled(6)))
                label = small.render(
                    truncate_text(self.equipped_names[index].split(" ")[0], small,
                                  rect.width - scaled(8)), True, Colors.gold)
            screen.blit(label, (rect.x + (rect.width - label.get_width()) // 2,
                                rect.bottom - label.get_height() - scaled(4)))

    def draw(self, app):
        self._draw_xp_bar(app)
        self._draw_resource_bars(app)
        self._draw_stats(app)
        self._draw_gear(app)
        self._draw_artifact_slots(app)

        small = get_font(24)
        abilities = "   ".join(f"{name} Lv.{level}"
                               for name, level in self.skill_levels.items())
        text = small.render(abilities, True, Colors.light_gray)
        # Place below artifacts so abilities never overlap anything,
        # and keep at least a small gap from the bottom edge.
        abilities_y = max(
            int(app.height * 0.93),
            self._artifact_top(app)
            + get_font(30).get_height() + scaled(10)
            + int(app.height * 0.14) + scaled(8)
        )
        app.screen.blit(text, (app.width // 2 - text.get_width() // 2,
                               abilities_y))

        self.back_button.draw(app)
        self.skills_button.draw(app)
        self.artifacts_button.draw(app)
        self.draw_flash(app)


class GearPickerScene(Scene):
    """Overlay: pick an owned item for one gear slot."""

    ROW_HEIGHT = 66          # design pixels, scaled at use

    def __init__(self, slot):
        super().__init__()
        self.slot = slot
        self.items = []
        self.row_rects = []
        self.scroll_y = 0

    def on_enter(self, app):
        self.items = [item for item in db.get_inventory_items()
                      if item["slot"] == self.slot]

    def _panel_rect(self, app):
        width, height = int(app.width * 0.55), int(app.height * 0.66)
        return pygame.Rect((app.width - width) // 2, (app.height - height) // 2,
                           width, height)

    def _unequip_rect(self, app):
        panel = self._panel_rect(app)
        return pygame.Rect(panel.centerx - scaled(90), panel.bottom - scaled(56),
                           scaled(180), scaled(36))

    def handle_event(self, app, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, item in self.row_rects:
                if rect.collidepoint(event.pos):
                    db.equip_gear(self.slot, item["key"])
                    app.pop_scene()
                    return
            if self._unequip_rect(app).collidepoint(event.pos):
                db.unequip_gear(self.slot)
                app.pop_scene()
                return
            if not self._panel_rect(app).collidepoint(event.pos):
                app.pop_scene()
                return
        elif event.type == pygame.MOUSEWHEEL:
            row_step = scaled(self.ROW_HEIGHT + 8)
            max_scroll = -max(0, len(self.items) * row_step
                              - int(app.height * 0.4))
            self.scroll_y = max(max_scroll, min(0, self.scroll_y + event.y * scaled(24)))

    def draw(self, app):
        screen = app.screen
        panel = self._panel_rect(app)
        veil = pygame.Surface((app.width, app.height), pygame.SRCALPHA)
        veil.fill((8, 8, 16, 170))
        screen.blit(veil, (0, 0))
        draw_panel(screen, panel, (30, 30, 38, 245), radius=14,
                   border=(*Colors.accent, 200))

        medium, small = get_font(40), get_font(26)
        title = medium.render(f"Equip {stats_model.GEAR_LABELS[self.slot]}",
                             True, Colors.gold)
        screen.blit(title, (panel.x + scaled(24), panel.y + scaled(16)))
        hint = small.render("Click an item to equip it, or press ESC",
                            True, Colors.light_gray)
        screen.blit(hint, (panel.x + scaled(24),
                           panel.y + scaled(16) + title.get_height() + scaled(6)))

        clip = pygame.Rect(panel.x, panel.y + scaled(100), panel.width,
                           panel.height - scaled(180))
        row_height = scaled(self.ROW_HEIGHT)
        self.row_rects = []
        y = clip.y + self.scroll_y
        for item in self.items:
            rect = pygame.Rect(panel.x + scaled(16), y,
                               panel.width - scaled(32), row_height)
            if rect.colliderect(clip):
                draw_panel(screen, rect, (52, 52, 64, 235), radius=10)
                icon = get_icon(item["icon"], _parse_color(item["color"]),
                                scaled(52))
                screen.blit(icon, (rect.x + scaled(8), rect.y + scaled(7)))
                color = RARITY_COLORS.get(item["rarity"], Colors.white)
                name = small.render(
                    truncate_text(item["name"], small, rect.width - scaled(90)),
                    True, color)
                screen.blit(name, (rect.x + scaled(70), rect.y + scaled(6)))
                stats_line = "  ".join(item_stat_lines(item))
                stats_surf = get_font(22).render(
                    truncate_text(stats_line, get_font(22),
                                  rect.width - scaled(90)),
                    True, Colors.stat_text_color)
                screen.blit(stats_surf, (rect.x + scaled(70),
                                        rect.y + scaled(6)
                                        + name.get_height() + scaled(8)))
            if rect.bottom > clip.y and rect.y < clip.bottom:
                self.row_rects.append((rect, item))
            y += row_height + scaled(8)

        if not self.items:
            empty = small.render("You own nothing for this slot yet.",
                                 True, Colors.gray)
            screen.blit(empty, (panel.centerx - empty.get_width() // 2,
                                panel.y + scaled(160)))

        unequip_rect = self._unequip_rect(app)
        pygame.draw.rect(screen, (150, 60, 60), unequip_rect, border_radius=8)
        unequip_text = small.render("Unequip", True, Colors.white)
        screen.blit(unequip_text,
                    (unequip_rect.centerx - unequip_text.get_width() // 2,
                     unequip_rect.centery - unequip_text.get_height() // 2))
        self.draw_flash(app)


