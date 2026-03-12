from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / 'assets'

APP_NAME = 'Whisperwood Villa'
APP_VERSION = '1.0.0'
DEFAULT_PI_BASE_URL = 'http://192.168.4.1:8080'

# local update folder
UPDATE_MANIFEST_URL = ''
UPDATE_DOWNLOAD_DIR = BASE_DIR / 'updates'
UPDATE_DOWNLOAD_DIR.mkdir(exist_ok=True)

# GitHub release updater settings
GITHUB_OWNER = 'akinsolasco'
GITHUB_REPO = 'whisperwood-villa-meal'
INSTALLER_NAME = 'WhisperwoodVillaSetup.exe'