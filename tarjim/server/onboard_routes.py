"""The setup assistant: scan the computer, propose a plan, carry it out."""
from typing import Any, ClassVar

from tarjim.tools import Shelf

Query = dict[str, list[str]]


class OnboardRoutes:
    shelf: ClassVar[Shelf]

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def scan_part(self, query: Query, name: str) -> None:
        from tarjim.onboarding.scan import section

        self.reply(200, section(name, fresh=query.get("fresh") == ["1"]))

    def setup_plan(self, query: Query) -> None:
        from tarjim.onboarding.plan import make_plan
        from tarjim.onboarding.scan import everything

        found = everything(fresh=query.get("fresh") == ["1"])
        self.reply(200, {"scan": found, "plan": make_plan(found)})

    def setup_selftest(self, _query: Query) -> None:
        from tarjim.onboarding.selftest import selftest

        self.reply(200, selftest(str(self.read_json().get("language", "ar"))))

    def setup_apply(self, _query: Query) -> None:
        from tarjim.onboarding.apply import apply
        from tarjim.onboarding.scan import cache

        result = apply(self.read_json(), self.shelf)
        cache.clear()
        self.reply(200 if result["saved"] else 400, result)
