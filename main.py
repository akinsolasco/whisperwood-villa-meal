import sys
import traceback
from PyQt6.QtWidgets import QApplication
from ui.splash_screen import SplashScreen
from ui.login_window import LoginWindow
from ui.dashboard_window import DashboardWindow
from config import APP_DATA_DIR


class AppController:
    def __init__(self):
        self.splash = SplashScreen()
        self.login = LoginWindow()
        self.dashboard = None

        self.splash.finished.connect(self.show_login)
        self.login.login_success.connect(self.show_dashboard)

    def start(self):
        self.splash.show()

    def show_login(self):
        self.login.show()

    def show_dashboard(self, user: dict):
        try:
            self.dashboard = DashboardWindow(current_user=user)
            self.dashboard.show()
            self.login.close()
        except Exception as exc:
            self.dashboard = None
            error_message = f"Could not open dashboard.\n\n{exc}"
            self.login.handle_dashboard_open_error(error_message)
            try:
                APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
                error_file = APP_DATA_DIR / "startup_errors.log"
                with error_file.open("a", encoding="utf-8") as f:
                    f.write("\n=== Dashboard startup error ===\n")
                    f.write(traceback.format_exc())
                    f.write("\n")
            except Exception:
                pass


def main():
    app = QApplication(sys.argv)
    controller = AppController()
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
