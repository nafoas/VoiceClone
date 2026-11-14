"""Fit the mouth to him: for each of his recorded vowels, find the articulator
positions (VocalTractLab parameters, in a tract scaled to his size) whose
resonances match the ones he really made.

    python scripts/fit_mouth.py [--scale 0.72]   -> models/mouth_fit.json

Cost = Bark distance on F1..F3 (F4 at half weight) + a small pull toward the
human starting shape (so the fit stays an ordinary, plausible articulation).
"""
import argparse, json, sys, time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince_voice.mouth import Mouth  # noqa: E402

# his vowels (analysis/fingerprint_sounds.csv, mid-vowel medians) and the human
# shape each one starts from
HIS = {
    "iː": dict(F=(362, 3323, 4119, 4963), start="i"),
    "ũ":  dict(F=(388, 1325, 3914, 4871), start="u"),
    "ã":  dict(F=(1178, 2138, 3679, 4824), start="a"),
    "ɐ˞": dict(F=(813, 1954, 3082, 4342), start="@"),
}
W = np.array([1.0, 1.0, 0.7, 0.35])
FREE = ["HX", "HY", "JA", "LP", "LD", "TCX", "TCY", "TTX", "TTY", "TBX", "TBY", "TRX", "TRY"]


def bark(f):
    f = np.asarray(f, float)
    return 26.81 * f / (1960 + f) - 0.53


def fit_one(m, target, start, reg=0.15, iters=600):
    p0 = m.shape(start)
    idx = [m.names.index(n) for n in FREE]
    span = (m.hi - m.lo)[idx]

    def params(z):
        p = p0.copy(); p[idx] = np.clip(p0[idx] + z * span, m.lo[idx], m.hi[idx]); return p

    def cost(z):
        F = np.array(m.formants(params(z), fmax=5800, df=10))
        F = np.where(np.isfinite(F), F, 9000)
        e = np.sqrt(np.sum(W * (bark(F) - bark(target)) ** 2))
        return e + reg * np.sqrt(np.mean(z ** 2))

    best = minimize(cost, np.zeros(len(idx)), method="Powell",
                    options=dict(maxfev=iters, xtol=1e-3, ftol=1e-4))
    p = params(best.x)
    return p, m.formants(p), float(best.fun)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--scale", type=float, default=0.72)
    a = ap.parse_args()
    m = Mouth(scale=a.scale)
    out = dict(scale=a.scale, vowels={})
    for v, d in HIS.items():
        t = time.time()
        p, F, c = fit_one(m, np.array(d["F"], float), d["start"])
        human = m.formants(m.shape(d["start"]))
        print(f"{v:3} from /{d['start']}/: his {d['F']}  scaled human {[int(x) for x in human]}  "
              f"fit {[int(x) for x in F]}  cost {c:.2f}  ({time.time() - t:.0f}s)")
        moved = {n: round(float(p[m.names.index(n)] - m.shape(d['start'])[m.names.index(n)]), 2) for n in FREE}
        print("     moved:", {k: v2 for k, v2 in moved.items() if abs(v2) > 0.05})
        out["vowels"][v] = dict(start=d["start"], params=[float(x) for x in p], formants=F, cost=c)
    (ROOT / "models").mkdir(exist_ok=True)
    (ROOT / "models/mouth_fit.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
