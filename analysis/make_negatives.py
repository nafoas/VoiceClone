"""Standard 'what he is not' examples, each isolating one failure type.

    python analysis/make_negatives.py   -> out/negatives/*.wav

child_like   ordinary adult voice, resonances x1.18, pitch ~280 Hz, normal source
chipmunk     ordinary voice, pitch AND resonances shifted up together (+7 st)
breathy      his gold rebuild with lots of breath noise mixed into the tone
robotic      his sounds with frozen spectra and dead-flat pitch (no movement)
choppy       his sounds held frozen, then jumping at each join
"""
import sys
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
SR = 24000
OUT = ROOT / "out" / "negatives"; OUT.mkdir(parents=True, exist_ok=True)


def world(x):
    x = np.ascontiguousarray(x, dtype=np.float64)
    f0, t = pw.harvest(x, SR, frame_period=5, f0_floor=60, f0_ceil=900)
    return f0, pw.cheaptrick(x, f0, t, SR), pw.d4c(x, f0, t, SR)


def warp(sp, a):
    k = sp.shape[1]; src = np.clip(np.arange(k) / a, 0, k - 1)
    i0 = np.floor(src).astype(int); i1 = np.minimum(i0 + 1, k - 1); fr = src - i0
    return sp[:, i0] * (1 - fr) + sp[:, i1] * fr


def save(name, y):
    y = np.asarray(y, dtype=np.float32); sf.write(OUT / f"{name}.wav", y / (np.abs(y).max() + 1e-9) * 0.8, SR)


eng, _ = sf.read(ROOT / "out/english_ref.wav")
gold, _ = sf.read(ROOT / "reference/gold/rebuild_gold_v9.wav")

# child-like: smaller tract, higher pitch, ordinary (human) source
f0, sp, ap = world(eng)
f0c = np.where(f0 > 0, f0 * (280.0 / np.median(f0[f0 > 0])), 0)
save("child_like", pw.synthesize(f0c, np.ascontiguousarray(warp(sp, 1.18)), ap, SR, 5.0))

# chipmunk: everything up together (resample trick)
k = 2 ** (7 / 12)
save("chipmunk", resample_poly(eng, 1000, int(1000 * k)))

# breathy: his rebuild with the tone half-replaced by breath
f0, sp, ap = world(gold)
fq = np.linspace(0, SR / 2, sp.shape[1])
save("breathy", pw.synthesize(f0, sp, np.ascontiguousarray(np.clip(ap + 0.55 * (1 - ap) * np.clip(fq / 1500, 0, 1)[None, :], 0, 1)), SR, 5.0))

# robotic & choppy: his catalogue without movement
from prince_voice.bnuysynth import Catalogue, synth  # noqa: E402
import iterate as I  # noqa: E402
cat = Catalogue()
flat = lambda t: 240.0
save("robotic", synth(I.P1, flat, cat, trajectories=False, life=0.0, sub_phonemes=False, hold=1.0, hold_cons=1.0))
save("choppy", synth(I.P1, I.ref_f0(I.T1), cat, trajectories=False, life=0.0, sub_phonemes=False, hold=0.9,
                     hold_cons=0.9))
print("written to", OUT)
