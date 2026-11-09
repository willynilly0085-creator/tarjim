"""How a clip is heard (2026-11-09). The defaults are listen/merge.PASSES, listen/chunks
.CHUNK_SECONDS and listen/coverage.GAP_SECONDS. Settings that only lower accuracy (the sync
retry, how eagerly a voice changes the speaker, skipping missed speech) are not offered: the
review of 2026-11-09 measured them as harm with no gain."""
from tarjim.prefs.make import ADVANCED, amount, basic, on_off, pick
from tarjim.prefs.spec import Spec

LISTEN: tuple[Spec, ...] = (
    # Odd counts only, so a word is kept by a real majority of the passes.
    pick("listen.passes", "كم مرة يسمع كل جزء", (3, 1, 5)),
    # 45 to 120: one request for a whole clip drifts, a short piece loses its context.
    basic(amount("listen.chunk_seconds", "طول الجزء اللي ينرسل للسماع (ثانية)", 75,
                 (45, 120, 5))),
    # Only tighter than 2 s: a longer gap would hide speech that was missed.
    amount("listen.gap_seconds", "أقل فراغ يعتبره كلام فايت (ثانية)", 2.0, (1.0, 2.0, 0.1)),
    on_off("listen.local_backup", "لو تعطل السماع بالإنترنت يكمل بالسماع اللي على جهازك", True,
           ADVANCED),
    # Speed switches for a weak computer, named honestly: each one costs accuracy.
    on_off("listen.second_opinion", "يتأكد من التوقيت بالسماع اللي على جهازك (طافي أسرع، "
           "والتوقيت أقل دقة)", True, ADVANCED),
    on_off("listen.voice_check", "يتأكد مين المتكلم من صوته (طافي أسرع، والمتكلم أقل دقة)",
           True, ADVANCED),
    # How the aligner reads the text against the sound (asr/align.py, 2026-11-09): strict gives
    # every written word a place; tolerant lets sound nobody wrote down pass, and a line written
    # twice or never said is dropped or marked instead of being squeezed onto real speech.
    pick("listen.aligner", "طريقة مطابقة الكلام مع الصوت (المرن يتجاوز السطر المكرر أو اللي "
         "ما انقال)", ("strict", "tolerant"), ADVANCED),
)
