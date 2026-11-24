#!/usr/bin/env python3
"""Create clearly marked demo residents through the demo Control API.

This script is intentionally additive and idempotent. It never deletes or
updates a resident and only creates missing DEMO-RES-### records.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ENV_FILE = Path("/opt/whisperwood/control/.env")


def read_control_key(env_file: Path) -> str:
    value = os.getenv("CONTROL_API_KEY", "").strip()
    if value:
        return value
    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("CONTROL_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def request_json(base_url: str, key: str, method: str, path: str, payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json", "X-Whisperwood-Key": key}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code} from {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach the Control API: {exc.reason}") from exc


def resident_payload(index: int) -> dict:
    room_number = 100 + index
    options = [
        ("Regular", "Regular", "Thin"),
        ("Diabetic", "Soft", "Mildly thick"),
        ("Low sodium", "Minced and moist", "Slightly thick"),
        ("High protein", "Easy to chew", "Moderately thick"),
    ]
    diet, texture, fluids = options[(index - 1) % len(options)]
    return {
        "resident_uid": f"DEMO-RES-{index:03d}",
        "full_name": f"Demo Resident {index:02d}",
        "room": f"D-{room_number}",
        "status_alert": "",
        "diet": diet,
        "texture": texture,
        "allergies": texture,
        "fluids": fluids,
        "schedule": fluids,
        "note": f"Demo record {index:02d} for Care Notebook testing.",
        "drinks": "Water",
        "active": True,
        "safety_review_flag": False,
        "needs_safety_review": False,
        "safety_review_note": "",
        "lcd_schedule_enabled": False,
        "lcd_on_time": None,
        "lcd_off_time": None,
        "sleep_if_no_image": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed additive demo residents through Whisperwood Control API")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--base-url", default=os.getenv("WHISPERWOOD_CONTROL_URL", "http://127.0.0.1:7000"))
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()
    count = max(1, min(args.count, 500))
    key = read_control_key(args.env_file)
    if not key:
        print(f"CONTROL_API_KEY was not found in {args.env_file} or the environment.", file=sys.stderr)
        return 2

    try:
        current = request_json(args.base_url, key, "GET", "/residents")
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    existing = {str(row.get("resident_uid") or "").strip() for row in current.get("residents") or []}

    created = 0
    skipped = 0
    failed = 0
    for index in range(1, count + 1):
        payload = resident_payload(index)
        uid = payload["resident_uid"]
        if uid in existing:
            skipped += 1
            continue
        try:
            response = request_json(args.base_url, key, "POST", "/residents", payload)
            if not response.get("ok"):
                raise RuntimeError(f"API returned an unsuccessful response for {uid}: {response}")
            created += 1
            existing.add(uid)
            print(f"CREATED {uid}")
        except RuntimeError as exc:
            failed += 1
            print(f"FAILED {uid}: {exc}", file=sys.stderr)

    print(f"Finished. created={created} skipped_existing={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
