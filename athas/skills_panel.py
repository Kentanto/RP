"""Skill catalogue — clicking a card opens that skill's upgrade tree."""
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from athas.skill_tree_dialog import SkillTreeDialog
from athas.skills_manager import SkillManager, migrate_skill_ranks
from athas.styles import CYAN, WHITE


def _nonnegative_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(0, value)
    return default


class SkillCard(QFrame):
    def __init__(
        self,
        skill: dict[str, Any],
        image_path: Path,
        on_click: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        # The click callback runs through a bound method below: connecting
        # widgets straight to a Python lambda crashes PySide6 on teardown
        # (stale global-receiver objects when cards are destroyed).
        self._on_click_cb: Callable[[], None] | None = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Scope the rules to the card itself: a plain ``QFrame`` selector would
        # also match every QLabel inside (QLabel is a QFrame subclass), making
        # each element light up individually on hover instead of the whole box.
        self.setObjectName("SkillCard")
        self.setStyleSheet(
            f"""
            QFrame#SkillCard {{ background-color: rgba(10,10,16,220); border: 1px solid {CYAN}55; }}
            QFrame#SkillCard:hover {{ background-color: rgba(16,28,38,235); border: 1px solid {CYAN}; }}
            QLabel {{ background: transparent; border: none; }}
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        image = QLabel()
        image.setFixedSize(88, 88)
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
        details.setSpacing(5)
        title = QLabel(skill["title"])
        title.setStyleSheet(f"color: {WHITE}; font-size: 18px; font-weight: bold;")
        details.addWidget(title)

        description = QLabel(skill["description"])
        description.setWordWrap(True)
        description.setStyleSheet("color: #aaa; font-size: 12px;")
        details.addWidget(description)

        stats = QLabel(f"MANA {skill['mana_cost']} · DMG {skill['base_damage']}")
        stats.setWordWrap(True)
        stats.setStyleSheet(f"color: {CYAN}; font-size: 10px; font-weight: bold;")
        details.addWidget(stats)
        details.addStretch()

        tip = QLabel("▸ CLICK TO VIEW UPGRADES")
        tip.setStyleSheet(
            "color: rgba(0,240,255,170); font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        details.addWidget(tip, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(details, 1)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_card_click()
        super().mouseReleaseEvent(event)

    def _handle_card_click(self):
        if self._on_click_cb is not None:
            self._on_click_cb()

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

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #ff9800; font-size: 11px;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._list = QWidget()
        self._list.setStyleSheet("background: transparent;")
        self._list_layout = QGridLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 8, 0)
        self._list_layout.setSpacing(12)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._cards: list[SkillCard] = []
        self._empty_state: QLabel | None = None
        scroll.setWidget(self._list)
        layout.addWidget(scroll, 1)

        # Reload automatically when skill files are added, removed, or edited.
        # The short debounce batches bursts of events (e.g. a git pull).
        self._reload_debounce = QTimer(self)
        self._reload_debounce.setSingleShot(True)
        self._reload_debounce.setInterval(300)
        self._reload_debounce.timeout.connect(self.refresh)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_skills_folder_changed)
        self._watcher.fileChanged.connect(self._on_skills_folder_changed)
        self._watched_paths: set[str] = set()
        # Upgrade ranks live in the skill files now; fold any legacy
        # config-saved ranks into them before the first load.
        migrate_skill_ranks(self.config, self.skills_manager)
        self.refresh()

    def _watch_skills_folder(self):
        """Track the skills folder and its files so any change reloads it."""
        paths = {str(self.skills_manager.skills_dir)}
        paths.update(str(file_path) for file_path in self.skills_manager.skill_files())
        # Re-register on every call: Qt silently drops a file's watch when the
        # file is deleted or replaced, so stale bookkeeping must never block
        # a fresh addPath for a path that exists again.
        for path in self._watched_paths - paths:
            self._watcher.removePath(path)
        self._watched_paths.clear()
        for path in paths:
            if self._watcher.addPath(path):
                self._watched_paths.add(path)

    def _on_skills_folder_changed(self):
        # A watched file may have been replaced or deleted, so re-register
        # the current paths before reloading.
        self._watch_skills_folder()
        self._reload_debounce.start()

    @staticmethod
    def _columns_for_width(width: int) -> int:
        return max(1, (width + 12) // 312)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_cards()

    def _arrange_cards(self):
        columns = self._columns_for_width(self._list.width())
        for column in range(self._list_layout.columnCount()):
            self._list_layout.setColumnStretch(column, 0)
        for column in range(columns):
            self._list_layout.setColumnStretch(column, 1)
        for index, card in enumerate(self._cards):
            self._list_layout.removeWidget(card)
            self._list_layout.addWidget(card, index // columns, index % columns)
        if self._empty_state is not None:
            self._list_layout.removeWidget(self._empty_state)
            self._list_layout.addWidget(self._empty_state, 0, 0)

    def refresh(self):
        skill_points = _nonnegative_int(self.config.get("player", "skill_points", 0))
        self._points_label.setText(f"SKILL POINTS: {skill_points}")

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            del item  # the caller owns taken layout items; release them now
            if widget is not None:
                # Detach instead of deleteLater(): these widgets are Python-
                # owned, so dropping their references destroys them safely
                # without deferred C++ deletes.
                widget.setParent(None)
        self._cards.clear()
        self._empty_state = None

        skills = self.skills_manager.load_skills()
        load_errors = self.skills_manager.load_errors
        if load_errors:
            self._error_label.setText("\n".join(load_errors))
            self._error_label.show()
        else:
            self._error_label.clear()
            self._error_label.hide()

        if not skills:
            self._empty_state = QLabel("You have no skills, loser.")
            self._empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_state.setStyleSheet("color: #888; font-size: 16px;")
        else:
            for skill in skills:
                image_path = self.skills_manager.skills_dir / skill["image"]
                card = SkillCard(
                    skill,
                    image_path,
                    lambda current_skill=skill: self._open_skill_tree(current_skill),
                )
                self._cards.append(card)
        self._arrange_cards()
        # Watch any files that appeared so later edits also reload.
        self._watch_skills_folder()

    def _open_skill_tree(self, skill: dict[str, Any]):
        """Open the skill's upgrade tree in its own window, then refresh."""
        dialog = SkillTreeDialog(skill, self.config, self.skills_manager, self)
        dialog.exec()
        self.refresh()
