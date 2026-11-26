"""The reason a job failed, read from its error, so the page can say it in the person's words."""
from tarjim import x_posts

SIGNED_OUT = ("Failed to authenticate", "OAuth session expired", "ot logged in", "run /login",
              "login required", "ign in again")
REFUSED_ACCOUNT = ("not eligible", "Eligibility check failed", "erify your account")
NOT_MEDIA = ("not a video or sound file",)
TOO_LONG = ("longer than six hours of sound",)
A_LIST = ("this link is a list of videos",)
IN_USE = ("is open in another program",)
# Hugging Face's words for a model not on the disk while downloads are off: before
# "download", which its own sentence also says (2026-11-20)
MISSING_PART = ("LocalEntryNotFoundError", "cached snapshot folder",
                "outgoing traffic has been disabled")
UPDATED = ("from 'tarjim.", "named 'tarjim.")  # its code changed on disk while it ran
# X kept the post from the signed-in account, or from tarjim's guest read (x_posts.py): before
# "signin", whose marks are about the AI's sign-in, and "download"
X_ACCOUNT = (x_posts.ACCOUNT,)
X_GUEST = x_posts.REFUSED
X_SILENT = (x_posts.SILENT,)
REASONS = [("updated", UPDATED), ("x_account", X_ACCOUNT), ("x_signin", X_GUEST),
           ("x_silent", X_SILENT),
           ("in_use", IN_USE), ("media", NOT_MEDIA), ("long", TOO_LONG), ("list", A_LIST),
           ("parts", MISSING_PART),
           ("account", REFUSED_ACCOUNT), ("quota", ("QuotaExhausted", "quota", " 429:")),
           ("signin", SIGNED_OUT),
           ("key", ("API key missing", "API key not valid", " 401:", " 403:")),
           ("download", ("DownloadError", "download")), ("tools", ("not found; install",)),
           ("dub", ("DubUnavailable", "VoiceError"))]


def classify(error: Exception) -> str:
    text = f"{type(error).__name__} {error}"
    return next((code for code, marks in REASONS if any(m in text for m in marks)), "unknown")
