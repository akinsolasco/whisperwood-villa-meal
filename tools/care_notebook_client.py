"""Small external client for the restricted Whisperwood Care Notebook API.

This is intentionally not the desktop administration application. It only
reads the notebook API and creates approval requests; it never edits residents
directly and never talks to the full Control Service.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests
from PyQt6 import QtCore, QtGui, QtWidgets


CLIENT_VERSION = "0.1.0"
DEFAULT_BASE_URL = "https://consistent-gilbert-graphs-adjacent.trycloudflare.com"
APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "EnhancedLivingCareNotebook"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"


def display_value(value: Any, fallback: str = "Not provided") -> str:
    text = str(value or "").strip()
    return text or fallback


@dataclass
class ApiFailure(Exception):
    message: str
    status_code: Optional[int] = None

    def __str__(self) -> str:
        return self.message


class NotebookApi:
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0):
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "X-Whisperwood-Notebook-Key": self.api_key,
            "User-Agent": f"EnhancedLivingCareNotebook/{CLIENT_VERSION}",
        })

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.base_url:
            raise ApiFailure("Enter the notebook API address first.")
        if not self.api_key:
            raise ApiFailure("Enter the notebook API key first.")
        try:
            response = self.session.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        except requests.exceptions.Timeout as exc:
            raise ApiFailure("The notebook service took too long to respond. Check the network or try again.") from exc
        except requests.exceptions.RequestException as exc:
            raise ApiFailure(f"Could not reach the notebook service. Check the API address and network.\n\n{exc}") from exc

        if response.status_code >= 400:
            detail = ""
            try:
                body = response.json()
                detail = str(body.get("detail") or body.get("error") or body.get("message") or "").strip()
            except ValueError:
                detail = response.text.strip()
            if response.status_code == 401:
                detail = "The notebook API key was rejected. Check that the key is correct and active."
            elif response.status_code == 403:
                detail = "This notebook key does not have permission for that action."
            raise ApiFailure(detail or f"Notebook service returned HTTP {response.status_code}.", response.status_code)

        try:
            return response.json()
        except ValueError as exc:
            raise ApiFailure("The notebook service returned an unreadable response.") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/notebook/health")

    def residents(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/notebook/residents", params={"limit": 500})
        return list(payload.get("residents") or [])

    def resident(self, resident_id: int) -> dict[str, Any]:
        payload = self._request("GET", f"/notebook/residents/{resident_id}")
        return dict(payload.get("resident") or {})

    def submit_note(self, resident_id: int, comment: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/notebook/change-requests",
            json={
                "resident_id": resident_id,
                "comment": comment,
                "proposed_payload": {},
                "client_note_id": f"care-notebook-{uuid.uuid4().hex}",
            },
        )

    def requests(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/notebook/change-requests", params={"limit": 50})
        return list(payload.get("requests") or [])


class ApiWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, operation: Any):
        super().__init__()
        self.operation = operation

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            self.finished.emit(self.operation())
        except ApiFailure as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # Keep unexpected failures visible instead of closing the window.
            self.failed.emit(f"Unexpected client error: {exc}")


class CareNotebookWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Enhanced Living Care Notebook")
        self.setMinimumSize(920, 620)
        self.resize(1120, 720)
        self.setWindowIcon(QtGui.QIcon(self._asset_path("enhanced_living_whisperwood_icon.ico")))

        self.residents_data: list[dict[str, Any]] = []
        self.selected_resident: Optional[dict[str, Any]] = None
        self.thread: Optional[QtCore.QThread] = None
        self.worker: Optional[ApiWorker] = None

        self._build_ui()
        self._load_settings()
        self._set_status("Enter the notebook key, then select Connect.", "info")

    @staticmethod
    def _asset_path(name: str) -> str:
        candidates = [
            Path(__file__).resolve().parents[1] / "assets" / name,
            Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "assets" / name,
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return ""

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f5f7fb; color: #172033; }
            QFrame#topbar, QFrame#card { background: #ffffff; border: 1px solid #dce3ee; border-radius: 12px; }
            QLabel#brand { color: #123d3d; font-size: 21px; font-weight: 800; }
            QLabel#subtitle { color: #64748b; font-size: 12px; }
            QLabel#section { color: #123d3d; font-size: 15px; font-weight: 800; }
            QLabel#muted { color: #64748b; }
            QLineEdit, QTextEdit, QListWidget { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 7px; }
            QLineEdit:focus, QTextEdit:focus, QListWidget:focus { border: 1px solid #ee9f12; }
            QListWidget::item { padding: 9px 8px; border-bottom: 1px solid #eef2f7; }
            QListWidget::item:selected { background: #fff2ce; color: #172033; border-left: 3px solid #ee9f12; }
            QPushButton { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 14px; font-weight: 700; }
            QPushButton:hover { border-color: #ee9f12; background: #fffaf0; }
            QPushButton#primary { background: #eea900; border-color: #d58f00; color: #1d1d1d; }
            QPushButton#primary:hover { background: #f6b915; }
            QPushButton:disabled { color: #94a3b8; background: #f1f5f9; }
            QScrollArea { border: none; background: transparent; }
        """)

        central = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(14)

        topbar = QtWidgets.QFrame(objectName="topbar")
        top_layout = QtWidgets.QVBoxLayout(topbar)
        top_layout.setContentsMargins(18, 14, 18, 14)
        title_row = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        brand = QtWidgets.QLabel("Enhanced Living Care Notebook", objectName="brand")
        subtitle = QtWidgets.QLabel("Resident information viewer and approval-note channel", objectName="subtitle")
        title_box.addWidget(brand)
        title_box.addWidget(subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch(1)
        title_row.addWidget(QtWidgets.QLabel(f"Client v{CLIENT_VERSION}", objectName="muted"))
        top_layout.addLayout(title_row)

        connection_row = QtWidgets.QHBoxLayout()
        connection_row.addWidget(QtWidgets.QLabel("Notebook API"))
        self.base_url_edit = QtWidgets.QLineEdit()
        self.base_url_edit.setPlaceholderText("https://your-notebook-address")
        connection_row.addWidget(self.base_url_edit, 3)
        connection_row.addWidget(QtWidgets.QLabel("API key"))
        self.api_key_edit = QtWidgets.QLineEdit()
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("wwnb_...")
        connection_row.addWidget(self.api_key_edit, 2)
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setObjectName("primary")
        self.connect_button.clicked.connect(self.connect_api)
        connection_row.addWidget(self.connect_button)
        top_layout.addLayout(connection_row)
        outer.addWidget(topbar)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("muted")
        outer.addWidget(self.status_label)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)

        left_card = QtWidgets.QFrame(objectName="card")
        left_layout = QtWidgets.QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.addWidget(QtWidgets.QLabel("Residents", objectName="section"))
        search_row = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search name, room, or resident UID")
        self.search_edit.textChanged.connect(self._filter_residents)
        search_row.addWidget(self.search_edit)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_residents)
        search_row.addWidget(self.refresh_button)
        left_layout.addLayout(search_row)
        self.resident_list = QtWidgets.QListWidget()
        self.resident_list.currentRowChanged.connect(self._select_resident)
        left_layout.addWidget(self.resident_list, 1)
        self.resident_count_label = QtWidgets.QLabel("No residents loaded", objectName="muted")
        left_layout.addWidget(self.resident_count_label)
        splitter.addWidget(left_card)

        right_card = QtWidgets.QFrame(objectName="card")
        right_layout = QtWidgets.QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 16, 18, 16)
        heading_row = QtWidgets.QHBoxLayout()
        self.resident_heading = QtWidgets.QLabel("Select a resident", objectName="section")
        heading_row.addWidget(self.resident_heading)
        heading_row.addStretch(1)
        self.updated_label = QtWidgets.QLabel("", objectName="muted")
        heading_row.addWidget(self.updated_label)
        right_layout.addLayout(heading_row)

        details = QtWidgets.QGridLayout()
        details.setHorizontalSpacing(22)
        details.setVerticalSpacing(10)
        self.detail_labels: dict[str, QtWidgets.QLabel] = {}
        detail_fields = [
            ("resident_uid", "Resident UID"), ("room", "Room"),
            ("diet", "Diet"), ("texture", "Texture"),
            ("fluids", "Fluids"), ("drinks", "Drinks"),
            ("note", "Care note"), ("safety_review", "Safety review"),
            ("attachments", "Attachments"),
        ]
        for index, (key, label_text) in enumerate(detail_fields):
            row, col = divmod(index, 2)
            label = QtWidgets.QLabel(label_text + "\nNot provided")
            label.setWordWrap(True)
            label.setObjectName("muted")
            self.detail_labels[key] = label
            details.addWidget(label, row, col)
        right_layout.addLayout(details)
        right_layout.addSpacing(8)

        right_layout.addWidget(QtWidgets.QLabel("Add a note for nurse/admin approval", objectName="section"))
        note_hint = QtWidgets.QLabel("Notes are submitted as pending requests. They do not change the resident record directly.", objectName="muted")
        note_hint.setWordWrap(True)
        right_layout.addWidget(note_hint)
        self.note_edit = QtWidgets.QTextEdit()
        self.note_edit.setPlaceholderText("Describe what happened or what should be reviewed...")
        self.note_edit.setMaximumHeight(130)
        right_layout.addWidget(self.note_edit)
        note_actions = QtWidgets.QHBoxLayout()
        self.submit_note_button = QtWidgets.QPushButton("Send for approval")
        self.submit_note_button.setObjectName("primary")
        self.submit_note_button.setEnabled(False)
        self.submit_note_button.clicked.connect(self.submit_note)
        note_actions.addWidget(self.submit_note_button)
        self.requests_button = QtWidgets.QPushButton("View my requests")
        self.requests_button.clicked.connect(self.load_requests)
        note_actions.addWidget(self.requests_button)
        note_actions.addStretch(1)
        right_layout.addLayout(note_actions)
        splitter.addWidget(right_card)
        splitter.setSizes([340, 700])

        self.setCentralWidget(central)

    def _load_settings(self) -> None:
        self.base_url_edit.setText(os.getenv("NOTEBOOK_API_BASE_URL", DEFAULT_BASE_URL))
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if data.get("base_url"):
                self.base_url_edit.setText(str(data["base_url"]))
        except (OSError, ValueError):
            pass

    def _save_settings(self) -> None:
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps({"base_url": self.base_url_edit.text().strip()}, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _set_status(self, text: str, kind: str = "info") -> None:
        color = {"ok": "#166534", "error": "#b42318", "working": "#9a6700"}.get(kind, "#64748b")
        self.status_label.setStyleSheet(f"color: {color}; padding: 2px 4px;")
        self.status_label.setText(text)

    def _api(self) -> NotebookApi:
        return NotebookApi(self.base_url_edit.text(), self.api_key_edit.text())

    def _run_async(self, operation: Any, on_success: Any) -> None:
        self._set_status("Working...", "working")
        self.connect_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.submit_note_button.setEnabled(False)
        self.thread = QtCore.QThread(self)
        self.worker = ApiWorker(operation)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._finish_worker)
        self.worker.finished.connect(on_success)
        self.worker.failed.connect(self._finish_worker)
        self.worker.failed.connect(self._worker_failed)
        self.thread.start()

    @QtCore.pyqtSlot()
    def _finish_worker(self) -> None:
        if self.thread:
            self.thread.quit()
            self.thread.wait(3000)
        self.thread = None
        self.worker = None
        self.connect_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.submit_note_button.setEnabled(bool(self.selected_resident))

    @QtCore.pyqtSlot(str)
    def _worker_failed(self, message: str) -> None:
        self._set_status(message, "error")
        QtWidgets.QMessageBox.warning(self, "Notebook connection", message)

    def connect_api(self) -> None:
        self._save_settings()
        self._run_async(lambda: self._api().health(), self._connected)

    def _connected(self, payload: dict[str, Any]) -> None:
        label = payload.get("label") or "notebook"
        self._set_status(f"Connected to {label}. Loading residents...", "ok")
        self.refresh_residents()

    def refresh_residents(self) -> None:
        self._run_async(lambda: self._api().residents(), self._residents_loaded)

    def _residents_loaded(self, residents: list[dict[str, Any]]) -> None:
        self.residents_data = residents
        self._filter_residents()
        self._set_status(f"Connected. {len(residents)} active resident(s) available.", "ok")

    def _filter_residents(self) -> None:
        query = self.search_edit.text().strip().lower()
        self.resident_list.blockSignals(True)
        self.resident_list.clear()
        visible: list[dict[str, Any]] = []
        for resident in self.residents_data:
            haystack = " ".join(str(resident.get(key) or "") for key in ("full_name", "room", "resident_uid")).lower()
            if query and query not in haystack:
                continue
            visible.append(resident)
            label = f"{display_value(resident.get('full_name'), 'Unnamed resident')}  |  Room {display_value(resident.get('room'), '-') }"
            self.resident_list.addItem(label)
        self.resident_list.blockSignals(False)
        self.resident_count_label.setText(f"{len(visible)} of {len(self.residents_data)} resident(s)")
        self._visible_residents = visible
        if visible:
            self.resident_list.setCurrentRow(0)
        else:
            self._clear_details()

    def _select_resident(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "_visible_residents", [])):
            self.selected_resident = None
            self._clear_details()
            return
        resident = self._visible_residents[row]
        self.selected_resident = resident
        self._show_details(resident)
        self.submit_note_button.setEnabled(True)
        resident_id = resident.get("id")
        if resident_id:
            self._run_async(lambda: self._api().resident(int(resident_id)), self._detail_loaded)

    def _detail_loaded(self, resident: dict[str, Any]) -> None:
        if self.selected_resident and resident.get("id") == self.selected_resident.get("id"):
            self.selected_resident = resident
            self._show_details(resident)
            self.submit_note_button.setEnabled(True)

    def _show_details(self, resident: dict[str, Any]) -> None:
        self.resident_heading.setText(display_value(resident.get("full_name"), "Unnamed resident"))
        self.updated_label.setText(f"Updated: {display_value(resident.get('updated_at'), 'Unknown')}")
        self.detail_labels["resident_uid"].setText(f"Resident UID\n{display_value(resident.get('resident_uid'))}")
        self.detail_labels["room"].setText(f"Room\n{display_value(resident.get('room'))}")
        self.detail_labels["diet"].setText(f"Diet\n{display_value(resident.get('diet'))}")
        self.detail_labels["texture"].setText(f"Texture\n{display_value(resident.get('texture'))}")
        self.detail_labels["fluids"].setText(f"Fluids\n{display_value(resident.get('fluids'))}")
        self.detail_labels["drinks"].setText(f"Drinks\n{display_value(resident.get('drinks'))}")
        self.detail_labels["note"].setText(f"Care note\n{display_value(resident.get('note'))}")
        safety = "Review required" if resident.get("safety_review_flag") else "No review flagged"
        self.detail_labels["safety_review"].setText(f"Safety review\n{safety}")
        attachments = []
        if resident.get("source_document_name"):
            attachments.append("source document")
        if resident.get("image_name"):
            attachments.append("resident image")
        self.detail_labels["attachments"].setText(f"Attachments\n{', '.join(attachments) if attachments else 'None attached'}")

    def _clear_details(self) -> None:
        self.resident_heading.setText("Select a resident")
        self.updated_label.setText("")
        for key, label in self.detail_labels.items():
            title = label.text().split("\n", 1)[0] if "\n" in label.text() else key.replace("_", " ").title()
            label.setText(f"{title}\nNot provided")
        self.submit_note_button.setEnabled(False)

    def submit_note(self) -> None:
        if not self.selected_resident or not self.selected_resident.get("id"):
            self._set_status("Select a resident before sending a note.", "error")
            return
        comment = self.note_edit.toPlainText().strip()
        if not comment:
            QtWidgets.QMessageBox.information(self, "Note required", "Write a note before sending it for approval.")
            return
        resident_id = int(self.selected_resident["id"])
        self._run_async(lambda: self._api().submit_note(resident_id, comment), self._note_submitted)

    def _note_submitted(self, payload: dict[str, Any]) -> None:
        request = payload.get("request") or {}
        request_id = request.get("id") or "pending"
        self.note_edit.clear()
        self._set_status(f"Note submitted for nurse/admin approval. Request #{request_id} is PENDING.", "ok")
        QtWidgets.QMessageBox.information(self, "Note submitted", f"The note was sent for approval.\n\nRequest #{request_id} is now pending review.")

    def load_requests(self) -> None:
        self._run_async(lambda: self._api().requests(), self._requests_loaded)

    def _requests_loaded(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            QtWidgets.QMessageBox.information(self, "My requests", "No notes have been submitted by this notebook yet.")
            return
        lines = []
        for row in rows[:20]:
            created = display_value(row.get("created_at"), "unknown time")
            resident = display_value(row.get("full_name") or row.get("resident_uid"), "resident")
            status = display_value(row.get("status"), "PENDING").upper()
            comment = display_value(row.get("comment"), "")
            lines.append(f"#{row.get('id', '?')}  {status}  {resident}\n{created}\n{comment}")
        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle("My approval requests")
        dialog.setText("\n\n".join(lines))
        dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        dialog.exec()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Enhanced Living Care Notebook")
    app.setApplicationVersion(CLIENT_VERSION)
    window = CareNotebookWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
