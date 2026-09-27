import re
from typing import Any

from tarjim.keys import status, store

JOB = "([0-9a-f]{12})"
PAIR = "([0-9a-f]{32})"
Query = dict[str, list[str]]
Routes = list[tuple[re.Pattern[str], str]]


def table(pairs: list[tuple[str, str]]) -> Routes:
    return [(re.compile(pattern), name) for pattern, name in pairs]


GET_ROUTES = table([
    (r"^/ping$", "ping"), (r"^/languages$", "languages"), (r"^/jobs$", "list_jobs"),
    (rf"^/jobs/{JOB}$", "show"), (rf"^/files/{JOB}/([^/]+)$", "send_output"),
    (r"^/translate$", "legacy"), (r"^/keys$", "key_status"), (r"^/$", "home"),
    (r"^/web/([\w.-]+(?:/[\w.-]+)?)$", "asset"), (r"^/system$", "system"),
    (r"^/setup$", "setup_state"), (r"^/tools$", "list_tools"),
    (rf"^/pair/{PAIR}$", "pair_state"), (r"^/pairs$", "list_pairs")])
POST_ROUTES = table([
    (r"^/jobs$", "create_json"), (r"^/upload$", "upload"), (rf"^/reveal/{JOB}$", "reveal"),
    (rf"^/open/{JOB}$", "play"), (rf"^/retry/{JOB}$", "retry"), (r"^/keys$", "save_key"),
    (r"^/setup$", "save_setup"), (r"^/tools/([a-z_]+)$", "get_tool"), (r"^/pair$", "ask_pair"),
    (rf"^/pairs/{PAIR}/(allow|deny)$", "decide_pair")])
OPEN = [re.compile(p) for p in (r"^/$", r"^/web/", r"^/ping$", r"^/languages$", r"^/pair$",
                                  rf"^/pair/{PAIR}$")]


def is_open(path: str) -> bool:
    return any(pattern.match(path) for pattern in OPEN)


class KeyRoutes:
    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def key_status(self, _query: Query) -> None:
        self.reply(200, status())

    def save_key(self, _query: Query) -> None:
        data = self.read_json()
        result = store(str(data.get("provider", "")), str(data.get("key", "")))
        self.reply(200 if result == "saved" else 400, {"result": result, **status()})
