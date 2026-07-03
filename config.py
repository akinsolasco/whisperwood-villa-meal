from pathlib import Path
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

APP_NAME = "Enhanced Living Whisperwood Live Demo"
APP_VERSION = "2.0.6.2"
APP_CHANNEL = "live-demo"
RELEASE_TAG_PREFIX = "live-demo-v"
DEFAULT_PI_BASE_URL = "http://localhost:8080"
DEFAULT_CONTROL_SERVICE_HOST = "172.20.0.240"
DEFAULT_CONTROL_SERVICE_PORT = 7000
DEFAULT_CONTROL_SERVICE_API_KEY = "c6149ae5af0ace91b7fd0fbcfa064b9682dc0ff737ba972eb0aa6baab74c039c"

GITHUB_OWNER = "akinsolasco"
GITHUB_REPO = "whisperwood-villa-meal"
INSTALLER_NAME = "EnhancedLivingWhisperwoodLiveDemoSetup.exe"

APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "EnhancedLivingWhisperwoodLiveDemo"
UPDATE_DOWNLOAD_DIR = APP_DATA_DIR / "updates"

DATABASE_MODE = "sqlite"
LOCAL_DB_PATH = APP_DATA_DIR / "whisperwood_live_demo.sqlite3"
DEMO_DEFAULT_USERNAME = "admin"
DEMO_DEFAULT_PASSWORD = "admin123"

ROLE_LABELS = {
    "ADMIN": "Admin",
    "NURSE_ADMIN": "Admin",
    "NURSE": "Staff",
    "STAFF": "Staff",
    "VERIFIER": "Display Verifier",
    "IT_ADMIN": "IT Admin",
    "IT_ADMIN_BACKEND": "IT Admin",
}

DEMO_USERS = [
    ("admin", "admin123", "NURSE_ADMIN"),
    ("itadmin", "itadmin123", "IT_ADMIN"),
]
