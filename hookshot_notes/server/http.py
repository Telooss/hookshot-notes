"""HTTP server on the local network only; nothing in it can change the game."""
from __future__ import annotations

import ipaddress
import json
import mimetypes
import queue
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .state import StateHub

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("font/otf", ".otf")
mimetypes.add_type("text/javascript", ".js")
PING_EVERY = 15


def is_local_client(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_loopback or addr.is_private or addr.is_link_local


def lan_url(port: int) -> str:
    """http://<this PC's LAN address>:<port>/ (no packet is sent: UDP connect only picks the interface)."""
    ip = "127.0.0.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except OSError:
        pass
    return f"http://{ip}:{port}/"


def _inside(base: Path, rel: str) -> Path | None:
    base = base.resolve()
    target = (base / rel).resolve()
    return target if base in target.parents and target.is_file() else None


class _Handler(BaseHTTPRequestHandler):
    server: "_Server"

    def log_message(self, *args) -> None:
        pass

    def _send(self, status: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path | None) -> None:
        if path is None:
            return self._send(404, b"not found")
        self._send(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")

    def do_GET(self) -> None:
        if not is_local_client(self.client_address[0]):
            return self._send(403, b"local network only")
        path = unquote(urlsplit(self.path).path)
        s = self.server
        if path == "/":
            return self._file(_inside(s.web_dir, "index.html"))
        if path.startswith("/web/"):
            return self._file(_inside(s.web_dir, path[5:]))
        if path.startswith("/data/"):
            return self._file(_inside(s.data_dir, path[6:]))
        if path == "/api/world":
            return self._file(_inside(s.data_dir, "world.json"))
        if path == "/api/state":
            return self._send(200, json.dumps(s.hub.snapshot(), ensure_ascii=False).encode(), "application/json")
        for route, handler in s.extra_routes.items():
            if path == route:
                body, ctype = handler()
                return self._send(200, body, ctype)
        if path == "/events":
            return self._events()
        self._send(404, b"not found")

    def _events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = self.server.hub.subscribe()
        try:
            self.wfile.write(b"retry: 2000\n\n")
            while True:
                try:
                    msg = f"data: {q.get(timeout=PING_EVERY)}\n\n"
                except queue.Empty:
                    msg = ": ping\n\n"
                self.wfile.write(msg.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            self.server.hub.unsubscribe(q)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    hub: StateHub
    data_dir: Path
    web_dir: Path
    extra_routes: dict


def serve(hub: StateHub, data_dir: Path, web_dir: Path, port: int) -> ThreadingHTTPServer:
    """Bound to all interfaces (phones on the Wi-Fi); non-local clients get 403. Call serve_forever() on it."""
    srv = _Server(("0.0.0.0", port), _Handler)
    srv.hub, srv.data_dir, srv.web_dir, srv.extra_routes = hub, Path(data_dir), Path(web_dir), {}
    return srv
