import os
import re
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView
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
        self.selected_resident_id: Optional[int] = None
        self.selected_image_path: Optional[str] = None
        self.rules: List[HighlightRule] = []
        self.logo_path = ASSETS_DIR / "Whisperwood-Villa-logo-removebg-preview.png"

        self.setWindowTitle("Whisperwood Villa Dashboard")
        self.setFixedSize(1520, 920)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.build_ui()
        self.bind_events()

        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.refresh_devices)

        self.new_resident()
        self.refresh_devices()
        self.load_residents()
        self.load_recent_logs()

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
            QPushButton:hover { background-color: #f0b814; }
            QPushButton:pressed { background-color: #c99508; }
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
            QPushButton:hover { background-color: #2a2a2a; }
        """

    def input_style(self):
        return """
            QLineEdit, QTextEdit, QComboBox {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #262626;
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #e2ab09;
            }
        """

    def label_style(self):
        return "font-size: 13px; font-weight: 600; color: #d7d7d7; background: transparent;"

    def prompt_install_update(self, installer_path: str):
        import subprocess
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Update Ready",
            "A new version has been downloaded. Install it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            subprocess.Popen([installer_path], shell=True)
            self.close()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setStyleSheet("QFrame { background-color: #0a0a0a; border-radius: 28px; color: white; }")
        root.addWidget(self.container)

        self.sidebar = QFrame(self.container)
        self.sidebar.setGeometry(12, 12, 245, 896)
        self.sidebar.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; }")

        self.logo = QLabel(self.sidebar)
        self.logo.setGeometry(22, 20, 200, 82)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.logo_path.exists():
            self.logo.setPixmap(QPixmap(str(self.logo_path)).scaled(175, 78, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo.setText("Whisperwood Villa")
            self.logo.setStyleSheet("font-size: 22px; font-weight: 700; color: #e2ab09;")

        self.user_card = QFrame(self.sidebar)
        self.user_card.setGeometry(18, 115, 208, 88)
        self.user_card.setStyleSheet("QFrame { background-color: #1a1a1a; border-radius: 16px; }")

        self.user_avatar = QLabel(self.user_card)
        self.user_avatar.setGeometry(12, 20, 48, 48)
        self.user_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_avatar.setText((self.current_user.get("username") or "U")[0].upper())
        self.user_avatar.setStyleSheet("QLabel { background-color: #e2ab09; color: #101010; border-radius: 24px; font-size: 18px; font-weight: 700; }")

        self.user_name = QLabel(self.user_card)
        self.user_name.setGeometry(72, 18, 120, 22)
        self.user_name.setText(self.current_user.get("username", "admin"))
        self.user_name.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.user_role = QLabel(self.user_card)
        self.user_role.setGeometry(72, 45, 120, 18)
        self.user_role.setText(str(self.current_user.get("role", "ADMIN")))
        self.user_role.setStyleSheet("font-size: 12px; color: #bdbdbd;")

        self.btn_menu_dashboard = QPushButton("Dashboard", self.sidebar)
        self.btn_menu_dashboard.setGeometry(18, 255, 208, 42)
        self.btn_menu_pairing = QPushButton("Resident Pairing", self.sidebar)
        self.btn_menu_pairing.setGeometry(18, 305, 208, 42)
        self.btn_menu_updates = QPushButton("Display Updates", self.sidebar)
        self.btn_menu_updates.setGeometry(18, 355, 208, 42)
        self.btn_menu_logs = QPushButton("Activity Logs", self.sidebar)
        self.btn_menu_logs.setGeometry(18, 405, 208, 42)
        for b in [self.btn_menu_dashboard, self.btn_menu_pairing, self.btn_menu_updates, self.btn_menu_logs]:
            b.setStyleSheet("""
                QPushButton {
                    text-align: left; padding-left: 18px; background-color: transparent; color: #dddddd;
                    border: none; border-radius: 12px; font-size: 14px; font-weight: 600;
                }
                QPushButton:hover { background-color: #1f1f1f; }
            """)

        self.btn_refresh_devices = QPushButton("Refresh Devices", self.sidebar)
        self.btn_refresh_devices.setGeometry(18, 500, 208, 42)
        self.btn_refresh_devices.setStyleSheet(self.secondary_btn_style())

        self.auto_refresh = QCheckBox("Auto-refresh every 3s", self.sidebar)
        self.auto_refresh.setGeometry(24, 555, 180, 24)
        self.auto_refresh.setStyleSheet("""
            QCheckBox { color: #d2d2d2; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px; border: 1px solid #888; background: transparent; }
            QCheckBox::indicator:checked { background-color: #e2ab09; border: 1px solid #e2ab09; }
        """)

        self.connection_badge = QLabel("Gateway: Unknown", self.sidebar)
        self.connection_badge.setGeometry(18, 610, 208, 28)
        self.connection_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_badge.setStyleSheet("QLabel { background-color: #1a1a1a; color: #cfcfcf; border-radius: 12px; font-size: 13px; font-weight: 700; }")

        self.title = QLabel("Whisperwood Villa Control Center", self.container)
        self.title.setGeometry(280, 22, 420, 32)
        self.title.setStyleSheet("font-size: 28px; font-weight: 700; color: white;")

        self.subtitle = QLabel("Resident records, device pairing, display updates, and logs", self.container)
        self.subtitle.setGeometry(280, 56, 450, 18)
        self.subtitle.setStyleSheet("font-size: 13px; color: #aaaaaa;")

        self.base_url_edit = QLineEdit(self.container)
        self.base_url_edit.setGeometry(1020, 24, 320, 42)
        self.base_url_edit.setText(DEFAULT_PI_BASE_URL)
        self.base_url_edit.setStyleSheet(self.input_style())

        self.close_btn = QPushButton("✕", self.container)
        self.close_btn.setGeometry(1460, 24, 38, 38)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #d6d6d6; border: none; font-size: 18px; font-weight: 700;
            }
            QPushButton:hover { color: white; background-color: rgba(255,255,255,0.08); border-radius: 19px; }
        """)

        self.pages = QStackedWidget(self.container)
        self.pages.setGeometry(280, 95, 1218, 805)
        self.pages.setStyleSheet("background: transparent;")

        self.page_dashboard = self.build_dashboard_page()
        self.page_pairing = self.build_pairing_page()
        self.page_updates = self.build_updates_page()
        self.page_logs = self.build_logs_page()
        for p in [self.page_dashboard, self.page_pairing, self.page_updates, self.page_logs]:
            self.pages.addWidget(p)
        self.pages.setCurrentWidget(self.page_dashboard)
        self.set_active_menu(self.btn_menu_dashboard)

    def build_dashboard_page(self):
        page = QWidget(); page.setStyleSheet("background: transparent;")
        self.residents_panel = QFrame(page)
        self.residents_panel.setGeometry(0, 0, 330, 805)
        self.residents_panel.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        QLabel("Residents", self.residents_panel).setGeometry(20, 18, 120, 24)
        self.residents_panel.children()[-1].setStyleSheet("font-size: 18px; font-weight: 700;")
        self.search_resident = QLineEdit(self.residents_panel)
        self.search_resident.setGeometry(18, 55, 294, 40)
        self.search_resident.setPlaceholderText("Search name, UID, room...")
        self.search_resident.setStyleSheet(self.input_style())
        self.resident_list = QListWidget(self.residents_panel)
        self.resident_list.setGeometry(18, 110, 294, 677)
        self.resident_list.setStyleSheet("""
            QListWidget { background-color: transparent; color: white; border: none; outline: none; font-size: 14px; }
            QListWidget::item { background-color: #1a1a1a; border-radius: 12px; padding: 12px; margin-bottom: 8px; }
            QListWidget::item:selected { background-color: #e2ab09; color: #111111; }
        """)

        self.form_panel = QFrame(page)
        self.form_panel.setGeometry(345, 0, 420, 805)
        self.form_panel.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        self.form_heading = QLabel("Resident Information", self.form_panel)
        self.form_heading.setGeometry(22, 18, 180, 24)
        self.form_heading.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.lbl_uid = QLabel("Resident UID", self.form_panel); self.lbl_uid.setGeometry(22, 58, 90, 18); self.lbl_uid.setStyleSheet(self.label_style())
        self.txt_uid = QLineEdit(self.form_panel); self.txt_uid.setGeometry(22, 80, 180, 42); self.txt_uid.setReadOnly(True); self.txt_uid.setStyleSheet(self.input_style())
        self.chk_active = QCheckBox("Resident enabled", self.form_panel); self.chk_active.setGeometry(230, 88, 140, 24); self.chk_active.setChecked(True)
        self.chk_active.setStyleSheet("""
            QCheckBox { color: #d2d2d2; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px; border: 1px solid #888; background: transparent; }
            QCheckBox::indicator:checked { background-color: #e2ab09; border: 1px solid #e2ab09; }
        """)
        self.lbl_name = QLabel("Full Name", self.form_panel); self.lbl_name.setGeometry(22, 130, 90, 18); self.lbl_name.setStyleSheet(self.label_style())
        self.txt_name = QLineEdit(self.form_panel); self.txt_name.setGeometry(22, 152, 376, 42); self.txt_name.setStyleSheet(self.input_style())
        self.lbl_room = QLabel("Room", self.form_panel); self.lbl_room.setGeometry(22, 205, 50, 18); self.lbl_room.setStyleSheet(self.label_style())
        self.txt_room = QLineEdit(self.form_panel); self.txt_room.setGeometry(22, 227, 120, 42); self.txt_room.setStyleSheet(self.input_style())
        self.lbl_alert = QLabel("Alert / Status", self.form_panel); self.lbl_alert.setGeometry(160, 205, 90, 18); self.lbl_alert.setStyleSheet(self.label_style())
        self.cmb_alert = QComboBox(self.form_panel); self.cmb_alert.setGeometry(160, 227, 160, 42); self.cmb_alert.addItems(["Stable", "Needs Attention", "Fall Risk", "Emergency"]); self.cmb_alert.setStyleSheet(self.input_style())
        self.lbl_diet = QLabel("Diet (comma list)", self.form_panel); self.lbl_diet.setGeometry(22, 280, 120, 18); self.lbl_diet.setStyleSheet(self.label_style())
        self.txt_diet = QLineEdit(self.form_panel); self.txt_diet.setGeometry(22, 302, 376, 42); self.txt_diet.setStyleSheet(self.input_style())
        self.lbl_allergies = QLabel("Allergies (comma list)", self.form_panel); self.lbl_allergies.setGeometry(22, 355, 140, 18); self.lbl_allergies.setStyleSheet(self.label_style())
        self.txt_allergies = QLineEdit(self.form_panel); self.txt_allergies.setGeometry(22, 377, 376, 42); self.txt_allergies.setStyleSheet(self.input_style())
        self.lbl_note = QLabel("Note", self.form_panel); self.lbl_note.setGeometry(22, 430, 60, 18); self.lbl_note.setStyleSheet(self.label_style())
        self.txt_note = QTextEdit(self.form_panel); self.txt_note.setGeometry(22, 452, 376, 80); self.txt_note.setStyleSheet(self.input_style())
        self.lbl_drinks = QLabel("Drinks", self.form_panel); self.lbl_drinks.setGeometry(22, 543, 60, 18); self.lbl_drinks.setStyleSheet(self.label_style())
        self.txt_drinks = QLineEdit(self.form_panel); self.txt_drinks.setGeometry(22, 565, 376, 42); self.txt_drinks.setStyleSheet(self.input_style())
        self.btn_new_resident = QPushButton("New Resident", self.form_panel); self.btn_new_resident.setGeometry(22, 630, 120, 44); self.btn_new_resident.setStyleSheet(self.secondary_btn_style())
        self.btn_save_resident = QPushButton("Save Resident", self.form_panel); self.btn_save_resident.setGeometry(152, 630, 120, 44); self.btn_save_resident.setStyleSheet(self.primary_btn_style())
        self.btn_clear_fields = QPushButton("Clear Form", self.form_panel); self.btn_clear_fields.setGeometry(282, 630, 116, 44); self.btn_clear_fields.setStyleSheet(self.secondary_btn_style())

        self.preview_panel = QFrame(page)
        self.preview_panel.setGeometry(780, 0, 438, 805)
        self.preview_panel.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        self.preview_heading = QLabel("Live Preview", self.preview_panel); self.preview_heading.setGeometry(22, 18, 120, 24); self.preview_heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.epaper_card = QFrame(self.preview_panel); self.epaper_card.setGeometry(22, 60, 394, 185); self.epaper_card.setStyleSheet("QFrame { background-color: #efefef; border-radius: 18px; }")
        QLabel("E-Paper Preview", self.epaper_card).setGeometry(16, 12, 120, 18); self.epaper_card.children()[-1].setStyleSheet("color: #111111; font-size: 13px; font-weight: 700;")
        self.ep_name = QLabel("Resident Name", self.epaper_card); self.ep_name.setGeometry(16, 40, 240, 28); self.ep_name.setStyleSheet("color: #111111; font-size: 22px; font-weight: 700;")
        self.ep_room = QLabel("Room ---", self.epaper_card); self.ep_room.setGeometry(16, 72, 180, 22); self.ep_room.setStyleSheet("color: #111111; font-size: 14px;")
        self.ep_diet = QLabel("Diet: ---", self.epaper_card); self.ep_diet.setGeometry(16, 98, 300, 22); self.ep_diet.setStyleSheet("color: #111111; font-size: 14px;")
        self.ep_allergies = QLabel("Allergies: ---", self.epaper_card); self.ep_allergies.setGeometry(16, 124, 350, 22); self.ep_allergies.setStyleSheet("color: #111111; font-size: 14px;")
        self.ep_note = QLabel("Note: ---", self.epaper_card); self.ep_note.setGeometry(16, 148, 350, 20); self.ep_note.setStyleSheet("color: #111111; font-size: 13px;")
        self.lcd_card = QFrame(self.preview_panel); self.lcd_card.setGeometry(22, 268, 394, 185); self.lcd_card.setStyleSheet("QFrame { background-color: #0a1831; border-radius: 18px; border: 2px solid #20457b; }")
        QLabel("LCD Preview", self.lcd_card).setGeometry(16, 12, 100, 18); self.lcd_card.children()[-1].setStyleSheet("color: white; font-size: 13px; font-weight: 700;")
        self.lcd_name = QLabel("Resident Name", self.lcd_card); self.lcd_name.setGeometry(20, 42, 354, 28); self.lcd_name.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lcd_name.setStyleSheet("color: white; font-size: 22px; font-weight: 700;")
        self.lcd_room = QLabel("Room ---", self.lcd_card); self.lcd_room.setGeometry(20, 72, 354, 22); self.lcd_room.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lcd_room.setStyleSheet("color: #d7e3f1; font-size: 14px;")
        self.lcd_alert_banner = QLabel("STABLE", self.lcd_card); self.lcd_alert_banner.setGeometry(92, 104, 210, 36); self.lcd_alert_banner.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lcd_alert_banner.setStyleSheet("QLabel { background-color: #146c2e; color: white; border-radius: 10px; font-size: 16px; font-weight: 700; }")
        self.lcd_note = QLabel("No note", self.lcd_card); self.lcd_note.setGeometry(20, 148, 354, 18); self.lcd_note.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lcd_note.setStyleSheet("color: #eef2f7; font-size: 13px;")
        return page

    def build_pairing_page(self):
        page = QWidget(); page.setStyleSheet("background: transparent;")
        self.pair_left = QFrame(page); self.pair_left.setGeometry(0, 0, 590, 805); self.pair_left.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        title = QLabel("Resident Pairing / Unpairing", self.pair_left); title.setGeometry(22, 18, 240, 24); title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.pair_resident_list = QListWidget(self.pair_left); self.pair_resident_list.setGeometry(20, 60, 260, 720)
        self.available_devices_list = QListWidget(self.pair_left); self.available_devices_list.setGeometry(310, 60, 260, 540)
        for lw in [self.pair_resident_list, self.available_devices_list]:
            lw.setStyleSheet("""
                QListWidget { background-color: #1a1a1a; color: white; border: 1px solid #262626; border-radius: 14px; padding: 6px; }
                QListWidget::item { padding: 10px; margin-bottom: 4px; border-radius: 10px; }
                QListWidget::item:selected { background-color: #e2ab09; color: #111111; }
            """)
        lbl_avail = QLabel("Available / Known Devices", self.pair_left); lbl_avail.setGeometry(310, 30, 180, 20); lbl_avail.setStyleSheet("font-size: 13px; color: #cfcfcf;")
        self.btn_pair_selected = QPushButton("Pair Selected Resident to Selected Device", self.pair_left); self.btn_pair_selected.setGeometry(310, 620, 260, 46); self.btn_pair_selected.setStyleSheet(self.primary_btn_style())
        self.btn_unpair_selected = QPushButton("Unpair Selected Device", self.pair_left); self.btn_unpair_selected.setGeometry(310, 678, 260, 46); self.btn_unpair_selected.setStyleSheet(self.secondary_btn_style())
        self.pair_info = QLabel("Select a resident and a device to pair.", self.pair_left); self.pair_info.setGeometry(310, 735, 260, 40); self.pair_info.setWordWrap(True); self.pair_info.setStyleSheet("font-size: 12px; color: #a8a8a8;")
        self.pair_right = QFrame(page); self.pair_right.setGeometry(610, 0, 608, 805); self.pair_right.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        self.pair_table = QTableWidget(self.pair_right); self.pair_table.setGeometry(18, 18, 572, 768); self.pair_table.setColumnCount(5)
        self.pair_table.setHorizontalHeaderLabels(["Device ID", "Resident", "Resident UID", "Online", "Last Seen(s)"])
        self.pair_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pair_table.setStyleSheet("""
            QTableWidget { background-color: #121212; color: white; border: 1px solid #1f1f1f; border-radius: 14px; gridline-color: #262626; font-size: 12px; }
            QHeaderView::section { background-color: #1a1a1a; color: #d7d7d7; padding: 8px; border: none; font-weight: 700; }
        """)
        self.pair_table.verticalHeader().setVisible(False); self.pair_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return page

    def build_updates_page(self):
        page = QWidget(); page.setStyleSheet("background: transparent;")
        self.upd_left = QFrame(page); self.upd_left.setGeometry(0, 0, 540, 805); self.upd_left.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        title = QLabel("Display Updates", self.upd_left); title.setGeometry(22, 18, 160, 24); title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.upd_target = QComboBox(self.upd_left); self.upd_target.setGeometry(22, 58, 490, 42); self.upd_target.setStyleSheet(self.input_style())
        self.hl_type = QComboBox(self.upd_left); self.hl_type.setGeometry(22, 118, 220, 38); self.hl_type.addItems(["Word highlight (VALUE)", "Section highlight (SECTION)"]); self.hl_type.setStyleSheet(self.input_style())
        self.hl_section = QComboBox(self.upd_left); self.hl_section.setGeometry(252, 118, 100, 38); self.hl_section.addItems(SECTIONS); self.hl_section.setStyleSheet(self.input_style())
        self.hl_bg = QComboBox(self.upd_left); self.hl_bg.setGeometry(362, 118, 70, 38); self.hl_bg.addItems(PALETTE); self.hl_bg.setStyleSheet(self.input_style())
        self.hl_fg = QComboBox(self.upd_left); self.hl_fg.setGeometry(442, 118, 70, 38); self.hl_fg.addItems(PALETTE); self.hl_fg.setStyleSheet(self.input_style())
        lbl_tokens = QLabel("Pick exact screen words only", self.upd_left); lbl_tokens.setGeometry(22, 168, 160, 18); lbl_tokens.setStyleSheet(self.label_style())
        self.token_list = QListWidget(self.upd_left); self.token_list.setGeometry(22, 192, 320, 120); self.token_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection); self.token_list.setStyleSheet("QListWidget { background-color: #1a1a1a; color: white; border: 1px solid #262626; border-radius: 12px; padding: 6px; }")
        self.rules_list = QListWidget(self.upd_left); self.rules_list.setGeometry(22, 340, 320, 120); self.rules_list.setStyleSheet("QListWidget { background-color: #1a1a1a; color: white; border: 1px solid #262626; border-radius: 12px; padding: 6px; }")
        self.btn_add_highlight = QPushButton("Add Highlight", self.upd_left); self.btn_add_highlight.setGeometry(360, 192, 152, 38); self.btn_add_highlight.setStyleSheet(self.secondary_btn_style())
        self.btn_remove_highlight = QPushButton("Remove Selected", self.upd_left); self.btn_remove_highlight.setGeometry(360, 238, 152, 38); self.btn_remove_highlight.setStyleSheet(self.secondary_btn_style())
        self.btn_clear_highlights = QPushButton("Clear Highlights", self.upd_left); self.btn_clear_highlights.setGeometry(360, 284, 152, 38); self.btn_clear_highlights.setStyleSheet(self.secondary_btn_style())
        self.btn_preview = QPushButton("Preview Update", self.upd_left); self.btn_preview.setGeometry(360, 340, 152, 42); self.btn_preview.setStyleSheet(self.primary_btn_style())
        self.btn_send_text = QPushButton("Send Text Update", self.upd_left); self.btn_send_text.setGeometry(360, 392, 152, 42); self.btn_send_text.setStyleSheet(self.primary_btn_style())
        self.btn_choose_image = QPushButton("Choose LCD Image", self.upd_left); self.btn_choose_image.setGeometry(22, 488, 150, 42); self.btn_choose_image.setStyleSheet(self.secondary_btn_style())
        self.btn_send_image = QPushButton("Send Image", self.upd_left); self.btn_send_image.setGeometry(182, 488, 120, 42); self.btn_send_image.setStyleSheet(self.secondary_btn_style())
        self.image_path_label = QLabel("No image selected", self.upd_left); self.image_path_label.setGeometry(22, 540, 490, 40); self.image_path_label.setWordWrap(True); self.image_path_label.setStyleSheet("font-size: 12px; color: #a7a7a7;")
        self.upd_right = QFrame(page); self.upd_right.setGeometry(560, 0, 658, 805); self.upd_right.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        self.upd_epaper_card = QFrame(self.upd_right); self.upd_epaper_card.setGeometry(22, 22, 614, 260); self.upd_epaper_card.setStyleSheet("QFrame { background-color: #efefef; border-radius: 18px; }")
        QLabel("E-Paper Preview", self.upd_epaper_card).setGeometry(18, 14, 120, 18); self.upd_epaper_card.children()[-1].setStyleSheet("color: #111111; font-size: 13px; font-weight: 700;")
        self.upd_ep_name = QLabel("Resident Name", self.upd_epaper_card); self.upd_ep_name.setGeometry(18, 44, 320, 30); self.upd_ep_name.setStyleSheet("color: #111111; font-size: 24px; font-weight: 700;")
        self.upd_ep_room = QLabel("Room ---", self.upd_epaper_card); self.upd_ep_room.setGeometry(18, 80, 250, 24); self.upd_ep_room.setStyleSheet("color: #111111; font-size: 15px;")
        self.upd_ep_diet = QLabel("Diet: ---", self.upd_epaper_card); self.upd_ep_diet.setGeometry(18, 112, 400, 24); self.upd_ep_diet.setStyleSheet("color: #111111; font-size: 14px;")
        self.upd_ep_allergies = QLabel("Allergies: ---", self.upd_epaper_card); self.upd_ep_allergies.setGeometry(18, 144, 500, 24); self.upd_ep_allergies.setStyleSheet("color: #111111; font-size: 14px;")
        self.upd_ep_note = QLabel("Note: ---", self.upd_epaper_card); self.upd_ep_note.setGeometry(18, 176, 560, 22); self.upd_ep_note.setStyleSheet("color: #111111; font-size: 13px;")
        self.upd_lcd_card = QFrame(self.upd_right); self.upd_lcd_card.setGeometry(22, 304, 614, 260); self.upd_lcd_card.setStyleSheet("QFrame { background-color: #0a1831; border-radius: 18px; border: 2px solid #20457b; }")
        QLabel("LCD Preview", self.upd_lcd_card).setGeometry(18, 14, 120, 18); self.upd_lcd_card.children()[-1].setStyleSheet("color: white; font-size: 13px; font-weight: 700;")
        self.upd_lcd_name = QLabel("Resident Name", self.upd_lcd_card); self.upd_lcd_name.setGeometry(20, 54, 574, 32); self.upd_lcd_name.setAlignment(Qt.AlignmentFlag.AlignCenter); self.upd_lcd_name.setStyleSheet("color: white; font-size: 28px; font-weight: 700;")
        self.upd_lcd_room = QLabel("Room ---", self.upd_lcd_card); self.upd_lcd_room.setGeometry(20, 94, 574, 22); self.upd_lcd_room.setAlignment(Qt.AlignmentFlag.AlignCenter); self.upd_lcd_room.setStyleSheet("color: #d7e3f1; font-size: 15px;")
        self.upd_lcd_alert = QLabel("STABLE", self.upd_lcd_card); self.upd_lcd_alert.setGeometry(202, 134, 210, 40); self.upd_lcd_alert.setAlignment(Qt.AlignmentFlag.AlignCenter); self.upd_lcd_alert.setStyleSheet("QLabel { background-color: #146c2e; color: white; border-radius: 12px; font-size: 18px; font-weight: 700; }")
        self.upd_lcd_note = QLabel("No note", self.upd_lcd_card); self.upd_lcd_note.setGeometry(20, 196, 574, 20); self.upd_lcd_note.setAlignment(Qt.AlignmentFlag.AlignCenter); self.upd_lcd_note.setStyleSheet("color: #eef2f7; font-size: 14px;")
        return page

    def build_logs_page(self):
        page = QWidget(); page.setStyleSheet("background: transparent;")
        self.logs_panel = QFrame(page); self.logs_panel.setGeometry(0, 0, 1218, 805); self.logs_panel.setStyleSheet("QFrame { background-color: #121212; border-radius: 22px; border: 1px solid #1f1f1f; }")
        lbl = QLabel("Activity Logs", self.logs_panel); lbl.setGeometry(22, 18, 160, 24); lbl.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.logs_table = QTableWidget(self.logs_panel); self.logs_table.setGeometry(18, 58, 1180, 728); self.logs_table.setColumnCount(7)
        self.logs_table.setHorizontalHeaderLabels(["Date/Time", "Action", "Resident UID", "Device", "Pushed By", "Success", "Message"])
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.logs_table.setStyleSheet("""
            QTableWidget { background-color: #121212; color: white; border: 1px solid #1f1f1f; border-radius: 14px; gridline-color: #262626; font-size: 12px; }
            QHeaderView::section { background-color: #1a1a1a; color: #d7d7d7; padding: 8px; border: none; font-weight: 700; }
        """)
        self.logs_table.verticalHeader().setVisible(False); self.logs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return page

    def bind_events(self):
        self.close_btn.clicked.connect(self.close)
        self.btn_refresh_devices.clicked.connect(self.refresh_devices)
        self.auto_refresh.stateChanged.connect(self.toggle_auto_refresh)
        self.btn_menu_dashboard.clicked.connect(lambda: self.switch_page(self.page_dashboard, self.btn_menu_dashboard))
        self.btn_menu_pairing.clicked.connect(lambda: self.switch_page(self.page_pairing, self.btn_menu_pairing))
        self.btn_menu_updates.clicked.connect(lambda: self.switch_page(self.page_updates, self.btn_menu_updates))
        self.btn_menu_logs.clicked.connect(lambda: self.switch_page(self.page_logs, self.btn_menu_logs))
        self.btn_new_resident.clicked.connect(self.new_resident)
        self.btn_save_resident.clicked.connect(self.save_resident)
        self.btn_clear_fields.clicked.connect(self.clear_form)
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
        for w in [self.txt_name, self.txt_room, self.txt_diet, self.txt_allergies, self.txt_drinks]:
            w.textChanged.connect(self.refresh_token_list)
        self.txt_note.textChanged.connect(self.refresh_token_list)

    def set_active_menu(self, active_btn):
        buttons = [self.btn_menu_dashboard, self.btn_menu_pairing, self.btn_menu_updates, self.btn_menu_logs]
        for btn in buttons:
            if btn == active_btn:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding-left: 18px; background-color: #e2ab09; color: #111111;
                        border: none; border-radius: 12px; font-size: 14px; font-weight: 700;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding-left: 18px; background-color: transparent; color: #dddddd;
                        border: none; border-radius: 12px; font-size: 14px; font-weight: 600;
                    }
                    QPushButton:hover { background-color: #1f1f1f; }
                """)

    def switch_page(self, page, btn):
        self.pages.setCurrentWidget(page)
        self.set_active_menu(btn)
        if page == self.page_pairing:
            self.load_pairing_views()
        elif page == self.page_updates:
            self.load_update_targets(); self.update_preview()
        elif page == self.page_logs:
            self.load_recent_logs()

    def base_url(self):
        return self.base_url_edit.text().strip().rstrip("/")

    def selected_device_id(self):
        return self.upd_target.currentData()

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
            "active": self.chk_active.isChecked(),
        }

    def show_error(self, title, text):
        QMessageBox.critical(self, title, text)

    def show_info(self, title, text):
        QMessageBox.information(self, title, text)

    def new_resident(self):
        self.selected_resident_id = None
        self.clear_form()
        self.txt_uid.setText(generate_resident_uid())
        self.chk_active.setChecked(True)
        self.update_preview()

    def clear_form(self):
        self.txt_uid.clear(); self.txt_name.clear(); self.txt_room.clear(); self.txt_diet.clear(); self.txt_allergies.clear(); self.txt_note.clear(); self.txt_drinks.clear()
        self.chk_active.setChecked(True); self.cmb_alert.setCurrentIndex(0); self.selected_image_path = None; self.image_path_label.setText("No image selected")
        self.rules.clear(); self.rules_list.clear(); self.token_list.clear()

    def load_residents(self):
        self.resident_list.clear(); self.pair_resident_list.clear()
        for r in self.db.get_residents():
            label = f"{r['full_name']}  •  {r.get('room') or 'No room'}  •  {r['resident_uid']}"
            if r.get("paired_device_id"):
                icon = "🟢" if r.get("paired_device_online") else "🔴"
                label += f"  •  {icon} {r['paired_device_id']}"
            for lw in [self.resident_list, self.pair_resident_list]:
                item = QListWidgetItem(label); item.setData(Qt.ItemDataRole.UserRole, r['id']); lw.addItem(item)

    def filter_residents(self):
        query = self.search_resident.text().strip().lower()
        for i in range(self.resident_list.count()):
            item = self.resident_list.item(i)
            item.setHidden(query not in item.text().lower())

    def on_resident_selected(self, item):
        resident_id = item.data(Qt.ItemDataRole.UserRole)
        row = self.db.get_resident(resident_id)
        if not row: return
        self.selected_resident_id = resident_id
        self.txt_uid.setText(row['resident_uid'] or '')
        self.txt_name.setText(row['full_name'] or '')
        self.txt_room.setText(row.get('room') or '')
        self.txt_diet.setText(row.get('diet') or '')
        self.txt_allergies.setText(row.get('allergies') or '')
        self.txt_note.setPlainText(row.get('note') or '')
        self.txt_drinks.setText(row.get('drinks') or '')
        self.chk_active.setChecked(bool(row.get('active', True)))
        self.update_preview(); self.load_update_targets()

    def on_pair_resident_selected(self, item):
        resident_id = item.data(Qt.ItemDataRole.UserRole)
        row = self.db.get_resident(resident_id)
        if row:
            self.pair_info.setText(f"Selected resident:\n{row['full_name']} ({row['resident_uid']})")

    def save_resident(self):
        payload = self.collect_resident_payload()
        if not payload['resident_uid']:
            payload['resident_uid'] = generate_resident_uid(); self.txt_uid.setText(payload['resident_uid'])
        if not payload['full_name']:
            self.show_error('Missing name', 'Resident name is required.'); return
        try:
            if self.selected_resident_id is None:
                self.selected_resident_id = self.db.create_resident(payload)
                action = 'resident_create'; message = 'Resident created successfully'
            else:
                self.db.update_resident(self.selected_resident_id, payload)
                action = 'resident_update'; message = 'Resident updated successfully'
            self.db.log_update(action, self.selected_resident_id, payload['resident_uid'], None,
                               self.current_user.get('id'), self.current_user.get('username'), payload,
                               {'saved': True}, True, message)
            self.load_residents(); self.load_recent_logs(); self.load_pairing_views(); self.show_info('Saved', message)
        except Exception as e:
            self.show_error('Save failed', str(e))

    def refresh_devices(self):
        try:
            devices = self.gateway.get_devices(self.base_url())
            self.db.upsert_devices(devices)
            self.connection_badge.setText('Gateway: Connected')
            self.connection_badge.setStyleSheet("QLabel { background-color: #16351f; color: #76e28b; border-radius: 12px; font-size: 13px; font-weight: 700; }")
        except Exception as e:
            self.connection_badge.setText('Gateway: Offline')
            self.connection_badge.setStyleSheet("QLabel { background-color: #351616; color: #ff9090; border-radius: 12px; font-size: 13px; font-weight: 700; }")
            self.db.log_update('device_refresh', self.selected_resident_id, self.current_resident_uid(), None,
                               self.current_user.get('id'), self.current_user.get('username'),
                               {'base_url': self.base_url()}, {'error': str(e)}, False, f'Failed to refresh devices: {e}')
            self.load_recent_logs(); return
        self.load_update_targets(); self.load_pairing_views(); self.load_residents(); self.load_recent_logs()

    def load_update_targets(self):
        self.upd_target.clear()
        for d in self.db.get_devices():
            icon = '🟢' if d['is_online'] else '🔴'
            paired = f" • {d['resident_name']}" if d.get('resident_name') else ''
            label = f"{icon} {d['device_id']} ({d.get('ip') or '-'}:{d.get('port') or '-'}){paired}"
            self.upd_target.addItem(label, d['device_id'])

    def load_pairing_views(self):
        self.available_devices_list.clear()
        devices = self.db.get_devices()
        self.pair_table.setRowCount(len(devices))
        for r, d in enumerate(devices):
            vals = [d['device_id'], d.get('resident_name') or 'Unpaired', d.get('resident_uid') or '-', 'Online' if d.get('is_online') else 'Offline', str(d.get('last_seen_s') or '')]
            for c, val in enumerate(vals):
                self.pair_table.setItem(r, c, QTableWidgetItem(val))
            icon = '🟢' if d['is_online'] else '🔴'
            status = 'paired' if d.get('resident_name') else 'available'
            item = QListWidgetItem(f"{icon} {d['device_id']} • {status}")
            item.setData(Qt.ItemDataRole.UserRole, d['device_id'])
            self.available_devices_list.addItem(item)

    def pair_selected_from_menu(self):
        resident_item = self.pair_resident_list.currentItem(); device_item = self.available_devices_list.currentItem()
        if not resident_item: self.show_error('No resident', 'Select a resident first.'); return
        if not device_item: self.show_error('No device', 'Select a device first.'); return
        resident_id = resident_item.data(Qt.ItemDataRole.UserRole); device_id = device_item.data(Qt.ItemDataRole.UserRole)
        row = self.db.get_resident(resident_id)
        if not row: self.show_error('Not found', 'Resident record was not found.'); return
        try:
            self.db.pair_resident_to_device(resident_id, device_id)
            self.db.log_update('pair_device', resident_id, row['resident_uid'], device_id, self.current_user.get('id'), self.current_user.get('username'), {'device_id': device_id}, {'paired': True}, True, f"{row['full_name']} paired to {device_id}")
            self.refresh_devices(); self.show_info('Paired', f"{row['full_name']} paired to {device_id}.")
        except Exception as e:
            self.show_error('Pair failed', str(e))

    def unpair_selected_from_menu(self):
        device_item = self.available_devices_list.currentItem()
        if not device_item: self.show_error('No device', 'Select a device first.'); return
        device_id = device_item.data(Qt.ItemDataRole.UserRole)
        try:
            self.db.unpair_device(device_id)
            self.db.log_update('unpair_device', None, None, device_id, self.current_user.get('id'), self.current_user.get('username'), {'device_id': device_id}, {'unpaired': True}, True, f'Device {device_id} unpaired')
            self.refresh_devices(); self.show_info('Unpaired', f'{device_id} was unpaired.')
        except Exception as e:
            self.show_error('Unpair failed', str(e))

    def section_text(self, section):
        section = section.upper()
        if section == 'NAME': return self.txt_name.text().strip()
        if section == 'ROOM': return self.txt_room.text().strip()
        if section == 'DIET': return self.txt_diet.text().strip()
        if section == 'ALLERGIES': return self.txt_allergies.text().strip()
        if section == 'NOTE': return self.txt_note.toPlainText().strip()
        if section == 'DRINKS': return self.txt_drinks.text().strip()
        return ''

    def extract_tokens(self, section):
        text = self.section_text(section)
        if not text: return []
        raw = re.split(r"[,\s;/]+", text)
        seen, out = set(), []
        for w in raw:
            w = w.strip()
            if not w: continue
            key = w.lower()
            if key not in seen:
                seen.add(key); out.append(w.upper())
        return out

    def refresh_token_list(self):
        self.token_list.clear()
        for t in self.extract_tokens(self.hl_section.currentText()):
            self.token_list.addItem(QListWidgetItem(t))

    def apply_auto_fg(self):
        fg = auto_fg_for_bg(self.hl_bg.currentText())
        idx = self.hl_fg.findText(fg)
        if idx >= 0: self.hl_fg.setCurrentIndex(idx)

    def on_hl_type_changed(self):
        self.token_list.setEnabled('SECTION' not in self.hl_type.currentText())

    def rule_exists(self, rule):
        return any(r.type == rule.type and r.section == rule.section and r.value == rule.value and r.bg == rule.bg and r.fg == rule.fg for r in self.rules)

    def add_highlight(self):
        section, bg, fg = self.hl_section.currentText(), self.hl_bg.currentText(), self.hl_fg.currentText()
        if 'SECTION' in self.hl_type.currentText():
            rule = HighlightRule('section', section, None, bg, fg)
            if not self.rule_exists(rule): self.rules.append(rule); self.rules_list.addItem(rule.label())
            return
        selected = self.token_list.selectedItems()
        if not selected: self.show_error('No words selected', 'Select at least one word from the token list.'); return
        for item in selected:
            rule = HighlightRule('value', section, item.text().strip().upper(), bg, fg)
            if not self.rule_exists(rule): self.rules.append(rule); self.rules_list.addItem(rule.label())

    def remove_selected_highlight(self):
        row = self.rules_list.currentRow()
        if row < 0: return
        self.rules_list.takeItem(row); self.rules.pop(row)

    def clear_highlights(self):
        self.rules.clear(); self.rules_list.clear()

    def update_preview(self):
        name = self.txt_name.text().strip() or 'Resident Name'
        room = self.txt_room.text().strip() or '---'
        diet = self.txt_diet.text().strip() or '---'
        allergies = self.txt_allergies.text().strip() or '---'
        note = self.txt_note.toPlainText().strip() or '---'
        alert = self.cmb_alert.currentText().upper()
        self.ep_name.setText(name); self.ep_room.setText(f'Room {room}'); self.ep_diet.setText(f'Diet: {diet}'); self.ep_allergies.setText(f'Allergies: {allergies}'); self.ep_note.setText(f'Note: {note[:42]}')
        self.lcd_name.setText(name); self.lcd_room.setText(f'Room {room}'); self.lcd_note.setText(note[:40])
        self.upd_ep_name.setText(name); self.upd_ep_room.setText(f'Room {room}'); self.upd_ep_diet.setText(f'Diet: {diet}'); self.upd_ep_allergies.setText(f'Allergies: {allergies}'); self.upd_ep_note.setText(f'Note: {note[:60]}')
        self.upd_lcd_name.setText(name); self.upd_lcd_room.setText(f'Room {room}'); self.upd_lcd_note.setText(note[:55])
        color = '#146c2e'
        if alert in ('NEEDS ATTENTION', 'FALL RISK'): color = '#b45309'
        if alert == 'EMERGENCY': color = '#b91c1c'
        for lbl in [self.lcd_alert_banner, self.upd_lcd_alert]:
            lbl.setText(alert)
            lbl.setStyleSheet(f"QLabel {{ background-color: {color}; color: white; border-radius: 12px; font-size: 18px; font-weight: 700; }}")

    def build_gateway_payload(self, device_id):
        payload = {'id': device_id}
        name = self.txt_name.text().strip(); room = self.txt_room.text().strip(); note = self.txt_note.toPlainText().strip(); drinks = self.txt_drinks.text().strip()
        if name: payload['name'] = name
        if room: payload['room'] = room
        if note: payload['note'] = note
        if drinks: payload['drinks'] = drinks
        diet = self.txt_diet.text().strip(); allergies = self.txt_allergies.text().strip()
        if diet: payload['diet'] = [x.strip() for x in diet.split(',') if x.strip()]
        if allergies: payload['allergies'] = [x.strip() for x in allergies.split(',') if x.strip()]
        if self.rules: payload['highlights'] = [r.to_json() for r in self.rules]
        return payload

    def send_text_update(self):
        if not self.selected_resident_id: self.show_error('No resident', 'Select or save a resident first.'); return
        device_id = self.selected_device_id()
        if not device_id: self.show_error('No device', 'Please select a device.'); return
        payload = self.build_gateway_payload(device_id)
        try:
            result = self.gateway.send_text(self.base_url(), payload)
            success = result['status_code'] == 200
            message = 'Text update sent successfully' if success else f"Text update failed ({result['status_code']})"
            self.db.log_update('send_text', self.selected_resident_id, self.current_resident_uid(), device_id, self.current_user.get('id'), self.current_user.get('username'), payload, result['body'], success, message)
            self.load_recent_logs(); self.refresh_devices()
            if success: self.show_info('Success', message)
            else: self.show_error('Send failed', f"{message}\n\n{result['body']}")
        except Exception as e:
            self.db.log_update('send_text', self.selected_resident_id, self.current_resident_uid(), device_id, self.current_user.get('id'), self.current_user.get('username'), payload, {'error': str(e)}, False, str(e))
            self.load_recent_logs(); self.show_error('Network Error', str(e))

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose image for LCD', '', 'Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if not path: return
        self.selected_image_path = path; self.image_path_label.setText(path)

    def send_image(self):
        if not self.selected_resident_id: self.show_error('No resident', 'Select or save a resident first.'); return
        device_id = self.selected_device_id()
        if not device_id: self.show_error('No device', 'Please select a device.'); return
        if not self.selected_image_path or not os.path.isfile(self.selected_image_path): self.show_error('No image', 'Choose a valid image first.'); return
        payload = {'device_id': device_id, 'image_path': self.selected_image_path}
        try:
            result = self.gateway.send_image(self.base_url(), device_id, self.selected_image_path)
            success = result['status_code'] == 200
            message = 'Image sent successfully' if success else f"Image send failed ({result['status_code']})"
            self.db.log_update('send_image', self.selected_resident_id, self.current_resident_uid(), device_id, self.current_user.get('id'), self.current_user.get('username'), payload, result['body'], success, message)
            self.load_recent_logs(); self.refresh_devices()
            if success: self.show_info('Success', message)
            else: self.show_error('Send failed', f"{message}\n\n{result['body']}")
        except Exception as e:
            self.db.log_update('send_image', self.selected_resident_id, self.current_resident_uid(), device_id, self.current_user.get('id'), self.current_user.get('username'), payload, {'error': str(e)}, False, str(e))
            self.load_recent_logs(); self.show_error('Network Error', str(e))

    def load_recent_logs(self):
        rows = self.db.get_recent_logs(limit=50)
        self.logs_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            created = row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else ''
            values = [created, row.get('action_type') or '', row.get('resident_uid') or '', row.get('device_id') or '', row.get('pushed_by_username') or '', 'Yes' if row.get('success') else 'No', row.get('message') or '']
            for c, value in enumerate(values):
                self.logs_table.setItem(r, c, QTableWidgetItem(str(value)))

    def toggle_auto_refresh(self):
        if self.auto_refresh.isChecked(): self.timer.start()
        else: self.timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None; event.accept()

    def closeEvent(self, event):
        try: self.db.close()
        except Exception: pass
        event.accept()
