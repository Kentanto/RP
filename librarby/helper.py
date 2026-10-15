"""Legacy compatibility shim.

The old helpers moved to `game.db`, `game.ui` and `game.settings`.
This module re-exports them so any old external code keeps working.
"""
import sys

import pygame

from game.settings import Colors, DB_PATH  # noqa: F401
from game.db import (  # noqa: F401
    add_artifact, add_artifact_points, add_points, format_stat_value,
    generate_artifact_by_level, generate_random_artifact_name,
    get_artifact_points, get_artifact_stat_total, get_current_points,
    get_equipped_artifacts, get_inventory_items, get_shop_items,
    level_up_artifact, purchase_item, remove_equipped_artifact, roll_stat,
    set_equipped_artifact, spend_artifact_points, subtract_points,
    update_artifact_points, update_points,
)
from game.ui import (  # noqa: F401
    create_circular_icon, draw_text, fit_text_to_box, get_edge_points,
    truncate_text, wrap_text,
)


def cleanup():
    try:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except pygame.error:
        pass
    pygame.quit()
    sys.exit()


def round_result(result, precision=0.1):
    return round(result / precision) * precision


class WindowState:
    """Legacy no-op stub — window state is owned by game.core.App now."""

    def __init__(self):
        self.width, self.height = 800, 600

    def update(self, force=False):
        return True
