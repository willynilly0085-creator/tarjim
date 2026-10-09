"""Look at this computer the way a setup assistant would: hardware, tools, AI programs,
subscriptions and saved keys. Each part answers on its own so the page can fill its checklist as
answers arrive. Nothing here changes anything or leaves the computer.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

CACHE_SECONDS = 60
cache: dict[str, tuple[float, dict[str, Any]]] = {}


def device() -> dict[str, Any]:
    from tarjim.system import free_disk_gb, graphics, memory_gb

    card = graphics() or {}
    usable = bool(card.get("usable"))
    return {"gpu": usable, "gpu_name": str(card.get("name", "")),
            "vram_gb": float(str(card.get("memory_gb") or 0)) if usable else 0.0,
            "memory_gb": memory_gb(), "disk_free_gb": free_disk_gb()}


def tools() -> dict[str, Any]:
    from tarjim.tools import TOOLS, installed, self_installs

    return {"installed": {tool.id: installed(tool) for tool in TOOLS},
            "sizes": {tool.id: tool.size_gb for tool in TOOLS},
            "manual": [tool.id for tool in TOOLS if not self_installs(tool)]}


def local() -> dict[str, Any]:
    from tarjim.engines.local_programs import installed
    from tarjim.engines.local_servers import discover

    running = discover()
    programs = [{"id": s.id, "name": s.name, "running": True, "models": s.models} for s in running]
    stopped = installed({s.id for s in running})
    programs += [{"id": p.id, "name": p.name, "running": False, "models": p.models,
                  "can_start": p.can_start} for p in stopped]
    return {"programs": programs}


def subscriptions() -> dict[str, Any]:
    from tarjim.engines.catalog import SUBSCRIPTION, of_method
    from tarjim.engines.sign_in import ASKED, BROWSER, signed_in
    from tarjim.engines.subscription import launcher

    def look(provider: Any) -> dict[str, Any]:
        present = bool(launcher(provider.program))
        known = provider.id in BROWSER or provider.id in ASKED
        return {"id": provider.id, "name": provider.name, "installed": present,
                "signed_in": present and known and signed_in(provider.id)}

    providers = of_method(SUBSCRIPTION)
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        return {"apps": list(pool.map(look, providers))}


def keys() -> dict[str, Any]:
    from tarjim.engines.catalog import API, of_method
    from tarjim.engines.choice import has_key

    return {"saved": [p.id for p in of_method(API) if has_key(p.id)]}


SECTIONS = {"device": device, "tools": tools, "local": local, "subscriptions": subscriptions,
            "keys": keys}


def section(name: str, fresh: bool = False) -> dict[str, Any]:
    kept = cache.get(name)
    if kept and not fresh and time.monotonic() - kept[0] < CACHE_SECONDS:
        return kept[1]
    answer = SECTIONS[name]()
    cache[name] = (time.monotonic(), answer)
    return answer


def everything(fresh: bool = False) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=len(SECTIONS)) as pool:
        answers = pool.map(lambda name: (name, section(name, fresh)), SECTIONS)
        return dict(answers)
