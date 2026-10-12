"""Node.js of tarjim's own, for subscription programs that are npm packages (Codex, Copilot).

A person with no Node.js is not sent to install it: on Windows tarjim downloads the official
portable build from nodejs.org into its own folder and installs the package beside it, so nothing
else on the computer changes. Elsewhere the page still links to the Node.js download.
"""
import os
import sys

from tarjim.config import HOME

FOLDER = HOME / "node"
AVAILABLE = sys.platform == "win32"
SCRIPT = """$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'
$all = Invoke-RestMethod https://nodejs.org/dist/index.json
$version = ($all | Where-Object {{ $_.lts }} | Select-Object -First 1).version
$name = "node-$version-win-x64"
$zip = Join-Path $env:TEMP 'tarjim-node.zip'
Invoke-WebRequest "https://nodejs.org/dist/$version/$name.zip" -OutFile $zip
if (Test-Path '{folder}') {{ Remove-Item -Recurse -Force '{folder}' }}
Expand-Archive $zip '{home}' -Force
Rename-Item (Join-Path '{home}' $name) 'node'
Remove-Item $zip
& '{folder}\\npm.cmd' install -g --prefix '{folder}' {package}
exit $LASTEXITCODE"""


def npm() -> str:
    found = FOLDER / "npm.cmd"
    return str(found) if found.is_file() else ""


def node() -> str:
    found = FOLDER / "node.exe"
    return str(found) if found.is_file() else ""


def shim(name: str) -> str | None:
    found = FOLDER / f"{name}.cmd"
    return str(found) if found.is_file() else None


def install(package: str) -> list[str]:
    """Add the package with tarjim's own Node.js, downloading that first when it is missing."""
    if npm():
        return [npm(), "install", "-g", "--prefix", str(FOLDER), package]
    script = SCRIPT.format(folder=FOLDER, home=HOME, package=package)
    return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]


def environment() -> dict[str, str]:
    """npm's own scripts call `node`, so tarjim's folder is on the path while it installs."""
    return {**os.environ, "PATH": f"{FOLDER}{os.pathsep}{os.environ.get('PATH', '')}"}
