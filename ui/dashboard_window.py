import os
import re
import json
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QCursor, QPixmap, QGuiApplication, QTextDocument, QPageSize
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QHBoxLayout, QTimeEdit, QAbstractSpinBox, QScrollArea
)

from config import DEFAULT_PI_BASE_URL, ASSETS_DIR
from core.db_service import DatabaseService, generate_resident_uid
from core.gateway_client import GatewayClient
from core.models import HighlightRule, auto_fg_for_bg, PALETTE, SECTIONS


class DashboardWindow(QWidget):
    def __init__(self, current_user: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.current_user = current_user or {"id": None, "username": "admin", "role": "ADMIN"}
        self.db = DatabaseService()
        self.db.ensure_tables()
        self.gateway = GatewayClient()

        self.drag_pos = None
        self.normal_geometry = None
        self.is_custom_maximized = False
        self.selected_resident_id: Optional[int] = None
        self.selected_image_path: Optional[str] = None
        self.selected_source_document: Optional[str] = None
        self.rules: List[HighlightRule] = []
        self.logo_path = ASSETS_DIR / "Whisperwood-Villa-logo-removebg-preview.png"

        self.setWindowTitle("Whisperwood Villa Dashboard")
        self.setMinimumSize(1120, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("QLabel { border: none; background: transparent; }")

        self.build_ui()
        self.bind_events()
        self.fit_to_screen()

        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.refresh_devices)

        self.new_resident()
        self.refresh_devices()
        self.load_residents()
        self.load_recent_logs()
        self.refresh_dashboard_summary()

    # ---------------------------- styles ----------------------------

    def primary_btn_style(self):
        return """
            QPushButton {
                background-color: #e2ab09;
                color: #111111;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #f0b814;
            }
            QPushButton:pressed {
                background-color: #c99508;
            }
        """

    def secondary_btn_style(self):
        return """
            QPushButton {
                background-color: #202020;
                color: white;
                border: 1px solid #2d2d2d;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
        """

    def input_style(self):
        return """
            QLineEdit, QTextEdit, QComboBox, QTimeEdit {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #262626;
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QTimeEdit:focus {
                border: 1px solid #e2ab09;
            }
        """

    def label_style(self):
        return "font-size: 13px; font-weight: 600; color: #d7d7d7; background: transparent; border: none;"

    # ---------------------------- window helpers ----------------------------

    def fit_to_screen(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        width = min(1520, int(screen.width() * 0.97))
        height = min(920, int(screen.height() * 0.96))
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)
        self.is_custom_maximized = False

    # ---------------------------- build ui ----------------------------

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setStyleSheet("""
            background-color: #0a0a0a;
            border-radius: 28px;
            color: white;
        """)
        root.addWidget(self.container)

        # Sidebar
        self.sidebar = QFrame(self.container)
        self.sidebar.setGeometry(12, 12, 245, 896)
        self.sidebar.setStyleSheet("background-color: #121212; border-radius: 22px;")

        self.logo = QLabel(self.sidebar)
        self.logo.setGeometry(22, 20, 200, 82)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.logo_path.exists():
            self.logo.setPixmap(
                QPixmap(str(self.logo_path)).scaled(
                    175, 78,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            self.logo.setText("Whisperwood Villa")
            self.logo.setStyleSheet("font-size: 22px; font-weight: 700; color: #e2ab09;")

        self.user_card = QFrame(self.sidebar)
        self.user_card.setGeometry(18, 115, 208, 88)
        self.user_card.setStyleSheet("background-color: #1a1a1a; border-radius: 16px;")

        self.user_avatar = QLabel(self.user_card)
        self.user_avatar.setGeometry(12, 20, 48, 48)
        self.user_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_avatar.setText((self.current_user.get("username") or "U")[0].upper())
        self.user_avatar.setStyleSheet("""
            QLabel {
                background-color: #e2ab09;
                color: #101010;
                border-radius: 24px;
                font-size: 18px;
                font-weight: 700;
            }
        """)

        self.user_name = QLabel(self.user_card)
        self.user_name.setGeometry(72, 18, 120, 22)
        self.user_name.setText(self.current_user.get("username", "admin"))
        self.user_name.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.user_role = QLabel(self.user_card)
        self.user_role.setGeometry(72, 45, 120, 18)
        self.user_role.setText(str(self.current_user.get("role", "ADMIN")))
        self.user_role.setStyleSheet("font-size: 12px; color: #bdbdbd;")

        nav_buttons = [
            ("Overview", 235),
            ("Resident Records", 285),
            ("Device Pairing", 335),
            ("LCD Schedule", 385),
            ("Logs Admin", 435),
        ]

        self.btn_menu_overview = QPushButton(nav_buttons[0][0], self.sidebar)
        self.btn_menu_overview.setGeometry(18, nav_buttons[0][1], 208, 42)

        self.btn_menu_dashboard = QPushButton(nav_buttons[1][0], self.sidebar)
        self.btn_menu_dashboard.setGeometry(18, nav_buttons[1][1], 208, 42)

        self.btn_menu_pairing = QPushButton(nav_buttons[2][0], self.sidebar)
        self.btn_menu_pairing.setGeometry(18, nav_buttons[2][1], 208, 42)

        self.btn_menu_updates = QPushButton(nav_buttons[3][0], self.sidebar)
        self.btn_menu_updates.setGeometry(18, nav_buttons[3][1], 208, 42)

        self.btn_menu_logs = QPushButton(nav_buttons[4][0], self.sidebar)
        self.btn_menu_logs.setGeometry(18, nav_buttons[4][1], 208, 42)

        for b in [self.btn_menu_overview, self.btn_menu_dashboard, self.btn_menu_pairing, self.btn_menu_updates, self.btn_menu_logs]:
            b.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 18px;
                    background-color: transparent;
                    color: #dddddd;
                    border: none;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #1f1f1f;
                }
            """)

        self.btn_refresh_devices = QPushButton("Refresh Devices", self.sidebar)
        self.btn_refresh_devices.setGeometry(18, 520, 208, 42)
        self.btn_refresh_devices.setStyleSheet(self.secondary_btn_style())

        self.auto_refresh = QCheckBox("Auto-refresh every 3s", self.sidebar)
        self.auto_refresh.setGeometry(24, 575, 180, 24)
        self.auto_refresh.setStyleSheet("""
            QCheckBox {
                color: #d2d2d2;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1px solid #888;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #e2ab09;
                border: 1px solid #e2ab09;
            }
        """)

        self.connection_badge = QLabel("Gateway: Unknown", self.sidebar)
        self.connection_badge.setGeometry(18, 630, 208, 28)
        self.connection_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_badge.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                color: #cfcfcf;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
            }
        """)

        self.btn_profile_settings = QPushButton("Profile & Settings", self.sidebar)
        self.btn_profile_settings.setGeometry(18, 705, 208, 42)
        self.btn_profile_settings.setStyleSheet(self.secondary_btn_style())

        # Title area
        self.title = QLabel("Whisperwood Villa Control Center", self.container)
        self.title.setGeometry(280, 22, 520, 32)
        self.title.setStyleSheet("font-size: 28px; font-weight: 700; color: white;")

        self.subtitle = QLabel("Overview, resident records, pairing, LCD schedule, and logs admin", self.container)
        self.subtitle.setGeometry(280, 56, 520, 18)
        self.subtitle.setStyleSheet("font-size: 13px; color: #aaaaaa;")

        self.base_url_edit = QLineEdit(self.container)
        self.base_url_edit.setGeometry(1020, 24, 320, 42)
        self.base_url_edit.setText(DEFAULT_PI_BASE_URL)
        self.base_url_edit.setStyleSheet(self.input_style())

        self.min_btn = QPushButton("-", self.container)
        self.min_btn.setGeometry(1370, 24, 38, 38)
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #d6d6d6;
                border: none;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: white;
                background-color: rgba(255,255,255,0.08);
                border-radius: 19px;
            }
        """)

        self.max_btn = QPushButton("[]", self.container)
        self.max_btn.setGeometry(1415, 24, 38, 38)
        self.max_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.max_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #d6d6d6;
                border: none;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: white;
                background-color: rgba(255,255,255,0.08);
                border-radius: 19px;
            }
        """)

        self.close_btn = QPushButton("X", self.container)
        self.close_btn.setGeometry(1460, 24, 38, 38)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #d6d6d6;
                border: none;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                color: white;
                background-color: rgba(255,255,255,0.08);
                border-radius: 19px;
            }
        """)

        # Pages
        self.pages = QStackedWidget(self.container)
        self.pages.setGeometry(280, 95, 1218, 805)
        self.pages.setStyleSheet("background: transparent;")

        self.page_overview = self.build_overview_page()
        self.page_dashboard = self.build_dashboard_page()
        self.page_pairing = self.build_pairing_page()
        self.page_updates = self.build_updates_page()
        self.page_logs = self.build_logs_page()

        for p in [self.page_overview, self.page_dashboard, self.page_pairing, self.page_updates, self.page_logs]:
            self.pages.addWidget(p)

        self.pages.setCurrentWidget(self.page_overview)
        self.set_active_menu(self.btn_menu_overview)
        self.strip_text_only_label_frames()
        self.min_btn.setText("-")
        self.max_btn.setText("[]")
        self.close_btn.setText("X")
        self.position_window_controls()

    def toggle_max_restore(self):
        if self.is_custom_maximized:
            if self.normal_geometry is not None:
                self.setGeometry(self.normal_geometry)
            self.is_custom_maximized = False
        else:
            self.normal_geometry = self.geometry()
            available = QGuiApplication.primaryScreen().availableGeometry()
            self.setGeometry(available)
            self.is_custom_maximized = True
        self.max_btn.setText("[]")

    def position_window_controls(self):
        self.sidebar.setGeometry(12, 12, 245, max(640, self.container.height() - 24))
        right = self.container.width() - 48
        self.close_btn.move(right, 24)
        self.max_btn.move(right - 45, 24)
        self.min_btn.move(right - 90, 24)
        self.base_url_edit.setGeometry(max(650, right - 470), 24, 330, 42)
        self.pages.setGeometry(280, 95, self.container.width() - 302, self.container.height() - 115)

    def card_style(self):
        return "background-color: #121212; border-radius: 18px; border: 1px solid #242424;"

    def table_style(self):
        return """
            QTableWidget {
                background-color: #111111;
                color: white;
                border: 1px solid #242424;
                border-radius: 14px;
                gridline-color: #2a2a2a;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1b1b1b;
                color: #d7d7d7;
                padding: 8px;
                border: none;
                font-weight: 700;
            }
        """

    def strip_text_only_label_frames(self):
        # Keep intentional badge/alert labels untouched.
        protected_labels = {
            getattr(self, "user_avatar", None),
            getattr(self, "connection_badge", None),
            getattr(self, "lcd_alert_banner", None),
            getattr(self, "upd_lcd_alert", None),
        }
        for label in self.findChildren(QLabel):
            if label in protected_labels:
                continue
            if label.pixmap() is not None:
                continue

            style = label.styleSheet() or ""
            lower = style.lower()
            has_custom_bg = "background-color" in lower and "background: transparent" not in lower
            has_custom_border = "border:" in lower and "border: none" not in lower
            if has_custom_bg or has_custom_border:
                continue

            label.setFrameStyle(0)
            parts = style.strip().rstrip(";")
            extras = []
            if "background:" not in lower and "background-color" not in lower:
                extras.append("background: transparent")
            if "border:" not in lower:
                extras.append("border: none")

            if extras:
                parts = f"{parts}; {'; '.join(extras)}" if parts else "; ".join(extras)
                label.setStyleSheet(parts + ";")

    def wrap_scroll_page(self, content: QWidget, min_height: int):
        content.setMinimumSize(1218, min_height)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #121212;
                width: 10px;
                border-radius: 5px;
                margin: 6px 2px 6px 2px;
            }
            QScrollBar::handle:vertical {
                background: #2d2d2d;
                border-radius: 5px;
                min-height: 28px;
            }
            QScrollBar:horizontal {
                background: #121212;
                height: 10px;
                border-radius: 5px;
                margin: 2px 6px 2px 6px;
            }
            QScrollBar::handle:horizontal {
                background: #2d2d2d;
                border-radius: 5px;
                min-width: 28px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0px;
                height: 0px;
            }
        """)
        scroll.setWidget(content)
        return scroll

    # ---------------------------- dashboard page ----------------------------

    def build_overview_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")

        hero = QFrame(page)
        hero.setGeometry(0, 0, 1218, 145)
        hero.setStyleSheet("background-color: #101010; border-radius: 22px; border: 1px solid #273447;")

        title = QLabel("Care operations dashboard", hero)
        title.setGeometry(24, 22, 420, 32)
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: white;")

        subtitle = QLabel("Follow the resident-first flow: save record, pair device, auto-send to display pipeline, confirm LCD schedule, then review logs.", hero)
        subtitle.setGeometry(24, 58, 780, 24)
        subtitle.setStyleSheet("font-size: 13px; color: #b8c1cc;")

        self.btn_overview_new_resident = QPushButton("Open Resident Records", hero)
        self.btn_overview_new_resident.setGeometry(24, 92, 190, 42)
        self.btn_overview_new_resident.setStyleSheet(self.primary_btn_style())

        self.btn_overview_pairing = QPushButton("Go to Pairing", hero)
        self.btn_overview_pairing.setGeometry(228, 92, 150, 42)
        self.btn_overview_pairing.setStyleSheet(self.secondary_btn_style())

        self.overview_status = QLabel("Gateway and local database status will appear here.", hero)
        self.overview_status.setGeometry(820, 28, 360, 82)
        self.overview_status.setWordWrap(True)
        self.overview_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.overview_status.setStyleSheet("font-size: 13px; color: #d8d8d8;")

        self.summary_labels = {}
        cards = [
            ("active_residents", "Saved residents", 0, 165),
            ("known_devices", "Known devices", 248, 165),
            ("paired_devices", "Paired devices", 496, 165),
            ("recent_activity", "Recent activity", 744, 165),
            ("online_devices", "Connected now", 992, 165),
        ]
        for key, label, x, y in cards:
            card = QFrame(page)
            card.setGeometry(x, y, 226, 116)
            card.setStyleSheet(self.card_style())
            small = QLabel(label, card)
            small.setGeometry(18, 18, 170, 22)
            small.setStyleSheet("font-size: 12px; color: #aeb7c2; font-weight: 700;")
            value = QLabel("0", card)
            value.setGeometry(18, 48, 170, 44)
            value.setStyleSheet("font-size: 34px; color: white; font-weight: 800;")
            self.summary_labels[key] = value

        workflow = QFrame(page)
        workflow.setGeometry(0, 305, 402, 470)
        workflow.setStyleSheet(self.card_style())
        workflow_title = QLabel("Workflow Guide", workflow)
        workflow_title.setGeometry(22, 20, 180, 24)
        workflow_title.setStyleSheet("font-size: 18px; color: white; font-weight: 800;")
        steps = [
            "1. Create or update the resident record.",
            "2. Pair the resident to a known device.",
            "3. On pairing, latest resident text auto-sends to the device.",
            "4. If already paired, saving updates auto-sends the latest text.",
            "5. Save LCD image and schedule, then confirm in Logs Admin.",
        ]
        for i, step in enumerate(steps):
            lbl = QLabel(step, workflow)
            lbl.setGeometry(24, 68 + i * 54, 340, 34)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 13px; color: #dedede;")

        device_panel = QFrame(page)
        device_panel.setGeometry(425, 305, 793, 470)
        device_panel.setStyleSheet(self.card_style())
        device_title = QLabel("Device Status Snapshot", device_panel)
        device_title.setGeometry(22, 18, 260, 24)
        device_title.setStyleSheet("font-size: 18px; color: white; font-weight: 800;")
        self.overview_device_table = QTableWidget(device_panel)
        self.overview_device_table.setGeometry(18, 58, 756, 390)
        self.overview_device_table.setColumnCount(5)
        self.overview_device_table.setHorizontalHeaderLabels(["Device ID", "Status", "Battery", "Assigned Resident", "Last Seen"])
        self.overview_device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.overview_device_table.verticalHeader().setVisible(False)
        self.overview_device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.overview_device_table.setStyleSheet(self.table_style())

        return self.wrap_scroll_page(page, 820)

    def build_dashboard_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")

        self.residents_panel = QFrame(page)
        self.residents_panel.setGeometry(0, 0, 330, 805)
        self.residents_panel.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        title = QLabel("Residents", self.residents_panel)
        title.setGeometry(20, 18, 120, 24)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.search_resident = QLineEdit(self.residents_panel)
        self.search_resident.setGeometry(18, 55, 294, 40)
        self.search_resident.setPlaceholderText("Search name, UID, room...")
        self.search_resident.setStyleSheet(self.input_style())

        self.resident_list = QListWidget(self.residents_panel)
        self.resident_list.setGeometry(18, 110, 294, 677)
        self.resident_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: white;
                border: none;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                background-color: #1a1a1a;
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 8px;
            }
            QListWidget::item:selected {
                background-color: #e2ab09;
                color: #111111;
            }
        """)

        self.form_panel = QFrame(page)
        self.form_panel.setGeometry(345, 0, 420, 805)
        self.form_panel.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        self.form_heading = QLabel("Resident Information", self.form_panel)
        self.form_heading.setGeometry(22, 18, 180, 24)
        self.form_heading.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.lbl_uid = QLabel("Resident UID", self.form_panel)
        self.lbl_uid.setGeometry(22, 58, 90, 18)
        self.lbl_uid.setStyleSheet(self.label_style())

        self.txt_uid = QLineEdit(self.form_panel)
        self.txt_uid.setGeometry(22, 80, 180, 42)
        self.txt_uid.setReadOnly(True)
        self.txt_uid.setStyleSheet(self.input_style())

        self.chk_active = QCheckBox("Resident enabled", self.form_panel)
        self.chk_active.setGeometry(230, 88, 140, 24)
        self.chk_active.setChecked(True)
        self.chk_active.setStyleSheet("""
            QCheckBox {
                color: #d2d2d2;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1px solid #888;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #e2ab09;
                border: 1px solid #e2ab09;
            }
        """)

        self.lbl_name = QLabel("Full Name", self.form_panel)
        self.lbl_name.setGeometry(22, 130, 90, 18)
        self.lbl_name.setStyleSheet(self.label_style())

        self.txt_name = QLineEdit(self.form_panel)
        self.txt_name.setGeometry(22, 152, 376, 42)
        self.txt_name.setStyleSheet(self.input_style())

        self.lbl_room = QLabel("Room", self.form_panel)
        self.lbl_room.setGeometry(22, 205, 50, 18)
        self.lbl_room.setStyleSheet(self.label_style())

        self.txt_room = QLineEdit(self.form_panel)
        self.txt_room.setGeometry(22, 227, 120, 42)
        self.txt_room.setStyleSheet(self.input_style())

        self.lbl_alert = QLabel("Alert / Status", self.form_panel)
        self.lbl_alert.setGeometry(160, 205, 90, 18)
        self.lbl_alert.setStyleSheet(self.label_style())

        self.cmb_alert = QComboBox(self.form_panel)
        self.cmb_alert.setGeometry(160, 227, 160, 42)
        self.cmb_alert.addItems(["Stable", "Needs Attention", "Fall Risk", "Emergency"])
        self.cmb_alert.setStyleSheet(self.input_style())

        self.lbl_diet = QLabel("Diet (comma list)", self.form_panel)
        self.lbl_diet.setGeometry(22, 280, 120, 18)
        self.lbl_diet.setStyleSheet(self.label_style())

        self.txt_diet = QLineEdit(self.form_panel)
        self.txt_diet.setGeometry(22, 302, 376, 42)
        self.txt_diet.setStyleSheet(self.input_style())

        self.lbl_allergies = QLabel("Allergies (comma list)", self.form_panel)
        self.lbl_allergies.setGeometry(22, 355, 140, 18)
        self.lbl_allergies.setStyleSheet(self.label_style())

        self.txt_allergies = QLineEdit(self.form_panel)
        self.txt_allergies.setGeometry(22, 377, 376, 42)
        self.txt_allergies.setStyleSheet(self.input_style())

        self.lbl_note = QLabel("Note", self.form_panel)
        self.lbl_note.setGeometry(22, 430, 60, 18)
        self.lbl_note.setStyleSheet(self.label_style())

        self.txt_note = QTextEdit(self.form_panel)
        self.txt_note.setGeometry(22, 452, 376, 58)
        self.txt_note.setStyleSheet(self.input_style())

        self.lbl_drinks = QLabel("Drinks", self.form_panel)
        self.lbl_drinks.setGeometry(22, 520, 60, 18)
        self.lbl_drinks.setStyleSheet(self.label_style())

        self.txt_drinks = QLineEdit(self.form_panel)
        self.txt_drinks.setGeometry(22, 542, 180, 42)
        self.txt_drinks.setStyleSheet(self.input_style())

        self.lbl_schedule = QLabel("Schedule", self.form_panel)
        self.lbl_schedule.setGeometry(218, 520, 80, 18)
        self.lbl_schedule.setStyleSheet(self.label_style())

        self.txt_schedule = QLineEdit(self.form_panel)
        self.txt_schedule.setGeometry(218, 542, 180, 42)
        self.txt_schedule.setPlaceholderText("Meals, care, reminders")
        self.txt_schedule.setStyleSheet(self.input_style())

        self.lbl_source = QLabel("Source document", self.form_panel)
        self.lbl_source.setGeometry(22, 586, 120, 18)
        self.lbl_source.setStyleSheet(self.label_style())

        self.btn_attach_source = QPushButton("Attach Document", self.form_panel)
        self.btn_attach_source.setGeometry(22, 608, 150, 36)
        self.btn_attach_source.setStyleSheet(self.secondary_btn_style())

        self.source_doc_label = QLabel("No source document attached", self.form_panel)
        self.source_doc_label.setGeometry(182, 608, 216, 36)
        self.source_doc_label.setWordWrap(True)
        self.source_doc_label.setStyleSheet("font-size: 11px; color: #a7a7a7;")

        self.chk_safety_review = QCheckBox("Needs safety review", self.form_panel)
        self.chk_safety_review.setGeometry(22, 650, 160, 24)
        self.chk_safety_review.setStyleSheet(self.chk_active.styleSheet())

        self.btn_new_resident = QPushButton("New Resident", self.form_panel)
        self.btn_new_resident.setGeometry(22, 686, 120, 42)
        self.btn_new_resident.setStyleSheet(self.secondary_btn_style())

        self.btn_save_resident = QPushButton("Save Resident", self.form_panel)
        self.btn_save_resident.setGeometry(152, 686, 120, 42)
        self.btn_save_resident.setStyleSheet(self.primary_btn_style())

        self.btn_clear_fields = QPushButton("Clear Form", self.form_panel)
        self.btn_clear_fields.setGeometry(282, 686, 116, 42)
        self.btn_clear_fields.setStyleSheet(self.secondary_btn_style())

        self.preview_panel = QFrame(page)
        self.preview_panel.setGeometry(780, 0, 438, 805)
        self.preview_panel.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        self.preview_heading = QLabel("Live Preview", self.preview_panel)
        self.preview_heading.setGeometry(22, 18, 120, 24)
        self.preview_heading.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.btn_go_pairing_after_save = QPushButton("Go to Pairing", self.preview_panel)
        self.btn_go_pairing_after_save.setGeometry(285, 16, 130, 34)
        self.btn_go_pairing_after_save.setStyleSheet(self.secondary_btn_style())

        self.epaper_card = QFrame(self.preview_panel)
        self.epaper_card.setGeometry(22, 60, 394, 185)
        self.epaper_card.setStyleSheet("background-color: #efefef; border-radius: 18px;")

        ep_title = QLabel("E-Paper Preview", self.epaper_card)
        ep_title.setGeometry(16, 12, 120, 18)
        ep_title.setStyleSheet("color: #111111; font-size: 13px; font-weight: 700;")

        self.ep_name = QLabel("Resident Name", self.epaper_card)
        self.ep_name.setGeometry(16, 40, 240, 28)
        self.ep_name.setStyleSheet("color: #111111; font-size: 22px; font-weight: 700;")

        self.ep_room = QLabel("Room ---", self.epaper_card)
        self.ep_room.setGeometry(16, 72, 180, 22)
        self.ep_room.setStyleSheet("color: #111111; font-size: 14px;")

        self.ep_diet = QLabel("Diet: ---", self.epaper_card)
        self.ep_diet.setGeometry(16, 98, 300, 22)
        self.ep_diet.setStyleSheet("color: #111111; font-size: 14px;")

        self.ep_allergies = QLabel("Allergies: ---", self.epaper_card)
        self.ep_allergies.setGeometry(16, 124, 350, 22)
        self.ep_allergies.setStyleSheet("color: #111111; font-size: 14px;")

        self.ep_note = QLabel("Note: ---", self.epaper_card)
        self.ep_note.setGeometry(16, 148, 350, 30)
        self.ep_note.setWordWrap(True)
        self.ep_note.setStyleSheet("color: #111111; font-size: 13px;")

        self.lcd_card = QFrame(self.preview_panel)
        self.lcd_card.setGeometry(22, 268, 394, 210)
        self.lcd_card.setStyleSheet("background-color: #0a1831; border-radius: 18px; border: 2px solid #20457b;")

        lcd_title = QLabel("LCD Preview", self.lcd_card)
        lcd_title.setGeometry(16, 12, 100, 18)
        lcd_title.setStyleSheet("color: white; font-size: 13px; font-weight: 700;")

        self.lcd_image = QLabel(self.lcd_card)
        self.lcd_image.setGeometry(20, 40, 354, 120)
        self.lcd_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lcd_image.setStyleSheet("""
            QLabel {
                background-color: #0a1831;
                border-radius: 10px;
            }
        """)
        self.lcd_image.hide()

        self.lcd_name = QLabel("Resident Name", self.lcd_card)
        self.lcd_name.setGeometry(20, 42, 354, 28)
        self.lcd_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lcd_name.setStyleSheet("color: white; font-size: 22px; font-weight: 700;")

        self.lcd_room = QLabel("Room ---", self.lcd_card)
        self.lcd_room.setGeometry(20, 72, 354, 22)
        self.lcd_room.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lcd_room.setStyleSheet("color: #d7e3f1; font-size: 14px;")

        self.lcd_alert_banner = QLabel("STABLE", self.lcd_card)
        self.lcd_alert_banner.setGeometry(92, 104, 210, 36)
        self.lcd_alert_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lcd_alert_banner.setStyleSheet("""
            QLabel {
                background-color: #146c2e;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 700;
            }
        """)

        self.lcd_note = QLabel("No note", self.lcd_card)
        self.lcd_note.setGeometry(20, 148, 354, 42)
        self.lcd_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lcd_note.setWordWrap(True)
        self.lcd_note.setStyleSheet("color: #eef2f7; font-size: 13px;")

        self.overview_panel = QFrame(self.preview_panel)
        self.overview_panel.setGeometry(22, 500, 394, 260)
        self.overview_panel.setStyleSheet("background-color: #1a1a1a; border-radius: 16px; border: 1px solid #262626;")

        overview_title = QLabel("Overall Dashboard", self.overview_panel)
        overview_title.setGeometry(16, 14, 180, 22)
        overview_title.setStyleSheet("font-size: 16px; font-weight: 700; color: white;")

        self.record_summary_labels = {}
        summary_items = [
            ("active_residents", "Active residents", 52),
            ("online_devices", "Online devices", 90),
            ("paired_devices", "Paired devices", 128),
            ("safety_reviews", "Safety reviews", 166),
            ("failed_updates", "Failed updates", 204),
        ]
        for key, title_text, y in summary_items:
            label = QLabel(f"{title_text}: 0", self.overview_panel)
            label.setGeometry(18, y, 250, 24)
            label.setStyleSheet("font-size: 13px; color: #dedede;")
            self.record_summary_labels[key] = label

        self.record_summary_labels["database_mode"] = QLabel("Data store: checking", self.overview_panel)
        self.record_summary_labels["database_mode"].setGeometry(210, 14, 160, 22)
        self.record_summary_labels["database_mode"].setAlignment(Qt.AlignmentFlag.AlignRight)
        self.record_summary_labels["database_mode"].setStyleSheet("font-size: 12px; color: #e2ab09;")

        return self.wrap_scroll_page(page, 860)

    # ---------------------------- pairing page ----------------------------

    def build_pairing_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")

        self.pair_left = QFrame(page)
        self.pair_left.setGeometry(0, 0, 590, 805)
        self.pair_left.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        title = QLabel("Resident Pairing / Unpairing", self.pair_left)
        title.setGeometry(22, 18, 240, 24)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.pair_resident_list = QListWidget(self.pair_left)
        self.pair_resident_list.setGeometry(20, 60, 260, 500)

        self.available_devices_list = QListWidget(self.pair_left)
        self.available_devices_list.setGeometry(310, 60, 260, 500)

        for lw in [self.pair_resident_list, self.available_devices_list]:
            lw.setStyleSheet("""
                QListWidget {
                    background-color: #1a1a1a;
                    color: white;
                    border: 1px solid #262626;
                    border-radius: 14px;
                    padding: 6px;
                }
                QListWidget::item {
                    padding: 10px;
                    margin-bottom: 4px;
                    border-radius: 10px;
                }
                QListWidget::item:selected {
                    background-color: #e2ab09;
                    color: #111111;
                }
            """)

        lbl_avail = QLabel("Available / Known Devices", self.pair_left)
        lbl_avail.setGeometry(310, 30, 180, 20)
        lbl_avail.setStyleSheet("font-size: 13px; color: #cfcfcf;")

        self.btn_pair_selected = QPushButton("Pair Resident to Device", self.pair_left)
        self.btn_pair_selected.setGeometry(310, 572, 260, 44)
        self.btn_pair_selected.setStyleSheet(self.primary_btn_style())

        self.btn_unpair_selected = QPushButton("Unpair Selected Device", self.pair_left)
        self.btn_unpair_selected.setGeometry(310, 624, 260, 44)
        self.btn_unpair_selected.setStyleSheet(self.secondary_btn_style())

        self.pair_info = QLabel("Select a resident and a device to pair.")
        self.pair_info.setParent(self.pair_left)
        self.pair_info.setGeometry(310, 676, 260, 64)
        self.pair_info.setWordWrap(True)
        self.pair_info.setStyleSheet("font-size: 12px; color: #a8a8a8;")

        self.pair_right = QFrame(page)
        self.pair_right.setGeometry(610, 0, 608, 805)
        self.pair_right.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        self.pair_table = QTableWidget(self.pair_right)
        self.pair_table.setGeometry(18, 18, 572, 768)
        self.pair_table.setColumnCount(5)
        self.pair_table.setHorizontalHeaderLabels(["Device ID", "Resident", "Resident UID", "Online", "Battery"])
        self.pair_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pair_table.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: white;
                border: 1px solid #1f1f1f;
                border-radius: 14px;
                gridline-color: #262626;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: #d7d7d7;
                padding: 8px;
                border: none;
                font-weight: 700;
            }
        """)
        self.pair_table.verticalHeader().setVisible(False)
        self.pair_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        return self.wrap_scroll_page(page, 860)

    # ---------------------------- updates page ----------------------------

    def build_updates_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")

        self.upd_left = QFrame(page)
        self.upd_left.setGeometry(0, 0, 540, 805)
        self.upd_left.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        title = QLabel("LCD Schedule", self.upd_left)
        title.setGeometry(22, 18, 180, 24)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.upd_target = QComboBox(self.upd_left)
        self.upd_target.setGeometry(22, 58, 490, 42)
        self.upd_target.setStyleSheet(self.input_style())

        self.hl_type = QComboBox(self.upd_left)
        self.hl_type.setGeometry(22, 118, 220, 38)
        self.hl_type.addItems(["Word highlight (VALUE)", "Section highlight (SECTION)"])
        self.hl_type.setStyleSheet(self.input_style())

        self.hl_section = QComboBox(self.upd_left)
        self.hl_section.setGeometry(252, 118, 100, 38)
        self.hl_section.addItems(SECTIONS)
        self.hl_section.setStyleSheet(self.input_style())

        self.hl_bg = QComboBox(self.upd_left)
        self.hl_bg.setGeometry(362, 118, 70, 38)
        self.hl_bg.addItems(PALETTE)
        self.hl_bg.setStyleSheet(self.input_style())

        self.hl_fg = QComboBox(self.upd_left)
        self.hl_fg.setGeometry(442, 118, 70, 38)
        self.hl_fg.addItems(PALETTE)
        self.hl_fg.setStyleSheet(self.input_style())

        lbl_tokens = QLabel("Pick exact screen words only", self.upd_left)
        lbl_tokens.setGeometry(22, 168, 160, 18)
        lbl_tokens.setStyleSheet(self.label_style())

        self.token_list = QListWidget(self.upd_left)
        self.token_list.setGeometry(22, 192, 320, 120)
        self.token_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.token_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #262626;
                border-radius: 12px;
                padding: 6px;
            }
        """)

        self.rules_list = QListWidget(self.upd_left)
        self.rules_list.setGeometry(22, 340, 320, 120)
        self.rules_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #262626;
                border-radius: 12px;
                padding: 6px;
            }
        """)

        self.btn_add_highlight = QPushButton("Add Highlight", self.upd_left)
        self.btn_add_highlight.setGeometry(360, 192, 152, 38)
        self.btn_add_highlight.setStyleSheet(self.secondary_btn_style())

        self.btn_remove_highlight = QPushButton("Remove Selected", self.upd_left)
        self.btn_remove_highlight.setGeometry(360, 238, 152, 38)
        self.btn_remove_highlight.setStyleSheet(self.secondary_btn_style())

        self.btn_clear_highlights = QPushButton("Clear Highlights", self.upd_left)
        self.btn_clear_highlights.setGeometry(360, 284, 152, 38)
        self.btn_clear_highlights.setStyleSheet(self.secondary_btn_style())

        self.btn_preview = QPushButton("Preview Update", self.upd_left)
        self.btn_preview.setGeometry(360, 340, 152, 42)
        self.btn_preview.setStyleSheet(self.primary_btn_style())

        self.btn_send_text = QPushButton("Send Text Update", self.upd_left)
        self.btn_send_text.setGeometry(360, 392, 152, 42)
        self.btn_send_text.setStyleSheet(self.primary_btn_style())

        self.btn_choose_image = QPushButton("Choose LCD Image", self.upd_left)
        self.btn_choose_image.setGeometry(22, 488, 150, 42)
        self.btn_choose_image.setStyleSheet(self.secondary_btn_style())

        self.btn_send_image = QPushButton("Send Image", self.upd_left)
        self.btn_send_image.setGeometry(182, 488, 120, 42)
        self.btn_send_image.setStyleSheet(self.secondary_btn_style())

        self.btn_clear_image = QPushButton("Clear Image", self.upd_left)
        self.btn_clear_image.setGeometry(312, 488, 120, 42)
        self.btn_clear_image.setStyleSheet(self.secondary_btn_style())

        self.image_path_label = QLabel("No image selected", self.upd_left)
        self.image_path_label.setGeometry(22, 540, 490, 44)
        self.image_path_label.setWordWrap(True)
        self.image_path_label.setStyleSheet("font-size: 12px; color: #a7a7a7;")

        manual_title = QLabel("Manual LCD Control", self.upd_left)
        manual_title.setGeometry(22, 566, 180, 22)
        manual_title.setStyleSheet("font-size: 15px; font-weight: 800; color: white;")

        self.btn_lcd_on = QPushButton("Turn LCD ON", self.upd_left)
        self.btn_lcd_on.setGeometry(22, 596, 150, 40)
        self.btn_lcd_on.setStyleSheet(self.primary_btn_style())

        self.btn_lcd_off = QPushButton("Turn LCD OFF", self.upd_left)
        self.btn_lcd_off.setGeometry(184, 596, 150, 40)
        self.btn_lcd_off.setStyleSheet(self.secondary_btn_style())

        self.chk_sleep_no_image = QCheckBox("Keep LCD asleep if no image exists", self.upd_left)
        self.chk_sleep_no_image.setGeometry(22, 644, 300, 24)
        self.chk_sleep_no_image.setStyleSheet(self.chk_active.styleSheet())

        self.upd_right = QFrame(page)
        self.upd_right.setGeometry(560, 0, 658, 805)
        self.upd_right.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        self.upd_epaper_card = QFrame(self.upd_right)
        self.upd_epaper_card.setGeometry(22, 22, 614, 220)
        self.upd_epaper_card.setStyleSheet("background-color: #efefef; border-radius: 18px;")

        ep_title = QLabel("E-Paper Preview", self.upd_epaper_card)
        ep_title.setGeometry(18, 14, 120, 18)
        ep_title.setStyleSheet("color: #111111; font-size: 13px; font-weight: 700;")

        self.upd_ep_name = QLabel("Resident Name", self.upd_epaper_card)
        self.upd_ep_name.setGeometry(18, 44, 320, 30)
        self.upd_ep_name.setStyleSheet("color: #111111; font-size: 24px; font-weight: 700;")

        self.upd_ep_room = QLabel("Room ---", self.upd_epaper_card)
        self.upd_ep_room.setGeometry(18, 80, 250, 24)
        self.upd_ep_room.setStyleSheet("color: #111111; font-size: 15px;")

        self.upd_ep_diet = QLabel("Diet: ---", self.upd_epaper_card)
        self.upd_ep_diet.setGeometry(18, 112, 400, 24)
        self.upd_ep_diet.setStyleSheet("color: #111111; font-size: 14px;")

        self.upd_ep_allergies = QLabel("Allergies: ---", self.upd_epaper_card)
        self.upd_ep_allergies.setGeometry(18, 144, 500, 24)
        self.upd_ep_allergies.setStyleSheet("color: #111111; font-size: 14px;")

        self.upd_ep_note = QLabel("Note: ---", self.upd_epaper_card)
        self.upd_ep_note.setGeometry(18, 172, 560, 30)
        self.upd_ep_note.setWordWrap(True)
        self.upd_ep_note.setStyleSheet("color: #111111; font-size: 13px;")

        self.upd_lcd_card = QFrame(self.upd_right)
        self.upd_lcd_card.setGeometry(22, 252, 614, 210)
        self.upd_lcd_card.setStyleSheet("background-color: #0a1831; border-radius: 18px; border: 2px solid #20457b;")

        lcd_title = QLabel("LCD Preview", self.upd_lcd_card)
        lcd_title.setGeometry(18, 14, 120, 18)
        lcd_title.setStyleSheet("color: white; font-size: 13px; font-weight: 700;")

        self.upd_lcd_image = QLabel(self.upd_lcd_card)
        self.upd_lcd_image.setGeometry(20, 44, 574, 136)
        self.upd_lcd_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upd_lcd_image.setStyleSheet("""
            QLabel {
                background-color: #0a1831;
                border-radius: 12px;
            }
        """)
        self.upd_lcd_image.hide()

        self.upd_lcd_name = QLabel("Resident Name", self.upd_lcd_card)
        self.upd_lcd_name.setGeometry(20, 48, 574, 30)
        self.upd_lcd_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upd_lcd_name.setStyleSheet("color: white; font-size: 28px; font-weight: 700;")

        self.upd_lcd_room = QLabel("Room ---", self.upd_lcd_card)
        self.upd_lcd_room.setGeometry(20, 78, 574, 22)
        self.upd_lcd_room.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upd_lcd_room.setStyleSheet("color: #d7e3f1; font-size: 15px;")

        self.upd_lcd_alert = QLabel("STABLE", self.upd_lcd_card)
        self.upd_lcd_alert.setGeometry(202, 104, 210, 34)
        self.upd_lcd_alert.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upd_lcd_alert.setStyleSheet("""
            QLabel {
                background-color: #146c2e;
                color: white;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 700;
            }
        """)

        self.upd_lcd_note = QLabel("No note", self.upd_lcd_card)
        self.upd_lcd_note.setGeometry(20, 144, 574, 46)
        self.upd_lcd_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upd_lcd_note.setWordWrap(True)
        self.upd_lcd_note.setStyleSheet("color: #eef2f7; font-size: 14px;")

        self.schedule_panel = QFrame(self.upd_right)
        self.schedule_panel.setGeometry(22, 472, 614, 196)
        self.schedule_panel.setStyleSheet(self.card_style())

        schedule_title = QLabel("Schedule Management", self.schedule_panel)
        schedule_title.setGeometry(18, 12, 220, 24)
        schedule_title.setStyleSheet("font-size: 16px; color: white; font-weight: 800;")

        self.schedule_resident = QComboBox(self.schedule_panel)
        self.schedule_resident.setGeometry(18, 46, 290, 38)
        self.schedule_resident.setStyleSheet(self.input_style())

        self.chk_schedule_enabled = QCheckBox("Enabled", self.schedule_panel)
        self.chk_schedule_enabled.setGeometry(320, 53, 84, 24)
        self.chk_schedule_enabled.setStyleSheet(self.chk_active.styleSheet())

        on_label = QLabel("ON", self.schedule_panel)
        on_label.setGeometry(414, 24, 30, 18)
        on_label.setStyleSheet(self.label_style())

        self.schedule_on = QTimeEdit(self.schedule_panel)
        self.schedule_on.setGeometry(414, 46, 80, 38)
        self.schedule_on.setDisplayFormat("HH:mm")
        self.schedule_on.setTime(QTime(7, 0))
        self.schedule_on.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.schedule_on.setStyleSheet(self.input_style())

        off_label = QLabel("OFF", self.schedule_panel)
        off_label.setGeometry(504, 24, 36, 18)
        off_label.setStyleSheet(self.label_style())

        self.schedule_off = QTimeEdit(self.schedule_panel)
        self.schedule_off.setGeometry(504, 46, 80, 38)
        self.schedule_off.setDisplayFormat("HH:mm")
        self.schedule_off.setTime(QTime(20, 0))
        self.schedule_off.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.schedule_off.setStyleSheet(self.input_style())

        self.btn_save_schedule = QPushButton("Save Schedule to Pi", self.schedule_panel)
        self.btn_save_schedule.setGeometry(18, 102, 190, 40)
        self.btn_save_schedule.setStyleSheet(self.primary_btn_style())

        self.schedule_table = QTableWidget(self.schedule_panel)
        self.schedule_table.setGeometry(225, 96, 370, 88)
        self.schedule_table.setColumnCount(4)
        self.schedule_table.setHorizontalHeaderLabels(["Resident", "Device", "Image", "Times"])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.schedule_table.setStyleSheet(self.table_style())

        return self.wrap_scroll_page(page, 820)

    # ---------------------------- logs page ----------------------------

    def build_logs_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")

        self.logs_panel = QFrame(page)
        self.logs_panel.setGeometry(0, 0, 1218, 805)
        self.logs_panel.setStyleSheet("background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f;")

        lbl = QLabel("Activity Logs", self.logs_panel)
        lbl.setGeometry(22, 18, 160, 24)
        lbl.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.logs_table = QTableWidget(self.logs_panel)
        self.logs_table.setGeometry(18, 100, 1180, 686)
        self.logs_table.setColumnCount(7)
        self.logs_table.setHorizontalHeaderLabels(["Date/Time", "Action", "Resident UID", "Device", "Pushed By", "Success", "Message"])
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.logs_table.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: white;
                border: 1px solid #1f1f1f;
                border-radius: 14px;
                gridline-color: #262626;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: #d7d7d7;
                padding: 8px;
                border: none;
                font-weight: 700;
            }
        """)
        self.logs_table.verticalHeader().setVisible(False)
        self.logs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.btn_view_log = QPushButton("View Full Log", self.logs_panel)
        self.btn_view_log.setGeometry(930, 18, 130, 42)
        self.btn_view_log.setStyleSheet(self.secondary_btn_style())

        self.btn_export_logs_pdf = QPushButton("Export Logs PDF", self.logs_panel)
        self.btn_export_logs_pdf.setGeometry(1070, 18, 128, 42)
        self.btn_export_logs_pdf.setStyleSheet(self.primary_btn_style())

        hint = QLabel("Double-click a row to view the full log.", self.logs_panel)
        hint.setGeometry(22, 62, 360, 24)
        hint.setStyleSheet("font-size: 12px; color: #a7a7a7;")

        return self.wrap_scroll_page(page, 860)

    # ---------------------------- events ----------------------------

    def bind_events(self):
        self.close_btn.clicked.connect(self.close)
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_max_restore)

        self.btn_refresh_devices.clicked.connect(self.refresh_devices)
        self.auto_refresh.stateChanged.connect(self.toggle_auto_refresh)

        self.btn_menu_overview.clicked.connect(lambda: self.switch_page(self.page_overview, self.btn_menu_overview))
        self.btn_menu_dashboard.clicked.connect(lambda: self.switch_page(self.page_dashboard, self.btn_menu_dashboard))
        self.btn_menu_pairing.clicked.connect(lambda: self.switch_page(self.page_pairing, self.btn_menu_pairing))
        self.btn_menu_updates.clicked.connect(lambda: self.switch_page(self.page_updates, self.btn_menu_updates))
        self.btn_menu_logs.clicked.connect(lambda: self.switch_page(self.page_logs, self.btn_menu_logs))
        self.btn_profile_settings.clicked.connect(self.show_profile_settings)
        self.btn_overview_new_resident.clicked.connect(lambda: self.switch_page(self.page_dashboard, self.btn_menu_dashboard))
        self.btn_overview_pairing.clicked.connect(lambda: self.switch_page(self.page_pairing, self.btn_menu_pairing))

        self.btn_new_resident.clicked.connect(self.new_resident)
        self.btn_save_resident.clicked.connect(self.save_resident)
        self.btn_clear_fields.clicked.connect(self.clear_form)
        self.btn_go_pairing_after_save.clicked.connect(lambda: self.switch_page(self.page_pairing, self.btn_menu_pairing))
        self.btn_attach_source.clicked.connect(self.attach_source_document)

        self.search_resident.textChanged.connect(self.filter_residents)
        self.resident_list.itemClicked.connect(self.on_resident_selected)

        self.pair_resident_list.itemClicked.connect(self.on_pair_resident_selected)
        self.btn_pair_selected.clicked.connect(self.pair_selected_from_menu)
        self.btn_unpair_selected.clicked.connect(self.unpair_selected_from_menu)

        self.hl_bg.currentTextChanged.connect(self.apply_auto_fg)
        self.hl_type.currentTextChanged.connect(self.on_hl_type_changed)
        self.hl_section.currentTextChanged.connect(self.refresh_token_list)

        self.btn_add_highlight.clicked.connect(self.add_highlight)
        self.btn_remove_highlight.clicked.connect(self.remove_selected_highlight)
        self.btn_clear_highlights.clicked.connect(self.clear_highlights)

        self.btn_preview.clicked.connect(self.update_preview)
        self.btn_send_text.clicked.connect(self.send_text_update)
        self.btn_choose_image.clicked.connect(self.choose_image)
        self.btn_send_image.clicked.connect(self.send_image)
        self.btn_clear_image.clicked.connect(self.clear_lcd_image)
        self.btn_lcd_on.clicked.connect(lambda: self.send_lcd_command("on"))
        self.btn_lcd_off.clicked.connect(lambda: self.send_lcd_command("off"))
        self.btn_save_schedule.clicked.connect(self.save_lcd_schedule)
        self.logs_table.cellDoubleClicked.connect(lambda row, _col: self.show_log_detail(row))
        self.btn_view_log.clicked.connect(self.show_selected_log_detail)
        self.btn_export_logs_pdf.clicked.connect(self.export_logs_pdf)

        for w in [self.txt_name, self.txt_room, self.txt_diet, self.txt_allergies, self.txt_drinks, self.txt_schedule]:
            w.textChanged.connect(self.refresh_token_list)

        self.txt_note.textChanged.connect(self.refresh_token_list)

    # ---------------------------- page switching ----------------------------

    def set_active_menu(self, active_btn):
        buttons = [self.btn_menu_overview, self.btn_menu_dashboard, self.btn_menu_pairing, self.btn_menu_updates, self.btn_menu_logs]
        for btn in buttons:
            if btn == active_btn:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 18px;
                        background-color: #e2ab09;
                        color: #111111;
                        border: none;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 18px;
                        background-color: transparent;
                        color: #dddddd;
                        border: none;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #1f1f1f;
                    }
                """)

    def switch_page(self, page, btn):
        self.pages.setCurrentWidget(page)
        self.set_active_menu(btn)
        if page == self.page_overview:
            self.refresh_dashboard_summary()
        elif page == self.page_pairing:
            self.load_pairing_views()
        elif page == self.page_updates:
            self.load_update_targets()
            self.load_schedule_view()
            self.update_preview()
        elif page == self.page_logs:
            self.load_recent_logs()

    # ---------------------------- helpers ----------------------------

    def base_url(self):
        return self.base_url_edit.text().strip().rstrip("/")

    def selected_device_id(self):
        return self.upd_target.currentData()

    def schedule_on_time(self):
        return self.schedule_on.time().toString("HH:mm")

    def schedule_off_time(self):
        return self.schedule_off.time().toString("HH:mm")

    def current_resident_uid(self):
        return self.txt_uid.text().strip() or None

    def collect_resident_payload(self):
        return {
            "resident_uid": self.txt_uid.text().strip(),
            "full_name": self.txt_name.text().strip(),
            "room": self.txt_room.text().strip(),
            "diet": self.txt_diet.text().strip(),
            "allergies": self.txt_allergies.text().strip(),
            "note": self.txt_note.toPlainText().strip(),
            "drinks": self.txt_drinks.text().strip(),
            "schedule": self.txt_schedule.text().strip(),
            "source_document": self.selected_source_document,
            "safety_review_note": "Pending safety review" if self.chk_safety_review.isChecked() else "",
            "needs_safety_review": self.chk_safety_review.isChecked(),
            "lcd_image_path": self.selected_image_path,
            "lcd_schedule_enabled": getattr(self, "chk_schedule_enabled", self.chk_active).isChecked() if hasattr(self, "chk_schedule_enabled") else False,
            "lcd_on_time": self.schedule_on_time() if hasattr(self, "schedule_on") else None,
            "lcd_off_time": self.schedule_off_time() if hasattr(self, "schedule_off") else None,
            "sleep_if_no_image": self.chk_sleep_no_image.isChecked() if hasattr(self, "chk_sleep_no_image") else False,
            "active": self.chk_active.isChecked(),
        }

    def show_error(self, title, text):
        QMessageBox.critical(self, title, text)

    def show_info(self, title, text):
        QMessageBox.information(self, title, text)

    def attach_source_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Attach source document",
            "",
            "Documents (*.pdf *.doc *.docx *.txt *.png *.jpg *.jpeg);;All Files (*)"
        )
        if not path:
            return
        self.selected_source_document = path
        self.source_doc_label.setText(os.path.basename(path))

    # ---------------------------- resident management ----------------------------

    def new_resident(self):
        self.selected_resident_id = None
        self.clear_form()
        self.txt_uid.setText(generate_resident_uid())
        self.chk_active.setChecked(True)
        self.update_preview()

    def clear_form(self):
        self.txt_uid.clear()
        self.txt_name.clear()
        self.txt_room.clear()
        self.txt_diet.clear()
        self.txt_allergies.clear()
        self.txt_note.clear()
        self.txt_drinks.clear()
        self.txt_schedule.clear()

        self.chk_active.setChecked(True)
        self.chk_safety_review.setChecked(False)
        self.cmb_alert.setCurrentIndex(0)

        self.selected_image_path = None
        self.image_path_label.setText("No image selected")
        self.selected_source_document = None
        self.source_doc_label.setText("No source document attached")

        self.rules.clear()
        self.rules_list.clear()
        self.token_list.clear()

        self.update_lcd_image_preview()

    def load_residents(self):
        self.resident_list.clear()
        self.pair_resident_list.clear()

        for r in self.db.get_residents():
            label = f"{r['full_name']} | {r.get('room') or 'No room'} | {r['resident_uid']}"
            if r.get("paired_device_id"):
                status = "online" if r.get("paired_device_online") else "offline"
                label += f" | {status}: {r['paired_device_id']}"

            for lw in [self.resident_list, self.pair_resident_list]:
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, r["id"])
                lw.addItem(item)

    def filter_residents(self):
        query = self.search_resident.text().strip().lower()
        for i in range(self.resident_list.count()):
            item = self.resident_list.item(i)
            item.setHidden(query not in item.text().lower())

    def refresh_dashboard_summary(self):
        summary = self.db.get_dashboard_summary()
        titles = {
            "active_residents": "Active residents",
            "online_devices": "Online devices",
            "paired_devices": "Paired devices",
            "safety_reviews": "Safety reviews",
            "failed_updates": "Failed updates",
        }
        for key, title in titles.items():
            if hasattr(self, "record_summary_labels") and key in self.record_summary_labels:
                self.record_summary_labels[key].setText(f"{title}: {summary.get(key, 0)}")
        if hasattr(self, "record_summary_labels") and "database_mode" in self.record_summary_labels:
            mode = "local fallback" if summary.get("database_mode") == "sqlite" else "gateway database"
            self.record_summary_labels["database_mode"].setText(f"Data store: {mode}")

        overview_values = {
            "active_residents": summary.get("active_residents", 0),
            "known_devices": summary.get("known_devices", summary.get("online_devices", 0)),
            "paired_devices": summary.get("paired_devices", 0),
            "recent_activity": summary.get("recent_activity", 0),
            "online_devices": summary.get("online_devices", 0),
        }
        for key, value in overview_values.items():
            if hasattr(self, "summary_labels") and key in self.summary_labels:
                self.summary_labels[key].setText(str(value))
        if hasattr(self, "overview_status"):
            mode = "local fallback" if summary.get("database_mode") == "sqlite" else "gateway database"
            self.overview_status.setText(f"Data store: {mode}\nGateway: {self.connection_badge.text()}\nAuto-refresh: {'on' if self.auto_refresh.isChecked() else 'off'}")
        if hasattr(self, "overview_device_table"):
            self.load_overview_devices()

    def load_overview_devices(self):
        devices = self.db.get_devices()
        self.overview_device_table.setRowCount(len(devices))
        for r, d in enumerate(devices):
            values = [
                d.get("device_id") or "",
                "Online" if d.get("is_online") else "Offline",
                f"{d.get('battery_level')}%" if d.get("battery_level") is not None else "N/A",
                d.get("resident_name") or "Unassigned",
                str(d.get("last_seen_s") or ""),
            ]
            for c, value in enumerate(values):
                self.overview_device_table.setItem(r, c, QTableWidgetItem(str(value)))

    def load_schedule_view(self):
        if not hasattr(self, "schedule_resident"):
            return
        current_id = self.schedule_resident.currentData()
        self.schedule_resident.blockSignals(True)
        self.schedule_resident.clear()
        rows = self.db.get_schedule_rows()
        for row in rows:
            self.schedule_resident.addItem(f"{row['full_name']} ({row['resident_uid']})", row["id"])
        if current_id is not None:
            idx = self.schedule_resident.findData(current_id)
            if idx >= 0:
                self.schedule_resident.setCurrentIndex(idx)
        self.schedule_resident.blockSignals(False)

        self.schedule_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            times = f"{row.get('lcd_on_time') or '--:--'} - {row.get('lcd_off_time') or '--:--'}"
            image = "Ready" if row.get("lcd_image_path") else "No image"
            enabled = "Enabled" if row.get("lcd_schedule_enabled") else "Off"
            values = [
                row.get("full_name") or "",
                row.get("device_id") or "Unpaired",
                image,
                f"{enabled}: {times}",
            ]
            for c, value in enumerate(values):
                self.schedule_table.setItem(r, c, QTableWidgetItem(str(value)))

        selected = self.schedule_resident.currentData()
        if selected:
            row = self.db.get_resident(selected)
            if row:
                self.chk_schedule_enabled.setChecked(bool(row.get("lcd_schedule_enabled")))
                self.chk_sleep_no_image.setChecked(bool(row.get("sleep_if_no_image")))
                if row.get("lcd_on_time"):
                    self.schedule_on.setTime(QTime.fromString(row.get("lcd_on_time"), "HH:mm"))
                if row.get("lcd_off_time"):
                    self.schedule_off.setTime(QTime.fromString(row.get("lcd_off_time"), "HH:mm"))
                self.selected_resident_id = selected

    def show_profile_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Profile & Settings")
        dialog.resize(520, 420)
        layout = QVBoxLayout(dialog)
        body = QTextEdit(dialog)
        body.setReadOnly(True)
        body.setStyleSheet(self.input_style())
        body.setPlainText(
            f"User: {self.current_user.get('username', 'admin')}\n"
            f"Role: {self.current_user.get('role', 'ADMIN')}\n"
            f"Gateway URL: {self.base_url()}\n\n"
            "Configuration areas ready for later integration:\n"
            "- theme choice\n"
            "- add user\n"
            "- change password\n"
            "- gateway defaults\n"
            "- admin permissions"
        )
        layout.addWidget(body)
        close_btn = QPushButton("Close", dialog)
        close_btn.setStyleSheet(self.primary_btn_style())
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def on_resident_selected(self, item):
        resident_id = item.data(Qt.ItemDataRole.UserRole)
        row = self.db.get_resident(resident_id)
        if not row:
            return

        self.selected_resident_id = resident_id
        self.txt_uid.setText(row["resident_uid"] or "")
        self.txt_name.setText(row["full_name"] or "")
        self.txt_room.setText(row.get("room") or "")
        self.txt_diet.setText(row.get("diet") or "")
        self.txt_allergies.setText(row.get("allergies") or "")
        self.txt_note.setPlainText(row.get("note") or "")
        self.txt_drinks.setText(row.get("drinks") or "")
        self.txt_schedule.setText(row.get("schedule") or "")
        self.selected_source_document = row.get("source_document") or None
        self.source_doc_label.setText(os.path.basename(self.selected_source_document) if self.selected_source_document else "No source document attached")
        self.chk_safety_review.setChecked(bool(row.get("needs_safety_review", False)))
        self.selected_image_path = row.get("lcd_image_path") or None
        if self.selected_image_path and hasattr(self, "image_path_label"):
            self.image_path_label.setText(self.selected_image_path)
        self.chk_active.setChecked(bool(row.get("active", True)))

        self.update_preview()
        self.load_update_targets()

    def on_pair_resident_selected(self, item):
        resident_id = item.data(Qt.ItemDataRole.UserRole)
        row = self.db.get_resident(resident_id)
        if row:
            self.pair_info.setText(f"Selected resident:\n{row['full_name']} ({row['resident_uid']})")

    def save_resident(self):
        payload = self.collect_resident_payload()

        if not payload["resident_uid"]:
            payload["resident_uid"] = generate_resident_uid()
            self.txt_uid.setText(payload["resident_uid"])

        if not payload["full_name"]:
            self.show_error("Missing name", "Resident name is required.")
            return

        try:
            if self.selected_resident_id is None:
                self.selected_resident_id = self.db.create_resident(payload)
                action = "resident_create"
                message = "Resident created successfully"
            else:
                self.db.update_resident(self.selected_resident_id, payload)
                action = "resident_update"
                message = "Resident updated successfully"

            self.db.log_update(
                action,
                self.selected_resident_id,
                payload["resident_uid"],
                None,
                self.current_user.get("id"),
                self.current_user.get("username"),
                payload,
                {"saved": True},
                True,
                message
            )

            self.load_residents()
            self.load_recent_logs()
            self.load_pairing_views()
            self.refresh_dashboard_summary()
            self.send_saved_resident_if_paired()
            self.show_info("Saved", message)

        except Exception as e:
            self.show_error("Save failed", str(e))

    def send_saved_resident_if_paired(self):
        row = self.db.get_resident(self.selected_resident_id)
        device_id = row.get("paired_device_id") if row else None
        if not device_id:
            return

        payload = self.build_gateway_payload(device_id)
        try:
            result = self.gateway.send_text(self.base_url(), payload)
            success = result["status_code"] == 200
            message = "Saved resident sent to paired device" if success else f"Auto-send failed ({result['status_code']})"
            response = result["body"]
        except Exception as e:
            success = False
            message = f"Auto-send queued for later review: {e}"
            response = {"error": str(e)}

        self.db.log_update(
            "auto_send_after_save",
            self.selected_resident_id,
            self.current_resident_uid(),
            device_id,
            self.current_user.get("id"),
            self.current_user.get("username"),
            payload,
            response,
            success,
            message
        )
        self.load_recent_logs()

    # ---------------------------- devices / pairing ----------------------------

    def refresh_devices(self):
        try:
            devices = self.gateway.get_devices(self.base_url())
            self.db.upsert_devices(devices)
            self.connection_badge.setText("Gateway: Connected")
            self.connection_badge.setStyleSheet("""
                QLabel {
                    background-color: #16351f;
                    color: #76e28b;
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: 700;
                }
            """)
        except Exception as e:
            self.connection_badge.setText("Gateway: Offline")
            self.connection_badge.setStyleSheet("""
                QLabel {
                    background-color: #351616;
                    color: #ff9090;
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: 700;
                }
            """)
            self.db.log_update(
                "device_refresh",
                self.selected_resident_id,
                self.current_resident_uid(),
                None,
                self.current_user.get("id"),
                self.current_user.get("username"),
                {"base_url": self.base_url()},
                {"error": str(e)},
                False,
                f"Failed to refresh devices: {e}"
            )
            self.load_recent_logs()
            self.refresh_dashboard_summary()
            self.load_schedule_view()
            return

        self.load_update_targets()
        self.load_pairing_views()
        self.load_residents()
        self.load_recent_logs()
        self.refresh_dashboard_summary()
        self.load_schedule_view()

    def load_update_targets(self):
        self.upd_target.clear()
        for d in self.db.get_devices():
            status = "online" if d["is_online"] else "offline"
            paired = f" | {d['resident_name']}" if d.get("resident_name") else ""
            label = f"{status}: {d['device_id']} ({d.get('ip') or '-'}:{d.get('port') or '-'}){paired}"
            self.upd_target.addItem(label, d["device_id"])

    def load_pairing_views(self):
        self.available_devices_list.clear()
        devices = self.db.get_devices()

        self.pair_table.setRowCount(len(devices))
        for r, d in enumerate(devices):
            vals = [
                d["device_id"],
                d.get("resident_name") or "Unpaired",
                d.get("resident_uid") or "-",
                "Online" if d.get("is_online") else "Offline",
                f"{d.get('battery_level')}%" if d.get("battery_level") is not None else "N/A"
            ]
            for c, val in enumerate(vals):
                self.pair_table.setItem(r, c, QTableWidgetItem(val))

            icon = "online" if d["is_online"] else "offline"
            status = "paired" if d.get("resident_name") else "available"
            item = QListWidgetItem(f"{icon}: {d['device_id']} | {status}")
            item.setData(Qt.ItemDataRole.UserRole, d["device_id"])
            self.available_devices_list.addItem(item)

    def pair_selected_from_menu(self):
        resident_item = self.pair_resident_list.currentItem()
        device_item = self.available_devices_list.currentItem()

        if not resident_item:
            self.show_error("No resident", "Select a resident first.")
            return

        if not device_item:
            self.show_error("No device", "Select a device first.")
            return

        resident_id = resident_item.data(Qt.ItemDataRole.UserRole)
        device_id = device_item.data(Qt.ItemDataRole.UserRole)

        row = self.db.get_resident(resident_id)
        if not row:
            self.show_error("Not found", "Resident record was not found.")
            return

        try:
            self.db.pair_resident_to_device(resident_id, device_id)
            self.db.log_update(
                "pair_device",
                resident_id,
                row["resident_uid"],
                device_id,
                self.current_user.get("id"),
                self.current_user.get("username"),
                {"device_id": device_id},
                {"paired": True},
                True,
                f"{row['full_name']} paired to {device_id}"
            )
            self.push_resident_row_to_device(row, device_id, "auto_send_after_pair")
            self.refresh_devices()
            self.show_info("Paired", f"{row['full_name']} paired to {device_id}.")
        except Exception as e:
            self.show_error("Pair failed", str(e))

    def push_resident_row_to_device(self, row, device_id, action_type):
        payload = {
            "id": device_id,
            "name": row.get("full_name") or "",
            "room": row.get("room") or "",
            "note": row.get("note") or "",
            "drinks": row.get("drinks") or "",
        }
        if row.get("diet"):
            payload["diet"] = [x.strip() for x in row.get("diet").split(",") if x.strip()]
        if row.get("allergies"):
            payload["allergies"] = [x.strip() for x in row.get("allergies").split(",") if x.strip()]
        if row.get("schedule"):
            payload["schedule"] = row.get("schedule")
        try:
            result = self.gateway.send_text(self.base_url(), payload)
            success = result["status_code"] == 200
            message = "Latest resident text pushed after pairing" if success else f"Auto-push failed ({result['status_code']})"
            response = result["body"]
        except Exception as e:
            success = False
            message = f"Auto-push queued for review: {e}"
            response = {"error": str(e)}
        self.db.log_update(
            action_type,
            row.get("id"),
            row.get("resident_uid"),
            device_id,
            self.current_user.get("id"),
            self.current_user.get("username"),
            payload,
            response,
            success,
            message
        )

    def unpair_selected_from_menu(self):
        device_item = self.available_devices_list.currentItem()
        if not device_item:
            self.show_error("No device", "Select a device first.")
            return

        device_id = device_item.data(Qt.ItemDataRole.UserRole)
        try:
            self.db.unpair_device(device_id)
            self.db.log_update(
                "unpair_device",
                None,
                None,
                device_id,
                self.current_user.get("id"),
                self.current_user.get("username"),
                {"device_id": device_id},
                {"unpaired": True},
                True,
                f"Device {device_id} unpaired"
            )
            self.refresh_devices()
            self.show_info("Unpaired", f"{device_id} was unpaired.")
        except Exception as e:
            self.show_error("Unpair failed", str(e))

    # ---------------------------- highlights ----------------------------

    def section_text(self, section):
        section = section.upper()
        if section == "NAME":
            return self.txt_name.text().strip()
        if section == "ROOM":
            return self.txt_room.text().strip()
        if section == "DIET":
            return self.txt_diet.text().strip()
        if section == "ALLERGIES":
            return self.txt_allergies.text().strip()
        if section == "NOTE":
            return self.txt_note.toPlainText().strip()
        if section == "DRINKS":
            return self.txt_drinks.text().strip()
        return ""

    def extract_tokens(self, section):
        text = self.section_text(section)
        if not text:
            return []

        raw = re.split(r"[,\s;/]+", text)
        seen = set()
        out = []

        for w in raw:
            w = w.strip()
            if not w:
                continue
            key = w.lower()
            if key not in seen:
                seen.add(key)
                out.append(w.upper())

        return out

    def refresh_token_list(self):
        self.token_list.clear()
        for t in self.extract_tokens(self.hl_section.currentText()):
            self.token_list.addItem(QListWidgetItem(t))

    def apply_auto_fg(self):
        fg = auto_fg_for_bg(self.hl_bg.currentText())
        idx = self.hl_fg.findText(fg)
        if idx >= 0:
            self.hl_fg.setCurrentIndex(idx)

    def on_hl_type_changed(self):
        self.token_list.setEnabled("SECTION" not in self.hl_type.currentText())

    def rule_exists(self, rule):
        return any(
            r.type == rule.type and
            r.section == rule.section and
            r.value == rule.value and
            r.bg == rule.bg and
            r.fg == rule.fg
            for r in self.rules
        )

    def add_highlight(self):
        section = self.hl_section.currentText()
        bg = self.hl_bg.currentText()
        fg = self.hl_fg.currentText()

        if "SECTION" in self.hl_type.currentText():
            rule = HighlightRule("section", section, None, bg, fg)
            if not self.rule_exists(rule):
                self.rules.append(rule)
                self.rules_list.addItem(rule.label())
            return

        selected = self.token_list.selectedItems()
        if not selected:
            self.show_error("No words selected", "Select at least one word from the token list.")
            return

        for item in selected:
            rule = HighlightRule("value", section, item.text().strip().upper(), bg, fg)
            if not self.rule_exists(rule):
                self.rules.append(rule)
                self.rules_list.addItem(rule.label())

    def remove_selected_highlight(self):
        row = self.rules_list.currentRow()
        if row < 0:
            return
        self.rules_list.takeItem(row)
        self.rules.pop(row)

    def clear_highlights(self):
        self.rules.clear()
        self.rules_list.clear()

    # ---------------------------- preview ----------------------------

    def update_lcd_image_preview(self):
        if self.selected_image_path and os.path.isfile(self.selected_image_path):
            pix = QPixmap(self.selected_image_path)

            if not pix.isNull():
                big_pix = pix.scaled(
                    self.upd_lcd_image.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.upd_lcd_image.setPixmap(big_pix)
                self.upd_lcd_image.show()

                small_pix = pix.scaled(
                    self.lcd_image.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lcd_image.setPixmap(small_pix)
                self.lcd_image.show()

                self.upd_lcd_name.hide()
                self.upd_lcd_room.hide()
                self.upd_lcd_alert.hide()
                self.upd_lcd_note.hide()

                self.lcd_name.hide()
                self.lcd_room.hide()
                self.lcd_alert_banner.hide()
                self.lcd_note.hide()
                return

        self.upd_lcd_image.hide()
        self.lcd_image.hide()

        self.upd_lcd_name.show()
        self.upd_lcd_room.show()
        self.upd_lcd_alert.show()
        self.upd_lcd_note.show()

        self.lcd_name.show()
        self.lcd_room.show()
        self.lcd_alert_banner.show()
        self.lcd_note.show()

    def update_preview(self):
        name = self.txt_name.text().strip() or "Resident Name"
        room = self.txt_room.text().strip() or "---"
        diet = self.txt_diet.text().strip() or "---"
        allergies = self.txt_allergies.text().strip() or "---"
        note = self.txt_note.toPlainText().strip() or "---"
        alert = self.cmb_alert.currentText().upper()

        self.ep_name.setText(name)
        self.ep_room.setText(f"Room {room}")
        self.ep_diet.setText(f"Diet: {diet}")
        self.ep_allergies.setText(f"Allergies: {allergies}")
        self.ep_note.setText(f"Note: {note[:80]}")

        self.lcd_name.setText(name)
        self.lcd_room.setText(f"Room {room}")
        self.lcd_note.setText(note[:90])

        self.upd_ep_name.setText(name)
        self.upd_ep_room.setText(f"Room {room}")
        self.upd_ep_diet.setText(f"Diet: {diet}")
        self.upd_ep_allergies.setText(f"Allergies: {allergies}")
        self.upd_ep_note.setText(f"Note: {note[:120]}")

        self.upd_lcd_name.setText(name)
        self.upd_lcd_room.setText(f"Room {room}")
        self.upd_lcd_note.setText(note[:120])

        color = "#146c2e"
        if alert in ("NEEDS ATTENTION", "FALL RISK"):
            color = "#b45309"
        if alert == "EMERGENCY":
            color = "#b91c1c"

        self.lcd_alert_banner.setText(alert)
        self.lcd_alert_banner.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: white; border-radius: 10px; font-size: 16px; font-weight: 700; }}"
        )

        self.upd_lcd_alert.setText(alert)
        self.upd_lcd_alert.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: white; border-radius: 12px; font-size: 18px; font-weight: 700; }}"
        )

        self.update_lcd_image_preview()

    # ---------------------------- gateway payload / send ----------------------------

    def build_gateway_payload(self, device_id):
        payload = {"id": device_id}

        name = self.txt_name.text().strip()
        room = self.txt_room.text().strip()
        note = self.txt_note.toPlainText().strip()
        drinks = self.txt_drinks.text().strip()
        schedule = self.txt_schedule.text().strip()

        if name:
            payload["name"] = name
        if room:
            payload["room"] = room
        if note:
            payload["note"] = note
        if drinks:
            payload["drinks"] = drinks
        if schedule:
            payload["schedule"] = schedule

        diet = self.txt_diet.text().strip()
        allergies = self.txt_allergies.text().strip()

        if diet:
            payload["diet"] = [x.strip() for x in diet.split(",") if x.strip()]

        if allergies:
            payload["allergies"] = [x.strip() for x in allergies.split(",") if x.strip()]

        if self.rules:
            payload["highlights"] = [r.to_json() for r in self.rules]

        return payload

    def send_text_update(self):
        if not self.selected_resident_id:
            self.show_error("No resident", "Select or save a resident first.")
            return

        device_id = self.selected_device_id()
        if not device_id:
            self.show_error("No device", "Please select a device.")
            return

        payload = self.build_gateway_payload(device_id)

        try:
            result = self.gateway.send_text(self.base_url(), payload)
            success = result["status_code"] == 200
            message = "Text update sent successfully" if success else f"Text update failed ({result['status_code']})"

            self.db.log_update(
                "send_text",
                self.selected_resident_id,
                self.current_resident_uid(),
                device_id,
                self.current_user.get("id"),
                self.current_user.get("username"),
                payload,
                result["body"],
                success,
                message
            )

            self.load_recent_logs()
            self.refresh_devices()

            if success:
                self.show_info("Success", message)
            else:
                self.show_error("Send failed", f"{message}\n\n{result['body']}")

        except Exception as e:
            self.db.log_update(
                "send_text",
                self.selected_resident_id,
                self.current_resident_uid(),
                device_id,
                self.current_user.get("id"),
                self.current_user.get("username"),
                payload,
                {"error": str(e)},
                False,
                str(e)
            )
            self.load_recent_logs()
            self.show_error("Network Error", str(e))

    def send_lcd_command(self, command, device_id=None):
        device_id = device_id or self.selected_device_id()
        if not device_id:
            self.show_error("No device", "Please select a paired device first.")
            return
        payload = {"device_id": device_id, "command": command}
        try:
            result = self.gateway.send_lcd_command(self.base_url(), device_id, command)
            success = result["status_code"] == 200
            response = result["body"]
            message = f"LCD {command.upper()} command sent" if success else f"LCD command failed ({result['status_code']})"
        except Exception as e:
            success = False
            response = {"error": str(e)}
            message = f"LCD command queued for review: {e}"
        self.db.log_update(
            "lcd_command",
            self.selected_resident_id,
            self.current_resident_uid(),
            device_id,
            self.current_user.get("id"),
            self.current_user.get("username"),
            payload,
            response,
            success,
            message
        )
        self.load_recent_logs()
        if success:
            self.show_info("LCD Command", message)
        else:
            self.show_error("LCD Command", message)

    def save_lcd_schedule(self):
        resident_id = self.schedule_resident.currentData()
        if not resident_id:
            self.show_error("No resident", "Select a resident for the LCD schedule.")
            return
        row = self.db.get_resident(resident_id)
        if not row:
            self.show_error("Not found", "Resident record was not found.")
            return
        device_id = row.get("paired_device_id")
        enabled = self.chk_schedule_enabled.isChecked()
        on_time = self.schedule_on_time()
        off_time = self.schedule_off_time()
        sleep_if_no_image = self.chk_sleep_no_image.isChecked()
        self.db.save_resident_schedule(resident_id, enabled, on_time, off_time, sleep_if_no_image)

        payload = {
            "resident_uid": row.get("resident_uid"),
            "resident_id": resident_id,
            "device_id": device_id,
            "enabled": enabled,
            "lcd_on_time": on_time,
            "lcd_off_time": off_time,
            "sleep_if_no_image": sleep_if_no_image,
            "has_image": bool(row.get("lcd_image_path") or self.selected_image_path),
        }
        response = {"saved": True}
        success = True
        message = "LCD schedule saved"
        if device_id:
            try:
                result = self.gateway.save_schedule(self.base_url(), payload)
                success = result["status_code"] == 200
                response = result["body"]
                message = "LCD schedule saved to software and Pi" if success else f"Schedule saved locally; Pi returned {result['status_code']}"
            except Exception as e:
                success = False
                response = {"error": str(e)}
                message = f"Schedule saved locally; Pi update queued for review: {e}"

            if sleep_if_no_image and not payload["has_image"]:
                self.send_lcd_command("off", device_id)

        self.db.log_update(
            "save_schedule",
            resident_id,
            row.get("resident_uid"),
            device_id,
            self.current_user.get("id"),
            self.current_user.get("username"),
            payload,
            response,
            success,
            message
        )
        self.load_schedule_view()
        self.refresh_dashboard_summary()
        self.load_recent_logs()
        self.show_info("Schedule", message)

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose image for LCD",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return

        self.selected_image_path = path
        self.image_path_label.setText(path)
        self.update_lcd_image_preview()

    def clear_lcd_image(self):
        self.selected_image_path = None
        self.image_path_label.setText("No image selected")
        self.update_lcd_image_preview()

    def send_image(self):
        if not self.selected_resident_id:
            self.show_error("No resident", "Select or save a resident first.")
            return

        device_id = self.selected_device_id()
        if not device_id:
            self.show_error("No device", "Please select a device.")
            return

        if not self.selected_image_path or not os.path.isfile(self.selected_image_path):
            self.show_error("No image", "Choose a valid image first.")
            return

        payload = {"device_id": device_id, "image_path": self.selected_image_path}

        try:
            result = self.gateway.send_image(self.base_url(), device_id, self.selected_image_path)
            success = result["status_code"] == 200
            message = "Image sent successfully" if success else f"Image send failed ({result['status_code']})"

            self.db.log_update(
                "send_image",
                self.selected_resident_id,
                self.current_resident_uid(),
                device_id,
                self.current_user.get("id"),
                self.current_user.get("username"),
                payload,
                result["body"],
                success,
                message
            )

            self.load_recent_logs()
            self.refresh_devices()

            if success:
                self.show_info("Success", message)
            else:
                self.show_error("Send failed", f"{message}\n\n{result['body']}")

        except Exception as e:
            self.db.log_update(
                "send_image",
                self.selected_resident_id,
                self.current_resident_uid(),
                device_id,
                self.current_user.get("id"),
                self.current_user.get("username"),
                payload,
                {"error": str(e)},
                False,
                str(e)
            )
            self.load_recent_logs()
            self.show_error("Network Error", str(e))

    # ---------------------------- logs ----------------------------

    def load_recent_logs(self):
        rows = self.db.get_recent_logs(limit=50)
        self.logs_table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            created = self.db.format_timestamp(row.get("created_at"))
            values = [
                created,
                row.get("action_type") or "",
                row.get("resident_uid") or "",
                row.get("device_id") or "",
                row.get("pushed_by_username") or "",
                "Yes" if row.get("success") else "No",
                row.get("message") or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                self.logs_table.setItem(r, c, item)

    def selected_log_id(self):
        row = self.logs_table.currentRow()
        if row < 0:
            return None
        item = self.logs_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def show_selected_log_detail(self):
        row = self.logs_table.currentRow()
        if row < 0:
            self.show_error("No log selected", "Select a log row first.")
            return
        self.show_log_detail(row)

    def show_log_detail(self, row):
        item = self.logs_table.item(row, 0)
        log_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not log_id:
            return
        log = self.db.get_log(log_id)
        if not log:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Full Activity Log")
        dialog.resize(780, 620)
        layout = QVBoxLayout(dialog)

        body = QTextEdit(dialog)
        body.setReadOnly(True)
        body.setStyleSheet(self.input_style())
        body.setPlainText(self.format_log_detail(log))
        layout.addWidget(body)

        buttons = QHBoxLayout()
        export_btn = QPushButton("Export This Log PDF", dialog)
        export_btn.setStyleSheet(self.primary_btn_style())
        close_btn = QPushButton("Close", dialog)
        close_btn.setStyleSheet(self.secondary_btn_style())
        buttons.addWidget(export_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        export_btn.clicked.connect(lambda: self.export_log_pdf(log))
        close_btn.clicked.connect(dialog.accept)
        dialog.exec()

    def format_log_detail(self, log):
        return "\n".join([
            f"Date/Time: {self.db.format_timestamp(log.get('created_at'))}",
            f"Action: {log.get('action_type') or ''}",
            f"Resident UID: {log.get('resident_uid') or ''}",
            f"Device: {log.get('device_id') or ''}",
            f"Pushed By: {log.get('pushed_by_username') or ''}",
            f"Success: {'Yes' if log.get('success') else 'No'}",
            f"Message: {log.get('message') or ''}",
            "",
            "Payload:",
            self.pretty_json(log.get("payload_json")),
            "",
            "Response:",
            self.pretty_json(log.get("response_json")),
        ])

    def pretty_json(self, value):
        if value is None:
            return ""
        if not isinstance(value, str):
            return json.dumps(value, indent=2, default=str)
        try:
            return json.dumps(json.loads(value), indent=2)
        except Exception:
            return value

    def export_log_pdf(self, log):
        path, _ = QFileDialog.getSaveFileName(self, "Export log PDF", "activity-log.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self.write_pdf(path, self.format_log_detail(log))
        self.show_info("Exported", f"Log PDF saved to {path}")

    def export_logs_pdf(self):
        rows = self.db.get_recent_logs(limit=200)
        path, _ = QFileDialog.getSaveFileName(self, "Export logs PDF", "activity-logs.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        text = "\n\n".join(self.format_log_detail(row) for row in rows)
        self.write_pdf(path, text or "No logs available.")
        self.show_info("Exported", f"Logs PDF saved to {path}")

    def write_pdf(self, path, text):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        printer.setOutputFileName(path)
        doc = QTextDocument()
        doc.setPlainText(text)
        doc.print(printer)

    # ---------------------------- timers / window events ----------------------------

    def toggle_auto_refresh(self):
        if self.auto_refresh.isChecked():
            self.timer.start()
        else:
            self.timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos is not None and not self.is_custom_maximized:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "close_btn"):
            self.position_window_controls()

    def closeEvent(self, event):
        try:
            self.db.close()
        except Exception:
            pass
        event.accept()
