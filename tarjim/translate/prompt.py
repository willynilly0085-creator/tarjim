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
- الخانة اللي فيها جزءان مفصولان بـ || يُحتمل أنها حوار بين شخصين: اسمع الصوت، \
فإن كانا شخصين مختلفين أرجع ترجمة كل واحد مفصولة بـ || وبنفس الترتيب بدون شرطة، \
وإن كانا نفس الشخص أرجعهما جملة واحدة بدون ||.
- الأرقام بالأرقام اللاتينية 0-9. بدون علامتي ؟ و ! مع بعض.
- لو الخانة مجرد صوت بلا معنى، أرجع نصاً فارغاً.

أرجع JSON فقط: قائمة عناصر {{"id": رقم, "ar": "الترجمة"}} لكل الخانات ({count}) بنفس الأرقام.

الخانات:
{items}"""


def build_prompt(cues: list[Cue], dialect: str, rules: Rules = DEFAULT_RULES) -> str:
    items = "\n".join(format_item(i, cue, rules) for i, cue in enumerate(cues, start=1))
    return TEMPLATE.format(dialect=DIALECTS[dialect], count=len(cues), items=items)


def format_item(number: int, cue: Cue, rules: Rules) -> str:
    budget = rules.char_budget(cue.duration)
    return f"{number}. [{cue.start:.1f}-{cue.end:.1f}ث | budget={budget}] {cue.source}"
