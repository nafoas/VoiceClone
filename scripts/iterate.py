"""Rebuild the reference clip with the Bnuy synthesizer and score it against
the original, for quick iteration.

    python scripts/iterate.py                 # default settings
    python scripts/iterate.py --sweep         # small parameter sweep
    python scripts/iterate.py --save          # also write out/bnuy/iter_*.wav

Scores (lower = closer to the clip unless noted):
  LSD        log-spectral distance 0-5 kHz over aligned frames (dB)
  LSDshape   same with each frame's loudness removed (pure timbre/vowel shape)
  flux/p95   smoothness: frame-to-frame spectral change, median & 95th pct
             (closer to the clip's values is better, not lower)
  loud/p95   frame-to-frame loudness change, median & 95th pct
  H2..H4     harmonic profile (the hum), dB relative to H1
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "analysis")); sys.path.insert(0, str(ROOT / "scripts"))
from prince_voice.bnuysynth import SR, Catalogue, Unit as U, synth  # noqa: E402
from bnuy_demo import ref_f0  # noqa: E402

T1, T2 = 0.05, 1.455


def _avoiding(units, t0):
    """Mark each unit with its own time span in the clip: when the catalogue
    has another instance of that sound, the rebuild must use the other one."""
    out, t = [], t0
    for u in units:
        out.append(U(u.ph, u.ms, u.fade_ms, u.gain_db, avoid=(t, t + u.ms / 1000)))
        t += u.ms / 1000
    return out


P1 = _avoiding([U("n", 105), U("ã", 145), U("n", 75), U("ɐ˞", 95), U("ɹ", 50), U("m", 90),
                U("ũ", 120), U("n", 60), U("iː", 215), U("ɕ", 95)], T1)
# peets, with the closure silences before each t (1.70-1.715, 2.00-2.04)
P2 = _avoiding([U("p", 65), U("iː", 180, fade_ms=100), U("_", 15), U("tʰ", 45),
                U("iː", 240, fade_ms=100), U("_", 40), U("tʰ", 40), U("iː", 320, fade_ms=100)], T2)


def world(x):
    x = np.ascontiguousarray(x, dtype=np.float64)
    f0, t = pw.harvest(x, SR, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(x, f0, t, SR)
    fq = np.linspace(0, SR / 2, sp.shape[1])
    return f0, 10 * np.log10(sp[:, fq < 5000] + 1e-20), 10 * np.log10(sp.sum(1) + 1e-20)


def harm(x, nh=4):
    f0, t = pw.harvest(x.astype(np.float64), SR, frame_period=10, f0_floor=80, f0_ceil=1200)
    n = int(0.06 * SR) // 2 * 2; win = np.hanning(n); rows = []
    for k in np.where(f0 > 0)[0]:
        c = int(t[k] * SR); seg = x[c - n // 2: c + n // 2]
        if len(seg) < n or np.sqrt(np.mean(seg ** 2)) < 0.03 * np.abs(x).max():
            continue
        S = np.abs(np.fft.rfft(seg * win, 8 * n)); fq = np.fft.rfftfreq(8 * n, 1 / SR)
        h = [20 * np.log10(S[(fq > f0[k] * (m - .3)) & (fq < f0[k] * (m + .3))].max() + 1e-12) for m in range(1, nh + 1)]
        rows.append(np.array(h) - h[0])
    return np.median(rows, 0)


def smooth(L, e):
    act = e > e.max() - 30
    both = act[1:] & act[:-1]
    flux = np.sqrt(np.mean(np.diff(L, axis=0) ** 2, axis=1))[both]
    loud = np.abs(np.diff(e))[both]
    return np.median(flux), np.percentile(flux, 95), np.median(loud), np.percentile(loud, 95)


def reference():
    a, sr = sf.read(ROOT / "reference/source/prince_reference.wav")
    return resample_poly(a.mean(1), SR, sr)


def score(phrases, ref):
    lsd, shape, Ls, es, wav = [], [], [], [], []
    for y, t0 in phrases:
        r = ref[int(t0 * SR): int(t0 * SR) + len(y)]
        _, Ly, ey = world(y); _, Lr, er = world(r)
        n = min(len(Ly), len(Lr)); Ly, Lr, ey, er = Ly[:n], Lr[:n], ey[:n], er[:n]
        act = er > er.max() - 30
        d = Ly[act] - Lr[act]
        lsd.append(np.sqrt(np.mean(d ** 2, 1)))
        dc = d - d.mean(1, keepdims=True)
        shape.append(np.sqrt(np.mean(dc ** 2, 1)))
        Ls.append(Ly); es.append(ey); wav.append(y)
    fl = smooth(np.vstack(Ls), np.concatenate(es))
    return dict(LSD=np.mean(np.concatenate(lsd)), LSDshape=np.mean(np.concatenate(shape)),
                flux=fl[0], fp95=fl[1], loud=fl[2], lp95=fl[3], H=harm(np.concatenate(wav)))


def render(cat, **kw):
    return [(synth(P1, ref_f0(T1), cat, **kw), T1), (synth(P2, ref_f0(T2), cat, **kw), T2)]


def row(name, s):
    return (f"{name:28} {s['LSD']:5.1f} {s['LSDshape']:8.1f} {s['flux']:6.2f} {s['fp95']:6.2f} "
            f"{s['loud']:6.2f} {s['lp95']:6.2f}   " + " ".join(f"{h:4.0f}" for h in s['H'][1:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    cat, ref = Catalogue(), reference()
    print(f"{'':28} {'LSD':>5} {'LSDshape':>8} {'flux':>6} {'p95':>6} {'loud':>6} {'p95':>6}   H2   H3   H4")
    # the clip against itself: smoothness/hum targets
    _, Lr, er = world(np.concatenate([ref[int(T1*SR):int(1.15*SR)], ref[int(T2*SR):int(2.40*SR)]]))
    fl = smooth(Lr, er); h = harm(ref)
    print(f"{'CLIP (target)':28} {'-':>5} {'-':>8} {fl[0]:6.2f} {fl[1]:6.2f} {fl[2]:6.2f} {fl[3]:6.2f}   "
          + " ".join(f"{x:4.0f}" for x in h[1:]))
    configs = {"default": {}}
    if a.sweep:
        configs = {f"real_tails {r}": dict(real_tails=r) for r in (False, True)}
    for name, kw in configs.items():
        ph = render(cat, **kw)
        print(row(name, score(ph, ref)))
        if a.save:
            pause = np.zeros(int(0.34 * SR), np.float32)
            y = np.concatenate([ph[0][0], pause, ph[1][0]])
            slug = name.replace(" ", "_").replace(".", "")
            out = ROOT / "out" / "bnuy"; out.mkdir(parents=True, exist_ok=True)
            sf.write(out / f"iter_{slug}.wav", y / np.abs(y).max() * 0.8, SR)


if __name__ == "__main__":
    main()
