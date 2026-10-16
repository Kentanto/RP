"""Reusable UI widgets and drawing helpers.

All widgets are ratio-based (fractions of the window size) so they scale
when the window is resized. Button uses event.pos for click detection,
which is more reliable than re-reading the mouse during the event pump.
"""
import math

import pygame

from . import audio, settings
from .settings import Colors, get_font


# ------------------------------------------------------------------ text

def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def truncate_text(text, font, max_width):
    if font.size(text)[0] <= max_width:
        return text
    while text and font.size(text + "...")[0] > max_width:
        text = text[:-1]
    return text + "..."


def fit_text_to_box(text, box_width, box_height, max_size=55, min_size=18):
    """Largest default font <= max_size whose text fits in the box."""
    for size in range(max_size, min_size - 1, -2):
        font = get_font(size)
        if font.size(text)[0] <= box_width and font.size(text)[1] <= box_height:
            return font
    return get_font(min_size)


def draw_text_center(screen, text, font, color, cx, y):
    surface = font.render(text, True, color)
    screen.blit(surface, (cx - surface.get_width() // 2, y))
    return surface


def draw_text(text, font, color, surface, x, y):
    surface.blit(font.render(text, True, color), (x, y))


# ---------------------------------------------------------------- panels

def draw_panel(screen, rect, color=Colors.panel, radius=12, border=None):
    surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surface, color, surface.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, surface.get_rect(), width=2, border_radius=radius)
    screen.blit(surface, (rect.x, rect.y))


def draw_flash(screen, text, color, width, height, until):
    """Transient centered message (drawn while pygame ticks < until)."""
    if pygame.time.get_ticks() >= until:
        return False
    font = get_font(40)
    surface = font.render(text, True, color)
    x = width // 2 - surface.get_width() // 2
    y = height - settings.scaled(120)
    bg = pygame.Surface((surface.get_width() + 30, surface.get_height() + 14), pygame.SRCALPHA)
    pygame.draw.rect(bg, (0, 0, 0, 180), bg.get_rect(), border_radius=8)
    screen.blit(bg, (x - 15, y - 7))
    screen.blit(surface, (x, y))
    return True


# ----------------------------------------------------------------- icons

_icon_cache = {}


def create_circular_icon(image_path, size):
    """Load an image masked into a circle, cached (the old code reloaded the
    file from disk every frame)."""
    size = max(2, int(size))
    key = (image_path, size)
    if key in _icon_cache:
        return _icon_cache[key]
    icon = pygame.image.load(image_path)
    icon = pygame.transform.scale(icon, (size, size))
    circle = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(circle, (255, 255, 255), (size // 2, size // 2), size // 2)
    masked = pygame.Surface((size, size), pygame.SRCALPHA)
    masked.blit(icon, (0, 0))
    masked.blit(circle, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    if len(_icon_cache) > 32:
        _icon_cache.clear()
    _icon_cache[key] = masked
    return masked


def get_edge_points(start_pos, end_pos, radius):
    """Shorten a connector line so it starts/ends at node borders."""
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]
    angle = math.atan2(dy, dx)
    start = (start_pos[0] + math.cos(angle) * radius,
             start_pos[1] + math.sin(angle) * radius)
    end = (end_pos[0] - math.cos(angle) * radius,
           end_pos[1] - math.sin(angle) * radius)
    return start, end


# --------------------------------------------------------------- widgets

class Button:
    """Ratio-based text button that rescales with the window."""

    def __init__(self, text, x_ratio, y_ratio, width_ratio, height_ratio,
                 hover_color=(255, 255, 255, 128), is_back_button=False):
        self.text = text
        self.x_ratio = x_ratio
        self.y_ratio = y_ratio
        self.width_ratio = width_ratio
        self.height_ratio = height_ratio
        self.hover_color = hover_color
        self.was_hovered = False
        self.is_back_button = is_back_button
        self.rect = pygame.Rect(0, 0, 1, 1)

    def update_dimensions(self, app):
        width = int(app.width * self.width_ratio)
        height = int(app.height * self.height_ratio)
        x = int(app.width * self.x_ratio - width / 2)
        y = int(app.height * self.y_ratio - height / 2)
        self.rect = pygame.Rect(x, y, width, height)

    def is_hovered(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, app):
        self.update_dimensions(app)
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.is_hovered(mouse_pos)
        if is_hovered and not self.was_hovered:
            audio.play(app, "hover")
        self.was_hovered = is_hovered

        font = get_font(55)
        text_surface = font.render(self.text, True, Colors.white)
        if is_hovered:
            hover_width = text_surface.get_width() + 20
            hover_surface = pygame.Surface((hover_width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, self.hover_color, hover_surface.get_rect())
            app.screen.blit(hover_surface, (self.rect.x + (self.rect.width - hover_width) // 2,
                                           self.rect.y))
        app.screen.blit(text_surface, (
            self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
            self.rect.y + (self.rect.height - text_surface.get_height()) // 2))

    def is_clicked(self, app, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered(event.pos):
                if self.is_back_button:
                    audio.play(app, "back")
                else:
                    audio.play(app, "click")
                return True
        return False


class DropdownMenu:
    """Simple selection dropdown (used for artifact sorting)."""

    def __init__(self, options, x, y, width, height, font):
        self.options = options
        self.selected = 0
        self.open = False
        self.x, self.y, self.width, self.height = x, y, width, height
        self.font = font

    def draw(self, screen):
        pygame.draw.rect(screen, Colors.white, (self.x, self.y, self.width, self.height),
                         border_radius=5)
        text = self.font.render(self.options[self.selected], True, Colors.black)
        screen.blit(text, (self.x + 10, self.y + 5))
        if self.open:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(self.x, self.y + self.height + i * self.height,
                                          self.width, self.height)
                color = Colors.light_blue if i == self.selected or option_rect.collidepoint(
                    (mouse_x, mouse_y)) else Colors.white
                pygame.draw.rect(screen, color, option_rect, border_radius=3)
                screen.blit(self.font.render(option, True, Colors.black),
                            (option_rect.x + 10, option_rect.y + 5))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            main_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if main_rect.collidepoint((mx, my)):
                self.open = not self.open
                return True
            if self.open:
                for i, _ in enumerate(self.options):
                    option_rect = pygame.Rect(self.x, self.y + self.height + i * self.height,
                                              self.width, self.height)
                    if option_rect.collidepoint((mx, my)):
                        self.selected = i
                        self.open = False
                        return True
                self.open = False
        return False

    def get_selected(self):
        return self.options[self.selected]


class Checkbox:
    """Small labeled checkbox."""

    def __init__(self, x, y, size, checked=False, label="", font=None):
        self.x, self.y, self.size = x, y, size
        self.checked = checked
        self.label = label
        self.font = font

    def draw(self, screen):
        rect = pygame.Rect(self.x, self.y, self.size, self.size)
        pygame.draw.rect(screen, Colors.light_gray, rect, border_radius=3)
        if self.checked:
            pygame.draw.line(screen, Colors.green,
                             (self.x + 4, self.y + self.size // 2),
                             (self.x + self.size // 2, self.y + self.size - 4), 3)
            pygame.draw.line(screen, Colors.green,
                             (self.x + self.size // 2, self.y + self.size - 4),
                             (self.x + self.size - 4, self.y + 4), 3)
        if self.label and self.font:
            label_text = self.font.render(self.label, True, Colors.black)
            screen.blit(label_text, (self.x + self.size + 8,
                                     self.y + self.size // 2 - label_text.get_height() // 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(self.x, self.y, self.size, self.size).collidepoint(event.pos):
                self.checked = not self.checked
                return True
        return False

    def is_checked(self):
        return self.checked

