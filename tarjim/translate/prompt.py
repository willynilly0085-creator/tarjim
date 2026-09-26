from tarjim.models import Cue
from tarjim.rules import DEFAULT_RULES, Rules

DIALECTS = {
    "saudi": "اللهجة السعودية البيضاء العفوية كما يتكلمها الناس يومياً "
             "(مو فصحى رسمية، ومو مصري ولا شامي)",
    "msa": "العربية الفصحى المبسطة الواضحة كما في ترجمات الأفلام",
}

TEMPLATE = """أنت مترجم أفلام ومسلسلات محترف. معك الصوت الأصلي للمقطع، وقائمة خانات ترجمة \
مقسّمة مسبقاً بتوقيت ثابت. كل خانة تخص متكلماً واحداً.

المطلوب لكل خانة ترجمة عربية:
- بـ{dialect}، وبنفس نبرة المتكلم (مزح، تعجب، سخرية، استغراب).
- اسمع الصوت بنفسك وصحّح أي كلمة سمعها التفريغ الآلي غلط.
- لا تتجاوز عدد الحروف المسموح للخانة (budget) — اختصر واحذف الحشو مثل \
um و like و you know، مثل الترجمة الاحترافية.
- ترجم الخانة لوحدها: لا تنقل كلاماً من خانة لخانة، ولا تدمج خانتين.
- {dialogue_rule}
- أي عدد من 3 وفوق يُكتب بالأرقام اللاتينية 0-9 حتى لو نُطق كلمة \
(three months ← 3 شهور، 18 times ← 18 مرة)؛ أما مرة ومرتين فتبقى كلمات. \
بدون علامتي ؟ و ! مع بعض.
- لو الخانة مجرد صوت بلا معنى، أرجع نصاً فارغاً.

أرجع JSON فقط: قائمة عناصر {{"id": رقم, "ar": "الترجمة"}} لكل الخانات ({count}) بنفس الأرقام.

الخانات:
{items}"""


KNOWN_SPEAKERS = ("الخانة اللي فيها جزءان مفصولان بـ || هي حوار بين شخصين مختلفين مؤكد: "
                  "أرجع ترجمة الاثنين مفصولة بـ || وبنفس الترتيب بدون شرطة، ولا تحذف أي جزء.")
GUESSED_SPEAKERS = ("الخانة اللي فيها جزءان مفصولان بـ || يُحتمل أنها حوار: اسمع الصوت، فإن "
                    "كانا شخصين مختلفين أرجع ترجمة الاثنين مفصولة بـ || بنفس الترتيب، وإن كانا "
                    "نفس الشخص أرجعهما جملة واحدة بدون || — بدون حذف أي كلام.")


def has_speakers(cues: list[Cue]) -> bool:
    return any(word.speaker for cue in cues for word in cue.words)


def build_prompt(cues: list[Cue], dialect: str, rules: Rules = DEFAULT_RULES) -> str:
    items = "\n".join(format_item(i, cue, rules) for i, cue in enumerate(cues, start=1))
    rule = KNOWN_SPEAKERS if has_speakers(cues) else GUESSED_SPEAKERS
    return TEMPLATE.format(dialect=DIALECTS[dialect], count=len(cues), items=items,
                           dialogue_rule=rule)


def format_item(number: int, cue: Cue, rules: Rules) -> str:
    budget = rules.char_budget(cue.duration)
    return f"{number}. [{cue.start:.1f}-{cue.end:.1f}ث | budget={budget}] {cue.source}"
