"""Fresh Sayings through his mouth: the gold technique, with the new vowel and
the lip movement made by the tube model instead of by warping.

    python scripts/mouth_sayings.py   -> out/mouth/*.wav
"""
import json, sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from new_sayings import SAYINGS, FRESH  # noqa: E402
from prince_voice.bnuypitch import pitch_plan  # noqa: E402
from prince_voice.bnuysynth import SR, Catalogue, Unit as U, derive_vowel, synth  # noqa: E402
from prince_voice.mouthderive import derive_by_mouth  # noqa: E402

SAYINGS = dict(SAYINGS)
SAYINGS["minny"] = ([U("m", 90), U("iː", 140), U("n", 60), U("iː", 300, fade_ms=100)], [264, 264, 263, 262], 0.6)

VERSIONS = {   # name: (how ɑ is made, synth settings)
    "1_warp_lipwarp": ("warp", FRESH),                          # the pinned "mama F" method
    "2_mouth_lipwarp": ("mouth", FRESH),                        # mouth ɑ, old lip edge
    "3_mouth_mouthlips": ("mouth", dict(FRESH, mouth_edges=True)),   # mouth ɑ + mouth lips
}


def main():
    fit = json.loads((ROOT / "models/mouth_fit.json").read_text())
    out = ROOT / "out" / "mouth"; out.mkdir(parents=True, exist_ok=True)
    pause = np.zeros(int(0.35 * SR), np.float32)
    for vname, (how, kw) in VERSIONS.items():
        cat = Catalogue()
        if how == "warp":
            derive_vowel(cat, "ɑ", "ã", [(1200, 1200), (2160, 1700), (3700, 3600)])
        else:
            derive_by_mouth(cat, "ɑ", "ã", np.array(fit["derived"]["ɑ"]["params"]))
        for say in ("mama", "minny"):
            units, levels, onset = SAYINGS[say]
            y = synth(units, pitch_plan(units, levels, onset=onset, step_ms=60.0), cat, **kw)
            sf.write(out / f"{say}_{vname}.wav", y / np.abs(y).max() * 0.8, SR)
            print(out / f"{say}_{vname}.wav")


if __name__ == "__main__":
    main()
