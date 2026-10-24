"""`python -m tarjim.server`: the engine (engine.py), started so that it always leaves a trace in
server.log, even when it fails while importing (boot.py). `main` stays here for tarjim-serve."""
from tarjim.server import boot


def main(argv: list[str] | None = None) -> int:
    from tarjim.server.engine import main as engine

    return engine(argv)


if __name__ == "__main__":
    boot.open_log()
    raise SystemExit(boot.run(main))
