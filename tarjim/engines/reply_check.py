"""Why an engine's reply held no answer, said the same way for every engine.

An empty, blocked or cut-off reply used to surface as "returned an empty answer" or as a bare JSON
error, with nothing to say whether the service refused it, ran out of room or simply stopped. Each
engine reads its own reason (Gemini's finish and block reasons, the chat format's finish_reason,
Anthropic's stop_reason, a program's exit code and the end of what it complained) and this names
it in the log and in the error, with the model that answered.
"""
from dataclasses import dataclass
from typing import Any

from tarjim.engines.web import EngineError

CUT = {"max_tokens", "length", "model_length", "max_output_tokens", "error_max_turns"}
BLOCKED = {"safety", "recitation", "prohibited_content", "blocklist", "spii", "content_filter",
           "refusal", "image_safety", "language"}
TAIL = 300


@dataclass(frozen=True)
class Reason:
    finish: str = ""
    block: str = ""
    detail: str = ""

    def text(self) -> str:
        parts = [f"finish_reason={self.finish}" if self.finish else "",
                 f"block_reason={self.block}" if self.block else "", self.detail]
        return "; ".join(p for p in parts if p)

    def problem(self, answered: bool) -> str:
        finish = self.finish.lower()
        if self.block or finish in BLOCKED:
            return "blocked"
        if finish in CUT:
            return "cut off"
        return "" if answered else "empty reply"


class ReplyFailed(EngineError):
    def __init__(self, provider: str, model: str, problem: str, reason: Reason) -> None:
        why = reason.text()
        RuntimeError.__init__(self, f"{provider} ({model or 'default model'}): {problem}"
                                    f"{f' [{why}]' if why else ''}")
        self.provider, self.status, self.code = provider, 0, f"{problem} {why}".strip()


def named(value: Any) -> str:
    """An SDK's enum by its name ("MAX_TOKENS"), anything else as it is written."""
    if value is None:
        return ""
    return str(getattr(value, "name", None) or value).removeprefix("FinishReason.")


def inside(source: Any, step: str | int) -> Any:
    if isinstance(source, dict):
        return source.get(step)
    if isinstance(step, str):
        return getattr(source, step, None)
    try:
        return source[step]
    except (LookupError, TypeError):
        return None


def part(source: Any, *path: str | int) -> Any:
    """One value down a path of keys, places or attributes; None where the path ends early."""
    for step in path:
        source = inside(source, step)
    return source


def gemini_reason(response: Any) -> Reason:
    finish = part(response, "candidates", 0, "finish_reason")
    finish = finish if finish is not None else part(response, "candidates", 0, "finishReason")
    block = part(response, "prompt_feedback", "block_reason")
    block = block if block is not None else part(response, "promptFeedback", "blockReason")
    return Reason(named(finish), named(block))


def chat_reason(answer: Any) -> Reason:
    refusal = part(answer, "choices", 0, "message", "refusal")
    return Reason(named(part(answer, "choices", 0, "finish_reason")),
                  detail=f"refusal: {str(refusal)[:TAIL]}" if refusal else "")


def anthropic_reason(answer: Any) -> Reason:
    return Reason(named(part(answer, "stop_reason")))


def ollama_reason(answer: Any) -> Reason:
    return Reason(named(part(answer, "done_reason")))


def program_reason(code: int, complaint: str) -> Reason:
    said = " ".join(complaint.split())
    tail = f"; stderr: ...{said[-TAIL:]}" if len(said) > TAIL else f"; stderr: {said}"
    return Reason(detail=f"exit code {code}{tail if said else ''}")


def failed(provider: str, model: str, problem: str, reason: Reason) -> ReplyFailed:
    error = ReplyFailed(provider, model, problem, reason)
    print(f"reply: {error}", flush=True)
    return error


def require(provider: str, model: str, answered: bool, reason: Reason) -> None:
    problem = reason.problem(answered)
    if problem:
        raise failed(provider, model, problem, reason)


def checked(provider: str, model: str, text: str | None, reason: Reason) -> str:
    """The reply's text; an empty, blocked or cut-off reply is a failure that says why."""
    require(provider, model, bool((text or "").strip()), reason)
    return text or ""
