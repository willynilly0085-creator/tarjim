"""The bench's tiers: which cells (clip, fault, setting) a bench run makes.

    smoke  en_interview_quick, en_long_three_pieces, ar_dialogue, en_chant_bed
           x perfect, jitter, drift, stretched, omitted_all, omitted_tail, duplicated, early, slip
           x local off x oracle good, none                                        (72 cells)
    gate   every scenario x every fault, once, at seed 0; the four settings local off/on x
           oracle good/none turn with the cell (clip index + fault index), so every fault and
           every clip meets all four                         (18 x 19 = 342 cells today)
    gate4  the same with all four settings on every pair                       (1368 cells)
    full   every scenario x every fault x local on/off/wrong x oracle good/none/invent/quota
           x seeds 0, 1, 2 (defined, not meant to be run often)
    cpu    en_interview_quick, en_long_seven x perfect, with --cpu (its own process)
"""
from itertools import product

SMOKE_CLIPS = ("en_interview_quick", "en_long_three_pieces", "ar_dialogue", "en_chant_bed")
SMOKE_FAULTS = ("perfect", "jitter", "drift", "stretched", "omitted_all", "omitted_tail",
                "duplicated", "early", "slip")
GATE_SETTINGS = (("off", "good"), ("on", "good"), ("off", "none"), ("on", "none"))
FULL_LOCAL = ("on", "off", "wrong")
FULL_ORACLE = ("good", "none", "invent", "quota")
SEEDS = (0, 1, 2)
CPU_CLIPS = ("en_interview_quick", "en_long_seven")

Cell = tuple[str, str, str, str, int]  # clip, fault, local, oracle, seed
TIERS = ("smoke", "gate", "gate4", "full", "cpu")


def cells(tier: str, clips: list[str], faults: list[str]) -> list[Cell]:
    """The tier's cells over the clips and faults there are (each kept in its own order)."""
    if tier == "smoke":
        return [(c, f, "off", o, 0) for c in SMOKE_CLIPS if c in clips for f in SMOKE_FAULTS
                for o in ("good", "none")]
    if tier == "gate":
        return [(c, f, *GATE_SETTINGS[(i + j) % len(GATE_SETTINGS)], 0)
                for i, c in enumerate(clips) for j, f in enumerate(faults)]
    if tier == "gate4":
        return [(c, f, local, oracle, 0) for c, f in product(clips, faults)
                for local, oracle in GATE_SETTINGS]
    if tier == "full":
        return [(c, f, local, oracle, seed) for seed in SEEDS for c, f in product(clips, faults)
                for local, oracle in product(FULL_LOCAL, FULL_ORACLE)]
    if tier == "cpu":
        return [(c, "perfect", "off", "good", 0) for c in CPU_CLIPS if c in clips]
    raise ValueError(f"tier {tier!r}; known: {', '.join(TIERS)}")
