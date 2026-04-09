from __future__ import annotations

import importlib.util
import socket
import sys
from pathlib import Path
from threading import Thread
from typing import Optional


class TabletBridge:
    def __init__(self, host: str = "0.0.0.0", port: int = 8090):
        self.host = host
        self.port = port
        self._server = None
        self._thread: Optional[Thread] = None

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    @staticmethod
    def _runtime_roots():
        roots = []

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            roots.append(exe_dir)
            roots.append(exe_dir / "_internal")

        roots.append(Path(__file__).resolve().parent.parent)

        seen = set()
        unique_roots = []
        for root in roots:
            key = str(root)
            if key in seen:
                continue
            seen.add(key)
            unique_roots.append(root)
        return unique_roots

    def _resolve_tablet_app_file(self) -> Path:
        searched = []
        for root in self._runtime_roots():
            candidate = root / "whisperwood_villa_android_tab" / "app.py"
            searched.append(str(candidate))
            if candidate.exists():
                return candidate
        searched_list = "\n".join(f"- {path}" for path in searched)
        raise RuntimeError(f"Tablet app not found. Searched:\n{searched_list}")

    def _load_flask_app(self):
        try:
            from werkzeug.serving import make_server  # noqa: F401
        except Exception as exc:
            raise RuntimeError("Flask/Werkzeug is not installed in this build.") from exc

        app_file = self._resolve_tablet_app_file()

        tablet_dir = str(app_file.parent)
        if tablet_dir not in sys.path:
            sys.path.insert(0, tablet_dir)

        spec = importlib.util.spec_from_file_location("whisperwood_villa_android_runtime", app_file)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load tablet app module.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "app"):
            raise RuntimeError("Tablet app module does not expose Flask app.")
        return module.app

    @staticmethod
    def get_lan_ip() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    def public_url(self) -> str:
        return f"http://{self.get_lan_ip()}:{self.port}"

    def start(self) -> str:
        if self.is_running:
            return self.public_url()

        from werkzeug.serving import make_server

        flask_app = self._load_flask_app()
        self._server = make_server(self.host, self.port, flask_app, threaded=True)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.public_url()

    def stop(self):
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
