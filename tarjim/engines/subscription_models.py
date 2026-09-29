"""The models a subscription really offers, read from that subscription's own program.

Claude Code keeps the extra models an account can use (for example Fable) in ~/.claude.json;
the aliases opus, sonnet and haiku always point at the newest version of each family.
"""
import json
import os
from pathlib import Path

CLAUDE_ALIASES = ("opus", "sonnet", "haiku")


def claude_config() -> Path:
    folder = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(folder) / ".claude.json" if folder else Path.home() / ".claude.json"


def claude_models() -> list[tuple[str, str]]:
    """Every model this Claude account can pick, with Claude's own description when it has one."""
    try:
        extra = json.loads(claude_config().read_text(encoding="utf-8")).get(
            "additionalModelOptionsCache") or []
    except (OSError, ValueError, AttributeError):
        extra = []
    offered = [(str(m["value"]), str(m.get("description") or m.get("label") or ""))
               for m in extra if isinstance(m, dict) and m.get("value")]
    return [(alias, "") for alias in CLAUDE_ALIASES] + offered
