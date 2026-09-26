from dataclasses import dataclass

from tarjim.languages import Language, language
from tarjim.models import Cue
from tarjim.rules import DEFAULT_RULES, Rules

DIALECTS = {
    "saudi": "اللهجة السعودية البيضاء العفوية كما يتكلمها الناس يومياً "
             "(مو فصحى رسمية، ومو مصري ولا شامي)",
    "msa": "العربية الفصحى المبسطة الواضحة كما في ترجمات الأفلام",
}

ARABIC = """أنت مترجم أفلام ومسلسلات محترف. معك الصوت الأصلي للمقطع، وقائمة خانات ترجمة \
مقسّمة مسبقاً بتوقيت ثابت. كل خانة تخص متكلماً واحداً.

المطلوب لكل خانة ترجمة عربية:
- بـ{style}، وبنفس نبرة المتكلم (مزح، تعجب، سخرية، استغراب).
- اسمع الصوت بنفسك وصحّح أي كلمة سمعها التفريغ الآلي غلط.
- لا تتجاوز عدد الحروف المسموح للخانة (budget) — اختصر واحذف الحشو مثل \
um و like و you know، مثل الترجمة الاحترافية.
- ترجم الخانة لوحدها: لا تنقل كلاماً من خانة لخانة، ولا تدمج خانتين.
- {dialogue_rule}
- أي عدد من 3 وفوق يُكتب بالأرقام اللاتينية 0-9 حتى لو نُطق كلمة \
(three months ← 3 شهور، 18 times ← 18 مرة)؛ أما مرة ومرتين فتبقى كلمات. \
بدون علامتي ؟ و ! مع بعض.
- لو الخانة مجرد صوت بلا معنى، أرجع نصاً فارغاً.

أرجع JSON فقط: قائمة عناصر {{"id": رقم, "text": "الترجمة"}} لكل الخانات ({count}) بنفس الأرقام.

الخانات:
{items}"""

ANY = """You are a professional film and TV subtitle translator. You have the original audio of \
the clip and a list of subtitle slots that are already segmented with fixed timing. Each slot \
belongs to one speaker.

For every slot write a {style} subtitle:
- Natural, idiomatic, spoken {style} as in professional subtitles, keeping the speaker's tone \
(joking, surprise, sarcasm, doubt).
- Listen to the audio yourself and fix any word the automatic transcript misheard.
- Never exceed the slot's character budget: condense and drop fillers such as um, like and \
you know, the way professional subtitlers do.
- Translate each slot on its own: never move words between slots and never merge slots.
- {dialogue_rule}
- Write numbers of 3 and above as digits.
- If a slot is only a meaningless sound, return an empty text.

Return JSON only: a list of {{"id": number, "text": "translation"}} for all {count} slots, \
keeping the same ids.

Slots:
{items}"""

KNOWN_SPEAKERS = {
    "ar": "الخانة اللي فيها جزءان مفصولان بـ || هي حوار بين شخصين مختلفين مؤكد: "
          "أرجع ترجمة الاثنين مفصولة بـ || وبنفس الترتيب بدون شرطة، ولا تحذف أي جزء.",
    "any": "A slot with two parts separated by || is a confirmed exchange between two "
           "different people: return both translations separated by || in the same order, "
           "without dashes, and never drop a part.",
}
GUESSED_SPEAKERS = {
    "ar": "الخانة اللي فيها جزءان مفصولان بـ || يُحتمل أنها حوار: اسمع الصوت، فإن "
          "كانا شخصين مختلفين أرجع ترجمة الاثنين مفصولة بـ || بنفس الترتيب، وإن كانا "
          "نفس الشخص أرجعهما جملة واحدة بدون || — بدون حذف أي كلام.",
    "any": "A slot with two parts separated by || may be an exchange: listen to the audio. If "
           "they are two different people, return both translations separated by || in the "
           "same order; if it is the same person, return one sentence without ||. Drop nothing.",
}


ARABIC_TARGET = language("ar")


@dataclass(frozen=True)
class Brief:
    target: Language = ARABIC_TARGET
    dialect: str = "saudi"
    rules: Rules = DEFAULT_RULES
    offset: float = 0.0

    @property
    def arabic(self) -> bool:
        return self.target.code == "ar"


def has_speakers(cues: list[Cue]) -> bool:
    return any(word.speaker for cue in cues for word in cue.words)


def build_prompt(cues: list[Cue], brief: Brief) -> str:
    key = "ar" if brief.arabic else "any"
    rule = (KNOWN_SPEAKERS if has_speakers(cues) else GUESSED_SPEAKERS)[key]
    items = "\n".join(format_item(i, cue, brief) for i, cue in enumerate(cues, start=1))
    template = ARABIC if brief.arabic else ANY
    style = DIALECTS[brief.dialect] if brief.arabic else brief.target.name
    return template.format(style=style, count=len(cues), items=items, dialogue_rule=rule)


def format_item(number: int, cue: Cue, brief: Brief) -> str:
    budget = brief.rules.char_budget(cue.duration)
    start, end = cue.start - brief.offset, cue.end - brief.offset
    unit = "ث" if brief.arabic else "s"
    return f"{number}. [{start:.1f}-{end:.1f}{unit} | budget={budget}] {cue.source}"
