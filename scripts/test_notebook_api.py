#!/usr/bin/env python3
"""Read-only smoke test for the restricted Care Notebook API.

Set NOTEBOOK_API_BASE_URL and NOTEBOOK_API_KEY before running. The optional
--submit-note command intentionally creates a pending approval request.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests


def request_json(session: requests.Session, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:
    try:
        response = session.request(method, url, timeout=15, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach {url}: {exc}") from exc
    try:
        body = response.json()
    except ValueError:
        body = response.text[:500]
    return response.status_code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the restricted Whisperwood Care Notebook API")
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOK_API_BASE_URL", ""))
    parser.add_argument("--token", default=os.getenv("NOTEBOOK_API_KEY", ""))
    parser.add_argument("--submit-note", action="store_true", help="Create one pending note for nurse approval")
    parser.add_argument("--resident-id", type=int, help="Resident ID used with --submit-note")
    parser.add_argument("--comment", default="Notebook API smoke-test note; please reject after checking.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if not base_url or not args.token:
        print("Set NOTEBOOK_API_BASE_URL and NOTEBOOK_API_KEY, or pass --base-url and --token.", file=sys.stderr)
        return 2

    session = requests.Session()
    session.headers.update({"X-Whisperwood-Notebook-Key": args.token})

    checks = [
        ("notebook health", "GET", "/notebook/health"),
        ("resident list", "GET", "/notebook/residents"),
        ("request status", "GET", "/notebook/change-requests"),
        ("protected full API is blocked", "GET", "/residents"),
    ]

    for label, method, path in checks:
        status, body = request_json(session, method, f"{base_url}{path}")
        if label == "protected full API is blocked":
            # The dedicated service intentionally does not mount the full
            # Control Service routes, so 404 is also a successful boundary.
            passed = status in {401, 403, 404}
        else:
            passed = status == 200 and isinstance(body, dict) and body.get("ok") is True
        print(f"{'PASS' if passed else 'FAIL'} {label}: HTTP {status}")
        if not passed:
            print(body)
            return 1
        if path == "/notebook/residents":
            print(f"  residents returned: {len(body.get('residents') or [])}")
        if path == "/notebook/change-requests":
            print(f"  requests returned: {len(body.get('requests') or [])}")

    if args.submit_note:
        if not args.resident_id:
            print("--resident-id is required with --submit-note.", file=sys.stderr)
            return 2
        payload = {
            "resident_id": args.resident_id,
            "comment": args.comment,
            "proposed_payload": {},
            "client_note_id": "notebook-api-smoke-test",
        }
        status, body = request_json(
            session,
            "POST",
            f"{base_url}/notebook/change-requests",
            json=payload,
        )
        passed = status == 200 and isinstance(body, dict) and body.get("ok") is True
        print(f"{'PASS' if passed else 'FAIL'} pending note submission: HTTP {status}")
        if passed:
            print(f"  request id: {(body.get('request') or {}).get('id')}")
        else:
            print(body)
            return 1

    print("Notebook API smoke test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
