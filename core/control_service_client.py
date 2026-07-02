from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class ControlServiceProfile:
    name: str
    host: str
    port: int
    api_key: str = ""
    description: str = ""

    @property
    def base_url(self) -> str:
        try:
            port = int(self.port)
        except (TypeError, ValueError):
            port = 7000
        return f"http://{self.host.strip()}:{port}"


class ControlServiceClient:
    def __init__(self, host: str, port: int, api_key: str = "", timeout: float = 4.0):
        self.host = (host or "").strip()
        try:
            self.port = int(port or 7000)
        except (TypeError, ValueError):
            self.port = 0
        self.api_key = api_key or ""
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def configured(self) -> bool:
        return bool(self.host and self.port)

    def masked_api_key(self) -> str:
        key = self.api_key or ""
        if not key:
            return "Not configured"
        tail = key[-4:] if len(key) >= 4 else key
        return f"{'*' * max(8, len(key) - len(tail))}{tail}"

    def _headers(self) -> Dict[str, str]:
        return {"X-Whisperwood-Key": self.api_key}

    def _result(
        self,
        ok: bool,
        endpoint: str,
        status_code: Optional[int] = None,
        data: Optional[Any] = None,
        error: str = "",
    ) -> Dict[str, Any]:
        return {
            "ok": ok,
            "endpoint": endpoint,
            "status_code": status_code,
            "data": data,
            "error": error,
            "url": f"{self.base_url}{endpoint}" if self.configured() else "",
        }

    def _request(self, method: str, endpoint: str) -> Dict[str, Any]:
        if not self.host:
            return self._result(False, endpoint, error="Control Service host is not configured.")
        if not self.port or self.port < 1 or self.port > 65535:
            return self._result(False, endpoint, error="Control Service port is not valid.")
        if not self.api_key:
            return self._result(False, endpoint, error="Missing Control Service API key.")

        try:
            response = self.session.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.Timeout:
            return self._result(False, endpoint, error="Control Service request timed out.")
        except requests.ConnectionError:
            return self._result(False, endpoint, error="Control Service Offline or Unreachable.")
        except requests.RequestException as exc:
            return self._result(False, endpoint, error=f"Control Service request failed: {exc}")

        if response.status_code == 403:
            return self._result(False, endpoint, response.status_code, error="Unauthorized Control Service request.")

        try:
            data = response.json()
        except ValueError:
            return self._result(False, endpoint, response.status_code, error="Malformed Control Service response.")

        if response.status_code >= 400:
            message = data.get("err") or data.get("error") or data.get("message") or response.reason
            return self._result(False, endpoint, response.status_code, data, str(message))

        return self._result(True, endpoint, response.status_code, data)

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def system_status(self) -> Dict[str, Any]:
        return self._request("GET", "/system")

    def network_status(self) -> Dict[str, Any]:
        return self._request("GET", "/network")

    def tailscale_status(self) -> Dict[str, Any]:
        return self._request("GET", "/tailscale")

    def operation_status(self) -> Dict[str, Any]:
        return self._request("GET", "/operation/status")

    def restart_operation(self) -> Dict[str, Any]:
        return self._request("POST", "/operation/restart")

    def pending(self, feature_name: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "pending": True,
            "feature": feature_name,
            "message": "Pending backend implementation",
        }

    def logs(self) -> Dict[str, Any]:
        return self.pending("logs")

    def create_backup(self) -> Dict[str, Any]:
        return self.pending("create_backup")

    def restore_backup(self) -> Dict[str, Any]:
        return self.pending("restore_backup")

    def ota_status(self) -> Dict[str, Any]:
        return self.pending("ota_status")

    def upload_firmware(self) -> Dict[str, Any]:
        return self.pending("upload_firmware")

    def release_firmware(self) -> Dict[str, Any]:
        return self.pending("release_firmware")

    def ai_debug_summary(self) -> Dict[str, Any]:
        return self.pending("ai_debug_summary")
