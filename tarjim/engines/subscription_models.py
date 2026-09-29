"""The models a subscription offers, named the way the subscription's own app names them.

Claude lists the newest model of each family first and the older ones under "more models", like
the model picker in the Claude app. Claude Code accepts these full ids with --model. Extra models
an account has (Claude Code keeps them in ~/.claude.json) are added when they are not listed yet.
Translation needs little of a model, so the lightest one is suggested.
"""
import json
import os
import re
from pathlib import Path

CLAUDE_LATEST = ("claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5-5", "claude-haiku-4-5")
CLAUDE_MORE = ("claude-sonnet-5", "claude-opus-5", "claude-fable-5", "claude-opus-4-8",
               "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6")
CLAUDE_SUGGESTED = "claude-haiku-4-5"
MODEL_ID = re.compile(r"^claude-([a-z]+)-(\d+)(?:-(\d+))?")
Model = dict[str, str]


def claude_config() -> Path:
    folder = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(folder) / ".claude.json" if folder else Path.home() / ".claude.json"


def display_name(model_id: str) -> str:
    found = MODEL_ID.match(model_id)
    if not found:
        return model_id
    family, major, minor = found.groups()
    return f"{family.title()} {major}.{minor}" if minor else f"{family.title()} {major}"


def account_extras() -> list[str]:
    try:
        extra = json.loads(claude_config().read_text(encoding="utf-8")).get(
            "additionalModelOptionsCache") or []
    except (OSError, ValueError, AttributeError):
        extra = []
    return [str(m["value"]) for m in extra
            if isinstance(m, dict) and m.get("value") and not m.get("disabled")]


def claude_models() -> list[Model]:
    """Every model this Claude account can pick: newest first, then older ones."""
    known = set(CLAUDE_LATEST) | set(CLAUDE_MORE)
    extras = [m for m in account_extras() if m.split("[")[0] not in known]
    rows = [(m, "latest") for m in CLAUDE_LATEST] + [(m, "more") for m in (*CLAUDE_MORE, *extras)]
    return [{"id": m, "name": display_name(m), "group": group,
             "suggested": "yes" if m == CLAUDE_SUGGESTED else ""} for m, group in rows]
