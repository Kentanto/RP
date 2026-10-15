"""Math difficulty selection."""
from .. import db
from ..core import Scene
from ..settings import Colors, get_font
from ..ui import Button


DIFFICULTIES = (
    ("Easy", "Easy", 20, 1),
    ("Medium", "Locked-Medium-Locked LV: 8", 50, 7),
    ("Hard", "Locked-Hard-Locked Lv: 15", 200, 14),
    ("Extreme", "Locked-Extreme-Locked LV: 25", 600, 20),
)


class MathMenuScene(Scene):
    def __init__(self):
        super().__init__()
        self.buttons = []
        for i, (_, label, _, _) in enumerate(DIFFICULTIES):
            self.buttons.append(Button(label, 0.5, 0.2 + i * 0.2, 0.4, 0.1, Colors.hover_color))
        self.leave_button = Button("Leave", 0.1, 0.1, 0.1, 0.1,
                                    is_back_button=True)
        self.points = 0

    def on_enter(self, app):
        self.points = db.get_current_points()

    def handle_event(self, app, event):
        if self.leave_button.is_clicked(app, event):
            app.pop_scene()
            return
        for i, (_, _, cost, difficulty) in enumerate(DIFFICULTIES):
            if self.buttons[i].is_clicked(app, event):
                if not db.subtract_points(cost):
                    self.flash("Not enough points!", Colors.red)
                    return
                from .minigames import MathGameScene
                app.push_scene(MathGameScene(difficulty))
                return

    def draw(self, app):
        text = get_font(40).render(f"Points: {self.points}/{20}", True, Colors.white)
        app.screen.blit(text, (app.width - 200, 50))
        for button in self.buttons:
            button.draw(app)
        self.leave_button.draw(app)
        self.draw_flash(app)
