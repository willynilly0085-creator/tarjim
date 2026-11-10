"""One bench run: a synthetic clip, a hearing with faults put in (faults.py), and tarjim's own
hearing and cue building on it (hearing.transcript_for, then segment.build_cues, as
pipeline.run does), with no translation and no burning. The real cloud is never called: it is
faked at its boundary (cloud.py), so tarjim's own re-listening (check.relistener, chunks.shift,
asked.Asked) runs and the Oracle answers from the truth by mode; Gemini itself raises.

Each run gets a fresh folder runs/<label>/<clip>-<fault>-local_<mode>-oracle_<mode>[-switches]
holding the clip, the injected hearing (heard.injected.json), the regions the faults altered
(faults.json), what tarjim kept, its log, the words, the cues and the score. With --rerun the
cell is run a second time in the same folder, from what the first run kept, and scored again
(row["rerun"]).

    python run.py <clip folder> <fault> [--label L] [--local on|off|wrong]
                  [--oracle good|none|invent|quota] [--seed N] [--voiceprint on|off]
                  [--letters none|weak|sparse|wrong] [--cpu] [--rerun]
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from unittest import mock

SYNTH = Path(os.environ.get("TARJIM_SYNTH", r"C:\Users\PC\Desktop\tarjim-files\tarjim-synth"))
TOOLS = Path(r"C:\Users\PC\.tarjim\tools\ffmpeg\368ccdd16812dd8b"
             r"\ffmpeg-n8.1-latest-win64-lgpl-shared-8.1\bin")
REPO = Path(__file__).resolve().parents[2]
ENVIRONMENT = {"TARJIM_FFMPEG": str(TOOLS / "ffmpeg.exe"),
               "TARJIM_FFPROBE": str(TOOLS / "ffprobe.exe"), "HF_HOME": str(REPO / ".models"),
               "TARJIM_HOME": str(SYNTH / "home")}
for _key, _value in ENVIRONMENT.items():
    os.environ.setdefault(_key, _value)
os.environ["TARJIM_HOME"] = ENVIRONMENT["TARJIM_HOME"]  # never the owner's settings
sys.path[:0] = [str(Path(__file__).resolve().parent), str(REPO)]
if "--cpu" in sys.argv:  # before torch is imported by anything
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

import cloud  # noqa: E402
import faults  # noqa: E402
import measures  # noqa: E402
import score  # noqa: E402
import switches  # noqa: E402

from tarjim.listen.kept import keep_heard  # noqa: E402
from tarjim.listen.merge import Heard  # noqa: E402
from tarjim.models import Cue, Word  # noqa: E402

Truth = dict[str, Any]
Row = dict[str, Any]
DECODE = switches.DecodeCache(SYNTH / "work" / "emissions")
RERUN_SKIP = ("ok", "trace", "error")


@dataclass(frozen=True)
class Setting:
    """How a run is made: its bench label, the local listener, the oracle, the seed and the
    switches."""
    label: str = "dev"
    local: str = "on"  # "on" | "off" | "wrong"
    oracle: str = "good"  # "good" | "none" | "invent" | "quota"
    seed: int = 0
    voiceprint: bool = True
    letters: str = "none"  # "none" | "weak" | "sparse" | "wrong"
    cpu: bool = False
    rerun: bool = False

    def folder(self, clip: str, fault: str) -> Path:
        name = f"{clip}-{fault.replace('+', '_')}-local_{self.local}-oracle_{self.oracle}"
        name += "" if self.voiceprint else "-vp_off"
        name += "" if self.letters == "none" else f"-letters_{self.letters}"
        name += "-cpu" if self.cpu else ""
        name += f"-s{self.seed}" if self.seed else ""
        return SYNTH / "runs" / self.label / name

    def keys(self) -> Row:
        return {"local": self.local, "oracle": self.oracle, "seed": self.seed,
                "voiceprint": "on" if self.voiceprint else "off", "letters": self.letters,
                "cpu": self.cpu}


@contextlib.contextmanager
def patched(oracle: cloud.Oracle, truth: Truth, setting: Setting) -> Any:
    language = str(truth.get("language") or "")
    fake = cloud.fake_cloud(oracle, language, float(truth["duration"]))
    patches: list[Any] = [mock.patch("tarjim.media.audio_bytes", cloud.span_token),
                          mock.patch("tarjim.hearing.cloud_listener", fake),
                          mock.patch("tarjim.hearing.listen_video", cloud.fresh_hearing),
                          mock.patch("tarjim.listen.gemini_listen.listen", switches.blocked),
                          mock.patch("tarjim.gemini_client.GeminiClient.ask", switches.blocked)]
    patches += switches.local_patches(setting.local, truth)
    patches += switches.voiceprint_patch(setting.voiceprint)
    patches += switches.letters_patch(setting.letters, setting.seed)
    with switches.applied(patches):
        yield


def prepared(clip_dir: Path, folder: Path, heard: Heard, regions: list[Row]) -> Path:
    """A fresh folder that is the job's cache too: the video is <folder name>.mp4 inside it,
    beside the injected hearing and the regions the faults altered."""
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    video = folder / f"{folder.name}.mp4"
    shutil.copyfile(clip_dir / "clip.mp4", video)
    keep_heard(folder, heard)
    shutil.copyfile(folder / "heard.json", folder / "heard.injected.json")
    faults.write_regions(folder, regions)
    return video


def heard_and_cut(video: Path) -> tuple[list[Word], list[Cue]]:
    from tarjim import media
    from tarjim.hearing import transcript_for
    from tarjim.job import Job
    from tarjim.pipeline import cuts_for
    from tarjim.render.room import fitted
    from tarjim.segment import build_cues

    job = Job(video, burn=False, out_dir=video.parent, cache_dir=video.parent.parent)
    words = transcript_for(job, lambda _stage: None).words
    info = media.probe(job.video)
    rules = fitted(job.rules, info.width, info.height)
    return words, build_cues(words, cuts_for(job), rules)


def cue_rows(cues: list[Cue]) -> list[Row]:
    return [{"start": c.start, "end": c.end, "text": c.source,
             "parts": [[asdict(w) for w in p] for p in (c.parts or [c.words])]} for c in cues]


def dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def once(video: Path, truth: Truth, setting: Setting, log: io.StringIO, tag: str) -> Row:
    """One pass of tarjim over the cell's folder, scored."""
    oracle = cloud.Oracle(truth, setting.oracle, setting.seed)
    with patched(oracle, truth, setting), measures.Probe() as probe, \
            contextlib.redirect_stdout(log):
        words, cues = heard_and_cut(video)
    rows, said = cue_rows(cues), [asdict(w) for w in words]
    dump(video.parent / f"words{tag}.json", said)
    dump(video.parent / f"cues{tag}.json", rows)
    return {**oracle.counts(), **score.score(truth, said, rows),
            **probe.results(video.parent, truth, said)}


def made(clip_dir: Path, fault: str, setting: Setting, log: io.StringIO) -> Row:
    """The run itself, its score as a row; with `rerun` the second run's too."""
    truth = json.loads((clip_dir / "truth.json").read_text(encoding="utf-8"))
    folder = setting.folder(clip_dir.name, fault)
    DECODE.clip = clip_dir.name
    video = prepared(clip_dir, folder, *faults.traced(truth, fault, setting.seed))
    row = {**once(video, truth, setting, log, ""), "ok": True}
    if setting.rerun:
        log.write("\n===== rerun in the same folder =====\n")
        again = once(video, truth, setting, log, ".rerun")
        row["rerun"] = {k: v for k, v in again.items() if k not in RERUN_SKIP}
    return row


def run_one(clip_dir: Path, fault: str, setting: Setting | None = None) -> Row:
    """One run's row; a failure is a row with its error, never a crash."""
    chosen = setting or Setting()
    folder = chosen.folder(clip_dir.name, fault)
    row: Row = {"label": chosen.label, "clip": clip_dir.name, "fault": fault, **chosen.keys(),
                "ok": False, "folder": str(folder)}
    began, log = time.monotonic(), io.StringIO()
    try:
        row.update(made(clip_dir, fault, chosen, log))
    except Exception as error:  # one failing run is a recorded error
        row["error"] = f"{type(error).__name__}: {error}"
        row["trace"] = traceback.format_exc()[-2000:]
    row["seconds"] = round(time.monotonic() - began, 1)
    with contextlib.suppress(OSError):
        (folder / "tarjim.log").write_text(log.getvalue(), encoding="utf-8")
        dump(folder / "score.json", row)
    return row


def start(cpu: bool) -> None:
    """Once a process, before the first cell: the processor switch and the decode cache."""
    if cpu:
        switches.cpu_first()
    DECODE.install()


def parsed() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split(chr(10))[0])
    parser.add_argument("clip", type=Path)
    parser.add_argument("fault")
    parser.add_argument("--label", default="dev")
    parser.add_argument("--local", choices=("on", "off", "wrong"), default="on")
    parser.add_argument("--oracle", choices=("good", "none", "invent", "quota"), default="good")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--voiceprint", choices=("on", "off"), default="on")
    parser.add_argument("--letters", choices=("none", "weak", "sparse", "wrong"), default="none")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--rerun", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parsed()
    start(args.cpu)
    setting = Setting(args.label, args.local, args.oracle, args.seed, args.voiceprint == "on",
                      args.letters, args.cpu, args.rerun)
    row = run_one(args.clip, args.fault, setting)
    print(json.dumps({k: v for k, v in row.items() if k != "trace"}, indent=1,
                     ensure_ascii=False))
    if not row["ok"]:
        print(row.get("trace", ""), file=sys.stderr)
    score.table([row])


if __name__ == "__main__":
    main()
