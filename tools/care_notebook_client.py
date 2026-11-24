"""Portable Windows client for the restricted Whisperwood Care Notebook API.

This client uses only Tkinter and requests so the packaged EXE does not depend
on Qt DLLs. It can read resident display information and submit notes for
approval; it cannot edit residents directly.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

import requests
import tkinter as tk
from tkinter import messagebox, ttk


CLIENT_VERSION = "0.1.2"
DEFAULT_BASE_URL = "https://consistent-gilbert-graphs-adjacent.trycloudflare.com"
AUTO_REFRESH_MS = 5000
APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "EnhancedLivingCareNotebook"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"


class ApiFailure(Exception):
    pass


def value(value: Any, fallback: str = "Not provided") -> str:
    text = str(value or "").strip()
    return text or fallback


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

    def request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.base_url:
            raise ApiFailure("Enter the notebook API address first.")
        if not self.api_key:
            raise ApiFailure("Enter the notebook API key first.")
        try:
            response = self.session.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        except requests.exceptions.Timeout as exc:
            raise ApiFailure("The notebook service took too long to respond. Check the network and try again.") from exc
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
            raise ApiFailure(detail or f"Notebook service returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise ApiFailure("The notebook service returned an unreadable response.") from exc

    def health(self) -> dict[str, Any]:
        return self.request_json("GET", "/notebook/health")

    def residents(self) -> list[dict[str, Any]]:
        return list(self.request_json("GET", "/notebook/residents", params={"limit": 500}).get("residents") or [])

    def submit_note(self, resident_id: int, comment: str) -> dict[str, Any]:
        return self.request_json(
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
        return list(self.request_json("GET", "/notebook/change-requests", params={"limit": 50}).get("requests") or [])


class CareNotebookApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Enhanced Living Care Notebook")
        self.root.geometry("1100x720")
        self.root.minsize(860, 560)
        self.root.configure(bg="#f4f7fb")
        self.residents_data: list[dict[str, Any]] = []
        self.visible_residents: list[dict[str, Any]] = []
        self.selected_resident: Optional[dict[str, Any]] = None
        self.busy = False
        self.connected_once = False

        self._configure_style()
        self._build_ui()
        self._load_settings()
        self.set_status("Enter the notebook key, then select Connect.", "info")
        self.root.after(AUTO_REFRESH_MS, self.auto_refresh)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Title.TLabel", background="#ffffff", foreground="#123d3d", font=("Segoe UI", 20, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 9))
        style.configure("Section.TLabel", background="#ffffff", foreground="#123d3d", font=("Segoe UI", 12, "bold"))
        style.configure("Status.TLabel", background="#f4f7fb", font=("Segoe UI", 9))
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="Card.TFrame", padding=16)
        header.pack(fill="x", pady=(0, 10))
        title_row = ttk.Frame(header, style="Card.TFrame")
        title_row.pack(fill="x")
        title_box = ttk.Frame(title_row, style="Card.TFrame")
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="Enhanced Living Care Notebook", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Resident information viewer and approval-note channel", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))
        ttk.Label(title_row, text=f"Client v{CLIENT_VERSION}", style="Muted.TLabel").pack(side="right", anchor="n")

        connection = ttk.Frame(header, style="Card.TFrame")
        connection.pack(fill="x", pady=(14, 0))
        ttk.Label(connection, text="Notebook API", background="#ffffff").pack(side="left", padx=(0, 7))
        self.base_url = ttk.Entry(connection)
        self.base_url.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(connection, text="API key", background="#ffffff").pack(side="left", padx=(0, 7))
        self.api_key = ttk.Entry(connection, show="*")
        self.api_key.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.connect_button = ttk.Button(connection, text="Connect", style="Primary.TButton", command=self.connect)
        self.connect_button.pack(side="left")

        self.status = ttk.Label(outer, text="", style="Status.TLabel")
        self.status.pack(fill="x", pady=(0, 10))

        pane = ttk.PanedWindow(outer, orient="horizontal")
        pane.pack(fill="both", expand=True)

        left = ttk.Frame(pane, style="Card.TFrame", padding=14)
        right = ttk.Frame(pane, style="Card.TFrame", padding=16)
        pane.add(left, weight=1)
        pane.add(right, weight=2)

        ttk.Label(left, text="Residents", style="Section.TLabel").pack(anchor="w")
        search_row = ttk.Frame(left, style="Card.TFrame")
        search_row.pack(fill="x", pady=(10, 8))
        self.search = ttk.Entry(search_row)
        self.search.pack(side="left", fill="x", expand=True)
        self.search.insert(0, "Search name, room, or UID")
        self.search.configure(foreground="#64748b")
        self.search.bind("<FocusIn>", self._clear_search_hint)
        self.search.bind("<KeyRelease>", lambda _event: self.filter_residents())
        ttk.Button(search_row, text="Refresh", command=self.refresh).pack(side="left", padx=(7, 0))
        list_frame = ttk.Frame(left, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, activestyle="none", selectmode="browse", font=("Segoe UI", 10), bg="#ffffff", fg="#172033", selectbackground="#fff0c4", selectforeground="#172033", relief="solid", borderwidth=1, highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self.select_resident)
        self.count_label = ttk.Label(left, text="No residents loaded", style="Muted.TLabel")
        self.count_label.pack(anchor="w", pady=(8, 0))

        heading = ttk.Frame(right, style="Card.TFrame")
        heading.pack(fill="x")
        self.resident_heading = ttk.Label(heading, text="Select a resident", style="Section.TLabel")
        self.resident_heading.pack(side="left")
        self.updated = ttk.Label(heading, text="", style="Muted.TLabel")
        self.updated.pack(side="right")

        detail_frame = ttk.Frame(right, style="Card.TFrame")
        detail_frame.pack(fill="x", pady=(16, 8))
        self.detail_vars: dict[str, tk.StringVar] = {}
        fields = [("resident_uid", "Resident UID"), ("room", "Room"), ("diet", "Diet"), ("texture", "Texture"), ("fluids", "Fluids"), ("drinks", "Drinks"), ("note", "Care note"), ("safety", "Safety review"), ("attachments", "Attachments")]
        for index, (key, caption) in enumerate(fields):
            row, column = divmod(index, 2)
            detail = ttk.Frame(detail_frame, style="Card.TFrame")
            detail.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 14, 12), pady=(0, 10))
            detail_frame.columnconfigure(column, weight=1)
            ttk.Label(detail, text=caption, style="Muted.TLabel").pack(anchor="w")
            var = tk.StringVar(value="Not provided")
            self.detail_vars[key] = var
            ttk.Label(detail, textvariable=var, style="Section.TLabel", wraplength=320).pack(anchor="w", pady=(2, 0))

        ttk.Label(right, text="Add a note for nurse/admin approval", style="Section.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(right, text="Notes are submitted as pending requests. They do not change the resident record directly.", style="Muted.TLabel", wraplength=700).pack(anchor="w", pady=(3, 7))
        self.note = tk.Text(right, height=5, wrap="word", font=("Segoe UI", 10), relief="solid", borderwidth=1, padx=7, pady=7)
        self.note.pack(fill="x")
        actions = ttk.Frame(right, style="Card.TFrame")
        actions.pack(fill="x", pady=(8, 0))
        self.submit_button = ttk.Button(actions, text="Send for approval", style="Primary.TButton", command=self.submit_note, state="disabled")
        self.submit_button.pack(side="left")
        ttk.Button(actions, text="View my requests", command=self.load_requests).pack(side="left", padx=(8, 0))

    def _clear_search_hint(self, _event: Any) -> None:
        if self.search.get() == "Search name, room, or UID":
            self.search.delete(0, "end")
            self.search.configure(foreground="#172033")

    def _load_settings(self) -> None:
        self.base_url.insert(0, os.getenv("NOTEBOOK_API_BASE_URL", DEFAULT_BASE_URL))
        try:
            saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if saved.get("base_url"):
                self.base_url.delete(0, "end")
                self.base_url.insert(0, str(saved["base_url"]))
        except (OSError, ValueError):
            pass

    def _save_settings(self) -> None:
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps({"base_url": self.base_url.get().strip()}, indent=2), encoding="utf-8")
        except OSError:
            pass

    def set_status(self, text: str, kind: str = "info") -> None:
        colors = {"ok": "#166534", "error": "#b42318", "working": "#9a6700", "info": "#64748b"}
        self.status.configure(text=text, foreground=colors.get(kind, colors["info"]))

    def api(self) -> NotebookApi:
        return NotebookApi(self.base_url.get(), self.api_key.get())

    def run_async(self, operation: Callable[[], Any], on_success: Callable[[Any], None], show_errors: bool = True) -> None:
        if self.busy:
            return
        self.busy = True
        self.connect_button.configure(state="disabled")
        self.submit_button.configure(state="disabled")
        self.set_status("Working...", "working")

        def task() -> None:
            try:
                result = operation()
                self.root.after(0, lambda: self.finish_async(lambda: on_success(result)))
            except Exception as exc:
                if show_errors:
                    callback = lambda: self.show_error(str(exc))
                else:
                    callback = lambda: self.set_status(f"Auto-refresh unavailable: {exc}", "error")
                self.root.after(0, lambda: self.finish_async(callback))

        threading.Thread(target=task, daemon=True).start()

    def finish_async(self, callback: Callable[[], None]) -> None:
        self.busy = False
        self.connect_button.configure(state="normal")
        self.submit_button.configure(state="normal" if self.selected_resident else "disabled")
        callback()

    def show_error(self, text: str) -> None:
        self.set_status(text, "error")
        messagebox.showerror("Notebook connection", text, parent=self.root)

    def connect(self) -> None:
        self._save_settings()
        self.run_async(lambda: self.api().health(), self.connected)

    def connected(self, payload: dict[str, Any]) -> None:
        self.connected_once = True
        self.set_status(f"Connected to {payload.get('label') or 'notebook'}. Loading residents...", "ok")
        self.refresh()

    def auto_refresh(self) -> None:
        if self.connected_once and not self.busy and self.api_key.get().strip():
            self.refresh(silent=True)
        self.root.after(AUTO_REFRESH_MS, self.auto_refresh)

    def refresh(self, silent: bool = False) -> None:
        self.run_async(
            lambda: self.api().residents(),
            lambda rows: self.residents_loaded(rows, silent=silent),
            show_errors=not silent,
        )

    def residents_loaded(self, residents: list[dict[str, Any]], silent: bool = False) -> None:
        self.residents_data = residents
        self.filter_residents()
        self.set_status(f"Connected. {len(residents)} active resident(s) available.", "ok")

    def filter_residents(self) -> None:
        selected_id = self.selected_resident.get("id") if self.selected_resident else None
        query = self.search.get().strip().lower()
        if query == "search name, room, or uid":
            query = ""
        self.visible_residents = []
        self.listbox.delete(0, "end")
        for resident in self.residents_data:
            haystack = " ".join(str(resident.get(key) or "") for key in ("full_name", "room", "resident_uid")).lower()
            if query and query not in haystack:
                continue
            self.visible_residents.append(resident)
            self.listbox.insert("end", f"{value(resident.get('full_name'), 'Unnamed resident')}  |  Room {value(resident.get('room'), '-')}" )
        self.count_label.configure(text=f"{len(self.visible_residents)} of {len(self.residents_data)} resident(s)")
        if self.visible_residents:
            target = next((index for index, resident in enumerate(self.visible_residents) if resident.get("id") == selected_id), 0)
            self.listbox.selection_set(target)
            self.listbox.see(target)
            self.select_resident()
        else:
            self.selected_resident = None
            self.clear_details()

    def select_resident(self, _event: Any = None) -> None:
        selection = self.listbox.curselection()
        if not selection or selection[0] >= len(self.visible_residents):
            return
        self.selected_resident = self.visible_residents[selection[0]]
        self.show_details(self.selected_resident)
        self.submit_button.configure(state="normal" if not self.busy else "disabled")

    def show_details(self, resident: dict[str, Any]) -> None:
        self.resident_heading.configure(text=value(resident.get("full_name"), "Unnamed resident"))
        self.updated.configure(text=f"Updated: {value(resident.get('updated_at'), 'Unknown')}")
        for key in ("resident_uid", "room", "diet", "texture", "fluids", "drinks", "note"):
            self.detail_vars[key].set(value(resident.get(key)))
        self.detail_vars["safety"].set("Review required" if resident.get("safety_review_flag") else "No review flagged")
        attachments = []
        if resident.get("source_document_name"):
            attachments.append("source document")
        if resident.get("image_name"):
            attachments.append("resident image")
        self.detail_vars["attachments"].set(", ".join(attachments) if attachments else "None attached")

    def clear_details(self) -> None:
        self.resident_heading.configure(text="Select a resident")
        self.updated.configure(text="")
        for var in self.detail_vars.values():
            var.set("Not provided")
        self.submit_button.configure(state="disabled")

    def submit_note(self) -> None:
        if not self.selected_resident or not self.selected_resident.get("id"):
            self.set_status("Select a resident before sending a note.", "error")
            return
        comment = self.note.get("1.0", "end").strip()
        if not comment:
            messagebox.showinfo("Note required", "Write a note before sending it for approval.", parent=self.root)
            return
        resident_id = int(self.selected_resident["id"])
        self.run_async(lambda: self.api().submit_note(resident_id, comment), self.note_submitted)

    def note_submitted(self, payload: dict[str, Any]) -> None:
        request_id = (payload.get("request") or {}).get("id") or "pending"
        self.note.delete("1.0", "end")
        self.set_status(f"Note submitted for nurse/admin approval. Request #{request_id} is PENDING.", "ok")
        messagebox.showinfo("Note submitted", f"The note was sent for approval.\n\nRequest #{request_id} is now pending review.", parent=self.root)

    def load_requests(self) -> None:
        self.run_async(lambda: self.api().requests(), self.requests_loaded)

    def requests_loaded(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            messagebox.showinfo("My requests", "No notes have been submitted by this notebook yet.", parent=self.root)
            return
        lines = []
        for row in rows[:20]:
            lines.append(f"#{row.get('id', '?')}  {value(row.get('status'), 'PENDING').upper()}  {value(row.get('full_name') or row.get('resident_uid'), 'resident')}\n{value(row.get('created_at'), 'unknown time')}\n{value(row.get('comment'), '')}")
        messagebox.showinfo("My approval requests", "\n\n".join(lines), parent=self.root)


def main() -> int:
    root = tk.Tk()
    CareNotebookApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
