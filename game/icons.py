"""Auto-generated item/artifact icons.

Items and artifacts don't need image files: their text definitions give a
shape name and a color, and this module draws a cached vector icon with
pygame primitives. If a definition names an existing image in icons/,
that image is used instead (masked into a rounded square).
"""
import math
import os

import pygame

from . import settings

_cache = {}


def _draw_shape(surf, kind, color, s):
    """Draw the vector shape for `kind`, centered in an s x s surface."""
    light = tuple(min(255, c + 55) for c in color)
    dark = tuple(max(0, c - 70) for c in color)
    cx, cy = s // 2, s // 2
    r = int(s * 0.34)
    w = max(2, s // 22)

    if kind == "sword":
        pygame.draw.line(surf, color, (cx - r, cy + r), (cx + int(r * 0.55), cy - int(r * 0.55)), w)
        pygame.draw.line(surf, dark, (cx - int(r * 0.7), cy - int(r * 0.25)),
                         (cx + int(r * 0.1), cy + int(r * 0.55)), w)
        pygame.draw.circle(surf, light, (cx - int(r * 0.85), cy + int(r * 0.85)), w)
    elif kind == "axe":
        pygame.draw.line(surf, dark, (cx - int(r * 0.5), cy + r), (cx + int(r * 0.2), cy - r), w)
        pygame.draw.polygon(surf, color, [
            (cx + int(r * 0.1), cy - r), (cx + r, cy - int(r * 0.7)),
            (cx + int(r * 0.9), cy + int(r * 0.1)), (cx + int(r * 0.1), cy - int(r * 0.4))])
    elif kind == "bow":
        rect = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
        pygame.draw.arc(surf, color, rect, math.radians(-60), math.radians(60), w)
        pygame.draw.line(surf, light, (cx + int(r * 0.5), cy - int(r * 0.87)),
                         (cx + int(r * 0.5), cy + int(r * 0.87)), 2)
    elif kind == "shield":
        pygame.draw.polygon(surf, color, [
            (cx - int(r * 0.8), cy - int(r * 0.8)), (cx + int(r * 0.8), cy - int(r * 0.8)),
            (cx + int(r * 0.8), cy + int(r * 0.2)), (cx, cy + r),
            (cx - int(r * 0.8), cy + int(r * 0.2))], w)
    elif kind == "helm":
        pygame.draw.arc(surf, color, pygame.Rect(cx - r, cy - r, 2 * r, 2 * r),
                        0, math.pi, w)
        pygame.draw.line(surf, color, (cx - r, cy), (cx + r, cy), w)
        pygame.draw.line(surf, light, (cx - int(r * 0.5), cy + int(r * 0.3)),
                         (cx + int(r * 0.5), cy + int(r * 0.3)), w)
    elif kind == "chest":
        pygame.draw.polygon(surf, color, [
            (cx - int(r * 0.9), cy - int(r * 0.7)), (cx - int(r * 0.3), cy - r),
            (cx + int(r * 0.3), cy - r), (cx + int(r * 0.9), cy - int(r * 0.7)),
            (cx + int(r * 0.7), cy + r), (cx - int(r * 0.7), cy + r)], w)
    elif kind == "potion":
        pygame.draw.rect(surf, dark, (cx - w * 2, cy - r, w * 4, int(r * 0.7)), border_radius=2)
        pygame.draw.circle(surf, color, (cx, cy + int(r * 0.25)), int(r * 0.75), w)
        pygame.draw.circle(surf, color, (cx, cy + int(r * 0.25)), int(r * 0.4))
    elif kind == "gem":
        pygame.draw.polygon(surf, color, [
            (cx, cy - r), (cx + int(r * 0.8), cy - int(r * 0.15)),
            (cx, cy + r), (cx - int(r * 0.8), cy - int(r * 0.15))], w)
        pygame.draw.polygon(surf, light, [
            (cx, cy - r), (cx + int(r * 0.4), cy + int(r * 0.3)), (cx, cy + r)], 1)
    elif kind == "ring":
        pygame.draw.circle(surf, color, (cx, cy + int(r * 0.2)), int(r * 0.7), w)
        pygame.draw.polygon(surf, light, [
            (cx, cy - r), (cx + int(r * 0.35), cy - int(r * 0.45)),
            (cx, cy - int(r * 0.1)), (cx - int(r * 0.35), cy - int(r * 0.45))])
    elif kind == "scroll":
        pygame.draw.rect(surf, color, (cx - int(r * 0.7), cy - r, int(r * 1.4), 2 * r), w,
                         border_radius=3)
        for dy in (-int(r * 0.4), 0, int(r * 0.4)):
            pygame.draw.line(surf, light, (cx - int(r * 0.35), cy + dy),
                             (cx + int(r * 0.35), cy + dy), 2)
    elif kind == "star":
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            radius = r if i % 2 == 0 else int(r * 0.45)
            points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        pygame.draw.polygon(surf, color, points)
    elif kind == "orb":
        pygame.draw.circle(surf, color, (cx, cy), int(r * 0.85), w)
        pygame.draw.circle(surf, light, (cx, cy), int(r * 0.5), 2)
        pygame.draw.circle(surf, light, (cx - int(r * 0.3), cy - int(r * 0.3)), int(r * 0.15))
    elif kind == "crystal":
        pygame.draw.polygon(surf, color, [
            (cx, cy - r), (cx + int(r * 0.55), cy - int(r * 0.2)),
            (cx + int(r * 0.4), cy + r), (cx - int(r * 0.4), cy + r),
            (cx - int(r * 0.55), cy - int(r * 0.2))], w)
    elif kind == "fang":
        pygame.draw.polygon(surf, color, [
            (cx - int(r * 0.45), cy - r), (cx + int(r * 0.45), cy - r),
            (cx + int(r * 0.15), cy + r), (cx - int(r * 0.1), cy + int(r * 0.6))], w)
    elif kind == "feather":
        pygame.draw.line(surf, dark, (cx - int(r * 0.6), cy + int(r * 0.7)),
                         (cx + int(r * 0.6), cy - int(r * 0.7)), 2)
        pygame.draw.ellipse(surf, color, (cx - int(r * 0.7), cy - int(r * 0.9),
                                         int(r * 1.4), int(r * 1.7)), w)
    elif kind == "book":
        pygame.draw.rect(surf, color, (cx - int(r * 0.85), cy - int(r * 0.95),
                                      int(r * 1.7), int(r * 1.9)), w, border_radius=3)
        pygame.draw.line(surf, light, (cx, cy - int(r * 0.95)), (cx, cy + int(r * 0.95)), w)
    elif kind == "crown":
        pygame.draw.polygon(surf, color, [
            (cx - r, cy + int(r * 0.6)), (cx - r, cy - int(r * 0.3)),
            (cx - int(r * 0.45), cy + int(r * 0.1)), (cx, cy - r),
            (cx + int(r * 0.45), cy + int(r * 0.1)), (cx + r, cy - int(r * 0.3)),
            (cx + r, cy + int(r * 0.6))], w)
    elif kind == "key":
        pygame.draw.circle(surf, color, (cx - int(r * 0.45), cy - int(r * 0.4)),
                          int(r * 0.35), w)
        pygame.draw.line(surf, color, (cx - int(r * 0.2), cy - int(r * 0.1)),
                         (cx + int(r * 0.75), cy + int(r * 0.75)), w)
        pygame.draw.line(surf, color, (cx + int(r * 0.45), cy + int(r * 0.45)),
                         (cx + int(r * 0.45), cy + r), w)
        pygame.draw.line(surf, color, (cx + int(r * 0.7), cy + int(r * 0.7)),
                         (cx + r, cy + int(r * 0.5)), w)
    else:                       # unknown shape -> generic orb mark
        pygame.draw.circle(surf, color, (cx, cy), int(r * 0.8), w)
        pygame.draw.circle(surf, light, (cx, cy), int(r * 0.35), 2)


_SHAPE_ALIASES = {
    "weapon": "sword", "armor": "chest", "consumable": "potion",
    "material": "gem", "quest": "scroll", "relic": "gem",
}


def get_icon(icon_key, color, size, fallback_shape="orb"):
    """Cached icon Surface for an item/artifact.

    icon_key may be a shape name (see _draw_shape), an item type (aliased
    to a shape), or an image filename inside icons/.
    """
    size = max(8, int(size))
    color = tuple(color[:3])
    key = (icon_key, color, size, fallback_shape)
    if key in _cache:
        return _cache[key]

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surf, (28, 28, 34, 235), surf.get_rect(),
                     border_radius=max(3, size // 6))
    pygame.draw.rect(surf, (*color, 150), surf.get_rect(),
                     width=max(2, size // 26), border_radius=max(3, size // 6))

    shape = (icon_key or "").strip().lower()
    image_path = os.path.join(settings.ICONS_DIR, shape)
    if shape and os.path.isfile(image_path):
        try:
            image = pygame.image.load(image_path)
            image = pygame.transform.scale(
                image, (int(size * 0.78), int(size * 0.78))).convert_alpha()
            surf.blit(image, (size * 0.11, size * 0.11))
        except pygame.error:
            _draw_shape(surf, _SHAPE_ALIASES.get(shape, fallback_shape), color, size)
    else:
        if shape in _SHAPE_ALIASES:
            shape = _SHAPE_ALIASES[shape]
        _draw_shape(surf, shape if shape else fallback_shape, color, size)

    _cache[key] = surf
    return surf

