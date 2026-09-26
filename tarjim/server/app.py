import json
import re
import shutil
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from tarjim.languages import LANGUAGES
from tarjim.server.guard import allowed_origin, local_host, safe_name, token_ok
from tarjim.server.jobs import MODES, Board, Order, Task

PORT = 17653
MAX_UPLOAD = 8 * 1024**3
BLOCK = 1024 * 1024
TOKEN_HEADERS = ("X-Tarjim-Token", "X-Trans-Token")
OPEN_PATHS = {"/ping", "/languages"}
JOB = "([0-9a-f]{12})"
Query = dict[str, list[str]]
GET_ROUTES = [(re.compile(p), name) for p, name in [
    (r"^/ping$", "ping"), (r"^/languages$", "languages"), (r"^/jobs$", "list_jobs"),
    (rf"^/jobs/{JOB}$", "show"), (rf"^/files/{JOB}/([^/]+)$", "send_output"),
    (r"^/translate$", "legacy")]]
POST_ROUTES = [(re.compile(p), name) for p, name in [
    (r"^/jobs$", "create_json"), (r"^/upload$", "upload"), (rf"^/reveal/{JOB}$", "reveal")]]


class Handler(BaseHTTPRequestHandler):
    board: ClassVar[Board]
    token: ClassVar[str]
    uploads: ClassVar[Path]

    def reply(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def cors(self) -> None:
        origin = allowed_origin(self.headers.get("Origin", ""))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", ", ".join((*TOKEN_HEADERS,
                                                                   "Content-Type")))
        self.end_headers()

    def admitted(self, path: str) -> bool:
        if not local_host(self.headers.get("Host", "")):
            self.reply(403, {"error": "host"})
            return False
        given = next((self.headers.get(h, "") for h in TOKEN_HEADERS if self.headers.get(h)), "")
        if path not in OPEN_PATHS and not token_ok(given, self.token):
            self.reply(403, {"error": "token"})
            return False
        return True

    def do_GET(self) -> None:
        self.dispatch(GET_ROUTES)

    def do_POST(self) -> None:
        self.dispatch(POST_ROUTES)

    def dispatch(self, routes: list[tuple[re.Pattern[str], str]]) -> None:
        url = urllib.parse.urlparse(self.path)
        if not self.admitted(url.path):
            return
        query = urllib.parse.parse_qs(url.query)
        for pattern, name in routes:
            match = pattern.match(url.path)
            if match:
                getattr(self, name)(query, *map(urllib.parse.unquote, match.groups()))
                return
        self.reply(404, {"error": "not found"})

    def ping(self, _query: Query) -> None:
        self.reply(200, {"ok": True, "app": "tarjim"})

    def languages(self, _query: Query) -> None:
        self.reply(200, [{"code": c, "name": lang.name, "native": lang.native}
                         for c, lang in LANGUAGES.items()])

    def list_jobs(self, _query: Query) -> None:
        self.reply(200, [t.view() for t in self.board.recent()])

    def create_json(self, _query: Query) -> None:
        self.create(self.read_json())
    def read_json(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0") or 0)
        try:
            data = json.loads(self.rfile.read(min(size, BLOCK)) or b"{}")
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def create(self, data: dict[str, Any]) -> None:
        source = str(data.get("url", "")).strip()
        if not source.lower().startswith(("http://", "https://")):
            return self.reply(400, {"error": "bad url"})
        self.accept(order_from(source, data))

    def accept(self, order: Order) -> None:
        if order.mode not in MODES:
            return self.reply(400, {"error": "mode"})
        self.reply(200, self.board.submit(order).view())

    def upload(self, query: Query) -> None:
        name = safe_name(first(query, "name"))
        size = int(self.headers.get("Content-Length", "0") or 0)
        if name is None or not 0 < size <= MAX_UPLOAD:
            return self.reply(400, {"error": "file"})
        folder = self.uploads / Task(Order("")).id
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / name).open("wb") as out:
            copy_limited(self.rfile, out, size)
        options = {k: first(query, k) for k in ("target", "mode", "dialect")}
        self.accept(order_from(str(folder / name), options, name))

    def show(self, _query: Query, task_id: str) -> None:
        task = self.board.get(task_id)
        self.reply(200, task.view()) if task else self.reply(404, {"error": "job"})

    def send_output(self, _query: Query, task_id: str, name: str) -> None:
        task = self.board.get(task_id)
        match = next((p for p in (task.outputs if task else []) if p.name == name), None)
        if match is None:
            return self.reply(404, {"error": "file"})
        self.send_response(200)
        self.cors()
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(match.stat().st_size))
        quoted = urllib.parse.quote(match.name)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quoted}")
        self.end_headers()
        with match.open("rb") as source:
            shutil.copyfileobj(source, self.wfile, BLOCK)

    def reveal(self, _query: Query, task_id: str) -> None:
        from tarjim.server.desktop import reveal

        task = self.board.get(task_id)
        if not task or not task.outputs:
            return self.reply(404, {"error": "job"})
        reveal(task.outputs[0])
        self.reply(200, {"ok": True})

    def legacy(self, query: Query) -> None:
        mode = first(query, "mode") or "srt"
        self.create({"url": first(query, "url"), "mode": mode if mode in MODES else "burn"})

    def log_message(self, format: str, *args: Any) -> None:
        return None


def first(query: Query, key: str) -> str:
    return (query.get(key) or [""])[0].strip()


def order_from(source: str, data: dict[str, Any], name: str = "") -> Order:
    return Order(source, str(data.get("target") or "ar"), str(data.get("mode") or "burn"),
                 str(data.get("dialect") or "saudi"), name)


def copy_limited(source: Any, target: Any, size: int) -> None:
    left = size
    while left > 0:
        chunk = source.read(min(BLOCK, left))
        if not chunk:
            break
        target.write(chunk)
        left -= len(chunk)


def serve(board: Board, token: str, uploads: Path, port: int = PORT) -> None:
    Handler.board, Handler.token, Handler.uploads = board, token, uploads
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
