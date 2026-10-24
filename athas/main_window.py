"""
Athas — Main Window.
"""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGraphicsDropShadowEffect,
    QStackedWidget,
)
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from athas.styles import MAIN_QSS, CYAN, BLACK, WHITE, DIFF_COLOURS, mission_card_style
from athas.mission_manager import MissionManager, Mission
from athas.inventory_manager import InventoryManager
from athas.inventory_panel import InventoryPanel
from athas.shop_panel import ShopPanel
from athas.detailed_stats import DetailedStatsPanel
from athas.git_sync import GitSyncWorker
from athas.backup_manager import BackupManager, BACKUP_INTERVAL_MS
from athas.notification_widget import NotificationWidget
from athas.reward_popup import RewardPopup
from athas.drop_manager import DropManager
from athas.detailed_stats import collect_temp_points
from athas import equip
from athas.settings_panel import SettingsPanel
from athas.stats_widget import LEVEL_PERM_BONUS, LEVEL_TEMP_BONUS, StatsWidget
from athas.ability_tree_panel import AbilityTreePanel
from athas.skills_manager import SkillManager
from athas.skills_panel import SkillsPanel
from athas import audio


class HoverButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Every hover button clicks and hovers audibly.
        self.clicked.connect(lambda _=False: audio.play("click"))

    def enterEvent(self, event):
        audio.play("hover")
        super().enterEvent(event)


class MissionCard(QFrame):
    def __init__(self, mission: Mission, on_click=None, parent=None, zoom: float = 1.0):
        super().__init__(parent)
        self.mission = mission
        self.on_click = on_click
        self.setObjectName("MissionCard")
        self.setStyleSheet(mission_card_style(mission.difficulty, mission.completed))
        # zoom scales every element so the cards stay readable at any
        # display scaling (1.0 = default size)
        z = max(0.5, float(zoom))
        self.setMinimumHeight(int(100 * z))
        self.setMaximumHeight(int(140 * z))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(2, 4)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(int(16 * z), int(12 * z), int(16 * z), int(12 * z))
        layout.setSpacing(int(16 * z))

        diff = mission.difficulty.upper() if mission.difficulty else "E"
        diff_col = DIFF_COLOURS.get(diff, CYAN)
        badge = QLabel(diff)
        badge.setFixedSize(int(44 * z), int(44 * z))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {diff_col}22;
                border: 2px solid {diff_col};
                border-radius: {int(22 * z)}px;
                color: {diff_col};
                font-size: {max(8, int(18 * z))}px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(badge)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(int(4 * z))
        title = QLabel(mission.title)
        title.setStyleSheet(f"font-size: {max(8, int(16 * z))}px; font-weight: bold; color: #ffffff;")
        text_layout.addWidget(title)

        desc = QLabel(mission.description)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: {max(7, int(12 * z))}px; color: #aaaaaa;")
        text_layout.addWidget(desc)

        reward = QLabel(f"Reward: {mission.reward}")
        reward.setStyleSheet(f"font-size: {max(7, int(11 * z))}px; color: {diff_col}; font-weight: bold;")
        text_layout.addWidget(reward)
        layout.addLayout(text_layout, 1)

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
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        self.mission = None
        self._on_close = None
        self._zoom = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        header = QHBoxLayout()
        self.diff_badge = QLabel("E")
        self.diff_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.diff_badge)

        title_layout = QVBoxLayout()
        self.title_label = QLabel("Title")
        title_layout.addWidget(self.title_label)

        self.reward_label = QLabel("Reward")
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
        story_layout.addWidget(self.story_label)
        story_layout.addStretch()
        story_scroll.setWidget(story_container)
        layout.addWidget(story_scroll, 1)

        self.file_label = QLabel("")
        layout.addWidget(self.file_label)
        self.hide()

        self.set_zoom(1.0)

    def set_zoom(self, zoom: float):
        """Scale the detail view's fonts and elements so the text stays
        readable at any display scaling (1.0 = default size)."""
        z = max(0.5, float(zoom))
        self._zoom = z
        badge_px = int(50 * z)
        self.diff_badge.setFixedSize(badge_px, badge_px)
        self.title_label.setStyleSheet(f"font-size: {max(9, int(26 * z))}px; font-weight: bold; color: #ffffff;")
        self.reward_label.setStyleSheet(f"font-size: {max(8, int(13 * z))}px; color: {CYAN};")
        self.desc_label.setStyleSheet(f"font-size: {max(8, int(14 * z))}px; color: #cccccc; padding-top: 10px;")
        self.story_label.setStyleSheet(f"font-size: {max(8, int(15 * z))}px; color: #bbbbbb; line-height: 1.6;")
        self.file_label.setStyleSheet(f"font-size: {max(7, int(10 * z))}px; color: #555555; margin-top: 4px;")

    def show_mission(self, mission, on_close):
        self.mission = mission
        self._on_close = on_close
        diff = mission.difficulty.upper() if mission.difficulty else "E"
        diff_col = DIFF_COLOURS.get(diff, CYAN)
        z = self._zoom
        self.diff_badge.setText(diff)
        self.diff_badge.setStyleSheet(f"""
            font-size: {max(8, int(20 * z))}px; font-weight: bold; border-radius: {int(25 * z)}px;
            background-color: {diff_col}22;
            border: 2px solid {diff_col};
            color: {diff_col};
        """)
        self.title_label.setText(mission.title)
        self.reward_label.setText(f"Reward: {mission.reward}")
        self.desc_label.setText(mission.description)
        self.story_label.setText(mission.story if mission.story else "No additional story available.")
        self.file_label.setText(f"File: {mission.source_file}")
        self.show()
        self.raise_()

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
        self._skills_manager: SkillManager | None = None
        self._inv_panel: InventoryPanel | None = None
        self._shop_panel: ShopPanel | None = None
        self._git_sync: GitSyncWorker | None = None
        self._scan_timer: QTimer | None = None
        self._backup_manager: BackupManager | None = None
        self._backup_timer: QTimer | None = None

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

        # Drops-folder reward popup (2-second close lockout).
        self._drop_manager: DropManager | None = None
        self._drop_timer: QTimer | None = None
        self.reward_popup = RewardPopup(self.root)
        self.reward_popup.reposition(self.root.rect())
        self.reward_popup.raise_()

        self._settings_panel = SettingsPanel(self.config, audio_output=audio_output, parent=self.root)
        self._settings_panel.hide()
        self._settings_panel.setGeometry(0, 0, self.root.width(), self.root.height())

        self._detail_view = MissionDetailView(self.root)

        self.resizeEvent(None)

        self._player = player
        self._audio_output = audio_output
        self._fade_timer = None
        self._fade_target_duration_ms = 13000

        # The shared SFX player follows the audio settings from here on.
        if config is not None:
            audio.player.set_config(config)

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
            completed_dir=str(rp / "completed_missions"),
            on_new_mission=self._on_new_mission,
            on_completed_mission=self._on_mission_completed,
            on_uncompleted_rewards=self._on_mission_uncompleted,
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
        if self._shop_panel is not None:
            self._shop_panel.inv_manager = self._inv_manager
            self._shop_panel.refresh()
        if getattr(self, "_details_panel", None) is not None:
            self._details_panel.inv_manager = self._inv_manager
            self._details_panel.refresh()
        if self.config.get("git_sync", "enabled", True):
            folders = self.config.get(
                "git_sync", "folders",
                "missions,completed_missions,items,icons,cache,skills,library,shop",
            )
            sync_paths = [p.strip() for p in str(folders).split(",") if p.strip()]
            # The completed-missions folder is part of the mission pipeline —
            # always sync it alongside the active missions folder.
            if "missions" in sync_paths and "completed_missions" not in sync_paths:
                sync_paths.append("completed_missions")
            for required_path in ("missions", "completed_missions", "cache", "skills", "library", "shop"):
                if required_path not in sync_paths:
                    sync_paths.append(required_path)
            self._git_sync = GitSyncWorker(
                repo_path=str(rp),
                sync_paths=sync_paths,
                interval_ms=int(self.config.get("git_sync", "interval_ms", 15000)),
            )
            self._git_sync.pull_complete.connect(self._on_git_pull)
            self._git_sync.new_files_detected.connect(self._on_new_files)
            self._git_sync.start()
        # Back up every JSON data file (plus the inventory db) once at
        # startup, then create a fresh backup folder every 30 minutes.
        # Folders older than 30 days are pruned inside create_backup().
        self._backup_manager = BackupManager(root=rp)
        self._backup_manager.create_backup()
        self._backup_timer = QTimer(self)
        self._backup_timer.timeout.connect(self._backup_manager.create_backup)
        self._backup_timer.start(BACKUP_INTERVAL_MS)

        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._scan_missions)
        self._scan_timer.start(5000)
        self._scan_missions()

        # Drops folder — local hand-outs (git-ignored, never uploaded).
        # The stat bars count the temp points granted by equipped artifacts.
        self._drop_manager = DropManager(rp / "drops")
        self._stats_widget.set_temp_bonus_provider(self._equipped_temp_points)
        self._drop_timer = QTimer(self)
        self._drop_timer.timeout.connect(self._process_drops)
        self._drop_timer.start(2000)
        self._process_drops()

    def _refresh_sidebar_player(self):
        """Keep the sidebar rank/level line in sync with the config."""
        rank = self.config.get("player", "rank", "E")
        level = self.config.get("player", "level", 1)
        if isinstance(level, float) and level.is_integer():
            level = int(level)
        gold = self.config.get("player", "gold", 0)
        try:
            gold = int(gold)
        except (TypeError, ValueError):
            gold = 0
        self._sidebar_player_lbl.setText(f"Rank: {rank}\nLevel: {level}\nGold: {gold}")

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
        for label in ["DASHBOARD", "MISSIONS", "INVENTORY", "SHOP", "SETTINGS"]:
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
            elif label == "SHOP":
                btn.clicked.connect(lambda _=None: self._show_page(5))
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

        header_row = QHBoxLayout()
        header = QLabel("AVAILABLE QUESTS")
        header.setStyleSheet(f"""
            color: {WHITE};
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addLayout(self._build_zoom_controls())
        m_layout.addLayout(header_row)

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
        self._inv_panel = InventoryPanel(inv_manager=None, config=self.config)
        self._inv_panel.gold_changed.connect(self._on_gold_changed)
        self._inv_panel.stats_changed.connect(self._on_stats_changed)
        self._content_pages.addWidget(self._inv_panel)

        # ── Page 3 : ABILITY TREE ──
        self._ability_panel = AbilityTreePanel(self.config, on_back=self._back_to_dashboard)
        self._content_pages.addWidget(self._ability_panel)
        self._skills_manager = SkillManager(Path(__file__).parent.parent / "skills")
        self._skills_panel = SkillsPanel(self.config, self._skills_manager)
        self._content_pages.addWidget(self._skills_panel)
        self._stats_widget.abilities_clicked.connect(lambda: self._show_page(3))
        self._stats_widget.skills_clicked.connect(self._show_skills)

        # ── Page 5 : SHOP ──
        self._shop_panel = ShopPanel(self.config, None)
        self._shop_panel.gold_changed.connect(self._refresh_sidebar_player)
        self._content_pages.addWidget(self._shop_panel)

        # ── Page 6 : DETAILED STATS ──
        self._details_panel = DetailedStatsPanel(
            self.config, None, on_back=self._back_to_dashboard,
        )
        self._stats_widget.details_clicked.connect(self._show_details)
        self._content_pages.addWidget(self._details_panel)

        return self._content_pages

    def _show_skills(self):
        self._skills_panel.refresh()
        self._show_page(4)

    def _show_details(self):
        if self._details_panel is not None:
            self._details_panel.refresh()
        self._show_page(6)

    def _back_to_dashboard(self):
        """Return to the dashboard from a detail page — audibly."""
        audio.play("back")
        self._show_page(0)

    def _show_page(self, index: int):
        """Switch the content area between pages."""
        if self._settings_panel.isVisible():
            self._settings_panel.hide()
        self._content_pages.setCurrentIndex(index)
        if index == 0:
            self._refresh_sidebar_player()
            self._stats_widget.refresh()
        elif index == 5 and self._shop_panel is not None:
            self._shop_panel.refresh()
        elif index == 6 and getattr(self, "_details_panel", None) is not None:
            self._details_panel.refresh()
        page_by_label = {"DASHBOARD": 0, "MISSIONS": 1, "INVENTORY": 2, "SHOP": 5}
        for label, btn in self._nav_buttons.items():
            if label == "SETTINGS":
                continue
            if page_by_label.get(label) == index:
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
        self.reward_popup.reposition(self.root.rect())
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

    # ── Mission zoom ──

    @staticmethod
    def _clamp_zoom(value) -> float:
        """Keep a zoom factor inside the supported range."""
        try:
            z = float(value)
        except (TypeError, ValueError):
            return 1.0
        return max(0.6, min(2.0, round(z, 2)))

    def _build_zoom_controls(self) -> QHBoxLayout:
        """- / + / RESET buttons that scale the mission cards (saved in config)."""
        self._missions_zoom = self._clamp_zoom(self.config.get("missions", "zoom", 1.0))

        row = QHBoxLayout()
        row.setSpacing(6)

        zoom_lbl = QLabel("ZOOM")
        zoom_lbl.setStyleSheet(f"color: {CYAN}; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        row.addWidget(zoom_lbl)

        btn_style = f"""
            QPushButton {{
                background-color: {CYAN}11;
                border: 1px solid {CYAN}44;
                color: {CYAN};
                padding: 4px 12px;
                border-radius: 2px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {CYAN}33;
            }}
            QPushButton:pressed {{
                background-color: {CYAN}55;
            }}
        """
        self.zoom_out_btn = HoverButton("-")
        self.zoom_out_btn.setStyleSheet(btn_style)
        self.zoom_out_btn.clicked.connect(lambda: self._set_missions_zoom(self._missions_zoom - 0.1))
        row.addWidget(self.zoom_out_btn)

        self._zoom_percent_lbl = QLabel(f"{int(round(self._missions_zoom * 100))}%")
        self._zoom_percent_lbl.setStyleSheet(f"color: {WHITE}; font-size: 12px; padding: 0 4px;")
        self._zoom_percent_lbl.setMinimumWidth(44)
        self._zoom_percent_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._zoom_percent_lbl)

        self.zoom_in_btn = HoverButton("+")
        self.zoom_in_btn.setStyleSheet(btn_style)
        self.zoom_in_btn.clicked.connect(lambda: self._set_missions_zoom(self._missions_zoom + 0.1))
        row.addWidget(self.zoom_in_btn)

        reset_btn = HoverButton("RESET")
        reset_btn.setStyleSheet(btn_style)
        reset_btn.clicked.connect(lambda: self._set_missions_zoom(1.0))
        row.addWidget(reset_btn)

        return row

    def _set_missions_zoom(self, zoom: float):
        """Apply (and persist) a new zoom level for the missions tab."""
        z = self._clamp_zoom(zoom)
        if z == self._missions_zoom:
            return
        self._missions_zoom = z
        self.config.set("missions", "zoom", z)
        self._zoom_percent_lbl.setText(f"{int(round(z * 100))}%")
        if self._detail_view.isVisible():
            self._detail_view.set_zoom(z)
        # force the mission cards to rebuild at the new size
        self._last_missions_state = {}
        self._scan_missions()

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
            card = MissionCard(mission, on_click=self._open_mission_detail, zoom=self._missions_zoom)
            self.missions_layout.insertWidget(self.missions_layout.count() - 1, card)

    def _open_mission_detail(self, mission: Mission):
        self._detail_view.set_zoom(self._missions_zoom)
        self._detail_view.show_mission(
            mission,
            on_close=lambda: self._detail_view.hide(),
        )
        self._detail_view.setGeometry(self.root.rect())
        self._detail_view.show()
        self._detail_view.raise_()

    def _add_gold(self, amount: int):
        """Credit gold to the player and refresh every gold display."""
        try:
            current = int(self.config.get("player", "gold", 0) or 0)
        except (TypeError, ValueError):
            current = 0
        self.config.set("player", "gold", max(0, current) + max(0, amount))
        self._refresh_sidebar_player()
        if self._shop_panel is not None:
            self._shop_panel.refresh_gold()

    # ── Workshop / equip side effects ──
    def _on_gold_changed(self):
        """Gold spent or earned inside the inventory panel."""
        self._refresh_sidebar_player()
        if self._shop_panel is not None:
            self._shop_panel.refresh_gold()

    def _on_stats_changed(self):
        """The equipped loadout changed — recompute every stat display."""
        self._stats_widget.refresh()
        if getattr(self, "_details_panel", None) is not None:
            self._details_panel.refresh()

    def _equipped_temp_points(self) -> int:
        """Temp points granted by the currently equipped artifacts."""
        if self._inv_manager is None:
            return 0
        equipped = self.inv_manager_equipped()
        return collect_temp_points(equipped)

    def inv_manager_equipped(self):
        ids = equip.equipped_ids(self.config)
        return self._inv_manager.get_equipped_artifacts(ids)

    # ── Drops folder ──
    def _process_drops(self):
        """Apply every drop file found in drops/ and show the reward popup."""
        if self._drop_manager is None:
            return
        grants = self._drop_manager.collect()
        for grant in grants:
            self._apply_drop(grant)

    def _apply_drop(self, grant: dict):
        summary: list = []
        gold = int(grant.get("gold", 0) or 0)
        if gold > 0:
            self._add_gold(gold)
            summary.append(f"+{gold} gold")
        xp = int(grant.get("xp", 0) or 0)
        levels = 0
        if xp > 0:
            levels = self._stats_widget.grant_xp(xp)
            self._refresh_sidebar_player()
            summary.append(f"+{xp} XP")
        skill_points = int(grant.get("skill_points", 0) or 0)
        if skill_points > 0:
            self._stats_widget.grant_skill_points(skill_points)
            if self._skills_panel is not None:
                self._skills_panel.refresh()
            summary.append(f"+{skill_points} skill point{'s' if skill_points != 1 else ''}")
        con_points = int(grant.get("constellation_points", 0) or 0)
        if con_points > 0:
            points = self.config.get("player", "constellation_points", 0)
            self.config.set("player", "constellation_points", max(0, points) + con_points)
            if self._ability_panel is not None:
                self._ability_panel.refresh_points()
            summary.append(f"+{con_points} constellation point{'s' if con_points != 1 else ''}")
        temp_points = int(grant.get("temp_points", 0) or 0)
        if temp_points > 0:
            self._stats_widget.grant_bonus_temp_points(temp_points)
            summary.append(f"+{temp_points} temp point{'s' if temp_points != 1 else ''}")
        perm_points = int(grant.get("perm_points", 0) or 0)
        if perm_points > 0:
            perm = max(0, int(self.config.get("player", "perm_points", 0) or 0))
            self.config.set("player", "perm_points", perm + perm_points)
            self._stats_widget.refresh()
            summary.append(f"+{perm_points} permanent point{'s' if perm_points != 1 else ''}")
        loot_lines: list = []
        artifact_reward = int(grant.get("artifact_reward", 0) or 0)
        if artifact_reward > 0 and self._inv_manager is not None:
            rarity = str(grant.get("artifact_rarity") or "").strip() or None
            artifacts = self._inv_manager.generate_artifacts(
                count=artifact_reward, rarity=rarity, source="drop",
            )
            for artifact in artifacts:
                loot_lines.append(f"ARTIFACT ACQUIRED - {artifact.name} ({artifact.rarity})")
            if self._inv_panel is not None:
                self._inv_panel.refresh()
        if levels > 0:
            summary.append(f"LEVEL UP - Level {self.config.get('player', 'level', 1)}")

        notification = grant.get("notification") or {}
        title = str(notification.get("title") or "SYSTEM REWARD")
        lines = []
        message = str(notification.get("message") or "").strip()
        if message:
            lines.append(message)
        if summary:
            lines.append("  ".join(summary))
        lines.extend(loot_lines)
        if not lines:
            lines.append("The System acknowledged a drop file - nothing was granted.")
        self.reward_popup.show_message(title, "  |  ".join(lines))
        audio.play("reward")
        if levels > 0:
            audio.play("level_up")

    def _on_mission_completed(self, mission: Mission):
        """The author marked a mission as done — grant its rewards once.

        Returns the ids of the artifacts granted so the credit record can
        revoke them if the completion is ever undone."""
        levels_gained = 0
        if mission.xp > 0:
            levels_gained = self._stats_widget.grant_xp(mission.xp)
            self._refresh_sidebar_player()
        if mission.skill_points > 0:
            self._stats_widget.grant_skill_points(mission.skill_points)
            self._skills_panel.refresh()
        if mission.constellation_points > 0:
            points = self.config.get("player", "constellation_points", 0)
            self.config.set("player", "constellation_points", max(0, points) + mission.constellation_points)
            self._ability_panel.refresh_points()
        if mission.gold > 0:
            self._add_gold(mission.gold)
        granted_ids: list = []
        loot_lines: list = []
        if mission.artifact_reward > 0 and self._inv_manager is not None:
            artifacts = self._inv_manager.generate_artifacts(
                count=mission.artifact_reward,
                rarity=mission.artifact_rarity or None,
                difficulty=mission.difficulty,
                source="mission",
            )
            for artifact in artifacts:
                granted_ids.append(int(artifact.uid.split(":", 1)[1]))
                loot_lines.append(f"  ARTIFACT ACQUIRED — {artifact.name} ({artifact.rarity}).")
            if self._inv_panel is not None:
                self._inv_panel.refresh()
        if not self.config.get("notifications", "enabled", True):
            return granted_ids
        audio.play("mission_complete")
        if levels_gained > 0:
            audio.play("level_up")
        description = f"Reward: {mission.reward}" if mission.reward else "The System acknowledges your success."
        if mission.gold > 0:
            description += f"  +{mission.gold} gold."
        description += "".join(loot_lines)
        if levels_gained > 0:
            temp_gain = LEVEL_TEMP_BONUS * levels_gained
            perm_gain = LEVEL_PERM_BONUS * levels_gained
            description += (
                f"  LEVEL UP — Level {self.config.get('player', 'level', 1)}!"
                f"  +{temp_gain} temp point{'s' if temp_gain != 1 else ''},"
                f" +{perm_gain} permanent point{'s' if perm_gain != 1 else ''}."
            )
        self.notif.show_notification(
            title=mission.title,
            description=description,
            difficulty=mission.difficulty,
            duration_ms=int(self.config.get("notifications", "duration_ms", 8000)),
            header="MISSION COMPLETED",
        )
        return granted_ids

    def _on_mission_uncompleted(self, mission: Mission, rewards: dict):
        """Revoke the numeric rewards previously granted for a mission."""
        xp = rewards.get("xp", 0)
        skill_points = rewards.get("skill_points", 0)
        constellation_points = rewards.get("constellation_points", 0)
        if xp > 0:
            self._stats_widget.remove_xp(xp)
            self._refresh_sidebar_player()
        if skill_points > 0:
            self._stats_widget.remove_skill_points(skill_points)
            self._skills_panel.refresh()
        if constellation_points > 0:
            points = self.config.get("player", "constellation_points", 0)
            self.config.set("player", "constellation_points", max(0, points - constellation_points))
            self._ability_panel.refresh_points()
        gold = rewards.get("gold", 0)
        if gold > 0:
            try:
                current = int(self.config.get("player", "gold", 0) or 0)
            except (TypeError, ValueError):
                current = 0
            self.config.set("player", "gold", max(0, current - gold))
            self._refresh_sidebar_player()
            if self._shop_panel is not None:
                self._shop_panel.refresh_gold()
        artifact_ids = rewards.get("artifact_ids") or []
        if artifact_ids and self._inv_manager is not None:
            clean_ids = [
                value for value in artifact_ids
                if isinstance(value, int) and not isinstance(value, bool)
            ]
            self._inv_manager.delete_artifacts(artifact_ids)
            # Revoked artifacts leave the equip slots too.
            equip.prune_equipped(self.config, clean_ids)
            self._on_stats_changed()
            if self._inv_panel is not None:
                self._inv_panel.refresh()

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
        if self._shop_panel is not None:
            self._shop_panel.refresh()

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
        if self._drop_timer is not None:
            self._drop_timer.stop()
        if self._backup_timer is not None:
            self._backup_timer.stop()
        if self._fade_timer is not None:
            self._fade_timer.stop()
        if self._player is not None:
            self._player.stop()
        super().closeEvent(event)
