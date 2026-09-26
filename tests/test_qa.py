from tarjim.models import Cue
from tarjim.qa import check


def test_clean_cues_have_no_issues() -> None:
    cues = [Cue(0.0, 2.0, text="سألت الكل كم مرة يتروشون؟"), Cue(2.5, 4.0, text="مو كفاية.")]
    assert check(cues) == []


def test_overlap_and_speed_are_reported() -> None:
    fast = "هذا نص طويل جداً ما يمدي أحد يقرأه في نص ثانية أبداً"
    cues = [Cue(0.0, 0.5, text=fast), Cue(0.45, 2.0, text="تمام")]
    kinds = {issue.kind for issue in check(cues)}
    assert {"overlap", "reading_speed"} <= kinds
