from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, ClassVar

from tarjim.server.guard import COOKIE, page_key

WEB = Path(__file__).resolve().parent.parent / "web"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png"}
POLICY = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
          "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
SECURITY = [("Content-Security-Policy", POLICY), ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"), ("X-Frame-Options", "DENY"),
            ("Cache-Control", "no-store")]
Query = dict[str, list[str]]


class PageRoutes(BaseHTTPRequestHandler):
    token: ClassVar[str]

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def home(self, _query: Query) -> None:
        self.send_file(WEB / "index.html", cookie=True)

    def asset(self, _query: Query, name: str) -> None:
        path = (WEB / name).resolve()
        if WEB not in path.parents or not path.is_file() or path.suffix not in TYPES:
            self.reply(404, {"error": "not found"})
            return
        self.send_file(path)

    def send_file(self, path: Path, cookie: bool = False) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPES[path.suffix])
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY:
            self.send_header(name, value)
        if cookie:
            self.send_header("Set-Cookie",
                             f"{COOKIE}={page_key(self.token)}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(body)
