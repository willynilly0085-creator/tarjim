import secrets
import threading
import time
from dataclasses import dataclass, field

# Requests one extension may hold within LIFETIME, waiting or answered; counted per extension,
# so other extensions can never lock it out, and one denied again and again must wait.
LIMIT = 5
LIFETIME = 600.0
CODES = 10000


@dataclass
class Request:
    origin: str
    id: str = field(default_factory=lambda: secrets.token_hex(16))
    state: str = "pending"
    created: float = field(default_factory=time.time)
    claimed: bool = False
    code: str = field(default_factory=lambda: f"{secrets.randbelow(CODES):04d}")

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
            waiting = (origin, "pending")
            again = [k for k, r in self.requests.items() if (r.origin, r.state) == waiting]
            for key in again:  # one waiting request per extension: asking again replaces it
                del self.requests[key]
            code = self.unused_code()
            if code is None or sum(r.origin == origin for r in self.requests.values()) >= LIMIT:
                return None
            request = Request(origin, code=code)
            self.requests[request.id] = request
            return request

    def unused_code(self) -> str | None:
        """A code no other waiting request shows, so the code the person types names one request."""
        taken = {r.code for r in self.requests.values() if r.state == "pending"}
        if len(taken) >= CODES:
            return None
        while (code := f"{secrets.randbelow(CODES):04d}") in taken:
            pass
        return code

    def pending(self) -> list[Request]:
        with self.lock:
            self.tidy()
            return [r for r in self.requests.values() if r.state == "pending"]

    def decide(self, request_id: str, allow: bool, code: str = "") -> bool:
        """Allowing needs the code the extension showed the person; denying never does."""
        with self.lock:
            request = self.requests.get(request_id)
            if request is None or request.state != "pending":
                return False
            if allow and not secrets.compare_digest(code.encode(), request.code.encode()):
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
