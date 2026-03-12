import requests

from config import APP_VERSION, GITHUB_OWNER, GITHUB_REPO, INSTALLER_NAME


class UpdaterService:
    def __init__(self):
        self.session = requests.Session()
        self.api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

    def parse_version(self, v):
        v = v.lower().replace("v", "")
        return tuple(int(x) for x in v.split("."))

    def check_for_updates(self):
        try:
            r = self.session.get(self.api_url, timeout=6)
            r.raise_for_status()

            data = r.json()

            latest_tag = data.get("tag_name", f"v{APP_VERSION}")
            latest_version = latest_tag.replace("v", "")

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