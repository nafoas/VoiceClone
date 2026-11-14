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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from prince_voice.bnuysynth import SR, Catalogue, Unit, synth  # noqa: E402

U = Unit

# settings for new phrases (how he'd speak: one breath, one steady hum, joins
# that melt like his real ones, little manipulation of his recordings)
NEW_PHRASE = dict(pitch_life=0.75, pitch_loud=0.6, w_pitch=4.0, edge_ms=10, hum_boost_db=4,
                  hum_steady=0.4, breath_support=0.7, attack_ms=40, release_ms=50)
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

    # 1. the transcription, rebuilt. Fair: each sound must come from a different
    #    instance in the clip when one exists (no copying the same moment).
    from iterate import P1, P2, T1, T2
    y = np.concatenate([synth(P1, ref_f0(T1), cat), pause, synth(P2, ref_f0(T2), cat)])
    sf.write(out / "rebuilt_reference.wav", y / np.abs(y).max() * 0.8, SR)

    # 2. new things he never said in the clip. Every version differs for a
    #    stated reason (his intent), never at random.
    from prince_voice.bnuyspeak import speak
    novel = Catalogue(level_match=0.5)
    S, W = True, False
    munis = [[("m ũ", S), ("n iː ɕ", W)]]
    nannar = [[("n ã", S), ("n ɐ˞ ɹ", W)]]
    mama_nanni = [[("m ã", S), ("m ã", W)], [("n ã", S), ("n iː", W)]]
    nanni = [[("n ã", S), ("n iː", W)]]
    tee_pee = [[("tʰ iː", S)], [("p iː", S)]]
    meeni = [[("m iː", S), ("n iː", W)]]
    versions = [
        ("01_munis_nannar_calm", "calm: just saying it",
         [dict(phrase=munis, mood="calm"), dict(phrase=nannar, mood="calm")]),
        ("02_munis_nannar_unsure", "unsure: still thinking, trails off",
         [dict(phrase=munis, mood="unsure"), dict(phrase=nannar, mood="unsure")]),
        ("03_mama_nanni_calm", "calm statement",
         [dict(phrase=mama_nanni, mood="calm")]),
        ("04_mama_NANNI_focus", "answering 'which one?': emphasis on nanni",
         [dict(phrase=mama_nanni, mood="calm", focus=1)]),
        ("05_MAMA_nanni_focus", "correcting: emphasis on mama",
         [dict(phrase=mama_nanni, mood="calm", focus=0)]),
        ("06_mama_nanni_sleepy", "sleepy and content",
         [dict(phrase=mama_nanni, mood="sleepy")]),
        ("07_nanni_curious", "asking: nanni?",
         [dict(phrase=nanni, mood="curious")]),
        ("08_tee_pee_meeni", "excited, then calming down",
         [dict(phrase=tee_pee, mood="excited"), dict(phrase=meeni, mood="calm")]),
    ]
    with open(out / "new_versions.txt", "w") as fh:
        for name, why, phrases in versions:
            sf.write(out / f"new_{name}.wav", speak(phrases, cat=novel), SR)
            fh.write(f"{name}: {why}\n")
    print("written to", out)


if __name__ == "__main__":
    main()
