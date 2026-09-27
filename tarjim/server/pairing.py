import secrets
import threading
import time
from dataclasses import dataclass, field

LIMIT = 5
LIFETIME = 600.0


@dataclass
class Request:
    origin: str
    id: str = field(default_factory=lambda: secrets.token_hex(16))
    state: str = "pending"
    created: float = field(default_factory=time.time)
    claimed: bool = False

    @property
    def expired(self) -> bool:
        return time.time() - self.created > LIFETIME


class Pairing:
    def __init__(self) -> None:
        self.requests: dict[str, Request] = {}
        self.lock = threading.Lock()

    def tidy(self) -> None:
        for key in [k for k, r in self.requests.items() if r.expired]:
            del self.requests[key]

    def ask(self, origin: str) -> Request | None:
        with self.lock:
            self.tidy()
            if sum(r.state == "pending" for r in self.requests.values()) >= LIMIT:
                return None
            request = Request(origin)
            self.requests[request.id] = request
            return request

    def pending(self) -> list[Request]:
        with self.lock:
            self.tidy()
            return [r for r in self.requests.values() if r.state == "pending"]

    def decide(self, request_id: str, allow: bool) -> bool:
        with self.lock:
            request = self.requests.get(request_id)
            if request is None or request.state != "pending":
                return False
            request.state = "allowed" if allow else "denied"
            return True

    def claim(self, request_id: str, token: str) -> dict[str, str]:
        with self.lock:
            request = self.requests.get(request_id)
            if request is None or request.expired:
                return {"state": "unknown"}
            if request.state == "allowed" and not request.claimed:
                request.claimed = True
                return {"state": "allowed", "token": token}
            return {"state": request.state}
