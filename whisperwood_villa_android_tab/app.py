from __future__ import annotations

import os
from functools import wraps
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, render_template, request, session

from auth.auth_service import AuthService
from config import DEFAULT_PI_BASE_URL
from core.db_service import DatabaseService, generate_resident_uid
from core.gateway_client import GatewayClient

app = Flask(__name__)
app.secret_key = os.environ.get("WV_ANDROID_SECRET", "whisperwood-villa-android-tab")


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return jsonify({"ok": False, "error": "not authenticated"}), 401
        return fn(*args, **kwargs)

    return wrapper


def current_user() -> Dict[str, Any]:
    return session.get("user") or {"id": None, "username": "admin", "role": "OFFLINE"}


def open_services() -> Tuple[DatabaseService, GatewayClient]:
    db = DatabaseService()
    db.ensure_tables()
    gateway = GatewayClient()
    return db, gateway


def close_services(db: DatabaseService):
    try:
        db.close()
    except Exception:
        pass


def parse_csv(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return []


def push_resident_text(
    db: DatabaseService,
    gateway: GatewayClient,
    row: Dict[str, Any],
    device_id: str,
    base_url: str,
    action_type: str,
):
    payload = {
        "id": device_id,
        "name": row.get("full_name") or "",
        "room": row.get("room") or "",
        "note": row.get("note") or "",
        "drinks": row.get("drinks") or "",
    }
    if row.get("diet"):
        payload["diet"] = [x.strip() for x in str(row.get("diet")).split(",") if x.strip()]
    if row.get("allergies"):
        payload["allergies"] = [x.strip() for x in str(row.get("allergies")).split(",") if x.strip()]
    if row.get("schedule"):
        payload["schedule"] = row.get("schedule")

    try:
        result = gateway.send_text(base_url, payload)
        success = result["status_code"] == 200
        response = result["body"]
        message = "Resident text pushed to paired device" if success else f"Auto-send failed ({result['status_code']})"
    except Exception as exc:
        success = False
        response = {"error": str(exc)}
        message = f"Auto-send failed: {exc}"

    user = current_user()
    db.log_update(
        action_type,
        row.get("id"),
        row.get("resident_uid"),
        device_id,
        user.get("id"),
        user.get("username"),
        payload,
        response,
        success,
        message,
    )


def refresh_devices(db: DatabaseService, gateway: GatewayClient, base_url: str) -> Dict[str, Any]:
    try:
        devices = gateway.get_devices(base_url)
        db.upsert_devices(devices)
        return {"ok": True, "message": "Gateway connected"}
    except Exception as exc:
        user = current_user()
        db.log_update(
            "device_refresh",
            None,
            None,
            None,
            user.get("id"),
            user.get("username"),
            {"base_url": base_url},
            {"error": str(exc)},
            False,
            f"Failed to refresh devices: {exc}",
        )
        return {"ok": False, "message": str(exc)}


def serialize_resident(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "resident_uid": row.get("resident_uid"),
        "full_name": row.get("full_name"),
        "room": row.get("room"),
        "diet": row.get("diet"),
        "allergies": row.get("allergies"),
        "note": row.get("note"),
        "drinks": row.get("drinks"),
        "schedule": row.get("schedule"),
        "source_document": row.get("source_document"),
        "needs_safety_review": bool(row.get("needs_safety_review")),
        "active": bool(row.get("active")),
        "paired_device_id": row.get("paired_device_id"),
        "paired_device_online": bool(row.get("paired_device_online")),
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/login")
def login():
    body = request.get_json(force=True, silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "username and password required"}), 400

    auth = AuthService()
    result = auth.login(username, password)
    if not result.get("success"):
        return jsonify({"ok": False, "error": result.get("message") or "login failed"}), 401

    session["user"] = result.get("user") or {"id": None, "username": username, "role": "OFFLINE"}
    return jsonify({"ok": True, "user": session["user"]})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/bootstrap")
@require_login
def bootstrap():
    base_url = (request.args.get("base_url") or DEFAULT_PI_BASE_URL).strip()
    db, gateway = open_services()
    try:
        gateway_state = refresh_devices(db, gateway, base_url)
        payload = {
            "ok": True,
            "gateway": gateway_state,
            "base_url": base_url,
            "summary": db.get_dashboard_summary(),
            "residents": [serialize_resident(r) for r in db.get_residents()],
            "devices": db.get_devices(),
            "logs": db.get_recent_logs(limit=100),
        }
        return jsonify(payload)
    finally:
        close_services(db)


@app.post("/api/residents")
@require_login
def save_resident():
    body = request.get_json(force=True, silent=True) or {}
    resident_id = body.get("id")
    base_url = (body.get("base_url") or DEFAULT_PI_BASE_URL).strip()

    full_name = (body.get("full_name") or "").strip()
    if not full_name:
        return jsonify({"ok": False, "error": "full_name is required"}), 400

    resident_payload = {
        "resident_uid": (body.get("resident_uid") or "").strip() or generate_resident_uid(),
        "full_name": full_name,
        "room": (body.get("room") or "").strip(),
        "diet": (body.get("diet") or "").strip(),
        "allergies": (body.get("allergies") or "").strip(),
        "note": (body.get("note") or "").strip(),
        "drinks": (body.get("drinks") or "").strip(),
        "schedule": (body.get("schedule") or "").strip(),
        "source_document": (body.get("source_document") or "").strip(),
        "safety_review_note": "Pending safety review" if body.get("needs_safety_review") else "",
        "needs_safety_review": bool(body.get("needs_safety_review")),
        "lcd_image_path": None,
        "lcd_schedule_enabled": False,
        "lcd_on_time": None,
        "lcd_off_time": None,
        "sleep_if_no_image": False,
        "active": bool(body.get("active", True)),
    }

    db, gateway = open_services()
    try:
        user = current_user()
        if resident_id:
            db.update_resident(int(resident_id), resident_payload)
            rid = int(resident_id)
            action = "resident_update"
            message = "Resident updated"
        else:
            rid = db.create_resident(resident_payload)
            action = "resident_create"
            message = "Resident created"

        db.log_update(
            action,
            rid,
            resident_payload["resident_uid"],
            None,
            user.get("id"),
            user.get("username"),
            resident_payload,
            {"saved": True},
            True,
            message,
        )

        row = db.get_resident(rid)
        if row and row.get("paired_device_id"):
            push_resident_text(db, gateway, row, row["paired_device_id"], base_url, "auto_send_after_save")

        return jsonify({"ok": True, "resident": serialize_resident(db.get_resident(rid)), "message": message})
    finally:
        close_services(db)


@app.delete("/api/residents/<int:resident_id>")
@require_login
def delete_resident(resident_id: int):
    db, _gateway = open_services()
    try:
        row = db.get_resident(resident_id)
        if not row:
            return jsonify({"ok": False, "error": "resident not found"}), 404

        user = current_user()
        resident_uid = row.get("resident_uid")
        paired_device = row.get("paired_device_id")
        full_name = row.get("full_name") or resident_uid
        db.delete_resident(resident_id)
        db.log_update(
            "resident_delete",
            None,
            resident_uid,
            paired_device,
            user.get("id"),
            user.get("username"),
            {"resident_id": resident_id, "resident_uid": resident_uid},
            {"deleted": True},
            True,
            f"Resident {full_name} deleted",
        )
        return jsonify({"ok": True})
    finally:
        close_services(db)


@app.get("/api/residents")
@require_login
def list_residents():
    db, _gateway = open_services()
    try:
        return jsonify({"ok": True, "residents": [serialize_resident(r) for r in db.get_residents()]})
    finally:
        close_services(db)


@app.post("/api/devices/refresh")
@require_login
def devices_refresh():
    body = request.get_json(force=True, silent=True) or {}
    base_url = (body.get("base_url") or DEFAULT_PI_BASE_URL).strip()
    db, gateway = open_services()
    try:
        state = refresh_devices(db, gateway, base_url)
        return jsonify({"ok": True, "gateway": state, "devices": db.get_devices()})
    finally:
        close_services(db)


@app.get("/api/devices")
@require_login
def list_devices():
    db, _gateway = open_services()
    try:
        return jsonify({"ok": True, "devices": db.get_devices()})
    finally:
        close_services(db)


@app.post("/api/pair")
@require_login
def pair():
    body = request.get_json(force=True, silent=True) or {}
    resident_id = body.get("resident_id")
    device_id = body.get("device_id")
    base_url = (body.get("base_url") or DEFAULT_PI_BASE_URL).strip()

    if resident_id is None or not device_id:
        return jsonify({"ok": False, "error": "resident_id and device_id are required"}), 400

    db, gateway = open_services()
    try:
        row = db.get_resident(int(resident_id))
        if not row:
            return jsonify({"ok": False, "error": "resident not found"}), 404

        db.pair_resident_to_device(int(resident_id), str(device_id))
        user = current_user()
        db.log_update(
            "pair_device",
            int(resident_id),
            row.get("resident_uid"),
            str(device_id),
            user.get("id"),
            user.get("username"),
            {"device_id": str(device_id)},
            {"paired": True},
            True,
            f"{row.get('full_name')} paired to {device_id}",
        )

        updated = db.get_resident(int(resident_id))
        if updated:
            push_resident_text(db, gateway, updated, str(device_id), base_url, "auto_send_after_pair")

        return jsonify({"ok": True})
    finally:
        close_services(db)


@app.post("/api/unpair")
@require_login
def unpair():
    body = request.get_json(force=True, silent=True) or {}
    device_id = body.get("device_id")
    if not device_id:
        return jsonify({"ok": False, "error": "device_id is required"}), 400

    db, _gateway = open_services()
    try:
        db.unpair_device(str(device_id))
        user = current_user()
        db.log_update(
            "unpair_device",
            None,
            None,
            str(device_id),
            user.get("id"),
            user.get("username"),
            {"device_id": str(device_id)},
            {"unpaired": True},
            True,
            f"Device {device_id} unpaired",
        )
        return jsonify({"ok": True})
    finally:
        close_services(db)


@app.post("/api/send_text")
@require_login
def send_text():
    body = request.get_json(force=True, silent=True) or {}
    base_url = (body.get("base_url") or DEFAULT_PI_BASE_URL).strip()
    device_id = body.get("device_id")
    resident_id = body.get("resident_id")
    if not device_id or resident_id is None:
        return jsonify({"ok": False, "error": "resident_id and device_id are required"}), 400

    db, gateway = open_services()
    try:
        row = db.get_resident(int(resident_id))
        if not row:
            return jsonify({"ok": False, "error": "resident not found"}), 404
        push_resident_text(db, gateway, row, str(device_id), base_url, "send_text")
        return jsonify({"ok": True})
    finally:
        close_services(db)


@app.post("/api/schedule/global")
@require_login
def schedule_global():
    body = request.get_json(force=True, silent=True) or {}
    base_url = (body.get("base_url") or DEFAULT_PI_BASE_URL).strip()
    enabled = bool(body.get("enabled", False))
    lcd_on_time = str(body.get("lcd_on_time") or "07:00")
    lcd_off_time = str(body.get("lcd_off_time") or "20:00")
    sleep_if_no_image = bool(body.get("sleep_if_no_image", False))

    db, gateway = open_services()
    try:
        devices = [d for d in db.get_devices() if d.get("device_id")]
        responses: List[Dict[str, Any]] = []
        failed: List[str] = []
        for d in devices:
            device_id = d["device_id"]
            payload = {
                "resident_uid": "GLOBAL",
                "resident_id": None,
                "device_id": device_id,
                "enabled": enabled,
                "lcd_on_time": lcd_on_time,
                "lcd_off_time": lcd_off_time,
                "sleep_if_no_image": sleep_if_no_image,
                "has_image": False,
            }
            try:
                result = gateway.save_schedule(base_url, payload)
                ok = result["status_code"] == 200
                responses.append({"device_id": device_id, "status_code": result["status_code"], "body": result["body"]})
                if not ok:
                    failed.append(device_id)
            except Exception as exc:
                failed.append(device_id)
                responses.append({"device_id": device_id, "error": str(exc)})

        user = current_user()
        ok_all = not failed
        db.log_update(
            "save_schedule",
            None,
            "GLOBAL",
            "ALL",
            user.get("id"),
            user.get("username"),
            {
                "scope": "all_lcd_devices",
                "enabled": enabled,
                "lcd_on_time": lcd_on_time,
                "lcd_off_time": lcd_off_time,
                "sleep_if_no_image": sleep_if_no_image,
                "device_ids": [d["device_id"] for d in devices],
            },
            responses,
            ok_all,
            "Global schedule saved" if ok_all else f"Global schedule partial failure: {', '.join(failed)}",
        )

        return jsonify({
            "ok": True,
            "applied": len(devices) - len(failed),
            "failed": failed,
            "total": len(devices),
        })
    finally:
        close_services(db)


@app.get("/api/logs")
@require_login
def logs():
    limit = int(request.args.get("limit", "100"))
    db, _gateway = open_services()
    try:
        return jsonify({"ok": True, "logs": db.get_recent_logs(limit=limit)})
    finally:
        close_services(db)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, debug=False)

