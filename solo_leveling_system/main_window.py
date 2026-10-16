"""
Solo Leveling System — Main Window.
"""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QPixmap, QColor

from solo_leveling_system.styles import MAIN_QSS, CYAN, BLACK, WHITE, DIFF_COLOURS, mission_card_style
from solo_leveling_system.mission_manager import MissionManager, Mission
from solo_leveling_system.git_sync import GitSyncWorker
from solo_leveling_system.notification_widget import NotificationWidget


class HoverButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MissionCard(QFrame):
    def __init__(self, mission: Mission, parent=None):
        super().__init__(parent)
        self.setObjectName("MissionCard")
        self.setStyleSheet(mission_card_style(mission.difficulty))
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
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
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        text_layout.addWidget(title)

        desc = QLabel(mission.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #aaaaaa;")
        text_layout.addWidget(desc)

        reward = QLabel(f"Reward: {mission.reward}")
        reward.setStyleSheet(f"font-size: 11px; color: {diff_col}; font-weight: bold;")
        text_layout.addWidget(reward)
        layout.addLayout(text_layout, 1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System — Solo Leveling")
        self.resize(1280, 720)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(MAIN_QSS)

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

        self.overlay = QFrame(self.root)
        self.overlay.setStyleSheet("background: transparent; border: none;")
        overlay_layout = QHBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)
        self._root_layout.addWidget(self.overlay)

        sidebar = self._build_sidebar()
        overlay_layout.addWidget(sidebar)

        content = self._build_content()
        overlay_layout.addWidget(content, 1)

        self.notif = NotificationWidget(self.root)
        self.notif.raise_()

        rp = Path(__file__).parent.parent
        self.missions_dir = rp / "missions"
        self.cache_dir = rp / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        self.manager = MissionManager(
            missions_dir=str(self.missions_dir),
            cache_path=str(self.cache_dir / "seen_missions.json"),
            on_new_mission=self._on_new_mission,
        )

        self.git_sync = GitSyncWorker(
            repo_path=str(rp),
            missions_dir=str(self.missions_dir),
            interval_ms=15000,
        )
        self.git_sync.pull_complete.connect(self._on_git_pull)
        self.git_sync.new_files_detected.connect(self._on_new_files)

        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._scan_missions)
        self.scan_timer.start(5000)

        self._scan_missions()
        self.git_sync.start()
        self.resizeEvent(None)

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

        sys_title = QLabel("_SYSTEM")
        sys_title.setStyleSheet(f"color: {CYAN}; font-size: 20px; font-weight: bold; letter-spacing: 4px;")
        sb_layout.addWidget(sys_title)

        rank = QLabel("Rank: E\nLevel: 1")
        rank.setStyleSheet("color: #888; font-size: 12px;")
        sb_layout.addWidget(rank)

        sb_layout.addSpacing(20)

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
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        self.git_status = QLabel("Git: Standby")
        self.git_status.setStyleSheet("color: #555; font-size: 10px;")
        sb_layout.addWidget(self.git_status)
        return sidebar

    def _build_content(self):
        content = QFrame()
        content.setStyleSheet("background: transparent; border: none;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        header = QLabel("AVAILABLE QUESTS")
        header.setStyleSheet(f"""
            color: {WHITE};
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        content_layout.addWidget(header)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {CYAN}44;")
        content_layout.addWidget(line)

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
        content_layout.addWidget(scroll)

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
        content_layout.addWidget(self.pull_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return content

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
        self.overlay.setGeometry(self.root.rect())
        self.notif.reposition(QPoint(self.root.width(), 0))
        super().resizeEvent(event)

    def _scan_missions(self):
        missions = self.manager.scan()
        if len(missions) != getattr(self, "_last_count", -1):
            self._rebuild_missions(missions)
            self._last_count = len(missions)

    def _rebuild_missions(self, missions):
        while self.missions_layout.count() > 1:
            item = self.missions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not missions:
            empty = QLabel("No active quests. Sync to fetch new missions.")
            empty.setStyleSheet("color: #555; font-size: 14px; padding: 20px;")
            self.missions_layout.insertWidget(0, empty)
        else:
            for mission in missions:
                card = MissionCard(mission)
                self.missions_layout.insertWidget(self.missions_layout.count() - 1, card)

    def _on_new_mission(self, mission: Mission):
        self.notif.show_notification(
            title=mission.title,
            description=mission.description,
            difficulty=mission.difficulty,
            duration_ms=8000,
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

    def _manual_pull(self):
        self.pull_btn.setText("SYNCING...")
        self.pull_btn.setEnabled(False)
        self.git_sync.force_pull()
        QTimer.singleShot(1500, lambda: (
            self.pull_btn.setText("SYNC WITH REMOTE"),
            self.pull_btn.setEnabled(True),
        ))

    def closeEvent(self, event):
        self.git_sync.stop()
        self.scan_timer.stop()
        super().closeEvent(event)
