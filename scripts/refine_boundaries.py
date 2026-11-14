"""Refine the reference transcription's sound boundaries by analysis-by-synthesis.

Rebuild each phrase from the catalogue, align it to the clip frame by frame with
dynamic time warping (DTW) on spectral envelopes, and move every boundary to
where the alignment maps it. Prints the refined boundaries; with --apply,
writes them into scripts/build_catalogue.py (PHRASES).

    python scripts/refine_boundaries.py [--iters 2] [--apply]
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import iterate as I  # noqa: E402
from prince_voice.bnuysynth import SR, Catalogue, synth  # noqa: E402


def bands(L):
    """log-spectrum (0-5 kHz) -> 40 coarse bands, mean-removed per frame."""
    B = np.array_split(L, 40, axis=1)
    X = np.stack([b.mean(1) for b in B], 1)
    return X - X.mean(1, keepdims=True)


def dtw(A, B, band=12):
    n, m = len(A), len(B)
    D = np.full((n + 1, m + 1), np.inf); D[0, 0] = 0
    for i in range(1, n + 1):
        lo, hi = max(1, i - band), min(m, i + band)
        c = np.sqrt(((A[i - 1] - B[lo - 1:hi]) ** 2).sum(1))
        for j in range(lo, hi + 1):
            D[i, j] = c[j - lo] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]])
        i, j = (i - 1, j - 1) if k == 0 else (i - 1, j) if k == 1 else (i, j - 1)
    return path[::-1]


def refine(units, t0, cat, ref):
    y = synth(units, I.ref_f0(t0), cat)
    r = ref[int(t0 * SR): int(t0 * SR) + len(y) + int(0.05 * SR)]
    _, Ly, _ = I.world(y); _, Lr, _ = I.world(r)
    path = dtw(bands(Ly), bands(Lr))
    m = {}
    for a, b in path:
        m.setdefault(a, []).append(b)
    edges = np.cumsum([0] + [int(round(u.ms / 5)) for u in units])
    new = []
    for e in edges:
        e = min(e, len(Ly) - 1)
        new.append(t0 + np.median(m.get(e, [e])) * 0.005)
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=1)
    a = ap.parse_args()
    cat, ref = Catalogue(), I.reference()
    for units, t0, name in ((I.P1, I.T1, "phrase1"), (I.P2, I.T2, "peets")):
        b = refine(units, t0, cat, ref)
        old = np.cumsum([t0] + [u.ms / 1000 for u in units])
        print(name)
        for k, u in enumerate(units):
            print(f"  {u.ph:3} {old[k]:.3f}-{old[k+1]:.3f}  ->  {b[k]:.3f}-{b[k+1]:.3f}   "
                  f"(start {1000*(b[k]-old[k]):+4.0f} ms)")


if __name__ == "__main__":
    main()
