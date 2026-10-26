"""Whether a translator can work right now, so the page never saves one that would only fail later
at the translation step, and says so when the saved one stopped working."""
from tarjim.engines.choice import LOCAL, usable


def local_works(server: str) -> bool:
    """An AI program on this computer translates only when it runs and has a model."""
    from tarjim.engines.local_servers import BY_ID, alive, models_of

    if server not in BY_ID:
        return False
    url = BY_ID[server][1]
    return alive(server, url) and bool(models_of(server, url))


def translator_works(provider: str, server: str) -> bool:
    return local_works(server) if provider == LOCAL else usable(provider, "translate")


def works_now(provider: str) -> bool:
    """Quick enough for the line above Translate: a program on this computer only has to answer."""
    if provider != LOCAL:
        return usable(provider, "translate")
    from tarjim.engines.local_servers import BY_ID, answering, chosen_server

    return answering(BY_ID[chosen_server()][1])
