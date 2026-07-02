from pathlib import Path
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

APP_NAME = "Whisperwood Villa Demo"
APP_VERSION = "2.0.5.6"
APP_CHANNEL = "demo"
RELEASE_TAG_PREFIX = "demo-v"
DEFAULT_PI_BASE_URL = "http://localhost:8080"

GITHUB_OWNER = "akinsolasco"
GITHUB_REPO = "whisperwood-villa-meal"
INSTALLER_NAME = "WhisperwoodVillaDemoSetup.exe"

APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "WhisperwoodVillaDemo"
UPDATE_DOWNLOAD_DIR = APP_DATA_DIR / "updates"

DATABASE_MODE = "sqlite"
LOCAL_DB_PATH = APP_DATA_DIR / "whisperwood_demo.sqlite3"
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
    ("nurseadmin", "admin123", "NURSE_ADMIN"),
    ("nurse", "admin123", "NURSE"),
    ("staff", "admin123", "NURSE"),
    ("verifier", "admin123", "VERIFIER"),
    ("itadmin", "itadmin123", "IT_ADMIN"),
]
