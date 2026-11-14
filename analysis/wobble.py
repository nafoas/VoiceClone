"""Non-pitch wobble inside vowels/hums: how much loudness and timbre flutter
in steady voiced stretches (after removing slow trends).

    python analysis/wobble.py file.wav [...]
loud_flutter  sd of loudness after removing a 60 ms moving trend (dB)
h1_flutter    sd of the 1st-harmonic level after detrending (dB)
tone_flutter  sd of spectral-shape change (0-3 kHz) after detrending (dB)
"""
import sys
import numpy as np, pyworld as pw, soundfile as sf
from scipy.signal import resample_poly

def detrend(x, n=12):
    k = np.ones(n) / n
    tr = np.convolve(np.pad(x, (n // 2, n - 1 - n // 2), mode="edge"), k, "valid")
    return x - tr

def wobble(path, SR=24000):
    a, sr = sf.read(path)
    if a.ndim > 1: a = a.mean(1)
    if sr != SR: a = resample_poly(a, SR, sr)
    a = a.astype(float)
    f0, t = pw.harvest(a, SR, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(a, f0, t, SR); fq = np.linspace(0, SR / 2, sp.shape[1])
    e = 10 * np.log10(sp.sum(1) + 1e-20)
    v = (f0 > 0) & (e > e.max() - 20)
    # runs of >= 60 ms steady voicing
    runs, s = [], None
    for i, x in enumerate(np.r_[v, False]):
        if x and s is None: s = i
        if not x and s is not None:
            if i - s >= 12: runs.append((s, i))
            s = None
    L, H, T = [], [], []
    for s, e_ in runs:
        idx = np.arange(s, e_)
        L.append(detrend(e[idx]))
        h1 = 10 * np.log10(np.array([np.interp(f0[k], fq, sp[k]) for k in idx]) + 1e-20)
        H.append(detrend(h1))
        S = 10 * np.log10(sp[idx][:, fq < 3000] + 1e-20)
        S = S - S.mean(1, keepdims=True)
        T.append(np.sqrt(np.mean(np.diff(S, axis=0) ** 2, 1)))
    c = lambda z: np.concatenate(z) if z else np.zeros(1)
    return np.std(c(L)), np.std(c(H)), np.median(c(T))

if __name__ == "__main__":
    print(f"{'':30} loud_flutter  h1_flutter  tone_flutter")
    for p in sys.argv[1:]:
        l, h, t = wobble(p)
        print(f"{p[-30:]:30} {l:10.2f} {h:11.2f} {t:12.2f}")
