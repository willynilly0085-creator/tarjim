"""Compare a full pip-audit of the newest tested versions with the advisories tarjim accepts.

    pip-audit --disable-pip --no-deps -r tarjim/constraints.txt -f json -o audit.json
    python scripts/advisories.py audit.json report.md

The accepted list is .github/audit-known.txt (what CI ignores), and tarjim/known_issues.json
holds what each one is and the versions that fix it. Writes a report and exits 1 when:
- an advisory is found that is not accepted (CI fails on it too);
- an accepted advisory is no longer found (its lines can be removed, and people's notice goes);
- a fixed version of an accepted one can now be installed with tarjim (so the weekly move or a
  release should take it).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = ROOT / ".github" / "audit-known.txt"
KNOWN = ROOT / "tarjim" / "known_issues.json"
OVERRIDES = ROOT / "tarjim" / "overrides.txt"
PYTHON = ROOT / "tarjim" / "python.txt"


def python() -> str:
    """The Python the release runs on (read here: this runs without tarjim installed)."""
    return PYTHON.read_text(encoding="utf-8").strip()


def accepted() -> set[str]:
    lines = ACCEPTED.read_text(encoding="utf-8").splitlines()
    return {line.split()[0] for line in lines if line.strip() and not line.startswith("#")}


def found(audit: dict) -> dict[str, str]:
    """Every advisory pip-audit reported, with the library and version it was found in."""
    seen = {}
    for dependency in audit.get("dependencies", []):
        for vuln in dependency.get("vulns", []):
            seen[vuln["id"]] = f"{dependency['name']} {dependency['version']}"
    return seen


def installable(package: str, fixed_by: str) -> bool:
    """Does tarjim (dub extra, the release's Python, Linux) resolve with the fixed version?"""
    with tempfile.TemporaryDirectory() as folder:
        wanted = Path(folder) / "fixed.in"
        wanted.write_text(f"{package}{fixed_by}\n", encoding="utf-8")
        done = subprocess.run(
            ["uv", "pip", "compile", str(ROOT / "pyproject.toml"), str(wanted), "--extra", "dub",
             "--python-version", python(), "--python-platform", "x86_64-unknown-linux-gnu",
             "--overrides", str(OVERRIDES), "--quiet", "-o", str(Path(folder) / "out.txt")],
            capture_output=True, text=True, check=False)
    return done.returncode == 0


def rows(seen: dict[str, str], known: list[dict]) -> tuple[list[str], int]:
    lines, problems = [], 0
    for entry in known:
        still = entry["id"] in seen
        fixable = installable(entry["package"], entry["fixed_by"])
        problems += (not still) + fixable
        lines.append(f"| {entry['id']} | {entry['package']} `{entry['affected']}` | "
                     f"{'yes' if still else '**no: remove it**'} | "
                     f"{'**yes: take it**' if fixable else 'no'} |")
    return lines, problems


def report(seen: dict[str, str]) -> tuple[str, int]:
    known = json.loads(KNOWN.read_text(encoding="utf-8"))
    new = sorted(set(seen) - accepted())
    lines, problems = rows(seen, known)
    text = ["Accepted advisories against the newest tested versions:", "",
            "| Advisory | Affected | Still found | Fixed version installable |",
            "|---|---|---|---|",
            *lines, ""]
    text += [f"New, not accepted: {name} ({seen[name]})" for name in new] or ["Nothing new."]
    return "\n".join(text) + "\n", problems + len(new)


def main(audit_file: str, out: str) -> int:
    seen = found(json.loads(Path(audit_file).read_text(encoding="utf-8")))
    text, problems = report(seen)
    Path(out).write_text(text, encoding="utf-8")
    print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
