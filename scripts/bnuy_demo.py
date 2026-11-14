"""Render with the Bnuy synthesizer (Prince's own sounds only).

1. The reference transcription rebuilt from the catalogue, with the clip's
   pitch: a fair test of "phoneme inventory + IPA = him?".
2. New recombinations the clip never says.

    python scripts/bnuy_demo.py   -> out/bnuy/*.wav
"""

import sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince_voice.bnuysynth import SR, Catalogue, Unit, synth  # noqa: E402

U = Unit
REF = ROOT / "reference/source/prince_reference.wav"


def ref_f0(offset):
    p = pm.Sound(str(REF)).convert_to_mono().to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
    return lambda t: p.get_value_at_time(offset + t)


def plateaus(units, levels, onset_fall_st=5.0, glide_ms=25.0):
    """Terraced pitch: one flat level per unit, short glides, quick onset fall."""
    edges = np.cumsum([0] + [u.ms / 1000 for u in units])

    def f(t):
        i = min(np.searchsorted(edges, t, side="right") - 1, len(levels) - 1)
        hz = levels[i]
        if i > 0 and t - edges[i] < glide_ms / 1000:
            x = (t - edges[i]) / (glide_ms / 1000)
            hz = levels[i - 1] * (1 - x) + hz * x
        return hz * 2 ** (onset_fall_st * np.exp(-t / 0.05) / 12)
    return f


def main():
    cat = Catalogue()
    out = ROOT / "out" / "bnuy"
    out.mkdir(parents=True, exist_ok=True)
    pause = np.zeros(int(0.34 * SR), np.float32)

    # 1. the transcription, rebuilt
    p1 = [U("n", 105), U("ã", 145), U("n", 75), U("ɐ˞", 95), U("ɹ", 50), U("m", 90),
          U("ũ", 120), U("n", 60), U("iː", 200), U("ɕ", 90)]
    p2 = [U("p", 55), U("iː", 180, fade_ms=100), U("tʰ", 45), U("iː", 230, fade_ms=100),
          U("tʰ", 40), U("iː", 310, fade_ms=100)]
    y = np.concatenate([synth(p1, ref_f0(0.05), cat), pause, synth(p2, ref_f0(1.455), cat)])
    sf.write(out / "rebuilt_reference.wav", y / np.abs(y).max() * 0.8, SR)

    # 2. new things he never said in the clip
    new = {
        "munis_nannar": ([U("m", 90), U("ũ", 120), U("n", 60), U("iː", 190), U("ɕ", 80)],
                         [270, 270, 270, 270, 265],
                         [U("n", 100), U("ã", 150), U("n", 75), U("ɐ˞", 110), U("ɹ", 60)],
                         [230, 216, 216, 214, 214]),
        "mama_nanni": ([U("m", 100), U("ã", 140), U("m", 80), U("ã", 200, fade_ms=80)],
                       [330, 330, 300, 300],
                       [U("n", 90), U("ã", 140), U("n", 70), U("iː", 240, fade_ms=100)],
                       [300, 300, 340, 340]),
        "tee_pee_meeni": ([U("tʰ", 45), U("iː", 160, fade_ms=80), U("p", 55), U("iː", 160, fade_ms=80)],
                          [380, 380, 360, 360],
                          [U("m", 80), U("iː", 140), U("n", 60), U("iː", 220, fade_ms=100)],
                          [300, 300, 300, 330]),
    }
    for name, (a, la, b, lb) in new.items():
        y = np.concatenate([synth(a, plateaus(a, la), cat), pause[: int(0.25 * SR)],
                            synth(b, plateaus(b, lb, onset_fall_st=2.0), cat)])
        sf.write(out / f"new_{name}.wav", y / np.abs(y).max() * 0.8, SR)
    print("written to", out)


if __name__ == "__main__":
    main()
