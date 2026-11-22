#!/usr/bin/env bash
# Install tarjim and start it, in one step, on macOS or Linux.
#
#   curl -fsSL https://github.com/willynilly0085-creator/tarjim/releases/latest/download/install.sh | bash
#
# The same steps as scripts/windows/install.ps1: it installs uv when it is missing, installs
# tarjim (from the folder this file came with, or the latest release when run on its own) with the
# library versions tested for that release, gets ffmpeg when the computer has none (conda-forge's
# build, in tarjim's own folder; nothing asks for a password), starts the engine in the
# background, makes it start with the computer and opens its page, where setup continues.
# TARJIM_QUIET=1 leaves the computer as it is (no browser, no start with the computer): for tests.
set -u

REPO="willynilly0085-creator/tarjim"
PORT="${TARJIM_PORT:-17653}"
PAGE="http://127.0.0.1:$PORT"
HOME_DIR="${TARJIM_HOME:-$HOME/.tarjim}"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/tarjim-install.XXXXXX")"

say() { echo "tarjim: $*"; }
stop_with() { echo; echo "tarjim could not be installed: $*" >&2; exit 1; }

find_uv() {
    export PATH="${UV_INSTALL_DIR:-$HOME/.local/bin}:$PATH"
    command -v uv >/dev/null 2>&1
}

# The folder this file came with when it holds tarjim, otherwise the latest release.
source_of() {
    local here=""
    # piped from curl there is no file, so no folder of its own: the release is used
    [ -f "${BASH_SOURCE[0]:-}" ] && here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    if [ -n "$here" ] && [ -f "$here/pyproject.toml" ] && [ -d "$here/tarjim" ]; then
        echo "$here"
        return
    fi
    local tag
    tag="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
        | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1)"
    [ -n "$tag" ] || stop_with "GitHub did not answer. Check the internet connection and run this again."
    echo "https://github.com/$REPO/archive/refs/tags/$tag.tar.gz"
}

# One of the release's own files (constraints.txt, overrides.txt, python.txt), or nothing.
release_file() {
    local out="$SCRATCH/$2" tag
    case "$1" in
        https://*)
            tag="$(echo "$1" | sed -n 's#.*/refs/tags/\(v\{0,1\}[0-9][0-9.]*\)\.tar\.gz$#\1#p')"
            [ -n "$tag" ] && curl -fsSL "https://raw.githubusercontent.com/$REPO/$tag/tarjim/$2" -o "$out" \
                || return 0 ;;
        *) cp "$1/tarjim/$2" "$out" 2>/dev/null || return 0 ;;
    esac
    # a copy unpacked on Windows ends its lines with \r, and "3.12\r" is no Python version
    tr -d '\r' < "$out" > "$out.plain" && mv "$out.plain" "$out"
    echo "$out"
}

# Pins are used only when every line is a plain name==version.
plain_pins() {
    [ -n "$1" ] && [ -s "$1" ] || return 1
    ! grep -v '^[[:space:]]*$' "$1" | grep -v '^#' \
        | grep -Eqv '^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9.+!_-]+( *;[ -~]*)?$'
}

engine_up() { curl -fsS -m 3 "$PAGE/ping" 2>/dev/null | grep -q '"tarjim"'; }

# A dropped connection is the usual reason an install stops: the same install is tried again,
# and what was downloaded is kept between tries.
install_engine() {
    local tries="$1" try
    shift
    for try in $(seq 1 "$tries"); do
        if uv tool install --force --python "$PYTHON" --torch-backend auto "$@" "tarjim[dub] @ $SOURCE"; then
            return 0
        fi
        [ "$try" -lt "$tries" ] && say "the download stopped; trying again in 20 seconds (try $try of $tries failed)" \
            && sleep 20
    done
    return 1
}

# ffmpeg from conda-forge into tarjim's own folder, when the computer has none.
get_ffmpeg() {
    command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 && return 0
    local system arch tools="$HOME_DIR/tools"
    case "$(uname -s)" in Darwin) system=osx ;; Linux) system=linux ;; *) return 1 ;; esac
    case "$(uname -m)" in arm64|aarch64) arch=$([ "$system" = osx ] && echo arm64 || echo aarch64) ;; *) arch=64 ;; esac
    mkdir -p "$tools/micromamba" && curl -fsSL "https://micro.mamba.pm/api/micromamba/$system-$arch/latest" \
        | tar -xj -C "$tools/micromamba" bin/micromamba || return 1
    "$tools/micromamba/bin/micromamba" create -q -y -r "$tools/mamba" -p "$tools/ffmpeg" -c conda-forge ffmpeg \
        >/dev/null || return 1
    FFMPEG="$tools/ffmpeg/bin/ffmpeg"
}

say "This installs tarjim on this computer. Nothing else is needed first."
say "It downloads a few GB: tarjim itself is under 1 MB, the rest is what it runs on"
say "(PyTorch for timing subtitles to speech, and the libraries for listening and dubbing)."
say ""
say "step 1 of 3: the installer tool (uv)"
if ! find_uv; then
    curl -LsSf https://astral.sh/uv/install.sh | sh || stop_with "uv could not be downloaded."
    find_uv || stop_with "uv was installed but cannot be found. Open a new terminal and run this again."
fi

SOURCE="$(source_of)"
say "step 2 of 3: downloading and installing. This takes several minutes; keep this window open."
PYTHON="3.11"
wanted="$(release_file "$SOURCE" python.txt)"
[ -n "$wanted" ] && grep -Eq '^3\.[0-9]{1,2}$' "$wanted" && PYTHON="$(head -n 1 "$wanted")"
pins="$(release_file "$SOURCE" constraints.txt)"
lifted="$(release_file "$SOURCE" overrides.txt)"
tested=()
if plain_pins "$pins"; then
    tested=(--upgrade -c "$pins")
    [ -n "$lifted" ] && [ -s "$lifted" ] && tested+=(--overrides "$lifted")
fi
done_ok=1
install_engine 3 "${tested[@]+"${tested[@]}"}" || done_ok=0
if [ "$done_ok" = 0 ] && [ "${#tested[@]}" -gt 0 ]; then
    say "trying again without the tested library versions"
    install_engine 1 && done_ok=1
fi
[ "$done_ok" = 1 ] || stop_with "the download or install stopped. Run this again; it continues where it stopped."
FFMPEG=""
get_ffmpeg || say "ffmpeg could not be fetched; tarjim's page will ask for it."

say "step 3 of 3: starting tarjim (it runs in the background, with no window)"
engine="$(uv tool dir)/tarjim/bin/python"
[ -x "$engine" ] || stop_with "tarjim was installed but its Python cannot be found."
mkdir -p "$HOME_DIR"
"$engine" -P -c "import sys; from tarjim import config
if sys.argv[1]:
    config.save('ffmpeg', sys.argv[1]); config.save('ffprobe', sys.argv[1][:-6] + 'ffprobe')" "$FFMPEG"
# an engine already running from an earlier install makes way for the new one
engine_up && command -v lsof >/dev/null 2>&1 && kill $(lsof -ti "tcp:$PORT" -sTCP:LISTEN) 2>/dev/null && sleep 2
nohup "$engine" -P -m tarjim.server --port "$PORT" >>"$HOME_DIR/server.log" 2>&1 &
for _ in $(seq 1 45); do engine_up && break; sleep 2; done
engine_up || stop_with "tarjim was installed but did not start. Run this again."

if [ -z "${TARJIM_QUIET:-}" ]; then
    "$engine" -P -c "from tarjim import autostart; autostart.enable()"
    if command -v open >/dev/null 2>&1; then open "$PAGE"; else xdg-open "$PAGE" >/dev/null 2>&1 || true; fi
fi
rm -rf "$SCRATCH"
say ""
say "Ready. tarjim's page is $PAGE."
say "Setup continues there. You can close this window."
