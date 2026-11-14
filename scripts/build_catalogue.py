"""Build Prince's phoneme catalogue from the labelled reference clip.

Segment times come from analysis/IPA_TRANSCRIPTION.md. Steady sounds keep the
median frame of the middle half of every instance (all instances pooled);
dynamic sounds (bursts) keep their full frame sequence.

    python scripts/build_catalogue.py   -> models/catalogue.npz
"""

import json
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
SR, FRAME_MS = 24000, 5.0

# label: list of (start, end) in the reference clip; "dyn" = keep whole sequence
SEGMENTS = {
    "n":  [(0.05, 0.155), (0.30, 0.375), (0.73, 0.79)],
    "ã":  [(0.155, 0.30)],
    "ɐ˞": [(0.375, 0.47)],
    "ɹ":  [(0.47, 0.52)],
    "m":  [(0.52, 0.61)],
    "ũ":  [(0.61, 0.73)],
    "iː": [(0.79, 0.99), (1.52, 1.60), (1.77, 1.90), (2.09, 2.30)],
    "ɕ":  [(1.02, 1.11)],
    "p":  [(1.455, 1.525)],   # dyn: weak lip release + rising transition
    "tʰ": [(1.712, 1.772)],   # dyn: crisp burst + aspiration
}
DYNAMIC = {"p", "tʰ"}
VOICED = {"n", "ã", "ɐ˞", "ɹ", "m", "ũ", "iː", "p", "tʰ"}


def main():
    a, sr = sf.read(ROOT / "reference/source/prince_reference.wav")
    x = resample_poly(a.mean(1), SR, sr)
    f0, t = pw.harvest(x, SR, frame_period=FRAME_MS, f0_floor=60, f0_ceil=900)
    sp, ap = pw.cheaptrick(x, f0, t, SR), pw.d4c(x, f0, t, SR)
    labels, store, voiced, dyn, f0s = [], {}, [], [], []
    for i, (lab, spans) in enumerate(SEGMENTS.items()):
        if lab in DYNAMIC:
            s, e = spans[0]
            m = (t >= s) & (t < e)
            S, A = sp[m], ap[m]
            fr = np.linspace(0, SR / 2, ap.shape[1]); band = (fr > 300) & (fr < 4000)
            store[f"vm_{i}"] = ((f0[m] > 0) & (A[:, band].mean(1) < 0.5)).astype(np.int8)  # tone, not noise
            f = float(np.median(f0[m][f0[m] > 0])) if (f0[m] > 0).any() else 0.0
        else:
            S_all, A_all, F = [], [], []
            for s, e in spans:
                d = e - s
                m = (t >= s + d * 0.25) & (t < e - d * 0.25)
                S_all.append(np.log(sp[m] + 1e-20)); A_all.append(ap[m]); F.append(f0[m])
            S = np.exp(np.median(np.vstack(S_all), 0))
            A = np.median(np.vstack(A_all), 0)
            Fv = np.concatenate(F); Fv = Fv[Fv > 0]
            f = float(np.median(Fv)) if len(Fv) else 0.0
        store[f"sp_{i}"], store[f"ap_{i}"] = S, A
        labels.append(lab); voiced.append(lab in VOICED); dyn.append(lab in DYNAMIC); f0s.append(f)
        print(f"{lab:3} {'dynamic ' + str(len(S)) + ' frames' if lab in DYNAMIC else 'steady':18} f0 {f:5.0f}")
    meta = dict(labels=labels, voiced=voiced, dynamic=dyn, f0=f0s,
                source="reference/source/prince_reference.wav", frame_ms=FRAME_MS)
    out = ROOT / "models"; out.mkdir(exist_ok=True)
    np.savez(out / "catalogue.npz", meta=json.dumps(meta, ensure_ascii=False), **store)
    print("saved models/catalogue.npz")


if __name__ == "__main__":
    main()
