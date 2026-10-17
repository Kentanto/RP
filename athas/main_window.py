"""
Athas — Main Window.
"""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget, QCheckBox,
)
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from athas.styles import MAIN_QSS, CYAN, BLACK, WHITE, DIFF_COLOURS, mission_card_style
from athas.mission_manager import MissionManager, Mission
from athas.inventory_manager import InventoryManager
from athas.inventory_panel import InventoryPanel
from athas.git_sync import GitSyncWorker
from athas.notification_widget import NotificationWidget
from athas.settings_panel import SettingsPanel
from athas.stats_widget import StatsWidget
from athas.ability_tree_panel import AbilityTreePanel


class HoverButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MissionCard(QFrame):
    def __init__(self, mission: Mission, on_click=None, parent=None):
        super().__init__(parent)
        self.mission = mission
        self.on_click = on_click
        self.setObjectName("MissionCard")
        self.setStyleSheet(mission_card_style(mission.difficulty, mission.completed))
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(2, 4)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        diff = mission.difficulty.upper() if mission.difficulty else "E"
        diff_col = DIFF_COLOURS.get(diff, CYAN)
        badge = QLabel(diff)
        badge.setFixedSize(44, 44)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {diff_col}22;
                border: 2px solid {diff_col};
                border-radius: 22px;
                color: {diff_col};
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(badge)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        title = QLabel(mission.title)
        title_color = "#888888" if mission.completed else "#ffffff"
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {title_color};")
        text_layout.addWidget(title)

        desc = QLabel(mission.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #aaaaaa;")
        text_layout.addWidget(desc)

        reward = QLabel(f"Reward: {mission.reward}")
        reward_col = "#555555" if mission.completed else diff_col
        reward.setStyleSheet(f"font-size: 11px; color: {reward_col}; font-weight: bold;")
        text_layout.addWidget(reward)
        layout.addLayout(text_layout, 1)

        if mission.completed:
            check = QLabel("✓")
            check.setStyleSheet("font-size: 28px; color: #4caf50; font-weight: bold; margin-right: 8px;")
            layout.addWidget(check)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.mission)
        super().mousePressEvent(event)


class MissionDetailView(QFrame):
    """Full overlay panel showing mission story and details."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(5,5,8,240);
                border: 1px solid {CYAN}44;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {WHITE};
            }}
            QPushButton {{
                background-color: {CYAN}11;
                border: 1px solid {CYAN};
                color: {CYAN};
                padding: 8px 18px;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {CYAN};
                color: {BLACK};
            }}
            QCheckBox {{
                background: transparent;
                color: {WHITE};
                font-size: 14px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {CYAN};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CYAN};
                image: none;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        self.mission = None
        self._on_completed_changed = None
        self._on_close = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        header = QHBoxLayout()
        self.diff_badge = QLabel("E")
        self.diff_badge.setFixedSize(50, 50)
        self.diff_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.diff_badge.setStyleSheet("font-size: 20px; font-weight: bold; border-radius: 25px;")
        header.addWidget(self.diff_badge)

        title_layout = QVBoxLayout()
        self.title_label = QLabel("Title")
        self.title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #ffffff;")
        title_layout.addWidget(self.title_label)

        self.reward_label = QLabel("Reward")
        self.reward_label.setStyleSheet(f"font-size: 13px; color: {CYAN};")
        title_layout.addWidget(self.reward_label)
        header.addLayout(title_layout, 1)

        back_btn = HoverButton("← BACK")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {CYAN}44;
                color: {CYAN};
                padding: 6px 14px;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {CYAN}22;
            }}
        """)
        back_btn.clicked.connect(self._close)
        header.addWidget(back_btn)
        layout.addLayout(header)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("font-size: 14px; color: #cccccc; padding-top: 10px;")
        layout.addWidget(self.desc_label)

        story_scroll = QScrollArea()
        story_scroll.setWidgetResizable(True)
        story_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        story_container = QFrame()
        story_layout = QVBoxLayout(story_container)
        story_layout.setContentsMargins(4, 4, 12, 4)
        self.story_label = QLabel("")
        self.story_label.setWordWrap(True)
        self.story_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.story_label.setStyleSheet("font-size: 15px; color: #bbbbbb; line-height: 1.6;")
        story_layout.addWidget(self.story_label)
        story_layout.addStretch()
        story_scroll.setWidget(story_container)
        layout.addWidget(story_scroll, 1)

        self.completed_checkbox = QCheckBox("Mark as Completed")
        self.completed_checkbox.setStyleSheet("font-size: 14px; color: #ffffff; margin-top: 10px;")
        self.completed_checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.completed_checkbox)

        self.file_label = QLabel("")
        self.file_label.setStyleSheet("font-size: 10px; color: #555555; margin-top: 4px;")
        layout.addWidget(self.file_label)
        self.hide()

    def show_mission(self, mission, on_completed_changed, on_close):
        self.mission = mission
        self._on_completed_changed = on_completed_changed
        self._on_close = on_close
        diff = mission.difficulty.upper() if mission.difficulty else "E"
        diff_col = DIFF_COLOURS.get(diff, CYAN)
        self.diff_badge.setText(diff)
        self.diff_badge.setStyleSheet(f"""
            font-size: 20px; font-weight: bold; border-radius: 25px;
            background-color: {diff_col}22;
            border: 2px solid {diff_col};
            color: {diff_col};
        """)
        self.title_label.setText(mission.title)
        self.reward_label.setText(f"Reward: {mission.reward}")
        self.desc_label.setText(mission.description)
        self.story_label.setText(mission.story if mission.story else "No additional story available.")
        self.file_label.setText(f"File: {mission.source_file}")
        self.completed_checkbox.blockSignals(True)
        self.completed_checkbox.setChecked(mission.completed)
        self.completed_checkbox.blockSignals(False)
        self.show()
        self.raise_()

    def _on_checkbox_changed(self, state):
        if self.mission and self._on_completed_changed:
            self.mission.completed = bool(state)
            self._on_completed_changed(self.mission)
        if self.mission.completed:
            self.title_label.setText(self.mission.title + "   ✓")
        else:
            self.title_label.setText(self.mission.title)

    def _close(self):
        self.hide()
        if self._on_close:
            self._on_close()



class MainWindow(QMainWindow):
    def __init__(self, config=None, player: QMediaPlayer | None = None, audio_output: QAudioOutput | None = None):
        super().__init__()
        self.config = config
        self.setWindowTitle("Athas System")
        self.resize(1280, 720)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(MAIN_QSS)

        # Initialise optional members BEFORE building the UI,
        # otherwise _build_content()'s inventory panel gets clobbered.
        self._manager: MissionManager | None = None
        self._inv_manager: InventoryManager | None = None
        self._inv_panel: InventoryPanel | None = None
        self._git_sync: GitSyncWorker | None = None
        self._scan_timer: QTimer | None = None

        self.root = QWidget(self)
        self.setCentralWidget(self.root)
        self._root_layout = QVBoxLayout(self.root)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self.bg_label = QLabel(self.root)
        self.bg_label.setScaledContents(True)
        self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_background()
        self.bg_label.lower()
        self.bg_label.setGeometry(self.root.rect())

        self._ui_overlay = QFrame(self.root)
        self._ui_overlay.setStyleSheet("background: transparent; border: none;")
        overlay_layout = QHBoxLayout(self._ui_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)
        self._root_layout.addWidget(self._ui_overlay)

        sidebar = self._build_sidebar()
        overlay_layout.addWidget(sidebar)

        content = self._build_content()
        overlay_layout.addWidget(content, 1)

        self.notif = NotificationWidget(self.root)
        self.notif.raise_()

        self._settings_panel = SettingsPanel(self.config, audio_output=audio_output, parent=self.root)
        self._settings_panel.hide()
        self._settings_panel.setGeometry(0, 0, self.root.width(), self.root.height())

        self._detail_view = MissionDetailView(self.root)

        self.resizeEvent(None)

        self._player = player
        self._audio_output = audio_output
        self._fade_timer = None
        self._fade_target_duration_ms = 13000

        self._loading_screen = None
        self._last_missions_state = {}

    # ── Idle / Active lifecycle ──

    def _resolve_paths(self):
        rp = Path(__file__).parent.parent
        return rp / "missions", rp / "cache", rp / "items", rp / "library", rp

    def attach_loading_screen(self, loading_screen):
        """Overlay the loading screen and wait for ``finished``."""
        self._loading_screen = loading_screen
        self._loading_screen.setParent(self.root)
        self._loading_screen.setGeometry(self.root.rect())
        self._loading_screen.raise_()
        self._loading_screen.finished.connect(self._on_loading_finished)

    def _on_loading_finished(self):
        """Remove overlay and wake up background logic."""
        if self._loading_screen:
            self._loading_screen.deleteLater()
            self._loading_screen = None
        self._start_background_tasks()

    def show_without_loading_screen(self):
        """Start background tasks immediately when loading screen is disabled."""
        self._start_background_tasks()
    def _start_background_tasks(self):
        """Start scanning, git sync, and timers."""
        missions_dir, cache_dir, items_dir, library_dir, rp = self._resolve_paths()
        cache_dir.mkdir(exist_ok=True)
        self._manager = MissionManager(
            missions_dir=str(missions_dir),
            cache_path=str(cache_dir / "seen_missions.json"),
            on_new_mission=self._on_new_mission,
        )
        self._inv_manager = InventoryManager(
            items_dir=str(items_dir),
            library_dir=str(library_dir),
            cache_dir=str(cache_dir),
            rp_root=str(rp),
        )
        if self._inv_panel is not None:
            self._inv_panel.inv_manager = self._inv_manager
            self._inv_panel.refresh()
        if self.config.get("git_sync", "enabled", True):
            self._git_sync = GitSyncWorker(
                repo_path=str(rp),
                missions_dir=str(missions_dir),
                items_dir=str(items_dir),
                interval_ms=int(self.config.get("git_sync", "interval_ms", 15000)),
            )
            self._git_sync.pull_complete.connect(self._on_git_pull)
            self._git_sync.new_files_detected.connect(self._on_new_files)
            self._git_sync.start()
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._scan_missions)
        self._scan_timer.start(5000)
        self._scan_missions()

    def _refresh_sidebar_player(self):
        """Keep the sidebar rank/level line in sync with the config."""
        rank = self.config.get("player", "rank", "E")
        level = self.config.get("player", "level", 1)
        if isinstance(level, float) and level.is_integer():
            level = int(level)
        self._sidebar_player_lbl.setText(f"Rank: {rank}\nLevel: {level}")

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(5,5,8,200);
                border-right: 2px solid {CYAN}22;
            }}
        """)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 24, 16, 24)
        sb_layout.setSpacing(16)

        sys_title = QLabel("ATHAS")
        sys_title.setStyleSheet(f"color: {CYAN}; font-size: 20px; font-weight: bold; letter-spacing: 4px;")
        sb_layout.addWidget(sys_title)

        self._sidebar_player_lbl = QLabel()
        self._sidebar_player_lbl.setStyleSheet("color: #888; font-size: 12px;")
        sb_layout.addWidget(self._sidebar_player_lbl)
        self._refresh_sidebar_player()

        sb_layout.addSpacing(20)

        self._nav_buttons = {}
        for label in ["DASHBOARD", "MISSIONS", "INVENTORY", "SETTINGS"]:
            btn = HoverButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    color: {WHITE};
                    padding: 10px 12px;
                    text-align: left;
                    font-size: 13px;
                    letter-spacing: 2px;
                }}
                QPushButton:hover {{
                    background-color: rgba(0,240,255,10);
                    border-left: 3px solid {CYAN};
                    color: {CYAN};
                }}
            """)
            if label == "DASHBOARD":
                btn.clicked.connect(lambda _=None: self._show_page(0))
            elif label == "MISSIONS":
                btn.clicked.connect(lambda _=None: self._show_page(1))
            elif label == "INVENTORY":
                btn.clicked.connect(lambda _=None: self._show_page(2))
            elif label == "SETTINGS":
                btn.clicked.connect(self._toggle_settings)
            sb_layout.addWidget(btn)
            self._nav_buttons[label] = btn

        sb_layout.addStretch()

        self.git_status = QLabel("Git: Standby")
        self.git_status.setStyleSheet("color: #555; font-size: 10px;")
        sb_layout.addWidget(self.git_status)
        return sidebar


    def _build_content(self):
        self._content_pages = QStackedWidget()
        self._content_pages.setStyleSheet("background: transparent; border: none;")

        # ── Page 0 : DASHBOARD / Stats ──
        self._stats_widget = StatsWidget(self.config)
        self._content_pages.addWidget(self._stats_widget)

        # ── Page 1 : MISSIONS ──
        missions_page = QFrame()
        missions_page.setStyleSheet("background: transparent; border: none;")
        m_layout = QVBoxLayout(missions_page)
        m_layout.setContentsMargins(32, 32, 32, 32)
        m_layout.setSpacing(20)

        header = QLabel("AVAILABLE QUESTS")
        header.setStyleSheet(f"""
            color: {WHITE};
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        m_layout.addWidget(header)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        m_layout.addWidget(line)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.missions_container = QFrame()
        self.missions_layout = QVBoxLayout(self.missions_container)
        self.missions_layout.setSpacing(12)
        self.missions_layout.setContentsMargins(0, 0, 8, 0)
        self.missions_layout.addStretch()
        scroll.setWidget(self.missions_container)
        m_layout.addWidget(scroll)

        self.pull_btn = HoverButton("SYNC WITH REMOTE")
        self.pull_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CYAN}11;
                border: 1px solid {CYAN};
                color: {CYAN};
                padding: 10px 24px;
                border-radius: 2px;
                font-size: 12px;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background-color: {CYAN};
                color: {BLACK};
            }}
        """)
        self.pull_btn.clicked.connect(self._manual_pull)
        m_layout.addWidget(self.pull_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self._content_pages.addWidget(missions_page)

        # ── Page 2 : INVENTORY ──
        self._inv_panel = InventoryPanel(inv_manager=None, parent=None)
        self._content_pages.addWidget(self._inv_panel)

        # ── Page 3 : ABILITY TREE ──
        self._ability_panel = AbilityTreePanel(self.config, on_back=lambda: self._show_page(0))
        self._content_pages.addWidget(self._ability_panel)
        self._stats_widget.abilities_clicked.connect(lambda: self._show_page(3))

        return self._content_pages

    def _show_page(self, index: int):
        """Switch the content area between pages."""
        if self._settings_panel.isVisible():
            self._settings_panel.hide()
        self._content_pages.setCurrentIndex(index)
        if index == 0:
            self._refresh_sidebar_player()
            self._stats_widget.refresh()
        for i, (label, btn) in enumerate(self._nav_buttons.items()):
            if label == "SETTINGS":
                continue
            if i == index:
                btn.setStyleSheet(btn.styleSheet() + f"color: {CYAN}; border-left: 3px solid {CYAN};")
            else:
                btn.setStyleSheet(btn.styleSheet().replace(f"color: {CYAN}; border-left: 3px solid {CYAN};", ""))

    def _toggle_settings(self):
        if self._settings_panel.isVisible():
            self._settings_panel.hide()
            self._content_pages.setCurrentIndex(0)
        else:
            self._content_pages.setCurrentIndex(0)
            w = int(self.root.width() * 0.7)
            h = int(self.root.height() * 0.7)
            x = (self.root.width() - w) // 2
            y = (self.root.height() - h) // 2
            self._settings_panel.setGeometry(x, y, w, h)
            self._settings_panel.show()
            self._settings_panel.raise_()


    def _load_background(self):
        bg_path = Path(__file__).parent.parent / "icons" / "background_menu.png"
        if bg_path.exists():
            self.bg_pixmap = QPixmap(str(bg_path))
            self.bg_label.setPixmap(self.bg_pixmap)
        else:
            self.bg_label.setStyleSheet(f"background-color: {BLACK};")
            self.bg_pixmap = None

    def resizeEvent(self, event):
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.root.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.bg_label.setPixmap(scaled)
        self.bg_label.setGeometry(self.root.rect())
        self._ui_overlay.setGeometry(self.root.rect())
        self.notif.reposition(QPoint(self.root.width(), 0))
        if hasattr(self, "_detail_view"):
            self._detail_view.setGeometry(self.root.rect())
        super().resizeEvent(event)

    def _scan_missions(self):
        if self._manager is None:
            return
        missions = self._manager.scan()
        current_state = {
            m.source_file: {"completed": m.completed, "difficulty": m.difficulty}
            for m in missions
        }
        if current_state != getattr(self, "_last_missions_state", {}):
            self._rebuild_missions(missions)
            self._last_missions_state = current_state

    def _rebuild_missions(self, missions):
        while self.missions_layout.count() > 1:
            item = self.missions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not missions:
            empty = QLabel("No active quests. Sync to fetch new missions.")
            empty.setStyleSheet("color: #555; font-size: 14px; padding: 20px;")
            self.missions_layout.insertWidget(0, empty)
            return

        diff_order = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
        missions.sort(key=lambda m: (m.completed, diff_order.get(m.difficulty.upper(), 99), m.title))

        for mission in missions:
            card = MissionCard(mission, on_click=self._open_mission_detail)
            self.missions_layout.insertWidget(self.missions_layout.count() - 1, card)

    def _open_mission_detail(self, mission: Mission):
        self._detail_view.show_mission(
            mission,
            on_completed_changed=self._on_mission_completed_changed,
            on_close=lambda: self._detail_view.hide(),
        )
        self._detail_view.setGeometry(self.root.rect())
        self._detail_view.show()
        self._detail_view.raise_()

    def _on_mission_completed_changed(self, mission: Mission):
        if self._manager is not None:
            self._manager.save_mission(mission)
        self._scan_missions()

    def _on_new_mission(self, mission: Mission):
        if not self.config.get("notifications", "enabled", True):
            return
        self.notif.show_notification(
            title=mission.title,
            description=mission.description,
            difficulty=mission.difficulty,
            duration_ms=int(self.config.get("notifications", "duration_ms", 8000)),
        )

    def _on_git_pull(self, success: bool, msg: str):
        if success:
            self.git_status.setText("Git: Synced")
            self.git_status.setStyleSheet("color: #4caf50; font-size: 10px;")
        else:
            self.git_status.setText(f"Git: {msg[:40]}...")
            self.git_status.setStyleSheet("color: #ff9800; font-size: 10px;")

    def _on_new_files(self, files: list):
        self._scan_missions()
        if self._inv_panel is not None:
            self._inv_panel.refresh()

    def _manual_pull(self):
        if self._git_sync is None:
            return
        self.pull_btn.setText("SYNCING...")
        self.pull_btn.setEnabled(False)
        self._git_sync.force_pull()
        QTimer.singleShot(1500, lambda: (
            self.pull_btn.setText("SYNC WITH REMOTE"),
            self.pull_btn.setEnabled(True),
        ))

    def set_media_player(self, player: QMediaPlayer, audio_output: QAudioOutput):
        self._player = player
        self._audio_output = audio_output

    def fade_out_music(self):
        if self._fade_timer is not None:
            self._fade_timer.stop()
        self._fade_steps = getattr(self, "_fade_target_duration_ms", 13000) // 100
        self._volume_drop = 0.1 / self._fade_steps
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._step_fade)
        self._fade_timer.start(100)

    def _step_fade(self):
        if self._audio_output is None:
            self._fade_timer.stop()
            return
        new_vol = max(0.0, self._audio_output.volume() - self._volume_drop)
        self._audio_output.setVolume(new_vol)
        if new_vol <= 0.0:
            self._audio_output.setVolume(0.0)
            self._fade_timer.stop()
            if self._player is not None:
                self._player.stop()

    def closeEvent(self, event):
        if self._git_sync is not None:
            self._git_sync.stop()
        if self._scan_timer is not None:
            self._scan_timer.stop()
        if self._fade_timer is not None:
            self._fade_timer.stop()
        if self._player is not None:
            self._player.stop()
        super().closeEvent(event)

