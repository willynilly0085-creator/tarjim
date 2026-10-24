"""Asked before a link is sent: the qualities it offers, so the person picks one (fetch.look).

A failure says why in a word the pages already explain: "list" for a link to several videos,
"download" for anything else (a site that refused, a link with no video). The page then sends
the link without a quality and tarjim takes 1080p or the nearest below it.
"""
from typing import Any

from tarjim.fetch import is_url, look
from tarjim.server.jobs import classify

Query = dict[str, list[str]]


class QualityRoutes:
    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def link_qualities(self, _query: Query) -> None:
        url = str(self.read_json().get("url", "")).strip()
        if not is_url(url):
            return self.reply(400, {"error": "bad url"})
        try:
            found = look(url)
        except Exception as error:  # yt-dlp raises many kinds; each becomes one reason
            reason = classify(error)
            return self.reply(422, {"error": reason if reason == "list" else "download"})
        self.reply(200, found)
