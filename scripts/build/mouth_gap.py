"""Where is the remaining gap of the reverse-engineered mouth (phase A4)?
Switch off each kind of sharing in turn, starting from the A4 solution:
  shared  : A4 as is (one anatomy, one position per sound)
  own pose: each instance its own mouth position (anatomy still shared)
  own all : each instance its own position AND its own tube shape map + larynx cavity"""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
os.environ.update(CHMIN="0.005", F1GUARD="1")
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts/build")); sys.argv = sys.argv[:1]
import mouth_inverse as M
from scipy.optimize import least_squares
Z = np.array(json.loads((ROOT / "models/mouth_inverse_A4.json").read_text())["z"])


def fit(args):
    i, mode = args; t = M.T[i]; s = t["lab"]
    free = list(range(M.PO[s].start, M.PO[s].stop)) + list(range(M.PU[i].start, M.PU[i].stop))
    if mode == "all":
        free += list(range(M.SH["shape"].start, M.SH["shape"].stop)) + list(range(2, 6))
    def res(x):
        z = Z.copy(); z[free] = x
        lv, ph, a = M.tones(z, t)
        r = [np.maximum(lv[1:], M.FLOOR) - np.maximum(t["level"][1:], M.FLOOR)]
        w = np.clip((t["coh"][1:] - 0.7) / 0.3, 0, 1); r.append(3.0 * w * np.angle(np.exp(1j * (ph[1:] - t["phase"][1:]))))
        if s not in M.CLOSED:
            r.append([3000 * max(0, 0.005 - a[4:].min())])
            _, L, fr, po, _ = M.sound_model(z, s); ff = np.arange(120.0, 1200.0, 5.0)
            f1 = ff[int(np.argmax(np.abs(M.X.tube_H(a, L, ff) / (1j * 2 * np.pi * ff))))]
            r.append([40.0 * max(0.0, 290.0 - f1) / 290.0])
        return np.concatenate([np.atleast_1d(q) for q in r])
    x0 = np.clip(Z[free], M.LO[free] + 1e-6, M.HI[free] - 1e-6)
    r = least_squares(res, x0, bounds=(M.LO[free], M.HI[free]), method="trf", max_nfev=400, diff_step=1e-3)
    z = Z.copy(); z[free] = r.x; lv, ph, a = M.tones(z, t)
    el = np.maximum(lv[1:], M.FLOOR) - np.maximum(t["level"][1:], M.FLOOR)
    return i, mode, float(np.sqrt(np.mean(el ** 2))), el.tolist()


if __name__ == "__main__":
    base = []
    for t in M.T:
        lv, ph, a = M.tones(Z, t); el = np.maximum(lv[1:], M.FLOOR) - np.maximum(t["level"][1:], M.FLOOR); base.append(float(np.sqrt(np.mean(el ** 2))))
    with Pool(4) as p:
        res = p.map(fit, [(i, m) for m in ("pose", "all") for i in range(len(M.T))])
    R = {(i, m): (e, el) for i, m, e, el in res}
    print(f"{'sound':14} {'shared':>7} {'own pose':>9} {'own all':>8}")
    for i, t in enumerate(M.T):
        print(f"{t['lab']:3} {t['f0']:4.0f} Hz      {base[i]:7.1f} {R[(i, 'pose')][0]:9.1f} {R[(i, 'all')][0]:8.1f}")
    rms = lambda v: float(np.sqrt(np.mean(np.square(v))))
    print(f"{'overall':14} {rms(base):7.2f} {rms([R[(i, 'pose')][0] for i in range(len(M.T))]):9.2f} {rms([R[(i, 'all')][0] for i in range(len(M.T))]):8.2f}")
    # where the 'own all' misses are (what even free shapes can't do)
    print("\nwhat remains with everything free, per tone (model - his, dB):")
    for i, t in enumerate(M.T):
        el = R[(i, "all")][1]; print(f"  {t['lab']:3} {t['f0']:4.0f}: " + " ".join(f"{v:+4.0f}" if abs(v) >= 4 else "   ." for v in el))
    json.dump({f"{i}_{m}": v[0] for (i, m), v in R.items()}, open(ROOT / "models/mouth_gap.json", "w"))
