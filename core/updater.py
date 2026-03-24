import requests
from pathlib import Path

from config import (
    APP_VERSION,
    GITHUB_OWNER,
    GITHUB_REPO,
    INSTALLER_NAME,
    UPDATE_DOWNLOAD_DIR,
)


class UpdaterService:
    def __init__(self):
        self.session = requests.Session()
        self.api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        self.download_dir = Path(UPDATE_DOWNLOAD_DIR)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def parse_version(self, v: str):
        v = v.lower().replace("v", "").strip()
        return tuple(int(x) for x in v.split("."))

    def check_for_updates(self, latest_version=None):
        print("Installed APP_VERSION:", APP_VERSION)
        print("Latest GitHub version:", latest_version)
        try:
            r = self.session.get(self.api_url, timeout=6)
            r.raise_for_status()

            data = r.json()

            latest_tag = data.get("tag_name", f"v{APP_VERSION}")
            latest_version = latest_tag.replace("v", "").strip()

            has_update = self.parse_version(latest_version) > self.parse_version(APP_VERSION)

            download_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest/download/{INSTALLER_NAME}"

            return {
                "enabled": True,
                "has_update": has_update,
                "latest_version": latest_version,
                "download_url": download_url,
                "message": "Update available" if has_update else "App is up to date",
            }

        except Exception as e:
            return {
                "enabled": True,
                "has_update": False,
                "message": f"Update check failed: {e}",
            }

    def download_update(self):
        download_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest/download/{INSTALLER_NAME}"
        target_path = self.download_dir / INSTALLER_NAME

        try:
            with self.session.get(download_url, stream=True, timeout=60) as r:
                r.raise_for_status()

                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)

            return {
                "success": True,
                "path": str(target_path),
                "message": "Update downloaded successfully",
            }

        except Exception as e:
            return {
                "success": False,
                "path": None,
                "message": f"Download failed: {e}",
            }