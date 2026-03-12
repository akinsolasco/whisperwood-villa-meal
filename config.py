from pathlib import Path
import os
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

APP_NAME = "Whisperwood Villa"
APP_VERSION = "1.0.1"
DEFAULT_PI_BASE_URL = "http://192.168.4.1:8080"

GITHUB_OWNER = "akinsolasco"
GITHUB_REPO = "whisperwood-villa-meal"
INSTALLER_NAME = "WhisperwoodVillaSetup.exe"

APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "WhisperwoodVilla"
UPDATE_DOWNLOAD_DIR = APP_DATA_DIR / "updates"
UPDATE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)