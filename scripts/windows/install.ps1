# Install tarjim and start it, in one step.
#
# Run by install.cmd from a downloaded copy of tarjim, or on its own with
#   irm https://raw.githubusercontent.com/willynilly0085-creator/tarjim/master/scripts/windows/install.ps1 | iex
# It installs uv when it is missing, installs tarjim (from the folder this file came with, or the
# latest release when run on its own), starts the engine without a window, makes it start with the
# computer, puts a shortcut to its page on the desktop and opens that page, where setup continues.
# -Quiet leaves the computer as it is (no browser, no startup entry, no shortcut): for tests.
param([int]$Port = 17653, [switch]$Quiet)

$ErrorActionPreference = "Stop"
$Repo = "willynilly0085-creator/tarjim"
$Page = "http://127.0.0.1:$Port"

function Say($text) { Write-Host "tarjim: $text" }

function Stop-With($text) {
    Write-Host ""
    Write-Host "tarjim could not be installed: $text" -ForegroundColor Red
    exit 1
}

function Find-Uv {
    $own = if ($env:UV_INSTALL_DIR) { $env:UV_INSTALL_DIR } else { Join-Path $env:USERPROFILE ".local\bin" }
    if ($env:Path -notlike "*$own*") { $env:Path = "$own;$env:Path" }
    return [bool](Get-Command uv -ErrorAction SilentlyContinue)
}

function Get-Source {
    $root = if ($PSScriptRoot) { Split-Path (Split-Path $PSScriptRoot) } else { "" }
    if ($root -and (Test-Path (Join-Path $root "pyproject.toml"))) { return $root }
    try {
        $tag = (Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest").tag_name
    } catch {
        Stop-With "GitHub did not answer. Check the internet connection and run this again."
    }
    return "https://github.com/$Repo/archive/refs/tags/$tag.zip"
}

function Test-Engine {
    try { return (Invoke-RestMethod "$Page/ping" -TimeoutSec 3).app -eq "tarjim" } catch { return $false }
}

function Stop-Engine {
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listening) { Stop-Process -Id $listening.OwningProcess -Force -ErrorAction SilentlyContinue }
}

function Add-Shortcut($folder) {
    $lines = "[InternetShortcut]", "URL=$Page", "IconIndex=0"
    Set-Content -Path (Join-Path $folder "tarjim.url") -Value $lines -Encoding ASCII
}

Say "This installs tarjim on this computer. Nothing else is needed first."
Say "It downloads about 4 GB: tarjim itself is under 1 MB, the rest is what it runs on"
Say "(PyTorch for timing subtitles to speech, and the libraries for listening and dubbing)."
Say ""
Say "step 1 of 3: the installer tool (uv)"
if (-not (Find-Uv)) {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    if (-not (Find-Uv)) { Stop-With "uv was installed but cannot be found. Close this window and run install again." }
}

$source = Get-Source
Say "step 2 of 3: downloading and installing. This takes several minutes; keep this window open."
if (Test-Engine) { Stop-Engine }
& uv tool install --force --python 3.11 --torch-backend auto "tarjim[dub] @ $source"
if ($LASTEXITCODE -ne 0) { Stop-With "the download or install stopped. Run install again; it continues where it stopped." }

Say "step 3 of 3: starting tarjim (it runs in the background, with no window)"
$python = Join-Path (& uv tool dir) "tarjim\Scripts\pythonw.exe"
Start-Process -FilePath $python -ArgumentList "-P", "-m", "tarjim.server", "--port", $Port -WindowStyle Hidden
foreach ($try in 1..45) {
    if (Test-Engine) { break }
    Start-Sleep -Seconds 2
}
if (-not (Test-Engine)) { Stop-With "tarjim was installed but did not start. Run install again." }

if (-not $Quiet) {
    & (Join-Path (Split-Path $python) "python.exe") -c "from tarjim import autostart; autostart.enable()"
    Add-Shortcut ([Environment]::GetFolderPath("Desktop"))
    Start-Process $Page
}
Say ""
Say "Ready. tarjim's page is $Page (also the 'tarjim' shortcut on your desktop)."
Say "Setup continues there. You can close this window."
