"""Step 3: reproduce his "ee" tones: the folds' puff and the mouth's tube, fitted
together so neither covers for the other.

Puff: a flexible physical pulse (open share Oq, rising share am, closing
roundness p, closing smoothness Ta), shared by all four "ee"s. His dips at
harmonic 4 (at three pitches) say it comes from the puff's shape.
Tube: a smooth area function (10 shape coefficients), bun-sized, the tongue
channel very narrow but open (>= 0.015 cm^2), its length set by larynx depth.
  stage 1: ONE tube + the puff for all four "ee"s
  stage 2: each "ee" nudges the tube (its context), with a cost per nudge
Judged on every tone's strength (above his noise floor) and the timing of his
steady low tones. Then: the tube translated back into bun anatomy, and
tones-only renders next to his.

    python scripts/build/ee_exact.py -> models/ee_exact.json, analysis/physics/ee_exact.png, out/build/ee_exact_*.wav
"""
import json, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import idct
from scipy.optimize import minimize
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics"))
sys.argv = sys.argv[:1] + ["30"]
import ee_recipe as R  # noqa: E402
from prince_voice.mouth import _chain, _radiation  # noqa: E402

import os
NH = 20; NS = 40; NC = 10; FLOOR = -58.0; SR = 48000
MIN_CH = float(os.environ.get("MIN_CH", "0.015")); LMAX = float(os.environ.get("LMAX", "8.6"))
FIXQ = os.environ.get("FIXQ")          # e.g. "0.5,0.5,1.0,0.1": the puff held fixed
TAG = os.environ.get("TAG", "")
T = R.his_tones()


def areas(c):
    z = np.zeros(NS); z[:len(c)] = c
    return np.exp(np.clip(idct(z, norm="ortho"), -7, 1.2))


def pulse_flex(n, Oq, am, p):
    x = np.arange(n, dtype=float) / n; Tp = am * Oq
    rise = 0.5 * (1 - np.cos(np.pi * x / Tp))
    fall = np.clip(np.cos(0.5 * np.pi * (x - Tp) / max(Oq - Tp, 1e-3)), 0, None) ** p
    return np.where(x < Tp, rise, np.where(x < Oq, fall, 0.0))


def tube_H(a, L, f):
    w = 2 * np.pi * np.asarray(f, float)
    K = _chain(np.maximum(a, 1e-4), np.full(NS, L / NS), w)
    return 1j * w / (K[1, 0] * _radiation(a[-1], w) + K[1, 1])


def puff_C(f0, q):
    Oq, am, p, Ta = q
    k = np.arange(1, NH + 1) * f0
    return np.fft.rfft(pulse_flex(4096, Oq, am, p))[1: NH + 1] / (1 + 1j * 2 * np.pi * k * Ta * 1e-3)


def tones(a, L, f0, q):
    Z = puff_C(f0, q) * tube_H(a, L, np.arange(1, NH + 1) * f0)
    lv = 20 * np.log10(np.abs(Z) + 1e-15); lv -= lv[0]
    ph = np.angle(np.exp(1j * (np.angle(Z) - np.arange(1, NH + 1) * np.angle(Z[0]))))
    return lv, ph


def err_one(a, L, q, t):
    lv, ph = tones(a, L, t["f0"], q)
    el = np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)
    w = np.clip((t["coh"][1:] - 0.7) / 0.3, 0, 1)
    ep = np.angle(np.exp(1j * (ph[1:] - t["phase"][1:])))
    return np.sqrt(np.mean(el ** 2)) + 4.0 * np.sqrt(np.sum(w * ep ** 2) / (w.sum() + 1e-9))


def phys_pen(a):
    return 300 * max(0, MIN_CH - a[4:].min()) + 300 * max(0, a.max() - 1.2)


def unpack1(z):
    q = tuple(np.clip(z[NC:NC + 4], [0.3, 0.3, 0.3, 0.0], [0.95, 0.95, 4.0, 1.5]))
    if FIXQ:
        q = tuple(float(v) for v in FIXQ.split(","))
    return areas(z[:NC]), float(np.clip(z[NC + 4], 7.0, LMAX)), q


def cost1(z):
    a, L, q = unpack1(z)
    return np.mean([err_one(a, L, q, t) for t in T]) + phys_pen(a)


def run1(seed):
    rng = np.random.default_rng(seed)
    z0 = np.r_[np.log(0.25) * np.sqrt(NS), rng.normal(0, 0.7, NC - 1), rng.uniform(0.4, 0.7), rng.uniform(0.4, 0.7),
               rng.uniform(0.7, 1.6), 0.1, 7.6]
    r = minimize(cost1, z0, method="Powell", options=dict(maxfev=9000, xtol=1e-4, ftol=1e-6))
    return float(r.fun), r.x.tolist()


def run2(args):
    j, z1 = args
    a0, L, q = unpack1(np.array(z1)); c0 = np.array(z1[:NC]); t = T[j]

    def cost(dc):
        a = areas(c0 + dc)
        return err_one(a, L, q, t) + phys_pen(a) + 1.5 * np.sqrt(np.mean(dc ** 2))
    r = minimize(cost, np.zeros(NC), method="Powell", options=dict(maxfev=5000, xtol=1e-4))
    return j, float(r.fun), (c0 + r.x).tolist()


def to_bun(a, L):
    """Translate a tube into his bun mouth: the "ee" pose (and larynx depth) whose
    tube is closest in shape (log area along the length)."""
    from prince_voice.bunmouth import BunMouth, Pose
    import ee as E
    target = np.log(a); xs = (np.arange(NS) + 0.5) / NS

    def cost(z):
        v = Pose().vec(); v[:9] = np.clip(z[:9], E.EE_LO, E.EE_HI); neck = float(np.clip(z[9], 15, 45))
        m = BunMouth(0.75, neck_mm=neck, larcav=R.LARCAV); ar, ln, _, _ = m.tube(Pose.from_vec(v))
        pos = (np.cumsum(ln) - ln / 2) / ln.sum()
        return float(np.sqrt(np.mean((np.interp(xs, pos, np.log(np.maximum(ar, 1e-4))) - target) ** 2))
                     + 0.3 * abs(ln.sum() - L))
    prev = json.loads((ROOT / "models/ee_recipe.json").read_text())
    r = min((minimize(cost, np.r_[np.array(s)[:9], n], method="Powell", options=dict(maxfev=3000)) for s in
             (prev["pose"], [0.1, 0.6, 0.6, 0, 1, 0.6, 0, 0, 0.5], [0.2, 0.8, 0.8, 0, 0.5, 0.8, 0.2, 0, 0.5]) for n in (20.0, 30.0)),
            key=lambda r: r.fun)
    v = Pose().vec(); v[:9] = np.clip(r.x[:9], E.EE_LO, E.EE_HI)
    return Pose.from_vec(v), float(np.clip(r.x[9], 15, 45)), float(r.fun)


def render(a, L, q, f0, ms, seed, close_ms=0.1):
    """Model-only: the puff train (closing moment varying ~0.1 ms) through the tube."""
    from scipy.signal import butter, sosfiltfilt, fftconvolve, lfilter
    rng = np.random.default_rng(seed); n_ms = ms + 60; n = int(n_ms * SR / 1000)
    sos = butter(2, 6 / 500, "low", output="sos")
    drift = sosfiltfilt(sos, rng.standard_normal(n_ms + 20))[:n_ms]; drift = drift / drift.std() * 6.0
    tt = np.arange(n_ms); amp = np.clip(tt / 30, 0, 1) * np.clip((n_ms - 10 - tt) / 50, 0, 1)
    u0 = np.zeros(n); u1 = np.zeros(n); t = 0.0
    while True:
        i = min(int(t * 1000), n_ms - 1)
        T_ = 1 / (f0 * 2 ** (drift[i] / 1200)); Ls = int(round(T_ * SR)); s0 = int(round(t * SR))
        if s0 + Ls + 10 >= n:
            break
        u0[s0:s0 + Ls] += pulse_flex(Ls, q[0], q[1], q[2]) * amp[i]
        d = close_ms * 1e-3 * rng.standard_normal()
        u1[s0:s0 + Ls] += pulse_flex(Ls, float(np.clip(q[0] + d / T_, 0.2, 0.97)), q[1] * q[0] / max(q[0] + d / T_, 0.2), q[2]) * amp[i]
        t += T_
    lo = butter(4, 1200 / (SR / 2), "low", output="sos"); hi = butter(4, 1200 / (SR / 2), "high", output="sos")
    u = sosfiltfilt(lo, u0) + sosfiltfilt(hi, u1)
    if q[3] > 0:
        aa = np.exp(-1.0 / (q[3] * 1e-3 * SR)); u = lfilter([1 - aa], [1, -aa], u)
    f = np.fft.rfftfreq(8192, 1 / SR); H = tube_H(a, L, np.maximum(f, 1.0)); H[0] = 0
    ir = np.fft.irfft(H, 8192) * np.hanning(16384)[8192:]
    y = fftconvolve(u, ir)[: len(u)]
    return y / (np.abs(y).max() + 1e-12) * 0.7


def main():
    with Pool(4) as pool:
        s1 = pool.map(run1, range(8))
    s1.sort(key=lambda r: r[0]); e1, z1 = s1[0]
    a1, L, q = unpack1(np.array(z1))
    print(f"stage 1 (one tube): error {e1:.2f}; tube {L:.2f} cm; narrowest {a1[4:].min():.3f} cm2; "
          f"puff: open {q[0]:.2f}, rising {q[1]:.2f}, closing roundness {q[2]:.2f}, smoothness {q[3]:.2f} ms", flush=True)
    with Pool(4) as pool:
        s2 = sorted(pool.map(run2, [(j, z1) for j in range(4)]))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 4, figsize=(22, 9)); res = []
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    import ee_decompose as DC
    gap = np.zeros(int(0.35 * 24000)); pieces = []
    for (j, e2, c), t, (s, e) in zip(s2, T, R.SPANS):
        a = areas(np.array(c)); lv, ph = tones(a, L, t["f0"], q)
        el = np.sqrt(np.mean((np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)) ** 2))
        print(f"\n{t['f0']:.0f} Hz: tone error {el:.2f} dB (narrowest {a[4:].min():.3f} cm2)")
        print("  his  " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print("  model" + " ".join(f"{v:4.0f}" for v in lv))
        print("  timing diff (steady tones) " + " ".join(f"{np.angle(np.exp(1j * (u - v))):4.1f}" if cc >= 0.7 else "   ."
                                                     for u, v, cc in zip(ph, t["phase"], t["coh"])))
        ax[0, j].plot(range(1, NH + 1), t["level"], "-o", color="#c0392b", label="his tones")
        ax[0, j].plot(range(1, NH + 1), lv, "-s", color="#2c3e50", label="model tones")
        ax[0, j].set_title(f"{t['f0']:.0f} Hz: error {el:.1f} dB"); ax[0, j].set_ylim(-80, 5); ax[0, j].legend(fontsize=7)
        pos = (np.arange(NS) + 0.5) * L / NS
        ax[1, j].fill_between(pos, -np.sqrt(a / np.pi), np.sqrt(a / np.pi), step="mid", color="#e58c9a")
        ax[1, j].set_title("the tube (vocal folds left, lips right), radius cm"); ax[1, j].set_xlabel("cm")
        res.append(dict(f0=t["f0"], err=el, coeffs=c, areas=a.tolist()))
        # tones-only comparison: his (rebuilt from his tones) vs the model's audio
        d = DC.decompose(x[int((s - 0.02) * sr): int((e + 0.02) * sr)], sr, f"x{j}")
        his_t = resample_poly(d["harm"], 1, 2); his_t = his_t / np.abs(his_t).max() * 0.7
        y = render(a, L, q, t["f0"], max(int((e - s) * 1000), 150), seed=j)
        pieces += [his_t, gap, resample_poly(y, 1, 2), gap, gap]
    plt.tight_layout(); plt.savefig(ROOT / f"analysis/physics/ee_exact{TAG}.png", dpi=65)
    sf.write(ROOT / f"out/build/ee_exact{TAG}_his_tones_vs_model.wav", np.concatenate(pieces), 24000)
    pose, neck, fitq = to_bun(np.mean([np.array(r["areas"]) for r in res], 0), L)
    print(f"\nas bun anatomy: {dict(zip(['jaw','body','front','tip','root','lips','round','velum','larynx'], np.round(pose.vec()[:9], 2)))}, "
          f"larynx {neck * 0.075:.2f} cm lower; shape match {fitq:.2f} (log-area rms)")
    (ROOT / f"models/ee_exact{TAG}.json").write_text(json.dumps(dict(
        L_cm=L, puff=dict(Oq=q[0], am=q[1], p=q[2], Ta_ms=q[3]), stage1_err=e1, shared_coeffs=z1[:NC], per_ee=res,
        bun_pose=pose.vec().tolist(), bun_neck=neck, bun_shape_match=fitq), indent=1, default=float))


if __name__ == "__main__":
    main()
