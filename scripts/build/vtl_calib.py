"""Calibrate (once) his vocal folds inside VocalTractLab, with his bun mouth's tube on top.

His folds: one setting for him (not per utterance): their size (rest thickness, rest length, chink length:
bun.speaker static parameters) and how he holds them (lung pressure, rest positions, gap, phase lag,
amplitude, pulse skew, breathiness). Judged on the tones of his three "ee"s (at their own pitches): the
same yardstick his mouth was fitted with (mouth_inverse tone error). The "ee" tube is checkpoint 8's.

    python scripts/build/vtl_calib.py [iterations] -> models/vtl_folds.json
"""
import json
import os
import re
import sys

ARGS = sys.argv[1:]
os.environ.update(SRC="his", MOUTH_V1="1", NH="40", BUNSIZE="0.8")
for p in (".", "scripts", "scripts/build", "analysis/physics"):
    sys.path.insert(0, p)
sys.argv = sys.argv[:1]
import numpy as np  # noqa: E402

import mouth_inverse as M  # noqa: E402

SPK = open("models/bun.speaker").read()
# name, lo, hi
SP = [("RT", 0.1, 0.6), ("RL", 0.25, 1.0), ("CL", 0.05, 0.3),
      ("PR", 4000.0, 14000.0), ("XB", -0.01, 0.03), ("XT", -0.01, 0.03), ("CA", 0.0, 0.03),
      ("PL", 0.4, 2.0), ("RA", 0.3, 1.0), ("PS", -0.3, 0.3), ("AS", -40.0, -5.0)]
GI = dict(F0=0, PR=1, XB=2, XT=3, CA=4, PL=5, RA=6, DP=7, PS=8, FL=9, AS=10)
_W = {}


POSE = os.environ.get("POSE", "0") == "1"   # also search the "ee" shape (his bun mouth's controls) inside VocalTractLab


def decode(u):
    return {n: lo + float(np.clip(q, 0, 1)) * (hi - lo) for (n, lo, hi), q in zip(SP, u)}


def pose_mask():
    msk = np.zeros(M.NP, bool); msk[M.PO["iː"]] = True; msk[M.EX["iː"]] = True; msk[M.SC["iː"]] = True
    return msk


def speaker_text(p):
    s = SPK
    for n in ("RT", "RL", "CL"):
        m = re.search(rf'<param index="\d+" name="{n}"[^/]*/>', s)   # the geometric glottis' static params (first match)
        s = s.replace(m.group(0), re.sub(r'neutral="[^"]*"', f'neutral="{p[n]:.6f}"', m.group(0)), 1)
    return s


def setup():
    import vtl_tube as V
    st = json.load(open("models/perc_state_overnight8.json")); z = M.pad(st["z"]); M.BUNSIZE[0] = 0.8; M._cache.clear(); M.body(z)
    if os.path.exists("models/vtl_folds.json") and json.load(open("models/vtl_folds.json")).get("z"):
        z = M.pad(json.load(open("models/vtl_folds.json"))["z"])
    tg = [t for t in M.T if t["lab"] == "iː"]
    _W.update(V=V, z=z, tg=tg, pid=os.getpid())
    set_pose(z)


def set_pose(z):
    V = _W["V"]
    a, L, frac, port = M.area_of(z, M.pose_full(z, "iː"))
    art = np.full(40, V.OTHER); art[12:38] = V.TONGUE; art[38] = V.INCISORS; art[39] = V.LOWER_LIP
    _W["fr"] = dict(lengths=np.full(40, L / 40), areas=a, artic=art, incisor=L - 0.48, velum=0.0)
    return a


def tones(y, f0, sr, nh=25):
    seg = y[int(0.15 * sr):]; S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1 / sr)
    k = np.arange(1, nh + 1) * f0
    h = np.array([S[(f > q - f0 / 3) & (f < q + f0 / 3)].max() if q < sr / 2 - f0 else 1e-12 for q in k])
    return 20 * np.log10(h / h[0] + 1e-12)


FIXED = json.loads(os.environ["FIXSTATIC"]) if os.environ.get("FIXSTATIC") else None   # fold size already settled


def run(p, f0, dur=0.3):
    V = _W["V"]
    if FIXED is None or not _W.get("loaded"):   # (reloading the speaker every try leaks memory in the library)
        q = dict(p); q.update(FIXED or {})
        path = f"/tmp/claude-0/-home-user-VoiceClone/7e3261ab-22a0-5713-8c0c-f1044b891953/scratchpad/bun_{_W['pid']}.speaker"
        open(path, "w").write(speaker_text(q)); V.use_speaker(path); _W["loaded"] = True
    import vocaltractlab_cython as cy
    g = np.array(cy.get_shape("modal", "glottis"), float)
    g[GI["F0"]] = f0; g[GI["DP"]] = 0.0; g[GI["FL"]] = 0.0
    for n in ("PR", "XB", "XT", "CA", "PL", "RA", "PS", "AS"):
        g[GI[n]] = p[n]
    F = int(dur * V.SR / V.STEP)
    return V.synth([_W["fr"]] * F, np.tile(g, (F, 1))), V.SR


def cost(u):
    if not _W:
        setup()
    pen = 0.0
    if POSE:
        msk = pose_mask(); z = _W["z"].copy(); n = msk.sum()
        z[msk] = M.LO[msk] + np.clip(u[len(SP):], 0, 1) * (M.HI[msk] - M.LO[msk])
        a = set_pose(z); u = u[: len(SP)]
        pen = 10.0 * max(0.0, np.log(0.008 / max(a[20:].min(), 1e-6)))   # an open vowel: no contact
    p = decode(u); err = []
    for t in _W["tg"]:
        try:
            y, sr = run(p, t["f0"])
        except Exception:
            return 1e6
        if not np.isfinite(y).all() or np.abs(y).max() < 1e-6:
            return 1e6
        lv = tones(y, t["f0"], sr)
        his = np.nan_to_num(t["level"][: len(lv)], nan=-58.0)
        e = np.maximum(lv[1:], -58) - np.maximum(his[1:], -58)
        err.append(np.sqrt(np.mean(e ** 2)))
    return float(np.sqrt(np.mean(np.square(err)))) + pen


if __name__ == "__main__":
    import cma
    from multiprocessing import Pool
    start = dict(RT=0.25, RL=0.5, CL=0.15, PR=8000.0, XB=0.002, XT=0.004, CA=0.0, PL=1.22, RA=1.0, PS=0.0, AS=-10.0)
    if os.path.exists("models/vtl_folds.json"):
        start.update(json.load(open("models/vtl_folds.json"))["folds"])
    if os.environ.get("START"):
        start.update(json.loads(os.environ["START"]))
    u0 = np.array([(start[n] - lo) / (hi - lo) for n, lo, hi in SP])
    if POSE:
        setup(); msk = pose_mask(); z0 = _W["z"]
        u0 = np.r_[u0, np.clip((z0[msk] - M.LO[msk]) / (M.HI[msk] - M.LO[msk]), 0, 1)]
        _W.clear()
    es = cma.CMAEvolutionStrategy(u0, 0.2, {"bounds": [0, 1], "popsize": 16, "maxiter": int(ARGS[0]) if ARGS else 25, "verbose": -9, "seed": 7})
    best = (1e9, None); best_u = u0
    with Pool(4) as pool:
        c0 = pool.map(cost, [u0])[0]
        print(f"start: tone error {c0:.2f} dB", flush=True)
        while not es.stop():
            U = es.ask(); Cs = pool.map(cost, U); es.tell(U, Cs)
            k = int(np.argmin(Cs))
            if Cs[k] < best[0]:
                best = (Cs[k], decode(U[k][: len(SP)])); best_u = np.array(U[k])
            print(f"iter {es.countiter}: best tone error {best[0]:.2f} dB  " + " ".join(f"{n}={v:.4g}" for n, v in best[1].items()), flush=True)
            if POSE and es.countiter % 5 == 0:   # keep the best shape so far
                np.save("out/vtlbun/best_u.npy", best_u)
    out = dict(error_db=best[0], folds=dict(best[1], **(FIXED or {})))
    if POSE:
        setup(); msk = pose_mask(); z = _W["z"].copy()
        z[msk] = M.LO[msk] + np.clip(best_u[len(SP):], 0, 1) * (M.HI[msk] - M.LO[msk]); out["z"] = z.tolist()
    json.dump(out, open("models/vtl_folds.json", "w"), indent=1)
