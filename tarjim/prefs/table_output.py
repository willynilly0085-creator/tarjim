"""Where files go and what a dub sounds like (2026-11-09). The defaults are server/engine
.DOWNLOADS, render/sharp's enlarging to 1080p, the encoders' quality aim (CQ 21, CRF 19),
dub/mix.py's full background and dub/clone.STEPS."""
from tarjim.prefs.folders import default_folder
from tarjim.prefs.make import ADVANCED, amount, basic, on_off, pick, saved_only
from tarjim.prefs.spec import Spec

OUTPUT: tuple[Spec, ...] = (
    # Kept in each order once it is made, so a queued job writes where the person saw it would.
    saved_only(Spec("output.folder", "وين تنحفظ الملفات", "folder", default_folder())),
    pick("output.enlarge", "يكبر الفيديو الصغير قبل ما يكتب عليه", ("1080", "720", "off"),
         ADVANCED),
    # normal: today's aim; high: a lower CQ/CRF (18), a bigger and clearer file.
    pick("output.quality", "جودة الفيديو الناتج", ("normal", "high"), ADVANCED),
    on_off("output.keep_ass", "يحفظ ملف الترجمة المنسق ASS", True, ADVANCED),
    on_off("output.burn_with_dub", "الدبلجة تطلع ومعها ترجمة مكتوبة على الفيديو", True),
)

DUB: tuple[Spec, ...] = (
    # One balance: the dub's peak is brought to 0.97 (dub/mix.HEADROOM), so a louder voice and
    # a quieter background are the same thing.
    basic(amount("dub.balance", "صوت الموسيقى والخلفية تحت الدبلجة", 100, (0, 100, 5))),
    pick("dub.gemini_tone", "نبرة أصوات جيميني", ("natural", "calm", "lively", "news"),
         ADVANCED),
    amount("dub.clone_steps", "دقة الصوت المنسوخ (أعلى أبطأ)", 10, (8, 20, 1)),
)
