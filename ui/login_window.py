from PyQt6 import QtCore, QtGui, QtWidgets

from config import ASSETS_DIR
from auth.auth_service import AuthService


class LoginWindow(QtWidgets.QWidget):
    login_success = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.auth = AuthService()
        self.drag_pos = None

        self.logo_path = ASSETS_DIR / "Whisperwood-Villa-logo-removebg-preview.png"
        self.photo_path = ASSETS_DIR / "senior-woman-talking-with-her-doctor.jpg"

        self.setWindowTitle("Whisperwood Villa Login")
        self.setFixedSize(1150, 740)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)

        self.build_ui()

    def build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        self.container = QtWidgets.QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #050505;
                border-radius: 28px;
            }
        """)
        outer.addWidget(self.container)

        self.left_panel = QtWidgets.QLabel(self.container)
        self.left_panel.setGeometry(12, 12, 570, 716)
        self.left_panel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.left_panel.setStyleSheet("""
            QLabel {
                border-radius: 28px;
                background-color: #111111;
            }
        """)

        if self.photo_path.exists():
            pix = QtGui.QPixmap(str(self.photo_path)).scaled(
                570, 716,
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.left_panel.setPixmap(pix)

        self.left_overlay = QtWidgets.QFrame(self.container)
        self.left_overlay.setGeometry(12, 12, 570, 716)
        self.left_overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 10, 10, 90);
                border-radius: 28px;
            }
        """)

        self.left_text = QtWidgets.QLabel(self.left_overlay)
        self.left_text.setGeometry(46, 545, 470, 125)
        self.left_text.setText('Care with<br>Comfort and <span style="font-weight:700; color:#ffffff;">Dignity</span>')
        self.left_text.setWordWrap(True)
        self.left_text.setStyleSheet("color:#f5f5f5;font-size:29px;font-weight:300;")

        self.left_subtext = QtWidgets.QLabel(self.left_overlay)
        self.left_subtext.setGeometry(48, 650, 400, 30)
        self.left_subtext.setText("Compassionate living, trusted care.")
        self.left_subtext.setStyleSheet("color:rgba(255,255,255,0.75);font-size:14px;")

        self.right_panel = QtWidgets.QFrame(self.container)
        self.right_panel.setGeometry(610, 40, 470, 660)
        self.right_panel.setStyleSheet("background: transparent;")

        self.logo = QtWidgets.QLabel(self.right_panel)
        self.logo.setGeometry(135, 20, 200, 100)
        self.logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        if self.logo_path.exists():
            pix = QtGui.QPixmap(str(self.logo_path)).scaled(
                180, 95,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.logo.setPixmap(pix)

        self.title = QtWidgets.QLabel("Login", self.right_panel)
        self.title.setGeometry(0, 130, 470, 50)
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color:white;font-size:34px;font-weight:700;")

        self.subtitle = QtWidgets.QLabel("Enter your credentials to access your account", self.right_panel)
        self.subtitle.setGeometry(0, 176, 470, 28)
        self.subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet("color:#c9c9c9;font-size:15px;")

        self.username_label = QtWidgets.QLabel("Username", self.right_panel)
        self.username_label.setGeometry(75, 245, 120, 25)
        self.username_label.setStyleSheet("color:white;font-size:14px;font-weight:600;")

        self.username_input = QtWidgets.QLineEdit(self.right_panel)
        self.username_input.setGeometry(75, 275, 320, 48)
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #1b1b1b;
                color: white;
                border: 1px solid #1b1b1b;
                border-radius: 12px;
                padding: 0 16px;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #d4a629;
            }
        """)

        self.password_label = QtWidgets.QLabel("Password", self.right_panel)
        self.password_label.setGeometry(75, 352, 120, 25)
        self.password_label.setStyleSheet("color:white;font-size:14px;font-weight:600;")

        self.password_input = QtWidgets.QLineEdit(self.right_panel)
        self.password_input.setGeometry(75, 382, 320, 48)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #1b1b1b;
                color: white;
                border: 1px solid #1b1b1b;
                border-radius: 12px;
                padding: 0 16px;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #d4a629;
            }
        """)

        self.login_btn = QtWidgets.QPushButton("Login", self.right_panel)
        self.login_btn.setGeometry(75, 500, 320, 50)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #e2ab09;
                color: #101010;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #f0b814;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)

        self.close_btn = QtWidgets.QPushButton("✕", self.container)
        self.close_btn.setGeometry(1090, 18, 38, 38)
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
        self.close_btn.clicked.connect(self.close)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "Login Error", "Please enter username and password.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        result = self.auth.login(username, password)
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Login")

        if result["success"]:
            self.login_success.emit(result["user"])
        else:
            QtWidgets.QMessageBox.critical(self, "Login Failed", result["message"])

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()
