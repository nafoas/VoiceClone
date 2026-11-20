"""How each consonant is made, checked against his clip (not against a recogniser).

For a model render on the clip's timeline (48 kHz) and the clip itself:
  moves   : every 5 ms through each consonant and its joins (40 ms either side), the spectrum's shape
            (third-octave bands 200 Hz-12.8 kHz, each frame's level removed) vs his: rms dB. This is
            where the ear finds out WHERE a consonant is made (the resonances moving in and out).
  level   : the loudness contour through the same stretch vs his (dB, rms), e.g. how loud the hum is
            inside a closure
  burst   : the release noise's spectral centre (first 12 ms after the release) vs his
  breath  : the aspiration's band shape (the rest of the noise before the voice starts) vs his: rms dB

    import cons_check; cons_check.report(y)          (y: model on the clip's timeline, 48 kHz)
"""
import numpy as np

SR = 48000
EDGES = 200 * 2 ** (np.arange(0, 19) / 3); EDGES = EDGES[EDGES <= 12800]
# the consonants and their joins: (name, start, end, release time or None)
STRETCH = [("n  (nann-)", 0.03, 0.20, None), ("ã-n-ɐ˞", 0.26, 0.42, None), ("ɐ˞-ɹ-m-ũ", 0.43, 0.66, None),
           ("ũ-n-i", 0.69, 0.83, None), ("soft S", 1.00, 1.14, None), ("p (lips)", 1.45, 1.51, None), ("p-ee", 1.45, 1.56, 1.465), ("ee-t (closing)", 1.56, 1.66, None),
           ("t-ee", 1.70, 1.82, 1.709), ("ee-t (closing)", 1.86, 1.96, None), ("t-ee", 2.03, 2.14, 2.037)]


def _bands(w, t, N=1024):
    c = int(t * SR); seg = w[c - N // 2: c + N // 2]
    if len(seg) < N:
        return None, -140.0
    S = np.abs(np.fft.rfft(seg * np.hanning(N))) ** 2; f = np.fft.rfftfreq(N, 1 / SR)
    b = np.array([10 * np.log10(S[(f >= lo) & (f < hi)].mean() + 1e-16) for lo, hi in zip(EDGES[:-1], EDGES[1:])])
    return b - b.max(), 10 * np.log10(np.mean(seg ** 2) + 1e-14)


def centroid(w, a, b):
    seg = w[int(a * SR): int(b * SR)]; S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR); k = (f > 1000) & (f < 16000)
    return float(np.sum(f[k] * S[k]) / np.sum(S[k]))


def report(y, x, ref_level=None, quiet=False):
    """Returns dict of measures; prints a table unless quiet."""
    out = {}
    # loudness reference: both normalised to their own vowel level (the "ee" of teet)
    lv = lambda w: 10 * np.log10(np.mean(w[int(1.79 * SR): int(1.88 * SR)] ** 2) + 1e-14)
    gx, gy = lv(x), lv(y)
    for name, a, b, rel in STRETCH:
        sh, le = [], []
        for t in np.arange(a, b, 0.005):
            bx, Lx = _bands(x, t); by, Ly = _bands(y, t)
            if bx is None or by is None:
                continue
            Lx -= gx; Ly -= gy
            if Lx > -45 and Ly > -70:   # where he is audible, the shape counts (weighted by how loud he is there)
                ok = bx > -45
                sh.append((float(np.sqrt(np.mean((np.maximum(by, -45) - bx)[ok] ** 2))), 1.0 + (Lx + 45) / 45))
            le.append(max(Ly, -60) - max(Lx, -60))
        s_ = float(np.sum([q * w for q, w in sh]) / np.sum([w for _, w in sh])) if sh else np.nan
        out[name + f"@{a:.2f}"] = dict(shape=s_, level=float(np.sqrt(np.mean(np.square(le)))), level_bias=float(np.mean(le)))
        if rel is not None:
            cx, cy = centroid(x, rel, rel + 0.012), centroid(y, rel, rel + 0.012)
            out[name + f"@{a:.2f}"].update(burst_his=cx, burst_model=cy)
    if not quiet:
        for k, v in out.items():
            extra = f"  burst centre {v['burst_model'] / 1000:4.1f} kHz (his {v['burst_his'] / 1000:4.1f})" if "burst_his" in v else ""
            print(f"  {k:22} shape {v['shape']:5.1f} dB   loudness {v['level']:5.1f} dB (model {v['level_bias']:+5.1f}){extra}")
        print(f"  ALL: shape {np.nanmean([v['shape'] for v in out.values()]):.2f} dB, loudness {np.mean([v['level'] for v in out.values()]):.2f} dB")
    return out
