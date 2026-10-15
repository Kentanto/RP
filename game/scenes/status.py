"""Stats window: base stats, artifact bonuses, and equip slots."""
import sqlite3

import pygame

from .. import db, settings
from ..core import Scene
from ..settings import Colors, get_font
from ..ui import Button

BASE_STATS = {
    "Level": 1,
    "CON": 10,
    "ATK": 5,
    "DEF": 10,
    "SPD": 5,
    "mana": 0,
    "Crit Rate": 0.2,
    "Crit DMG": 20,
}


class StatusScene(Scene):
    def __init__(self):
        super().__init__()
        self.back_button = Button("Back", 0.08, 0.05, 0.2, 0.1, Colors.hover_color,
                                  is_back_button=True)
        self.artifacts_button = Button("Artifacts", 0.85, 0.05, 0.3, 0.1, Colors.hover_color)
        self.skills_button = Button("Skills", 0.5, 0.05, 0.2, 0.1, Colors.hover_color)
        self.equipped = {}
        self.equipped_names = [None] * 4
        self.stat_surfaces = []

    def on_enter(self, app):
        # One query for all equipped artifacts (the old code opened a
        # separate DB connection for every slot, every frame).
        self.equipped = db.get_equipped_artifacts()
        self.equipped_names = [None] * 4
        artifact_bonus = {k: 0 for k in ("ATK", "DEF", "SPD", "CON", "mana",
                                        "Crit Rate", "Crit DMG")}
        percent_bonus = {k: 0.0 for k in ("ATK", "DEF", "SPD", "CON", "mana")}

        ids = [aid for aid in self.equipped.values() if aid]
        if ids:
            with sqlite3.connect(settings.DB_PATH) as conn:
                placeholders = ",".join("?" * len(ids))
                rows = conn.execute(
                    f"""SELECT id, name, main_stat, main_stat_value,
                              sub_stat1, sub_stat1_value, sub_stat2, sub_stat2_value
                       FROM artifacts WHERE id IN ({placeholders})""", ids).fetchall()
            by_id = {row[0]: row for row in rows}
            for slot in range(4):
                row = by_id.get(self.equipped.get(slot + 1))
                if not row:
                    continue
                self.equipped_names[slot] = row[1]
                for stat, value in ((row[2], row[3]), (row[4], row[5]), (row[6], row[7])):
                    if not stat or value is None:
                        continue
                    stat_key = stat.replace("%", "").replace("HP", "CON")
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        continue
                    if stat_key in ("Crit Rate", "Crit DMG"):
                        artifact_bonus[stat_key] += value
                    elif value < 5.0:
                        percent_bonus[stat_key] += value
                    elif stat_key in artifact_bonus:
                        artifact_bonus[stat_key] += int(round(value))

        self.stat_surfaces = []
        for stat, base_value in BASE_STATS.items():
            if stat in ("Crit Rate", "Crit DMG"):
                total = base_value + artifact_bonus.get(stat, 0.0)
                text = get_font(40).render(f"{stat}: {total:.1f}%", True,
                                          Colors.stat_text_color)
            else:
                total = base_value + artifact_bonus.get(stat, 0)
                total = int(round(total * (1 + percent_bonus.get(stat, 0.0))))
                text = get_font(40).render(f"{stat}: {total}", True, Colors.stat_text_color)
            self.stat_surfaces.append(text)

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
            for slot_index, rect in enumerate(self._slot_rects(app)):
                if rect.collidepoint(event.pos):
                    artifact_id = self.equipped.get(slot_index + 1)
                    if artifact_id:
                        from .artifacts import ArtifactDetailScene
                        app.push_scene(ArtifactDetailScene(
                            artifact_id, equip_slot=slot_index + 1, remove_slot=slot_index + 1))
                    else:
                        from .artifacts import ArtifactsScene
                        app.push_scene(ArtifactsScene(equip_slot=slot_index + 1,
                                                      remove_slot=slot_index + 1))
                    return

    @staticmethod
    def _slot_rects(app):
        slot_width = int(app.width * 0.12)
        slot_height = int(app.height * 0.11)
        slot_spacing = int(slot_width * 1.3)
        base_x = (app.width - (slot_width * 2.3 + slot_spacing * 2)) // 2
        base_y = int(app.height * 0.8)
        return [pygame.Rect(base_x + i * slot_spacing, base_y, slot_width, slot_height)
                for i in range(4)]

    def draw(self, app):
        rects = self._slot_rects(app)
        start_y = 150
        for i, surf in enumerate(self.stat_surfaces):
            app.screen.blit(surf, (app.width // 2 - 100, start_y + i * 40))

        slot_labels = ["Slot 1", "Slot 2", "Slot 3", "Slot 4"]
        for i, rect in enumerate(rects):
            pygame.draw.rect(app.screen, Colors.light_gray, rect, border_radius=10)
            label = get_font(30).render(slot_labels[i], True, Colors.gray)
            app.screen.blit(label, (rect.x + 8, rect.y + 6))
            name = self.equipped_names[i]
            if name:
                short_name = name.split(" ")[0]
                name_text = get_font(30).render(short_name, True, Colors.gold)
            else:
                name_text = get_font(30).render("Empty", True, Colors.gray)
            app.screen.blit(name_text, (rect.x + 8, rect.y + 35))

        self.back_button.draw(app)
        self.skills_button.draw(app)
        self.artifacts_button.draw(app)
        self.draw_flash(app)

