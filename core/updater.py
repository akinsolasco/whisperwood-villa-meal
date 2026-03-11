import requests

from config import APP_VERSION, UPDATE_MANIFEST_URL


class UpdaterService:
    def __init__(self):
        self.session = requests.Session()

    def check_for_updates(self):
        if not UPDATE_MANIFEST_URL:
            return {
                "enabled": False,
                "has_update": False,
                "message": "Updater not configured",
            }

        try:
            r = self.session.get(UPDATE_MANIFEST_URL, timeout=5)
            r.raise_for_status()
            manifest = r.json()

            latest_version = manifest.get("version", APP_VERSION)
            download_url = manifest.get("download_url", "")
            has_update = latest_version != APP_VERSION

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
