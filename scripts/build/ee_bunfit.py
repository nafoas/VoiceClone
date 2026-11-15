"""Step 3f: his "ee" tones from HIS BUN MOUTH plus natural variation only.

A free tube can hit his ~19 tone levels with many shapes, some not bun-like
(ripples, an inflated front: step 3e). So the bun mouth is the starting point:
  tube = the bun "ee" shape (tongue, jaw, lips, larynx depth: the bun model)
         x smooth departures (8 shape terms), each point within ~+-15% of the
         bun's width (natural variation), with a cost on every departure
  puff = per "ee" (open share, rise, roundness, closing smoothness, easing)
Least squares, every tone its own residual.

    python scripts/build/ee_bunfit.py -> models/ee_bunfit.json, out/build/ee_bunfit_his_tones_vs_model.wav,
                                        analysis/physics/ee_bunfit.png
"""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import idct
from scipy.optimize import least_squares
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics"))
os.environ.setdefault("PULSE", "smooth")
import ee_exact as X  # noqa: E402
import ee as E  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402

NH = X.NH; FLOOR = X.FLOOR; T = X.T; NS = X.NS
ND = 8                  # smooth departure terms
SIGMA = 0.15            # natural variation of width (~15%)
LARCAV = (7, 1.0, 4, 0.15)
_cache = {}


def bun_tube40(pose9, neck):
    key = (tuple(np.round(pose9, 3)), round(neck, 1))
    if key not in _cache:
        v = Pose().vec(); v[:9] = np.clip(pose9, E.EE_LO, E.EE_HI)
        m = BunMouth(0.75, neck_mm=neck, larcav=LARCAV); ar, ln, _, _ = m.tube(Pose.from_vec(v))
        edges = np.r_[0, np.cumsum(ln)]; L = edges[-1]; e40 = np.linspace(0, L, NS + 1); a40 = np.empty(NS)
        for i in range(NS):
            ov = np.clip(np.minimum(edges[1:], e40[i + 1]) - np.maximum(edges[:-1], e40[i]), 0, None)
            a40[i] = np.sum(ov * ar) / max(ov.sum(), 1e-9)
        if len(_cache) > 20000:
            _cache.clear()
        _cache[key] = (np.maximum(a40, 1e-4), L)
    return _cache[key]


def unpack(z):
    pose9 = z[:9]; neck = z[9]; d = z[10:10 + ND]; q = tuple(z[10 + ND:15 + ND])
    a0, L = bun_tube40(pose9, neck)
    dev = idct(np.r_[d, np.zeros(NS - ND)], norm="ortho")
    return a0 * np.exp(dev), L, q, dev


LO = np.r_[E.EE_LO, 15.0, np.full(ND, -3.0), 0.3, 0.3, 0.3, 0.0, 0.0]
HI = np.r_[E.EE_HI, 45.0, np.full(ND, 3.0), 0.97, 0.95, 4.0, 1.5, 1.0]


def resid(z, t):
    a, L, q, dev = unpack(z)
    Zc = X.puff_C(t["f0"], q) * X.tube_H(a, L, np.arange(1, NH + 1) * t["f0"])
    lv = 20 * np.log10(np.abs(Zc) + 1e-15); lv -= lv[0]
    ph = np.angle(np.exp(1j * (np.angle(Zc) - np.arange(1, NH + 1) * np.angle(Zc[0]))))
    r_lv = np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)
    w = np.clip((t["coh"][1:] - 0.7) / 0.3, 0, 1)
    r_ph = 3.0 * w * np.angle(np.exp(1j * (ph[1:] - t["phase"][1:])))
    r_nat = 1.5 * dev[::4] / SIGMA                                   # natural variation: ~15% costs as much as ~1.5 dB
    r_ch = [300 * max(0, 0.006 - a[4:].min())]
    return np.r_[r_lv, r_ph, r_nat, r_ch]


def fit_one(j):
    t = T[j]; prev = json.loads((ROOT / "models/ee_recipe.json").read_text()); rng = np.random.default_rng(j)
    best = None
    for k in range(6):
        p0 = np.array(prev["pose"][:9]) if k == 0 else np.array(prev["pose"][:9]) + rng.normal(0, 0.2, 9)
        z0 = np.r_[p0, rng.uniform(20, 40), np.zeros(ND), rng.uniform(0.6, 0.95), rng.uniform(0.4, 0.7), 1.0, 0.3, rng.uniform(0, 1)]
        z0 = np.clip(z0, LO + 1e-6, HI - 1e-6)
        r = least_squares(resid, z0, args=(t,), bounds=(LO, HI), method="trf", max_nfev=3000, diff_step=1e-3)
        e = float(np.sqrt(np.mean(r.fun[:NH - 1] ** 2)))
        if best is None or e < best[0]:
            best = (e, r.x.tolist())
    return j, best


def main():
    with Pool(4) as pool:
        res = sorted(pool.map(fit_one, range(4)))
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    import ee_decompose as DC
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(4, 2, figsize=(18, 13)); gap = np.zeros(int(0.35 * 24000)); pieces = []; out = []
    names = ["jaw", "body", "front", "tip", "root", "lips", "round", "velum", "larynx"]
    for (j, (e, z)), t, (s, en) in zip(res, T, X.R.SPANS):
        z = np.array(z); a, L, q, dev = unpack(z); a0, _ = bun_tube40(z[:9], z[9])
        Zc = X.puff_C(t["f0"], q) * X.tube_H(a, L, np.arange(1, NH + 1) * t["f0"]); lv = 20 * np.log10(np.abs(Zc)); lv -= lv[0]
        print(f"\n{t['f0']:.0f} Hz: tone error {e:.2f} dB | larynx {z[9] * 0.075:.2f} cm lower, tube {L:.2f} cm | "
              f"departures from the bun shape: up to {100 * (np.exp(np.abs(dev).max()) - 1):.0f}% (typical {100 * (np.exp(np.sqrt(np.mean(dev ** 2))) - 1):.0f}%)")
        print("  mouth: " + str({n: round(float(v), 2) for n, v in zip(names, z[:9])}))
        print(f"  puff: open {q[0]:.2f}, rise {q[1]:.2f}, roundness {q[2]:.2f}, smooth {q[3]:.2f} ms, eases shut {q[4]:.2f}")
        print("  his  " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print("  model" + " ".join(f"{v:4.0f}" for v in lv))
        pos = (np.arange(NS) + 0.5) * L / NS
        ax[j, 0].fill_between(pos, -np.sqrt(a / np.pi), np.sqrt(a / np.pi), step="mid", color="#e58c9a", label="fitted")
        ax[j, 0].plot(pos, np.sqrt(a0 / np.pi), "k-", lw=1, label="bun 'ee' shape"); ax[j, 0].plot(pos, -np.sqrt(a0 / np.pi), "k-", lw=1)
        ax[j, 0].set_title(f"{t['f0']:.0f} Hz: tube (vocal folds left, lips right), radius cm"); ax[j, 0].legend(fontsize=7)
        ax[j, 1].plot(range(1, NH + 1), t["level"], "-o", color="#c0392b", label="his tones")
        ax[j, 1].plot(range(1, NH + 1), lv, "-s", color="#2c3e50", label=f"model ({e:.1f} dB)"); ax[j, 1].legend(fontsize=7)
        ax[j, 1].set_ylim(-80, 5)
        d = DC.decompose(x[int((s - 0.02) * sr): int((en + 0.02) * sr)], sr, f"b{j}")
        his_t = resample_poly(d["harm"], 1, 2); his_t = his_t / np.abs(his_t).max() * 0.7
        y = X.render(a, L, q, t["f0"], max(int((en - s) * 1000), 150), seed=j)
        pieces += [his_t, gap, resample_poly(y, 1, 2), gap, gap]
        out.append(dict(f0=t["f0"], err=e, z=z.tolist(), areas=a.tolist(), L=L, puff=list(q),
                        max_departure_pct=float(100 * (np.exp(np.abs(dev).max()) - 1))))
    plt.tight_layout(); plt.savefig(ROOT / "analysis/physics/ee_bunfit.png", dpi=60)
    sf.write(ROOT / "out/build/ee_bunfit_his_tones_vs_model.wav", np.concatenate(pieces), 24000)
    (ROOT / "models/ee_bunfit.json").write_text(json.dumps(dict(ND=ND, SIGMA=SIGMA, per_ee=out), indent=1, default=float))


if __name__ == "__main__":
    main()
