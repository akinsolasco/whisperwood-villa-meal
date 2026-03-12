from PyQt6 import QtCore, QtGui, QtWidgets


from config import ASSETS_DIR
from core.updater import UpdaterService


class SafeSpinner(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(20)
        self.setFixedSize(120, 120)

    def rotate(self):
        self.angle = (self.angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)

        base_pen = QtGui.QPen(QtGui.QColor(42, 42, 42), 10)
        base_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(base_pen)
        painter.drawArc(rect, 0, 360 * 16)

        gold_pen = QtGui.QPen(QtGui.QColor("#e2ab09"), 10)
        gold_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(gold_pen)
        painter.drawArc(rect, (90 - self.angle) * 16, 220 * 16)


class SplashScreen(QtWidgets.QWidget):
    finished = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.logo_path = ASSETS_DIR / "Whisperwood-Villa-logo-removebg-preview.png"
        self.progress_value = 0
        self.message_index = 0
        self.messages = [
            "Initializing secure environment",
            "Loading resident management tools",
            "Checking application updates",
            "Preparing login interface",
        ]
        self.updater = UpdaterService()
        self.update_installer_path = None

        self.setFixedSize(760, 460)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: #090909;")

        self.build_ui()
        self.start_animations()

    def build_ui(self):
        self.container = QtWidgets.QFrame(self)
        self.container.setGeometry(0, 0, 760, 460)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #090909;
                border-radius: 24px;
            }
        """)

        self.logo_card = QtWidgets.QFrame(self.container)
        self.logo_card.setGeometry(220, 34, 320, 110)
        self.logo_card.setStyleSheet("""
            QFrame {
                background-color: #0f0f0f;
                border: 1px solid #1b1b1b;
                border-radius: 24px;
            }
        """)

        self.logo = QtWidgets.QLabel(self.logo_card)
        self.logo.setGeometry(20, 10, 280, 90)
        self.logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        if self.logo_path.exists():
            pix = QtGui.QPixmap(str(self.logo_path)).scaled(
                230, 90,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.logo.setPixmap(pix)
        else:
            self.logo.setText("Whisperwood Villa")
            self.logo.setStyleSheet("color:#e2ab09;font-size:28px;font-weight:700;")

        self.spinner = SafeSpinner(self.container)
        self.spinner.setGeometry(320, 158, 120, 120)

        self.title = QtWidgets.QLabel("Smart Resident Display System", self.container)
        self.title.setGeometry(0, 294, 760, 40)
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color:white;font-size:25px;font-weight:700;")

        self.subtitle = QtWidgets.QLabel(self.messages[0], self.container)
        self.subtitle.setGeometry(0, 336, 760, 24)
        self.subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet("color:#c7c7c7;font-size:14px;")

        self.loading_label = QtWidgets.QLabel("Starting", self.container)
        self.loading_label.setGeometry(0, 372, 760, 22)
        self.loading_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color:#e2ab09;font-size:14px;font-weight:700;")

        self.progress = QtWidgets.QProgressBar(self.container)
        self.progress.setGeometry(170, 408, 360, 14)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #151515;
                border: none;
                border-radius: 7px;
            }
            QProgressBar::chunk {
                background-color: #e2ab09;
                border-radius: 7px;
            }
        """)

        self.percent = QtWidgets.QLabel("0%", self.container)
        self.percent.setGeometry(545, 401, 52, 26)
        self.percent.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.percent.setStyleSheet("""
            QLabel {
                color: #d8d8d8;
                font-size: 13px;
                font-weight: 600;
                background-color: #101010;
                border: 1px solid #1c1c1c;
                border-radius: 8px;
                padding: 2px 6px;
            }
        """)

        self.boot_log = QtWidgets.QLabel("Boot sequence ready", self.container)
        self.boot_log.setGeometry(170, 430, 427, 18)
        self.boot_log.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.boot_log.setStyleSheet("color:#8f8f8f;font-size:12px;")

    def start_animations(self):
        self.dot_count = 0
        self.dot_timer = QtCore.QTimer(self)
        self.dot_timer.timeout.connect(self.animate_loading_text)
        self.dot_timer.start(350)

        self.progress_timer = QtCore.QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(32)

    def animate_loading_text(self):
        self.dot_count = (self.dot_count + 1) % 4
        self.loading_label.setText("Starting" + "." * self.dot_count)

    def update_progress(self):
        self.progress_value += 1

        if self.progress_value == 40:
            result = self.updater.check_for_updates()
            self.boot_log.setText(result["message"])

        if self.message_index < len(self.messages) and self.progress_value in (10, 30, 50, 70):
            self.subtitle.setText(self.messages[self.message_index])
            self.message_index += 1

        self.progress.setValue(self.progress_value)
        self.percent.setText(f"{self.progress_value}%")

        if self.progress_value >= 100:
            self.dot_timer.stop()
            self.progress_timer.stop()
            self.loading_label.setText("Ready")
            self.boot_log.setText("Startup complete")
            QtCore.QTimer.singleShot(400, self.finish)

    def finish(self):
        self.finished.emit()
        self.close()
