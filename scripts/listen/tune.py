"""Tune his mouth by what a listener hears (perc.py): CMA-ES over one group of his mouth's settings at a
time, starting from the saved best state; every improvement is saved (state + audio + log).

    python tune.py STAGE [max_evals]      (stages: cons, nasal, r, voicebox, glides, vowels)
State: models/perc_state.json = {"z": [...], "tp": {phrase: [[c,w,lips,velum],...]}, "cp": {...}}
"""
import json
import os
import sys
import time
from pathlib import Path

import cma
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
STAGE = sys.argv[1]; MAXE = int(sys.argv[2]) if len(sys.argv) > 2 else 200
import perc as P  # noqa: E402
import transitions as TRm  # noqa: E402

M = P.M; CN = P.CN; ROOT = P.ROOT
STATE = ROOT / os.environ.get("PERC_STATE", "out/listen/perc_state.json"); LOG = ROOT / "out/listen/tune_log.txt"
_SAVED = ROOT / ("models/perc_state.json" if "PERC_STATE" not in os.environ else os.environ["PERC_STATE"])
_src = max([q for q in (STATE, _SAVED) if q.exists()], key=lambda q: q.stat().st_mtime, default=None)
if _src is not None:
    st = json.loads(_src.read_text())
else:
    st = dict(z=P.R.Z.tolist(), tp={k: v["par"] for k, v in json.loads((ROOT / "models/transitions_F14.json").read_text()).items()},
              cp=dict(CN.CP), best=None)
z0 = np.array(st["z"]); tp0 = {k: [list(r) for r in v] for k, v in st["tp"].items()}; cp0 = dict(st["cp"])
names = "jaw body front tip root lips round velum larynx".split()


def pose(s, n):
    return ("z", M.PO[s].start + names.index(n), M.LO[M.PO[s].start + names.index(n)], M.HI[M.PO[s].start + names.index(n)])


def ex(s, j):
    return ("z", M.EX[s].start + j, M.LO[M.EX[s].start + j], M.HI[M.EX[s].start + j])


def zi(i):
    return ("z", i, M.LO[i], M.HI[i])


STAGES = {
    "cons": [("cp", "s_place", .65, .99), ("cp", "s_area", .003, .08), ("cp", "s_lips", .3, 1.5),
             ("cp", "t_place", .65, .99), ("cp", "t_area", .003, .08), ("cp", "t_lips", .3, 1.5), ("cp", "t_burst", .003, .04),
             ("cp", "p_area", .02, .6), ("cp", "p_lips", .2, 1.5), ("cp", "p_burst", 0.0, .02)],
    "nasal": [pose("m", n) for n in ("velum", "tip", "body", "front", "root", "larynx")] + [ex("m", 0), ex("m", 1)]
             + [pose("n", n) for n in ("velum", "tip", "body", "front", "root")] + [ex("n", 0), ex("n", 1)]
             + [pose("ũ", n) for n in ("velum", "lips", "round", "body", "front")] + [zi(6), zi(7), zi(M.NV)],
    "r": [pose("ɹ", n) for n in ("jaw", "body", "front", "tip", "root", "lips", "round")]
         + [pose("ɐ˞", n) for n in ("jaw", "body", "front", "tip", "root", "lips", "round")] + [ex("ɹ", 0), ex("ɐ˞", 0)],
    "voicebox": [zi(0), zi(2), zi(3), zi(4), zi(5), zi(M.NG), zi(1)],
    "throat": [pose(s, "root") for s in M.SOUNDS] + [ex(s, 0) for s in M.SOUNDS] + [pose(s, "larynx") for s in M.SOUNDS],
    "vowels": [pose(s, n) for s in ("ã", "iː", "i") for n in ("jaw", "body", "front", "lips", "round")] + [ex("iː", 2), ex("i", 2)],
    "glides": [("tp", k, b, j, lo, hi) for k, v in tp0.items() for b in range(len(v))
               for j, (lo, hi) in enumerate([(-0.03, 0.03), (0.008, 0.08), (-0.03, 0.03), (-0.04, 0.04)])],
}
SPEC = STAGES[STAGE]


def get(spec, z, tp, cp):
    if spec[0] == "z":
        return z[spec[1]]
    if spec[0] == "cp":
        return cp[spec[1]]
    return tp[spec[1]][spec[2]][spec[3]]


def apply(u):
    z = z0.copy(); tp = {k: [list(r) for r in v] for k, v in tp0.items()}; cp = dict(cp0)
    for ui, spec in zip(u, SPEC):
        lo, hi = spec[-2], spec[-1]; v = lo + (hi - lo) * float(np.clip(ui, 0, 1))
        if spec[0] == "z":
            z[spec[1]] = v
        elif spec[0] == "cp":
            cp[spec[1]] = v
        else:
            tp[spec[1]][spec[2]][spec[3]] = v
    return z, tp, cp


def evaluate(z, tp, cp):
    CN.CP.update(cp); TRm.Z[:] = z
    y, sp = P.render(z, tp)
    o = P.judge(y, sp)
    return P.objective(o), o, y


def norm(spec, v):
    lo, hi = spec[-2], spec[-1]; return float(np.clip((v - lo) / (hi - lo), 0, 1))


u0 = [norm(s, get(s, z0, tp0, cp0)) for s in SPEC]
f0, o0, _ = evaluate(z0, tp0, cp0)
best = dict(f=f0, o=o0)
with open(LOG, "a") as fh:
    fh.write(f"\n=== [{STATE.name}] stage {STAGE} start {time.strftime('%H:%M')} objective {f0:.3f} diction {o0['diction']:.3f} age {o0['age']:.1f} "
             f"speaker {o0['speaker']:.3f} spec {o0['spec']:.2f}\n")
es = cma.CMAEvolutionStrategy(u0, 0.12, {"bounds": [0, 1], "maxfevals": MAXE, "verbose": -9, "seed": int(time.time()) % 10000})
n = 0
while not es.stop():
    U = es.ask(); F = []
    for u in U:
        z, tp, cp = apply(u); f, o, y = evaluate(z, tp, cp); F.append(f); n += 1
        if f < best["f"] - 1e-4:
            best = dict(f=f, o=o)
            st = dict(z=z.tolist(), tp=tp, cp=cp, best=dict(f=f, **{k: o[k] for k in ("diction", "age", "child", "speaker", "spec")}))
            STATE.write_text(json.dumps(st)); sf.write(STATE.with_suffix(".wav"), y / np.abs(y).max() * 0.7, P.SR)
            with open(LOG, "a") as fh:
                fh.write(f"  [{STAGE} {n}] objective {f:.3f} diction {o['diction']:.3f} age {o['age']:.1f} child {o['child']:.2f} "
                         f"speaker {o['speaker']:.3f} spec {o['spec']:.2f}\n")
    es.tell(U, F)
with open(LOG, "a") as fh:
    fh.write(f"=== stage {STAGE} done {time.strftime('%H:%M')} after {n} evals; best objective {best['f']:.3f}\n")
print("done", STAGE, best["f"])
