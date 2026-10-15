"""Skill tree — full revamp.

What changed vs. the old skill_tree_menu():
  * Real skill points from the database (the old menu used a hardcoded
    100000 and never persisted spending).
  * Node positions are computed from the upgrade graph, not hardcoded.
  * Hit-testing happens in world space (the old code broke at zoom != 1).
  * Icons are cached (the old code loaded them from disk every frame).
  * Click a node to select it, then act via the side panel button or
    double-click. The old double-click-only leveling and accidental
    single-click purchases are gone.
  * Pan with drag, zoom with the wheel (anchored at the cursor), ESC to
    go back — and navigation uses the scene stack, not recursion.
"""
import math
import os

import pygame

from .. import audio, db, skills_data
from ..core import Scene
from ..settings import Colors, get_font, ICONS_DIR
from ..ui import Button, create_circular_icon, draw_panel, wrap_text

NODE_RADIUS = 42.0        # world-space radius of upgrade nodes
SKILL_RADIUS = 48.0       # world-space radius of skill roots
MIN_ZOOM = 0.35
MAX_ZOOM = 2.5
LEVEL_COST = 1            # skill points per skill level


class Camera:
    """World <-> screen transforms. The world point (x, y) sits at the
    center of the screen; zoom is applied around that center."""

    def __init__(self):
        self.x = 0.0
        self.y = 120.0
        self.zoom = 1.0

    def world_to_screen(self, wx, wy, size):
        return ((wx - self.x) * self.zoom + size[0] / 2,
                (wy - self.y) * self.zoom + size[1] / 2)

    def screen_to_world(self, sx, sy, size):
        return ((sx - size[0] / 2) / self.zoom + self.x,
                (sy - size[1] / 2) / self.zoom + self.y)

    def zoom_at(self, screen_pos, factor, size):
        before = self.screen_to_world(screen_pos[0], screen_pos[1], size)
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        after = self.screen_to_world(screen_pos[0], screen_pos[1], size)
        self.x += before[0] - after[0]
        self.y += before[1] - after[1]


# ------------------------------------------------------- vector node glyphs

def _draw_glyph(screen, kind, center, radius, color):
    """Tiny vector icons drawn with primitives — no emoji (the default
    pygame font can't render emoji, so the old tree often showed blanks)."""
    x, y = center
    r = radius
    if kind == "mastery":
        pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
        pygame.draw.polygon(screen, color, pts, width=3)
    elif kind == "flame":
        pygame.draw.polygon(screen, color,
                            [(x, y - r), (x + r * 0.8, y + r * 0.6), (x - r * 0.8, y + r * 0.6)],
                            width=3)
        pygame.draw.circle(screen, color, (x, y + r * 0.35), int(r * 0.35), 2)
    elif kind == "burst":
        for angle in (90, 270):
            rad = math.radians(angle)
            pygame.draw.line(screen, color,
                             (x - math.cos(rad) * r, y - math.sin(rad) * r),
                             (x + math.cos(rad) * r, y + math.sin(rad) * r), 3)
        pygame.draw.circle(screen, color, center, int(r * 0.55), 3)
    elif kind == "star":
        pygame.draw.circle(screen, color, center, int(r * 0.5), 3)
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            pygame.draw.line(screen, color, center,
                             (x + math.cos(rad) * r, y + math.sin(rad) * r), 2)
    elif kind == "cluster":
        for dx, dy in ((-0.45, 0.3), (0.45, 0.3), (0, -0.45)):
            pygame.draw.circle(screen, color, (x + dx * r, y + dy * r), int(r * 0.32), 2)
    elif kind == "meteor":
        pygame.draw.circle(screen, color, (x + r * 0.3, y - r * 0.3), int(r * 0.45), 3)
        pygame.draw.line(screen, color, (x + r * 0.55, y - r * 0.55),
                         (x - r * 0.8, y + r * 0.8), 3)
    elif kind == "snow":
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            pygame.draw.line(screen, color, center,
                             (x + math.cos(rad) * r, y + math.sin(rad) * r), 2)
    elif kind == "arrow":
        pygame.draw.line(screen, color, (x - r * 0.7, y + r * 0.6),
                         (x + r * 0.7, y - r * 0.5), 3)
        pygame.draw.polygon(screen, color, [
            (x + r * 0.9, y - r * 0.7), (x + r * 0.1, y - r * 0.6),
            (x + r * 0.6, y + r * 0.1)])
    elif kind == "shield":
        pygame.draw.polygon(screen, color, [
            (x - r * 0.7, y - r * 0.6), (x + r * 0.7, y - r * 0.6),
            (x + r * 0.7, y + r * 0.2), (x, y + r * 0.8),
            (x - r * 0.7, y + r * 0.2)], width=3)
    elif kind == "chain":
        pygame.draw.circle(screen, color, (x - r * 0.35, y), int(r * 0.45), 3)
        pygame.draw.circle(screen, color, (x + r * 0.35, y), int(r * 0.45), 3)
    elif kind == "wave":
        pygame.draw.arc(screen, color, (x - r, y - r * 0.6, 2 * r, r * 1.2),
                        math.pi, 2 * math.pi, 3)
        pygame.draw.arc(screen, color, (x - r, y, 2 * r, r * 1.2),
                        0, math.pi, 3)


class SkillTreeScene(Scene):
    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.camera = Camera()
        self.layout = skills_data.compute_layout()
        self.edges = skills_data.edges()
        self.progress = {}          # skill name -> {"level": int, "upgrades": set}
        self.points = 0
        self.selected = None        # node name
        self.hovered = None          # node name
        self.dragging = False
        self.drag_start = None
        self.drag_camera_start = None
        self.last_click_name = None
        self.last_click_ticks = 0

    # ------------------------------------------------------------- model

    def on_enter(self, app):
        stored = db.load_skill_progress()
        self.progress = {}
        for skill in skills_data.SKILLS:
            entry = stored.get(skill.name, {})
            self.progress[skill.name] = {
                "level": entry.get("level", 0),
                "upgrades": set(entry.get("upgrades", [])),
            }
        self.points = db.get_current_points()
        # Frame the first skill on entry; pan/zoom reaches everything else.
        first = skills_data.SKILLS[0]
        self.camera.x, self.camera.y = self.layout[first.name]
        self.camera.zoom = 0.85

    def _is_owned(self, upgrade_name):
        skill, _upgrade = skills_data.upgrade_owner(upgrade_name)
        if skill is None:
            return False
        return upgrade_name in self.progress[skill.name]["upgrades"]

    def _requirements_met(self, upgrade):
        return all(self._is_owned(req) for req in upgrade.requires)

    def _can_buy(self, upgrade):
        skill, _ = skills_data.upgrade_owner(upgrade.name)
        if skill is None or self._is_owned(upgrade.name):
            return False
        state = self.progress[skill.name]
        return (self._requirements_met(upgrade)
                and state["level"] >= upgrade.level_req
                and self.points >= upgrade.cost)

    def _can_level(self, skill):
        state = self.progress[skill.name]
        return state["level"] < skill.max_level and self.points >= LEVEL_COST

    def _node_at(self, world_pos):
        """Return the node name under a world position (or None)."""
        wx, wy = world_pos
        for name, (nx, ny) in self.layout.items():
            radius = SKILL_RADIUS if skills_data.skill_by_name(name) else NODE_RADIUS
            if (wx - nx) ** 2 + (wy - ny) ** 2 <= radius ** 2:
                return name
        return None

    # ------------------------------------------------------------ actions

    def _save(self, skill_name):
        state = self.progress[skill_name]
        db.save_skill_progress(skill_name, state["level"], state["upgrades"])

    def _level_up(self, app, skill_name):
        skill = skills_data.skill_by_name(skill_name)
        if skill is None or not self._can_level(skill):
            if self.points < LEVEL_COST:
                self.flash("Not enough skill points!", Colors.red)
            return
        if db.subtract_points(LEVEL_COST):
            self.progress[skill_name]["level"] += 1
            self.points = db.get_current_points()
            self._save(skill_name)
            audio.play(app, "click")

    def _unlock(self, app, upgrade_name):
        skill, upgrade = skills_data.upgrade_owner(upgrade_name)
        if skill is None or upgrade is None:
            return
        if not self._can_buy(upgrade):
            if self.points < upgrade.cost:
                self.flash("Not enough skill points!", Colors.red)
            return
        if db.subtract_points(upgrade.cost):
            self.progress[skill.name]["upgrades"].add(upgrade_name)
            self.points = db.get_current_points()
            self._save(skill.name)
            audio.play(app, "artifact_level_up")

    def _quick_action(self, app, node_name):
        if skills_data.skill_by_name(node_name):
            self._level_up(app, node_name)
        else:
            self._unlock(app, node_name)

    # ------------------------------------------------------------- events

    PANEL_WIDTH = 360

    def _panel_rect(self, app):
        return pygame.Rect(app.width - self.PANEL_WIDTH - 16, 70,
                           self.PANEL_WIDTH, app.height - 110)

    def _action_button_rect(self, app):
        panel = self._panel_rect(app)
        return pygame.Rect(panel.x + 24, panel.bottom - 66, panel.width - 48, 44)

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Panel action button first (fixed screen space).
            if self.selected and self._action_button_rect(app).collidepoint(event.pos):
                if self._action_enabled():
                    self._quick_action(app, self.selected)
                else:
                    self.flash(self._action_reason(), Colors.red)
                return
            world = self.camera.screen_to_world(event.pos[0], event.pos[1],
                                                (app.width, app.height))
            node = self._node_at(world)
            if node is not None:
                now = pygame.time.get_ticks()
                if node == self.last_click_name and now - self.last_click_ticks < 400:
                    self._quick_action(app, node)
                    self.last_click_name = None
                else:
                    self.last_click_name = node
                    self.last_click_ticks = now
                self.selected = node
                return
            # Click on empty space starts a pan drag.
            self.dragging = True
            self.drag_start = event.pos
            self.drag_camera_start = (self.camera.x, self.camera.y)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                dx = event.pos[0] - self.drag_start[0]
                dy = event.pos[1] - self.drag_start[1]
                self.camera.x = self.drag_camera_start[0] - dx / self.camera.zoom
                self.camera.y = self.drag_camera_start[1] - dy / self.camera.zoom
            else:
                world = self.camera.screen_to_world(event.pos[0], event.pos[1],
                                                    (app.width, app.height))
                self.hovered = self._node_at(world)
        elif event.type == pygame.MOUSEWHEEL:
            factor = 1.1 ** event.y
            self.camera.zoom_at(event.pos, factor, (app.width, app.height))

    # ------------------------------------------------------- panel helpers

    def _action(self):
        """(label, enabled, reason) for the panel button of the selection."""
        if self.selected is None:
            return None
        skill = skills_data.skill_by_name(self.selected)
        if skill is not None:
            state = self.progress[skill.name]
            if state["level"] >= skill.max_level:
                return ("Max level", False, "This skill is fully leveled.")
            if self.points < LEVEL_COST:
                return (f"Level Up ({LEVEL_COST} SP)", False, "Not enough skill points.")
            return (f"Level Up ({LEVEL_COST} SP)", True, "")
        _skill, upgrade = skills_data.upgrade_owner(self.selected)
        if upgrade is None:
            return None
        if self._is_owned(upgrade.name):
            return ("Unlocked", False, "Already unlocked.")
        if not self._requirements_met(upgrade):
            missing = [req for req in upgrade.requires if not self._is_owned(req)]
            return (f"Unlock ({upgrade.cost} SP)", False,
                    "Requires: " + ", ".join(missing))
        state = self.progress[skills_data.upgrade_owner(upgrade.name)[0].name]
        if state["level"] < upgrade.level_req:
            return (f"Unlock ({upgrade.cost} SP)", False,
                    f"Requires skill level {upgrade.level_req}.")
        if self.points < upgrade.cost:
            return (f"Unlock ({upgrade.cost} SP)", False, "Not enough skill points.")
        return (f"Unlock ({upgrade.cost} SP)", True, "")

    def _action_enabled(self):
        info = self._action()
        return bool(info and info[1])

    def _action_reason(self):
        info = self._action()
        return info[2] if info else ""

    # ---------------------------------------------------------------- draw

    def draw(self, app):
        screen = app.screen
        size = (app.width, app.height)
        time = pygame.time.get_ticks()

        # Dark veil so the tree reads clearly over the menu background.
        veil = pygame.Surface(size, pygame.SRCALPHA)
        veil.fill(Colors.veil)
        screen.blit(veil, (0, 0))

        self._draw_edges(app, size)
        self._draw_nodes(app, size, time)
        self._draw_header(app)
        self._draw_side_panel(app)
        self.draw_flash(app)

    def _draw_edges(self, app, size):
        screen = app.screen
        for source, target in self.edges:
            a = self.camera.world_to_screen(*self.layout[source], size)
            b = self.camera.world_to_screen(*self.layout[target], size)
            source_owned = self._is_owned(source) or skills_data.skill_by_name(source)
            target_owned = self._is_owned(target)
            target_upgrade = skills_data.upgrade_owner(target)[1]
            if source_owned and target_owned:
                color = Colors.light_green
            elif source_owned and target_upgrade and self._can_buy(target_upgrade):
                color = Colors.gold
            else:
                color = (70, 70, 80)
            radius = NODE_RADIUS * self.camera.zoom
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            start = (a[0] + ux * radius, a[1] + uy * radius)
            end = (b[0] - ux * radius, b[1] - uy * radius)
            pygame.draw.line(screen, color, start, end,
                             max(2, int(3 * self.camera.zoom)))

    def _draw_nodes(self, app, size, time):
        screen = app.screen
        small = get_font(30)
        pulse = 0.5 + 0.5 * math.sin(time / 300.0)
        for name, world_pos in self.layout.items():
            pos = self.camera.world_to_screen(*world_pos, size)
            skill = skills_data.skill_by_name(name)
            if skill is not None:
                self._draw_skill_node(screen, skill, pos, pulse, small)
            else:
                _owner, upgrade = skills_data.upgrade_owner(name)
                if upgrade is not None:
                    self._draw_upgrade_node(screen, upgrade, pos, name, pulse, small)

    def _draw_skill_node(self, screen, skill, pos, pulse, small):
        radius = SKILL_RADIUS * self.camera.zoom
        state = self.progress[skill.name]
        icon_path = os.path.join(ICONS_DIR, skill.icon)

        if os.path.exists(icon_path):
            size = max(24, int((2 * SKILL_RADIUS * self.camera.zoom) / 8) * 8)
            icon = create_circular_icon(icon_path, size)
            icon_rect = icon.get_rect(center=(int(pos[0]), int(pos[1])))
            screen.blit(icon, icon_rect)
        else:
            pygame.draw.circle(screen, (60, 60, 70), pos, int(radius))

        # Level progress ring around the icon.
        ring_rect = pygame.Rect(pos[0] - radius - 4, pos[1] - radius - 4,
                                2 * (radius + 4), 2 * (radius + 4))
        pygame.draw.arc(screen, (70, 70, 80), ring_rect, 0, 2 * math.pi, 4)
        fraction = state["level"] / skill.max_level
        if fraction > 0:
            pygame.draw.arc(screen, Colors.gold, ring_rect,
                            math.pi / 2, math.pi / 2 + 2 * math.pi * fraction, 4)

        if self._can_level(skill):
            pygame.draw.circle(screen, Colors.gold, pos, int(radius + 7),
                               width=max(2, int(2 + pulse * 2)))
        if skill.name == self.hovered or skill.name == self.selected:
            color = Colors.light_blue if skill.name == self.selected else Colors.white
            pygame.draw.circle(screen, color, pos, int(radius + 11), 3)

        name_text = small.render(skill.name, True, Colors.white)
        screen.blit(name_text, (pos[0] - name_text.get_width() // 2,
                                pos[1] + radius + 8))
        level_text = small.render(f"Lv.{state['level']}", True, Colors.light_gray)
        screen.blit(level_text, (pos[0] - level_text.get_width() // 2,
                                pos[1] + radius + 32))

    def _draw_upgrade_node(self, screen, upgrade, pos, name, pulse, small):
        radius = NODE_RADIUS * self.camera.zoom
        owned = self._is_owned(name)
        can_buy = self._can_buy(upgrade)

        if owned:
            fill, ring, glyph_color = (20, 90, 40), Colors.green, Colors.light_green
        elif can_buy:
            fill, ring, glyph_color = (60, 50, 20), Colors.gold, Colors.gold
        else:
            fill, ring, glyph_color = (50, 25, 25), (120, 60, 60), (150, 90, 90)

        pygame.draw.circle(screen, fill, pos, int(radius))
        pygame.draw.circle(screen, ring, pos, int(radius), 3)

        if can_buy and not owned:
            pygame.draw.circle(screen, ring, pos, int(radius + 5),
                               width=max(1, int(1 + pulse * 2)))
        if name == self.hovered or name == self.selected:
            color = Colors.light_blue if name == self.selected else Colors.white
            pygame.draw.circle(screen, color, pos, int(radius + 9), 3)

        _draw_glyph(screen, upgrade.glyph, pos, radius * 0.45, glyph_color)

        name_text = small.render(upgrade.name, True,
                                 Colors.white if owned or can_buy else Colors.gray)
        screen.blit(name_text, (pos[0] - name_text.get_width() // 2,
                                pos[1] + radius + 8))

    def _draw_header(self, app):
        screen = app.screen
        large, small = get_font(55), get_font(30)
        title = large.render("Skill Tree", True, Colors.gold)
        screen.blit(title, (app.width // 2 - title.get_width() // 2, 12))
        points_text = small.render(f"Skill Points: {self.points}", True, Colors.gold)
        screen.blit(points_text, (app.width - points_text.get_width() - 20, 18))
        hint = small.render("Drag to pan • Scroll to zoom • Click a node, then confirm",
                            True, Colors.light_gray)
        screen.blit(hint, (app.width // 2 - hint.get_width() // 2, app.height - 34))
        self.back_button.draw(app)

    def _draw_side_panel(self, app):
        screen = app.screen
        panel = self._panel_rect(app)
        draw_panel(screen, panel, Colors.panel, radius=14)
        if self.selected is None:
            small = get_font(30)
            text = small.render("Select a node to inspect it.", True, Colors.gray)
            screen.blit(text, (panel.x + 24, panel.y + 24))
            return

        medium, small = get_font(40), get_font(30)
        x = panel.x + 24
        y = panel.y + 18
        max_text_width = panel.width - 48

        skill = skills_data.skill_by_name(self.selected)
        if skill is not None:
            state = self.progress[skill.name]
            name_text = medium.render(skill.name, True, Colors.gold)
            screen.blit(name_text, (x, y))
            y += 42
            sub = small.render(f"Skill • Level {state['level']}/{skill.max_level}",
                               True, Colors.white)
            screen.blit(sub, (x, y))
            y += 34
            stats = skills_data.current_stats(skill, state["level"], state["upgrades"])
            for stat, value in stats.items():
                stat_text = small.render(f"{stat}: {value:.1f}", True, Colors.stat_text_color)
                screen.blit(stat_text, (x, y))
                y += 26
            y += 8
            for line in wrap_text(skill.description, small, max_text_width)[:4]:
                screen.blit(small.render(line, True, Colors.light_gray), (x, y))
                y += 26
        else:
            owner, upgrade = skills_data.upgrade_owner(self.selected)
            name_text = medium.render(upgrade.name, True, Colors.gold)
            screen.blit(name_text, (x, y))
            y += 42
            sub = small.render(f"Upgrade • {owner.name}", True, Colors.white)
            screen.blit(sub, (x, y))
            y += 34

            cost_color = Colors.green if self.points >= upgrade.cost else Colors.red
            cost_text = small.render(f"Cost: {upgrade.cost} SP", True, cost_color)
            screen.blit(cost_text, (x, y))
            y += 30

            current = skills_data.current_stats(
                owner, self.progress[owner.name]["level"], self.progress[owner.name]["upgrades"])
            for stat, boost in upgrade.stat_boost.items():
                if "damage" in stat.lower() and stat in current:
                    line = f"{stat}: {current[stat] * boost:.1f}"
                elif "mana" in stat.lower() and stat in current:
                    line = f"{stat}: {current[stat] * boost:.1f}"
                else:
                    line = f"+{boost:g} {stat}"
                screen.blit(small.render(line, True, Colors.stat_text_color), (x, y))
                y += 26

            if upgrade.requires:
                y += 6
                for req in upgrade.requires:
                    mark = "OK " if self._is_owned(req) else "X  "
                    color = Colors.green if self._is_owned(req) else Colors.red
                    screen.blit(small.render(f"{mark}{req}", True, color), (x, y))
                    y += 26

            y += 6
            for line in wrap_text(upgrade.description, small, max_text_width)[:4]:
                screen.blit(small.render(line, True, Colors.light_gray), (x, y))
                y += 26

        # Action button + reason.
        info = self._action()
        if info:
            label, enabled, reason = info
            button_rect = self._action_button_rect(app)
            color = (0, 130, 60) if enabled else (70, 70, 76)
            pygame.draw.rect(screen, color, button_rect, border_radius=8)
            pygame.draw.rect(screen, Colors.light_gray, button_rect, 1, border_radius=8)
            label_surface = small.render(label, True, Colors.white)
            screen.blit(label_surface,
                        (button_rect.x + (button_rect.width - label_surface.get_width()) // 2,
                         button_rect.y + (button_rect.height - label_surface.get_height()) // 2))
            if reason:
                reason_surface = small.render(reason, True, Colors.red)
                screen.blit(reason_surface,
                            (panel.centerx - reason_surface.get_width() // 2,
                             button_rect.bottom + 8))






