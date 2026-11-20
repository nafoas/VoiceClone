"""Global search (CMA-ES) for one or more sounds' positions in the fitted mouth, everything else held.

A local fit cannot jump between qualitatively different mouth shapes (e.g. from a tongue-tip contact to
a bunched, rounded "r"); this searches the sound's whole control range against the same steady-sound
judge as mouth_inverse (his tones, his resonances, the physical constraints).

    GEST=1 FMT3=1 ... python sound_search.py IN.json OUT.json "ɹ" [sigma] [iters]
  sound items as in mouth_inverse FREE: a sound (its whole position), "m*" (only m's own gesture), "nose"
"""
import json
import os
import sys

ARGS = sys.argv[1:]
sys.argv = sys.argv[:1]
import cma  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import mouth_inverse as M  # noqa: E402

_j = json.load(open(ARGS[0])); zin = M.pad(_j["z"]); M.body(zin)
if "rest" in _j:
    M.REST[: len(_j["rest"])] = _j["rest"]
REST = "rest" in ARGS[2].split(",")   # also search his rest posture (its free controls)
mask = np.zeros(M.NP, bool)
for it in ARGS[2].split(","):
    if it == "rest":
        continue
    if it == "nose":
        mask[[6, 7, M.NV]] = True
    elif it.endswith("*"):
        mask[[M.PO[it[:-1]].start + c for c in M.OWN[it[:-1]]]] = True
    else:
        mask[M.PO[it]] = True; mask[M.EX[it]] = True; mask[M.SC[it]] = True
sig = float(ARGS[3]) if len(ARGS) > 3 else 0.3
iters = int(ARGS[4]) if len(ARGS) > 4 else 120
lo, hi = M.LO[mask], M.HI[mask]
if REST:
    lo = np.r_[lo, [0.0, -1.0, 0.0, -1.0]]; hi = np.r_[hi, [0.6, 1.0, 1.0, 1.0]]
    zr0 = np.clip(M.REST[M.REST_FREE], lo[-4:], hi[-4:])
x0 = (np.clip(np.r_[zin[mask], zr0] if REST else zin[mask], lo, hi) - lo) / (hi - lo)   # search in 0..1 per setting
nm = int(mask.sum())


def setx(u):
    v = lo + np.clip(u, 0, 1) * (hi - lo); z = zin.copy(); z[mask] = v[:nm]
    if REST:
        M.REST[M.REST_FREE] = v[nm:]
    return z


def cost(u):
    return float(np.sum(M.resid(setx(u)) ** 2))


c0 = cost(x0)
print(f"searching {mask.sum()} settings ({ARGS[2]}); start cost {c0:.0f}", flush=True)
es = cma.CMAEvolutionStrategy(x0, sig, {"bounds": [0, 1], "popsize": 20, "maxiter": iters, "verbose": -9, "seed": 3})
best = (c0, x0)
while not es.stop():
    U = es.ask(); C = [cost(u) for u in U]; es.tell(U, C)
    k = int(np.argmin(C))
    if C[k] < best[0]:
        best = (C[k], np.array(U[k]))
    if es.countiter % 20 == 0:
        print(f"  iter {es.countiter}: best {best[0]:.0f}", flush=True)
z = setx(best[1])
print(f"done: cost {c0:.0f} -> {best[0]:.0f}", flush=True)
json.dump(dict(z=z.tolist(), sounds=M.SOUNDS, rest=M.REST[:9].tolist()), open(ARGS[1], "w"))
