"""Read-only skill catalogue with player skill upgrades."""
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from athas.skills_manager import SkillManager
from athas.styles import CYAN, WHITE


def _nonnegative_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    return default


class SkillCard(QFrame):
    def __init__(
        self,
        skill: dict[str, Any],
        level: int,
        skill_points: int,
        image_path: Path,
        on_upgrade: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: rgba(10,10,16,220); border: 1px solid {CYAN}55; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(18)

        image = QLabel()
        image.setFixedSize(144, 144)
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setStyleSheet("background-color: #101016; border: 1px solid #30303a; color: #777;")
        pixmap = self._load_image(image_path)
        if pixmap is not None:
            image.setPixmap(
                pixmap.scaled(
                    image.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            image.setText("NO IMAGE")
        layout.addWidget(image)

        details = QVBoxLayout()
        title = QLabel(skill["title"])
        title.setStyleSheet(f"color: {WHITE}; font-size: 22px; font-weight: bold;")
        details.addWidget(title)

        description = QLabel(skill["description"])
        description.setWordWrap(True)
        description.setStyleSheet("color: #aaa; font-size: 13px;")
        details.addWidget(description)

        max_level = skill["max_level"]
        damage = (
            0
            if level == 0
            else skill["base_damage"] + (level - 1) * skill["damage_per_level"]
        )
        stats = QLabel(
            f"Mana cost: {skill['mana_cost']}    "
            f"Damage: {damage}    "
            f"Level: {level}/{max_level}"
        )
        stats.setStyleSheet(f"color: {CYAN}; font-size: 12px; font-weight: bold;")
        details.addWidget(stats)
        details.addStretch()

        upgrade = QPushButton()
        upgrade.setCursor(Qt.CursorShape.PointingHandCursor)
        upgrade.setStyleSheet(f"""
            QPushButton {{
                background-color: {CYAN}11; border: 1px solid {CYAN};
                color: {CYAN}; padding: 8px 16px;
            }}
            QPushButton:hover {{ background-color: {CYAN}; color: #0a0a0a; }}
            QPushButton:disabled {{ color: #666; border-color: #444; background: transparent; }}
        """)
        if level >= max_level:
            upgrade.setText("MAX LEVEL")
            upgrade.setEnabled(False)
        else:
            cost = skill["upgrade_cost"]
            action = "UNLOCK" if level == 0 else "UPGRADE"
            upgrade.setText(f"{action} · {cost} SKILL POINT" + ("S" if cost != 1 else ""))
            upgrade.setEnabled(skill_points >= cost)
            upgrade.clicked.connect(on_upgrade)
        details.addWidget(upgrade, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(details, 1)

    @staticmethod
    def _load_image(path: Path) -> QPixmap | None:
        if not path.is_file():
            return None
        pixmap = QPixmap(str(path))
        return pixmap if not pixmap.isNull() else None


class SkillsPanel(QWidget):
    def __init__(self, config, skills_manager: SkillManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.skills_manager = skills_manager
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("SKILLS")
        title.setStyleSheet(f"color: {WHITE}; font-size: 28px; font-weight: bold; letter-spacing: 3px;")
        header.addWidget(title)
        header.addStretch()
        self._points_label = QLabel()
        self._points_label.setStyleSheet(f"color: {CYAN}; font-size: 16px; font-weight: bold;")
        header.addWidget(self._points_label)
        layout.addLayout(header)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        layout.addWidget(line)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._list = QWidget()
        self._list.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 8, 0)
        self._list_layout.setSpacing(12)
        scroll.setWidget(self._list)
        layout.addWidget(scroll, 1)
        self.refresh()

    def refresh(self):
        skill_points = _nonnegative_int(self.config.get("player", "skill_points", 0))
        self._points_label.setText(f"SKILL POINTS: {skill_points}")

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        skills = self.skills_manager.load_skills()
        if not skills:
            empty = QLabel("You have no skills, loser.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #888; font-size: 16px;")
            self._list_layout.addWidget(empty)
        else:
            for skill in skills:
                skill_id = skill["id"]
                level = _nonnegative_int(
                    self.config.get_nested("player", "skill_levels", skill_id, default=0)
                )
                image_path = self.skills_manager.skills_file.parent / skill["image"]
                card = SkillCard(
                    skill,
                    level,
                    skill_points,
                    image_path,
                    lambda _, current_skill=skill: self._upgrade(current_skill),
                )
                self._list_layout.addWidget(card)
        self._list_layout.addStretch()

    def _upgrade(self, skill: dict[str, Any]):
        points = _nonnegative_int(self.config.get("player", "skill_points", 0))
        level = _nonnegative_int(
            self.config.get_nested("player", "skill_levels", skill["id"], default=0)
        )
        cost = skill["upgrade_cost"]
        if level >= skill["max_level"] or points < cost:
            return

        self.config.set_nested("player", "skill_levels", skill["id"], level + 1, save=False)
        self.config.set("player", "skill_points", points - cost, save=False)
        self.config.save()
        self.refresh()
