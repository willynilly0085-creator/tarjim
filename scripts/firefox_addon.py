"""Have Mozilla sign the Firefox add-on, and write the file Firefox reads for its updates.

Firefox keeps for good only an add-on Mozilla has signed. tarjim's is signed "unlisted": checked
by Mozilla's machine, not shown in its shop, and handed out in tarjim's own release.

    python scripts/firefox_addon.py --updates   write firefox-updates.json for this version
    python scripts/firefox_addon.py             sign this version; prints the signed file's path

The two keys of the addons.mozilla.org account are read from AMO_JWT_ISSUER and AMO_JWT_SECRET
(on Windows the person's own variables too, so a shell opened before they were saved still finds
them). They are handed to web-ext in its environment: never on a command line, never printed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tarjim import __version__, extension_home  # noqa: E402

WEB_EXT = "web-ext@10.8.0"  # Mozilla's own signer, at the version this was tried with
KEYS = {"AMO_JWT_ISSUER": "WEB_EXT_API_KEY", "AMO_JWT_SECRET": "WEB_EXT_API_SECRET"}


def kept(name: str) -> str:
    """A key by its variable's name: this process's, else the person's own on Windows."""
    if os.environ.get(name) or sys.platform != "win32":
        return os.environ.get(name, "")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as own:
            return str(winreg.QueryValueEx(own, name)[0])
    except OSError:
        return ""


def folder(into: Path) -> Path:
    """What is signed: the packaged add-on with the manifest Firefox reads."""
    made = into / "addon"
    shutil.copytree(extension_home.PACKAGED, made)
    (made / extension_home.MANIFEST).write_text(
        extension_home.firefox_manifest(), encoding="utf-8", newline="\n")
    return made


def sign(source: Path, out: Path) -> Path:
    keys = {theirs: kept(ours) for ours, theirs in KEYS.items()}
    missing = [ours for ours, theirs in KEYS.items() if not keys[theirs]]
    if missing:
        raise SystemExit(f"not saved on this computer: {', '.join(missing)}")
    command = [shutil.which("npx") or "npx", "--yes", WEB_EXT, "sign", "--channel", "unlisted",
               "--no-input", "--no-config-discovery",
               "--source-dir", str(source), "--artifacts-dir", str(out)]
    subprocess.run(command, check=True, env={**os.environ, **keys})
    [signed] = out.glob("*.xpi")
    return signed.replace(out / extension_home.SIGNED)


def main() -> None:
    if "--updates" in sys.argv:
        told = json.dumps(extension_home.updates(__version__), indent=2) + "\n"
        (ROOT / "firefox-updates.json").write_text(told, encoding="utf-8", newline="\n")
        return
    work = Path(tempfile.mkdtemp(prefix="tarjim-firefox-"))
    print(sign(folder(work), work / "signed"))


if __name__ == "__main__":
    main()
