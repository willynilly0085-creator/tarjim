"""How the translation is written (2026-11-09). Each first choice is what the prompt asked
before the setting existed (translate/prompt.py). The dialect stays in the order itself
(server/jobs.Order.dialect), and engines, models and the glossary stay in setup."""
from tarjim.prefs.make import ADVANCED, on_off, pick
from tarjim.prefs.spec import Spec

TRANSLATE: tuple[Spec, ...] = (
    pick("translate.register", "أسلوب الكلام", ("natural", "casual", "formal")),
    # eastern: ٠-٩, for Arabic only (Persian and Urdu write other digits); words: the numbers
    # under ten spelled out, in place of the prompt's own rule for numbers.
    pick("translate.numbers", "شكل الأرقام", ("latin", "eastern", "words")),
    pick("translate.profanity", "الكلام البذيء", ("as_is", "soften", "mask")),
    pick("translate.names", "أسماء الأشخاص والماركات", ("model", "latin", "target")),
    pick("translate.fillers", "كلمات الحشو (يعني، اممم)", ("drop", "keep"), ADVANCED),
    pick("translate.question_marks", "علامتي ؟! مع بعض", ("collapse", "keep"), ADVANCED),
    on_off("translate.local_backup", "لو تعطلت الترجمة يكمل بالترجمة اللي على جهازك", True,
           ADVANCED),
    # A line too long for its time is first left up longer (translate/readable.py, 2026-11-12);
    # this is the second try, one request more, kept only when the answer fits.
    on_off("translate.shorten", "اختصر السطر لو كان أطول من وقته", True, ADVANCED),
)
