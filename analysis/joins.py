"""How big are the jumps at the joins between sounds? Compared for the gold
rebuild (seamless, real transitions) and new phrases.

For each boundary between two voiced sounds: spectral jump (0-4 kHz shape, dB),
loudness jump (dB), pitch jump (st) and hum jump (H1-H2 change, dB), measured
as the difference between the 15 ms just before and just after the join,
minus the typical change over the same span inside sounds (so only the
*extra* jump caused by the join counts).
"""
import numpy as np, pyworld as pw

SR, FP = 24000, 5.0

def feats(y):
    y = y.astype(np.float64)
    f0, t = pw.harvest(y, SR, frame_period=FP, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(y, f0, t, SR); fq = np.linspace(0, SR / 2, sp.shape[1])
    L = 10 * np.log10(sp[:, fq < 4000] + 1e-20)
    e = 10 * np.log10(sp.sum(1) + 1e-20)
    h12 = np.array([10 * np.log10(np.interp(f, fq, s_) / (np.interp(2 * f, fq, s_) + 1e-20) + 1e-20) if f > 0 else np.nan
                    for f, s_ in zip(f0, sp)])
    return f0, L - L.mean(1, keepdims=True), e, h12

def jumps(y, bounds, w=3):
    f0, L, e, h = feats(y)
    out = []
    def delta(a, b):
        A, B = slice(max(0, a - w), a), slice(b, min(len(e), b + w))
        if A.stop - A.start < 2 or B.stop - B.start < 2: return None
        vA, vB = f0[A] > 0, f0[B] > 0
        if not (vA.all() and vB.all()): return None
        return (np.sqrt(np.mean((L[A].mean(0) - L[B].mean(0)) ** 2)), abs(e[A].mean() - e[B].mean()),
                abs(12 * np.log2(f0[A].mean() / f0[B].mean())), abs(np.nanmean(h[A]) - np.nanmean(h[B])))
    J = [d for b, _, _ in bounds if (d := delta(b, b)) is not None]
    # baseline: same measurement inside sounds (away from joins)
    bset = np.array([b for b, _, _ in bounds])
    inner = [d for c in range(w + 1, len(e) - w - 1, 2) if (np.abs(bset - c).min() > 2 * w) and (d := delta(c, c)) is not None]
    return np.array(J), np.array(inner)

def report(name, y, bounds):
    J, I = jumps(y, bounds)
    if len(J) == 0:
        print(f"{name:30} (no voiced joins)"); return
    ex = J.mean(0) - I.mean(0)
    print(f"{name:30} joins {len(J):2}  extra jump at joins: spectrum {ex[0]:+5.2f} dB  loudness {ex[1]:+5.2f} dB  "
          f"pitch {ex[2]:+5.2f} st  hum {ex[3]:+5.2f} dB")
