"""The reason a job failed, read from its error, so the page can say it in the person's words."""
SIGNED_OUT = ("Failed to authenticate", "OAuth session expired", "ot logged in", "run /login",
              "login required", "ign in again")
REFUSED_ACCOUNT = ("not eligible", "Eligibility check failed", "erify your account")
NOT_MEDIA = ("not a video or sound file",)
TOO_LONG = ("longer than six hours of sound",)
A_LIST = ("this link is a list of videos",)
UPDATED = ("from 'tarjim.", "named 'tarjim.")  # its code changed on disk while it ran
REASONS = [("updated", UPDATED), ("media", NOT_MEDIA), ("long", TOO_LONG), ("list", A_LIST),
           ("account", REFUSED_ACCOUNT), ("quota", ("QuotaExhausted", "quota", " 429:")),
           ("signin", SIGNED_OUT),
           ("key", ("API key missing", "API key not valid", " 401:", " 403:")),
           ("download", ("DownloadError", "download")), ("tools", ("not found; install",)),
           ("dub", ("DubUnavailable", "VoiceError"))]


def classify(error: Exception) -> str:
    text = f"{type(error).__name__} {error}"
    return next((code for code, marks in REASONS if any(m in text for m in marks)), "unknown")
