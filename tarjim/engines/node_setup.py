"""The first install of tarjim's own Node.js with one npm program, run hidden by app_install.

`python -P -m tarjim.engines.node_setup @openai/codex`: the newest LTS from nodejs.org, checked
against its SHASUMS256.txt, unpacked beside ~/.tarjim/node with the program installed into it,
then put in place. What it prints goes to the install log, whose last line the page shows.
"""
import sys

from tarjim.engines import node_release
from tarjim.engines.app_install import PACKAGES


def main(arguments: list[str]) -> int:
    package = arguments[0] if len(arguments) == 1 else ""
    if package not in PACKAGES.values():
        print(f"not a program tarjim installs: {package!r}", flush=True)
        return 2
    version = node_release.newest_lts(node_release.ask_index())
    if not version:
        print("nodejs.org could not be reached or named no LTS release", flush=True)
        return 1
    print(f"Node.js {version} from nodejs.org, checked against SHASUMS256.txt", flush=True)
    try:
        node_release.build(version, [package])
    except node_release.FAILURES as error:
        print(f"Node.js {version} was not installed: {error}", flush=True)
        return 1
    print(f"Node.js {version} and {package} are installed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
