"""Does his windpipe help? From the best bun solution, for each windpipe length and
coupling strength, refine and compare (a decoupled windpipe can't be found by the
local search, so it is swept)."""
import json, os, sys, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np
os.environ.update(SUB="1", LARV="1", HEAD="1", HEAD_R="2.6", NAT_W="4", PULSE="smooth")
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts/build")); sys.argv = sys.argv[:1]
import ee_bunfit as B
from scipy.optimize import least_squares
W = json.loads((ROOT / "models/ee_bunfit_larv.json").read_text())["per_ee"]


def run(args):
    j, Lt, lzg = args; t = B.T[j]
    z0 = np.r_[W[j]["z"], Lt, 0.28, 1.0, lzg]; lo, hi = B.LO.copy(), B.HI.copy()
    k = len(lo) - 4; lo[k] = hi[k] = Lt; lo[k + 3] = hi[k + 3] = lzg; lo[k] -= 1e-3; hi[k] += 1e-3; lo[k + 3] -= 1e-3; hi[k + 3] += 1e-3
    z0 = np.clip(z0, lo + 1e-6, hi - 1e-6)
    r = least_squares(B.resid, z0, args=(t,), bounds=(lo, hi), method="trf", max_nfev=1500, diff_step=1e-3)
    return j, Lt, lzg, float(np.sqrt(np.mean(r.fun[:B.NH - 1] ** 2))), r.x.tolist()


if __name__ == "__main__":
    jobs = [(j, Lt, lzg) for j in range(4) for Lt in (3.5, 4.5, 5.5, 6.5, 7.5) for lzg in (2.0, 2.4, 2.8, 3.2)]
    with Pool(4) as p:
        res = p.map(run, jobs)
    best = {}
    for j, Lt, lzg, e, z in res:
        if j not in best or e < best[j][2]:
            best[j] = (Lt, lzg, e, z)
    base = [w["err"] for w in W]
    for j in range(4):
        Lt, lzg, e, z = best[j]
        print(f"{B.T[j]['f0']:.0f} Hz: without windpipe {base[j]:.2f} dB -> best with windpipe {e:.2f} dB "
              f"(length {Lt} cm, glottal resistance {10 ** lzg:.0f})")
    print("\nerror by windpipe length (mean of the four ee's, best coupling each):")
    for Lt in (3.5, 4.5, 5.5, 6.5, 7.5):
        print(f"  {Lt} cm: " + " ".join(f"{min(e for jj, L, z_, e, _ in res if jj == j and L == Lt):.2f}" for j in range(4)))
    json.dump({str(j): dict(Lt=best[j][0], log_zg=best[j][1], err=best[j][2], z=best[j][3]) for j in range(4)},
              open(ROOT / "models/ee_subgrid.json", "w"), indent=1)
