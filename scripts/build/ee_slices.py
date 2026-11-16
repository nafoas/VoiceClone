"""Is the rest of the gap his movement? Fit early / middle / late thirds of each
"ee" separately (each a frozen mouth), starting from the best whole-"ee" fit."""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
os.environ.update(LARV="1", HEAD="1", HEAD_R="2.6", NAT_W="4", PULSE="smooth")
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics")); sys.argv = sys.argv[:1]
import ee_bunfit as B, ee_decompose as DC, soundfile as sf
from scipy.optimize import least_squares
W = json.loads((ROOT / "models/ee_bunfit_larv.json").read_text())["per_ee"]
SPANS = [(0.79, 0.99), (1.52, 1.60), (1.77, 1.90), (2.09, 2.30)]


def slice_targets(j):
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    s, e = SPANS[j]; d = DC.decompose(x[int((s - 0.02) * sr): int((e + 0.02) * sr)], sr, f"s{j}")
    A = d["A"]; ok = ~np.isnan(A[:, 0]); dB = 20 * np.log10(A[ok] + 1e-12); dB -= dB[:, :1]
    rel = d["rel"][ok]; n = len(dB); a, b = n // 10, n - n // 10; edges = np.linspace(a, b, 4).astype(int)
    out = []
    for i in range(3):
        sl = slice(edges[i], edges[i + 1]); z = np.nanmean(np.exp(1j * rel[sl]), 0)
        out.append(dict(f0=float(np.median(d["F0"])), level=np.nanmedian(dB[sl], 0)[:20], phase=np.angle(z)[:20], coh=np.abs(z)[:20]))
    return out


def run(j):
    res = []
    for i, t in enumerate(slice_targets(j)):
        z0 = np.clip(np.array(W[j]["z"]), B.LO + 1e-6, B.HI - 1e-6)
        r = least_squares(B.resid, z0, args=(t,), bounds=(B.LO, B.HI), method="trf", max_nfev=3000, diff_step=1e-3)
        res.append((float(np.sqrt(np.mean(B.resid(z0, t)[:19] ** 2))), float(np.sqrt(np.mean(r.fun[:19] ** 2))), r.x.tolist()))
    return j, res


if __name__ == "__main__":
    with Pool(4) as p:
        out = sorted(p.map(run, range(4)))
    for j, res in out:
        print(f"{B.T[j]['f0']:.0f} Hz (whole-ee fit {W[j]['err']:.2f} dB): " +
              " | ".join(f"{nm}: frozen mouth {a:.2f} -> own shape {b:.2f}" for nm, (a, b, _) in zip(("early", "middle", "late"), res)))
    json.dump({str(j): [r[2] for r in res] for j, res in out}, open(ROOT / "models/ee_slices.json", "w"))
