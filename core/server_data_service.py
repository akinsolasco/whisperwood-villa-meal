import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.app_settings import AppSettingsStore
from core.control_service_client import ControlServiceClient


class ServerDataService:
    backend = "server"

    def __init__(self):
        self.settings = AppSettingsStore()

    def ensure_tables(self):
        return None

    def close(self):
        return None

    def client(self, timeout=4.0) -> ControlServiceClient:
        profile = self.settings.get_active_profile()
        return ControlServiceClient(
            profile.get("host") or "",
            profile.get("port") or 7000,
            profile.get("api_key") or "",
            timeout=timeout,
        )

    def _require_ok(self, result: Dict[str, Any]):
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Control Service offline or unreachable")
        return result.get("data")

    def _items(self, result: Dict[str, Any], *keys) -> List[Dict[str, Any]]:
        data = self._require_ok(result)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in keys:
                value = data.get(key)
                if isinstance(value, list):
                    return value
            nested = data.get("data")
            if isinstance(nested, list):
                return nested
        return []

    def _row(self, result: Dict[str, Any], *keys) -> Dict[str, Any]:
        data = self._require_ok(result)
        if isinstance(data, dict):
            for key in keys:
                value = data.get(key)
                if isinstance(value, dict):
                    return value
            nested = data.get("data")
            if isinstance(nested, dict):
                return nested
            return data
        return {}

    def _json_value(self, value):
        return value

    def _parse_json_field(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

    def list_control_profiles(self):
        return self.settings.list_profiles()

    def get_active_control_profile(self):
        return self.settings.get_active_profile()

    def save_control_profile(self, profile_id, profile_name, host, port, api_key, description, is_active=True):
        return self.settings.save_profile(profile_id, profile_name, host, port, api_key, description, is_active)

    def set_active_control_profile(self, profile_id):
        self.settings.set_active_profile(profile_id)

    def _normalize_resident(self, row: Dict[str, Any], devices: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        row = dict(row or {})
        resident_id = row.get("id") or row.get("resident_id")
        paired = next((d for d in devices or [] if str(d.get("paired_resident_id") or d.get("resident_id") or "") == str(resident_id)), {})
        status_alert = row.get("status_alert") or row.get("status") or row.get("alert") or "Stable"
        return {
            **row,
            "id": resident_id,
            "resident_uid": row.get("resident_uid") or row.get("uid") or "",
            "full_name": row.get("full_name") or row.get("name") or "",
            "room": row.get("room") or "",
            "status_alert": status_alert,
            "diet": row.get("diet") or "",
            "allergies": row.get("allergies") or "",
            "note": row.get("note") or "",
            "drinks": row.get("drinks") or "",
            "schedule": row.get("schedule") or "",
            "source_document": row.get("source_document") or row.get("document_path") or row.get("document_url") or "",
            "safety_review_note": row.get("safety_review_note") or "",
            "needs_safety_review": bool(row.get("needs_safety_review", False)),
            "lcd_image_path": row.get("lcd_image_path") or row.get("image_path") or row.get("image_url") or "",
            "lcd_schedule_enabled": bool(row.get("lcd_schedule_enabled", False)),
            "lcd_on_time": row.get("lcd_on_time"),
            "lcd_off_time": row.get("lcd_off_time"),
            "sleep_if_no_image": bool(row.get("sleep_if_no_image", False)),
            "active": bool(row.get("active", True)),
            "paired_device_id": row.get("paired_device_id") or paired.get("device_id") or paired.get("id"),
            "paired_device_online": row.get("paired_device_online") if "paired_device_online" in row else paired.get("is_online") or paired.get("online"),
        }

    def _resident_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resident_uid": data.get("resident_uid"),
            "full_name": data.get("full_name"),
            "room": data.get("room"),
            "status_alert": data.get("status_alert") or data.get("status") or "Stable",
            "diet": data.get("diet"),
            "allergies": data.get("allergies"),
            "note": data.get("note"),
            "drinks": data.get("drinks"),
            "active": bool(data.get("active", True)),
        }

    def get_residents(self):
        try:
            devices = self.get_devices(suppress_errors=True)
            return [self._normalize_resident(row, devices) for row in self._items(self.client().get_residents(), "residents", "items")]
        except Exception:
            return []

    def get_resident(self, resident_id):
        for row in self.get_residents():
            if str(row.get("id")) == str(resident_id):
                return row
        return None

    def create_resident(self, data):
        result = self.client(timeout=8.0).create_resident(self._resident_payload(data))
        row = self._row(result, "resident")
        resident_id = row.get("id") or row.get("resident_id")
        if not resident_id:
            residents = self.get_residents()
            match = next((r for r in residents if r.get("resident_uid") == data.get("resident_uid")), None)
            resident_id = match.get("id") if match else None
        self._upload_resident_files(resident_id, data)
        return resident_id

    def update_resident(self, resident_id, data):
        self._require_ok(self.client(timeout=8.0).update_resident(resident_id, self._resident_payload(data)))
        self._upload_resident_files(resident_id, data)

    def _upload_resident_files(self, resident_id, data):
        if not resident_id:
            return
        if data.get("source_document") and os.path.isfile(str(data.get("source_document"))):
            result = self.client(timeout=20.0).upload_document(resident_id, data.get("source_document"))
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "Source document upload failed.")
        if data.get("lcd_image_path") and os.path.isfile(str(data.get("lcd_image_path"))):
            result = self.client(timeout=30.0).upload_image(resident_id, data.get("lcd_image_path"))
            if not result.get("ok"):
                raise RuntimeError(result.get("error") or "Resident image upload failed.")

    def delete_resident(self, _resident_id):
        raise RuntimeError("Resident delete is not available in Server Mode because the Control Service does not expose a delete endpoint.")

    def _normalize_device(self, row: Dict[str, Any], residents: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        row = dict(row or {})
        device_id = row.get("device_id") or row.get("id") or ""
        resident_id = row.get("paired_resident_id") or row.get("resident_id")
        resident = next((r for r in residents or [] if str(r.get("id")) == str(resident_id)), {})
        return {
            **row,
            "device_id": device_id,
            "id": row.get("id") or device_id,
            "ip": row.get("ip") or row.get("lan_ip") or "",
            "port": row.get("port"),
            "fw": row.get("fw") or row.get("firmware"),
            "last_seen_s": row.get("last_seen_s") or row.get("last_seen") or "",
            "is_online": bool(row.get("is_online", row.get("online", False))),
            "battery_level": row.get("battery_level") or row.get("battery"),
            "paired_resident_id": resident_id,
            "resident_name": row.get("resident_name") or row.get("full_name") or resident.get("full_name"),
            "resident_uid": row.get("resident_uid") or resident.get("resident_uid"),
        }

    def get_devices(self, suppress_errors=False):
        try:
            rows = self._items(self.client().get_devices(), "devices", "items")
        except Exception:
            if suppress_errors:
                return []
            raise
        return [self._normalize_device(row) for row in rows]

    def upsert_devices(self, _devices):
        return None

    def pair_resident_to_device(self, resident_id, device_id):
        self._require_ok(self.client(timeout=8.0).pair_device(resident_id, device_id))

    def unpair_device(self, _device_id):
        raise RuntimeError("Unpairing is pending Control Service backend support.")

    def save_resident_schedule(self, resident_id, enabled, on_time, off_time, sleep_if_no_image):
        row = self.get_resident(resident_id) or {}
        payload = {
            "resident_id": resident_id,
            "device_id": row.get("paired_device_id"),
            "enabled": bool(enabled),
            "lcd_on_time": on_time,
            "lcd_off_time": off_time,
            "sleep_if_no_image": bool(sleep_if_no_image),
        }
        self._require_ok(self.client(timeout=8.0).save_schedule(payload))

    def get_schedule_rows(self):
        try:
            schedules = self._items(self.client().get_schedules(), "schedules", "items")
        except Exception:
            return []
        residents = {str(r.get("id")): r for r in self.get_residents()}
        out = []
        for row in schedules:
            resident = residents.get(str(row.get("resident_id")), {})
            out.append({
                **row,
                "id": row.get("resident_id"),
                "resident_uid": resident.get("resident_uid"),
                "full_name": resident.get("full_name"),
                "lcd_schedule_enabled": bool(row.get("enabled")),
                "lcd_on_time": row.get("lcd_on_time"),
                "lcd_off_time": row.get("lcd_off_time"),
                "sleep_if_no_image": bool(row.get("sleep_if_no_image")),
                "device_id": row.get("device_id"),
                "is_online": row.get("is_online"),
            })
        return out

    def log_update(self, *_args, **_kwargs):
        return None

    def get_recent_logs(self, limit=50):
        try:
            rows = self._items(self.client().get_logs(), "logs", "items")[:limit]
            return [self._normalize_log(row) for row in rows]
        except Exception:
            return []

    def get_log(self, log_id):
        return next((row for row in self.get_recent_logs(limit=500) if str(row.get("id")) == str(log_id)), None)

    def get_resident_audit_logs(self, limit=200):
        logs = self.get_recent_logs(limit=limit)
        return [row for row in logs if "resident" in (row.get("action_type") or "").lower()]

    def _normalize_log(self, row: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(row or {})
        result = str(row.get("result") or row.get("success") or "").lower()
        success = row.get("success")
        if success is None:
            success = result in {"success", "ok", "true", "1"}
        return {
            **row,
            "id": row.get("id") or row.get("log_id"),
            "created_at": row.get("created_at") or row.get("timestamp") or row.get("time"),
            "action_type": row.get("action_type") or row.get("action") or "",
            "resident_uid": row.get("resident_uid") or "",
            "device_id": row.get("device_id") or row.get("device") or "",
            "pushed_by_username": row.get("pushed_by_username") or row.get("username") or row.get("user") or "",
            "success": bool(success),
            "message": row.get("message") or "",
            "payload_json": row.get("payload_json") or row.get("payload"),
            "response_json": row.get("response_json") or row.get("response"),
        }

    def create_change_request(self, *_args, **_kwargs):
        raise RuntimeError("Staff review requests are pending Control Service backend support.")

    def get_change_requests(self, *_args, **_kwargs):
        return []

    def update_change_request_status(self, *_args, **_kwargs):
        raise RuntimeError("Review approval queue is pending Control Service backend support.")

    def create_verification_check(self, *_args, **_kwargs):
        raise RuntimeError("Display verification history is pending Control Service backend support.")

    def get_verification_checks(self, *_args, **_kwargs):
        return []

    def log_it_audit(self, *_args, **_kwargs):
        return None

    def get_it_audit_logs(self, limit=100):
        return self.get_recent_logs(limit=limit)

    def get_dashboard_summary(self):
        residents = self.get_residents()
        devices = self.get_devices(suppress_errors=True)
        logs = self.get_recent_logs(limit=500)
        return {
            "active_residents": sum(1 for r in residents if r.get("active")),
            "inactive_residents": sum(1 for r in residents if not r.get("active")),
            "online_devices": sum(1 for d in devices if d.get("is_online")),
            "known_devices": len(devices),
            "paired_devices": sum(1 for d in devices if d.get("paired_resident_id") or d.get("resident_name")),
            "failed_updates": sum(1 for row in logs if not row.get("success")),
            "recent_activity": len(logs),
            "recent_activity_today": len(logs),
            "recent_activity_total": len(logs),
            "safety_reviews": sum(1 for r in residents if r.get("needs_safety_review")),
            "pending_requests": 0,
            "verification_checks": 0,
            "verification_mismatches": 0,
            "database_mode": "server",
        }

    @staticmethod
    def format_timestamp(value):
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value or "")
