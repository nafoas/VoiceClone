"""Step 3e: tighten his "ee" tones with a least-squares fit (each tone its own
residual), more tube detail, and the full puff shape per "ee".

Target: his tones (averaged middle). His own first-half vs second-half spread is
~4 dB rms, so "exact" for a static recipe ~ within 3 dB.

  per "ee": tube = smooth area function (NC shape coefficients), length (larynx
  depth), puff = open share, rise share, closing roundness, closing
  smoothness, how gently the folds ease shut
  physical limits: tongue channel >= MIN_CH, widths bun-sized
  then: each "ee" tube translated to bun anatomy

    python scripts/build/ee_lsq.py -> models/ee_lsq.json, out/build/ee_lsq_his_tones_vs_model.wav
"""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.optimize import least_squares
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics"))
os.environ.setdefault("PULSE", "smooth")
import ee_exact as X  # noqa: E402  (tube_H, puff_C, pulse_flex, areas, render, T, to_bun)

NC = int(os.environ.get("NC", "16")); MIN_CH = float(os.environ.get("MIN_CH", "0.006"))
FRONT_MAX = float(os.environ.get("FRONT_MAX", "1.2"))      # widest the front of the mouth may be (cm^2)
TAG = os.environ.get("TAG", "")
NH = X.NH; FLOOR = X.FLOOR; T = X.T


def areas(c):
    from scipy.fft import idct
    z = np.zeros(X.NS); z[:len(c)] = c
    return np.exp(np.clip(idct(z, norm="ortho"), -7, 1.2))


LO = np.r_[np.full(NC, -12.0), 7.0, 0.3, 0.3, 0.3, 0.0, 0.0]
HI = np.r_[np.full(NC, 12.0), 9.5, 0.97, 0.95, 4.0, 1.5, 1.0]


def resid(z, t):
    c = z[:NC]; L = z[NC]; q = tuple(z[NC + 1:NC + 6])
    a = areas(c)
    Zc = X.puff_C(t["f0"], q) * X.tube_H(a, L, np.arange(1, NH + 1) * t["f0"])
    lv = 20 * np.log10(np.abs(Zc) + 1e-15); lv -= lv[0]
    ph = np.angle(np.exp(1j * (np.angle(Zc) - np.arange(1, NH + 1) * np.angle(Zc[0]))))
    r_lv = np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)
    w = np.clip((t["coh"][1:] - 0.7) / 0.3, 0, 1)
    r_ph = 3.0 * w * np.angle(np.exp(1j * (ph[1:] - t["phase"][1:])))
    front = a[int(0.75 * X.NS):]                                  # the last quarter: incisors, lips
    r_phys = np.r_[300 * max(0, MIN_CH - a[4:].min()), 300 * max(0, a.max() - 1.2), 300 * max(0, front.max() - FRONT_MAX)]
    return np.r_[r_lv, r_ph, r_phys]


def fit_one(args):
    j, starts = args; t = T[j]; best = None
    for z0 in starts:
        z0 = np.clip(z0, LO + 1e-6, HI - 1e-6)
        r = least_squares(resid, z0, args=(t,), bounds=(LO, HI), method="trf", max_nfev=4000, x_scale="jac")
        e = float(np.sqrt(np.mean(r.fun[:NH - 1] ** 2)))
        if best is None or e < best[0]:
            best = (e, r.x.tolist())
    return j, best


def main():
    D = json.loads((ROOT / "models/ee_exact_D.json").read_text())
    rng = np.random.default_rng(0)
    jobs = []
    for j, pe in enumerate(D["per_ee"]):
        c = np.zeros(NC); c[:len(pe["coeffs"])] = pe["coeffs"]
        q = pe.get("puff", [D["puff"]["Oq"], D["puff"]["am"], D["puff"]["p"], D["puff"]["Ta_ms"], D["puff"]["ease"]])
        base = np.r_[c, D["L_cm"], q]
        starts = [base]
        for k in range(5):
            z = base.copy(); z[:NC] += rng.normal(0, 0.4, NC); z[NC + 1] = rng.uniform(0.4, 0.95)
            z[NC + 2] = rng.uniform(0.35, 0.8); z[NC + 5] = rng.uniform(0, 1); starts.append(z)
        jobs.append((j, starts))
    with Pool(4) as pool:
        res = sorted(pool.map(fit_one, jobs))
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    import ee_decompose as DC
    gap = np.zeros(int(0.35 * 24000)); pieces = []; out = []
    for (j, (e, z)), t, (s, en) in zip(res, T, X.R.SPANS):
        z = np.array(z); a = areas(z[:NC]); L = z[NC]; q = tuple(z[NC + 1:NC + 6])
        Zc = X.puff_C(t["f0"], q) * X.tube_H(a, L, np.arange(1, NH + 1) * t["f0"])
        lv = 20 * np.log10(np.abs(Zc)); lv -= lv[0]
        print(f"\n{t['f0']:.0f} Hz: tone error {e:.2f} dB | tube {L:.2f} cm, narrowest {a[4:].min():.3f} cm2 | "
              f"puff open {q[0]:.2f}, rise {q[1]:.2f}, roundness {q[2]:.2f}, smooth {q[3]:.2f} ms, eases shut {q[4]:.2f}")
        print("  his  " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print("  model" + " ".join(f"{v:4.0f}" for v in lv))
        d = DC.decompose(x[int((s - 0.02) * sr): int((en + 0.02) * sr)], sr, f"q{j}")
        his_t = resample_poly(d["harm"], 1, 2); his_t = his_t / np.abs(his_t).max() * 0.7
        y = X.render(a, L, q, t["f0"], max(int((en - s) * 1000), 150), seed=j)
        pieces += [his_t, gap, resample_poly(y, 1, 2), gap, gap]
        pose, neck, match = X.to_bun(a, L)
        print(f"  as bun anatomy: larynx {neck * 0.075:.2f} cm lower, shape match {match:.2f}; "
              + str({k: round(float(v), 2) for k, v in zip(['jaw', 'body', 'front', 'tip', 'root', 'lips', 'round'], pose.vec()[:7])}))
        out.append(dict(f0=t["f0"], err=e, z=z.tolist(), L=L, puff=list(q), areas=a.tolist(), bun_pose=pose.vec().tolist(), bun_neck=neck, bun_match=match))
    sf.write(ROOT / f"out/build/ee_lsq{TAG}_his_tones_vs_model.wav", np.concatenate(pieces), 24000)
    (ROOT / f"models/ee_lsq{TAG}.json").write_text(json.dumps(dict(NC=NC, MIN_CH=MIN_CH, per_ee=out), indent=1, default=float))


if __name__ == "__main__":
    main()
