import sys
from PyQt6.QtWidgets import QApplication
from ui.splash_screen import SplashScreen
from ui.login_window import LoginWindow
from ui.dashboard_window import DashboardWindow


class AppController:
    def __init__(self):
        self.splash = SplashScreen()
        self.login = None
        self.dashboard = None

        self.splash.finished.connect(self.show_login)
        self._create_login_window()

    def _create_login_window(self):
        if self.login is not None:
            try:
                self.login.deleteLater()
            except Exception:
                pass
        self.login = LoginWindow()
        self.login.login_success.connect(self.show_dashboard)

    def start(self):
        self.splash.show()

    def show_login(self):
        if self.dashboard is not None:
            try:
                self.dashboard.close()
                self.dashboard.deleteLater()
            except Exception:
                pass
            self.dashboard = None
        if self.login is None:
            self._create_login_window()
        self.login.prepare_for_show(clear_username=False)
        self.login.show()

    def show_dashboard(self, user: dict):
        if self.dashboard is not None:
            try:
                self.dashboard.close()
                self.dashboard.deleteLater()
            except Exception:
                pass
        self.dashboard = DashboardWindow(current_user=user)
        self.dashboard.logout_requested.connect(self.show_login)
        self.dashboard.show()
        if self.login is not None:
            try:
                self.login.close()
                self.login.deleteLater()
            except Exception:
                pass
            self.login = None


def main():
    app = QApplication(sys.argv)
    controller = AppController()
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
