"""How the person wants a translation written, as lines of the prompt (2026-11-09).

Each first choice of translate.* is what the prompt said before the setting existed, word for
word, so a person who changed nothing is asked for the same translation; all but the length,
whose first choice since 2026-11-14 is the complete translation (below). The other choices
replace a line (numbers, fillers, question marks) or add one (register, profanity, names); they
are fixed text, never the person's own words, so no setting can tell the model to answer in
another language or break its JSON. The glossary comes after them and still wins for a name.
"""
from tarjim.prefs.model import Translate

Said = dict[str, str]  # by the prompt's language: "ar" for Arabic, "any" for the rest

NUMBERS: dict[str, Said] = {
    "latin": {"ar": "- أي عدد من 3 وفوق يُكتب بالأرقام اللاتينية 0-9 حتى لو نُطق كلمة "
                    "(three months ← 3 شهور، 18 times ← 18 مرة)؛ أما مرة ومرتين فتبقى كلمات.",
              "any": "- Write numbers of 3 and above as digits."},
    "eastern": {"ar": "- أي عدد من 3 وفوق يُكتب بالأرقام العربية ٠-٩ حتى لو نُطق كلمة "
                      "(three months ← ٣ شهور، 18 times ← ١٨ مرة)؛ أما مرة ومرتين فتبقى كلمات.",
                "any": "- Write numbers of 3 and above as digits."},
    "words": {"ar": "- الأعداد تحت العشرة تُكتب بالحروف (three months ← ثلاث شهور)، و10 وفوق "
                    "بالأرقام اللاتينية 0-9 (18 times ← 18 مرة).",
              "any": "- Spell out numbers under ten in words; write 10 and above as digits."},
}
QUESTION_MARKS: dict[str, Said] = {
    "collapse": {"ar": " بدون علامتي ؟ و ! مع بعض.", "any": ""},
    "keep": {"ar": "", "any": ""},
}
FILLERS: dict[str, Said] = {
    "drop": {"ar": "اختصر واحذف الحشو مثل um و like و you know، مثل الترجمة الاحترافية.",
             "any": "condense and drop fillers such as um, like and you know, the way "
                    "professional subtitlers do."},
    "keep": {"ar": "اختصر، وخلّ كلمات الحشو مثل um و like و you know لو الـ budget يكفيها.",
             "any": "condense, but keep fillers such as um, like and you know when the "
                    "budget has room for them."},
}
# How much of what is said the translation holds (translate.length, 2026-11-12). "fit" is the
# prompt's own words from before the setting, taken as they were; "full" asks for everything
# said, for a person to whom nothing left out matters more than a line read at ease.
LENGTH_FIT: dict[str, str] = {
    "ar": """- لا تتجاوز عدد الحروف المسموح للخانة (budget) — {fillers} الـ budget المكتوب a+b \
حدّ لكل جزء من الحوار لوحده، ولو رجّعت الخانة جملة واحدة فلك مجموعهما.
- ترجم الخانة لوحدها: لا تنقل كلاماً من خانة لخانة، ولا تدمج خانتين. لو الـ budget ما يكفي \
جملة الخانة، اختصر ترجمتها هي، ولا ترحّل باقيها للخانة اللي بعدها.""",
    "any": """- Never exceed the slot's character budget: {fillers} A budget written a+b is a \
limit for each part of an exchange on its own; one sentence for the whole slot may use their sum.
- Translate each slot on its own: never move words between slots and never merge slots. \
If a slot's budget is too small for its sentence, shorten that slot's own translation; \
never carry the rest into the next slot.""",
}
LENGTH_FULL: dict[str, str] = {
    "ar": """- ترجم كل ما قيل في الخانة كاملاً: لا تختصر ولا تحذف أي جزء من المعنى. {fillers} \
رقم budget هو الطول المريح للقراءة فقط، ولو الترجمة الكاملة أطول منه فاتركها كاملة.
- ترجم الخانة لوحدها: لا تنقل كلاماً من خانة لخانة، ولا تدمج خانتين، ولا ترحّل أي جزء من \
ترجمتها للخانة اللي بعدها.""",
    "any": """- Translate everything said in the slot, in full: never condense or leave out \
any part of the meaning. {fillers} The budget is only the length that reads at ease; when \
the full translation is longer, keep it full.
- Translate each slot on its own: never move words between slots, never merge slots, and \
never carry any part of a slot into the next one.""",
}
# A slip of the tongue is no part of the meaning (2026-11-14): told only that fillers go, a
# model asked for everything said wrote "And then he, the issue was" as "ثم هو، كانت القضية".
FULL_FILLERS: dict[str, Said] = {
    "drop": {"ar": "كلمات الحشو وحدها (um و like و you know) تنحذف، ومثلها زلة اللسان: الكلمة أو "
                   "العبارة اللي يبدأها المتكلم ويقطعها ثم يعيدها (he, the issue was أو "
                   "we've, we saw أو the the) تنكتب مرة واحدة مثل ما قصدها.",
             "any": "Fillers alone (um, like, you know) are dropped, and so is a slip of the "
                    "tongue: a word or phrase the speaker starts, breaks off and says again "
                    "(\"he, the issue was\", \"we've, we saw\", \"the the\") is written "
                    "once, the way they meant it."},
    "keep": {"ar": "وخلّ كلمات الحشو مثل um و like و you know.",
             "any": "Keep fillers such as um, like and you know too."},
}
REGISTER: dict[str, Said] = {
    "casual": {"ar": "- خلّ الأسلوب عفوي وخفيف مثل كلام الأصحاب.",
               "any": "- Keep the style casual and relaxed, the way friends talk."},
    "formal": {"ar": "- خلّ الأسلوب رسمي ومؤدب، بدون كلام شارع.",
               "any": "- Keep the style formal and polite, with no slang."},
}
PROFANITY: dict[str, Said] = {
    "soften": {"ar": "- خفّف الكلام البذيء والشتايم لكلام مقبول بنفس المعنى.",
               "any": "- Soften profanity and swearing into acceptable words of the same "
                      "meaning."},
    "mask": {"ar": "- اكتب الكلمة البذيئة بأول حرف منها ونجوم (ك***)، والنجوم تنحسب من الـ "
                   "budget.",
             "any": "- Write a profane word as its first letter and asterisks (f***); the "
                    "asterisks count toward the budget."},
}
NAMES: dict[str, Said] = {
    "latin": {"ar": "- أسماء الأشخاص والماركات تبقى بالحروف اللاتينية مثل ما تنكتب بلغتها.",
              "any": "- Keep the names of people and brands in Latin letters, as they are "
                     "written in their own language."},
    "target": {"ar": "- اكتب أسماء الأشخاص والماركات بالحروف العربية مثل ما تنلفظ.",
               "any": "- Write the names of people and brands in the target language's own "
                      "script, as they are said."},
}


def numbers_rule(manner: Translate, key: str) -> str:
    return NUMBERS[manner.numbers][key] + QUESTION_MARKS[manner.question_marks][key]


def fillers_rule(manner: Translate, key: str) -> str:
    return FILLERS[manner.fillers][key]


def length_rule(manner: Translate, key: str) -> str:
    """The two lines about how long a translation may be, for the person's choice."""
    if manner.length == "full":
        return LENGTH_FULL[key].format(fillers=FULL_FILLERS[manner.fillers][key])
    return LENGTH_FIT[key].format(fillers=fillers_rule(manner, key))


def added(manner: Translate, key: str) -> str:
    """The lines a choice other than the first adds, each ending its own line."""
    chosen = (REGISTER.get(manner.register), PROFANITY.get(manner.profanity),
              NAMES.get(manner.names))
    return "".join(f"{said[key]}\n" for said in chosen if said)
