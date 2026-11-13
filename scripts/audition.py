"""Render the same lines through several base voices for side-by-side listening.

    python scripts/audition.py                      # default shortlist
    python scripts/audition.py af_heart "af_heart:0.6,af_nicole:0.4"
    python scripts/audition.py --raw                # base voices untransformed

Writes one wav per voice to out/audition/, each containing all lines in order.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prince_voice import Params  # noqa: E402
from prince_voice.engine import SR, PrinceVoice  # noqa: E402

SHORTLIST = ["af_heart", "af_bella", "af_nicole", "af_sky", "af_river",
             "bf_emma", "am_puck", "am_michael"]

LINES = [
    "Da Boss!! youse is back!!",
    "oh!! what dis?",
    "OH!! IS TURNINGS BACK!!",
    "is round. mhm. is likes beings round.",
    "hmmmmm... I's has pieces... but dey isn't stickings togethers yet.",
    "is very warm... is very... very happies...",
    "I'S DIDS IT!!! Bnuy!!",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("voices", nargs="*", default=SHORTLIST)
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--preset")
    ap.add_argument("-o", "--out", default="out/audition")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = Params.load(a.preset) if a.preset else Params()
    pv = PrinceVoice(base)
    gap = np.zeros(int(0.8 * SR), np.float32)
    for v in a.voices:
        p = Params.from_dict({**base.to_dict(), "voice": v})
        clips = []
        for line in LINES:
            clips += [pv.render(line, p, raw=a.raw), gap]
        name = re.sub(r"[^a-z0-9.]+", "_", v.lower()).strip("_")
        path = out / f"{name}{'_raw' if a.raw else ''}.wav"
        sf.write(path, np.concatenate(clips), SR)
        print(path)


if __name__ == "__main__":
    main()
