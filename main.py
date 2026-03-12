import sys
from PyQt6.QtWidgets import QApplication
from ui.splash_screen import SplashScreen
from ui.login_window import LoginWindow
from ui.dashboard_window import DashboardWindow


class AppController:
    def __init__(self):
        self.splash = SplashScreen()
        self.login = LoginWindow()
        self.dashboard = None
        self.update_installer_path = None

        self.splash.finished.connect(self.show_login)
        self.login.login_success.connect(self.show_dashboard)

    def start(self):
        self.splash.show()

    def show_login(self):
        self.update_installer_path = getattr(self.splash, "update_installer_path", None)
        self.login.show()

    def show_dashboard(self, user: dict):
        self.dashboard = DashboardWindow(current_user=user)
        self.dashboard.show()
        self.login.close()

        if self.update_installer_path and hasattr(self.dashboard, "prompt_install_update"):
            self.dashboard.prompt_install_update(self.update_installer_path)


def main():
    app = QApplication(sys.argv)
    controller = AppController()
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()