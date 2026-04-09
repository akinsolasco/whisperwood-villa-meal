# Whisperwood Villa Android Tab Edition

This folder is a separate tablet-friendly web build of Whisperwood Villa.

## Why this version

The original desktop app is PyQt6 (Windows desktop UI). Android tablets run better with a responsive web UI, so this edition uses:

- Flask backend (`app.py`)
- Responsive tablet UI (`templates/index.html`, `static/app.css`, `static/app.js`)
- Same core services copied from the desktop app (`auth/`, `core/`)

## Run

1. Open this folder:
   - `whisperwood_villa_android_tab`
2. Install requirements:
   - `pip install -r requirements.txt`
3. Run:
   - `python app.py`
4. On Android tablet browser, open:
   - `http://<your-pc-ip>:8090`

## Current feature coverage

- Login
- Overview summary
- Resident create/update/delete
- Device refresh
- Pair / unpair
- Auto-send resident text after pair and save
- Manual send text
- Global LCD schedule apply to all devices
- Logs view

## Notes

- Set the Gateway Base URL on login screen (default is `http://192.168.4.1:8080`).
- This edition is intentionally separate and does not modify desktop PyQt windows.
