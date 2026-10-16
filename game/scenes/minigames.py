"""Minigames hub and the math mini-game.

The old math game used eval() on generated strings and chained rounds by
recursing into itself; here equations are checked against a whitelist AST
and rounds happen inside one scene.
"""
import ast
import random
import secrets

import pygame

from .. import db
from ..core import Scene
from ..settings import Colors, get_font, scaled
from ..ui import Button, draw_panel, truncate_text
from .math_menu import tier_for


# ------------------------------------------------------- equation generation

def generate_math_equation(equation_length):
    """Random arithmetic equation. Always syntactically valid, balanced
    parentheses, no dangling operators, and never a division by zero (the
    old generator could emit unclosed parens like '(5+(6+9' and groups
    like '(3-3)' that crash the evaluation)."""
    for _ in range(50):
        equation = _build_equation(equation_length)
        try:
            safe_eval(equation)
            return equation
        except (ValueError, ZeroDivisionError, SyntaxError):
            continue
    # Practically unreachable; fall back to a trivially valid equation.
    return "1+1"


def _build_equation(equation_length):
    equation_length += 2
    math_numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    math_operators = ["*", "-", "+", "/"]
    tokens = []
    open_groups = 0
    i = 0
    while i < equation_length:
        if i % 2 == 0:
            number = secrets.choice(math_numbers)
            if random.random() > 0.9:
                tokens.append(f"{number}**{random.randint(2, 4)}")
            else:
                tokens.append(number)
            # Open a group right before the number we just added, so the
            # token before "(" is an operator (or nothing, at the start).
            if random.random() > 0.8 and i < equation_length - 2:
                tokens.insert(-1, "(")
                open_groups += 1
        else:
            if open_groups > 0 and random.random() > 0.7 and i < equation_length - 2:
                tokens.append(")")
                open_groups -= 1
            tokens.append(secrets.choice(math_operators))
        i += 1

    while tokens and tokens[-1] in math_operators:
        tokens.pop()
    tokens.extend(")" * open_groups)
    return "".join(tokens)


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


def safe_eval(expr):
    """Evaluate an arithmetic expression without touching builtins eval."""
    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            return left ** right
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("unsupported expression")
    return visit(ast.parse(expr, mode="eval"))


def round_result(result, precision=0.1):
    return round(result / precision) * precision


# ------------------------------------------------------------- result overlay

class ResultOverlayScene(Scene):
    """Panel shown after answering a round; any key/click dismisses it."""

    def __init__(self, title, lines):
        super().__init__()
        self.title = title
        self.lines = lines

    def handle_event(self, app, event):
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            app.pop_scene()

    def draw(self, app):
        title_font, line_font, hint_font = get_font(55), get_font(40), get_font(30)
        panel_width = min(int(app.width * 0.92), scaled(620))
        # Truncate reward lines to the panel: artifact names can be long.
        lines = [(truncate_text(line, line_font, panel_width - scaled(40)), color)
                 for line, color in self.lines]
        line_height = line_font.get_height() + scaled(8)
        panel_height = (title_font.get_height() + scaled(36)
                        + line_height * len(lines)
                        + hint_font.get_height() + scaled(24))
        panel_x = app.width // 2 - panel_width // 2
        panel_y = max(scaled(20), app.height // 2 - panel_height // 2)
        draw_panel(app.screen, pygame.Rect(panel_x, panel_y, panel_width, panel_height))

        title_surface = title_font.render(self.title, True,
                                          Colors.green if self.title == "Correct!" else Colors.red)
        app.screen.blit(title_surface, (app.width // 2 - title_surface.get_width() // 2,
                                        panel_y + scaled(18)))
        y = panel_y + title_font.get_height() + scaled(30)
        for line, color in lines:
            surface = line_font.render(line, True, color)
            app.screen.blit(surface, (app.width // 2 - surface.get_width() // 2, y))
            y += line_height
        hint = hint_font.render("Press any key to continue...", True, Colors.white)
        app.screen.blit(hint, (app.width // 2 - hint.get_width() // 2, y))


# ---------------------------------------------------------- minigames hub

class MinigamesScene(Scene):
    def __init__(self):
        super().__init__()
        self.math_button = Button("Math", 0.5, 0.5, 0.1, 0.1, Colors.hover_color)
        self.back_button = Button("Back", 0.08, 0.05, 0.1, 0.1, Colors.hover_color,
                                   is_back_button=True)
        self.points = 0

    def on_enter(self, app):
        self.points = db.get_current_points()

    def handle_event(self, app, event):
        if self.back_button.is_clicked(app, event):
            app.pop_scene()
            return
        if self.math_button.is_clicked(app, event):
            from .math_menu import MathMenuScene
            app.push_scene(MathMenuScene())

    def draw(self, app):
        self.math_button.draw(app)
        self.back_button.draw(app)
        text = get_font(40).render(f"Points: {self.points}", True, Colors.white)
        app.screen.blit(text, (app.width - text.get_width() - scaled(20),
                               scaled(50)))
        self.draw_flash(app)


# -------------------------------------------------------------- math game

class MathGameScene(Scene):
    """One math round. After the result overlay is dismissed the scene
    charges the fee for the next round and continues, or pops back when
    the player can't pay / leaves (the leave fee is refunded).

    Correct answers pay skill points (per tier) and build a streak that
    boosts artifact points up to double; a wrong answer resets it.
    """

    MAX_STREAK_BONUS = 10           # +10% artifact points per streak step
    handles_escape = True  # ESC leaves (with refund) instead of plain back

    def __init__(self, difficulty):
        super().__init__()
        self.difficulty = difficulty
        tier = tier_for(difficulty)
        self.fee = tier.fee          # every round costs the tier entry fee
        self.reward = tier.reward    # skill points for a correct answer
        self.streak = 0
        self.leave_button = Button("Leave", 0.1, 0.1, 0.1, 0.1, Colors.hover_color,
                                   is_back_button=True)
        self.user_input = ""
        self.equation = ""
        self.answer = 0.0
        self._new_round()

    def _new_round(self):
        for _ in range(50):
            self.equation = generate_math_equation(self.difficulty)
            try:
                self.answer = round_result(safe_eval(self.equation), precision=0.1)
                break
            except (ValueError, ZeroDivisionError, SyntaxError):
                continue
        self.user_input = ""

    def _submit(self, app):
        try:
            user_answer = float(self.user_input)
        except ValueError:
            self.flash("Enter a number", Colors.red)
            self.user_input = ""
            return
        correct = round_result(user_answer, precision=0.1) == self.answer
        if correct:
            self.streak += 1
            artifact_points = int(100 * (1 + 0.1 * min(self.streak - 1,
                                                        self.MAX_STREAK_BONUS)))
            db.add_artifact_points(artifact_points)
            artifact = db.generate_artifact_by_level(self.difficulty)
            lines = []
            if artifact:
                db.add_artifact(artifact)
                lines.append((f"You received: {artifact['name']}", Colors.gold))
                lines.append((f"Main Stat: {artifact['main_stat']} "
                              f"+{db.format_stat_value(artifact['main_stat'], artifact['main_stat_value'])}",
                              Colors.white))
            lines.append((f"+{artifact_points} Artifact Points"
                          + (f"  (streak x{self.streak})" if self.streak > 1 else ""),
                          Colors.green))
            db.add_points(self.reward)
            db.bump_mission("math_correct", 1)
            lines.append((f"+{self.reward} Points", Colors.gold))
            xp_gain = 20 * self.difficulty
            xp_result = db.add_xp(xp_gain)
            if xp_result:
                lines.append((f"+{xp_gain} XP", Colors.light_blue))
                if xp_result["levels_gained"]:
                    lines.append((f"LEVEL UP! Now level {xp_result['level']}",
                                  Colors.gold))
        else:
            self.streak = 0
            lines = [(f"The correct answer is: {self.answer:g}", Colors.white),
                     ("Streak reset", Colors.light_gray)]
        self._round_done = True
        app.push_scene(ResultOverlayScene("Correct!" if correct else "Incorrect!", lines))
        self.user_input = ""

    def _charge_next_round(self, app):
        if db.subtract_points(self.fee):
            self._new_round()
        else:
            self.flash("Not enough points!", Colors.red)
            app.pop_scene()

    def _leave(self, app):
        db.add_points(self.fee)  # refund the round fee, as the old game did
        app.pop_scene()

    def on_enter(self, app):
        # Called again right after the result overlay pops -> next round fee.
        if app.scene is self and getattr(self, "_round_done", False):
            self._round_done = False
            self._charge_next_round(app)

    def handle_event(self, app, event):
        if self.leave_button.is_clicked(app, event):
            self._leave(app)
            return
        if event.type == pygame.KEYDOWN:
            event_key = getattr(event, "key", None)
            if event_key == pygame.K_ESCAPE:
                self._leave(app)
            elif event_key == pygame.K_RETURN:
                self._submit(app)
            elif event_key == pygame.K_BACKSPACE:
                self.user_input = self.user_input[:-1]
            elif event.unicode and event.unicode.isprintable():
                self.user_input += event.unicode

    def draw(self, app):
        # Shrink the equation font until it fits the window: the harder
        # tiers generate long equations that would overflow any width.
        text = f"Solve: {self.equation}"
        size = 55
        font = get_font(size)
        while font.size(text)[0] > app.width * 0.92 and size > 24:
            size -= 5
            font = get_font(size)
        equation_surface = font.render(text, True, Colors.white)
        equation_y = int(app.height * 0.24)
        app.screen.blit(equation_surface,
                        (app.width // 2 - equation_surface.get_width() // 2,
                         equation_y))

        if self.streak >= 2:
            streak_text = get_font(30).render(f"Streak x{self.streak}", True,
                                              Colors.gold)
            app.screen.blit(streak_text,
                            (app.width // 2 - streak_text.get_width() // 2,
                             equation_y + equation_surface.get_height()
                             + scaled(12)))

        input_surface = font.render(self.user_input or " ", True, Colors.white)
        app.screen.blit(input_surface,
                        (app.width // 2 - input_surface.get_width() // 2,
                         int(app.height * 0.52)))
        self.leave_button.draw(app)
        self.draw_flash(app)

