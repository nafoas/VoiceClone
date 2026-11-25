"""Roadmap Step 2: his vocal folds that really vibrate (VocalTractLab's self-oscillating triangular glottis,
bun-sized), calibrated ONCE on his three "ee"s and his "n" hum.

Scoring (Da Boss: every sound scored on its own, nothing traded away): each target sound has its own cells
(tones vs his, clean tone (HNR), hum (H1-H2), pitch reached); each cell has a band; the search minimises the
WORST cell's excess first (3x), then the mean. Folds that do not vibrate are rejected.

Searched: the folds' overall size s (lengths x s, masses x s^3, springs x s: natural pitch ~ 1/s), their
thickness, mass, stiffness and damping relative to that, how they rest (lower/upper rest gap, back gap),
lung pressure, breath noise strength, the "ee" shape (his bun controls), the "n" soft-palate opening.

    python scripts/build/vtl_folds2.py [iterations] -> models/vtl_folds2.json
"""
import json
import os
import sys

ARGS = sys.argv[1:]
os.environ.update(SRC="his", MOUTH_V1="1", NH="40", BUNSIZE="0.8")
# one maths thread per process: OpenBLAS's thread pool deadlocks with the forked workers (seen at 60 variables)
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
for p in (".", "scripts", "scripts/build", "scripts/listen", "analysis/physics"):
    sys.path.insert(0, p)
sys.argv = sys.argv[:1]
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

import mouth_inverse as M  # noqa: E402

HUMAN = dict(COL=1.3, LRT=0.24, URT=0.06, LRM=0.12, URM=0.03, LDR=0.1, UDR=0.6, LSK=80000., USK=8000., LCK=240000.,
             UCK=24000., CSK=25000., IL=0.05, OL=0.01, NF0=129., dF0=125.51)
# name, lo, hi, log
SPLIT = os.environ.get("SPLIT", "1") == "1"   # each part of the fold set on its own (the closing snap: brightness)
FP = [("s", 0.25, 0.6, False), ("thick", 0.5, 2.0, True), ("mass", 0.5, 2.0, True), ("stiff", 0.5, 2.0, True),
      ("damp", 0.3, 3.0, True), ("XB", -0.003, 0.006, False), ("XT", -0.003, 0.004, False), ("AA", 0.0, 0.002, False),
      ("PR", 3000.0, 14000.0, False), ("AS", -40.0, -10.0, False), ("nport", 0.01, 0.3, True)]
if SPLIT:
    FP += [("upper_mass", 0.3, 3.0, True), ("upper_spring", 0.3, 3.0, True), ("contact", 0.3, 4.0, True),
           ("upper_contact", 0.3, 4.0, True), ("coupling", 0.3, 3.0, True), ("upper_damp", 0.3, 3.0, True),
           ("upper_thick", 0.5, 2.0, True), ("inlet", 0.3, 3.0, True), ("outlet", 0.3, 3.0, True)]
# His tissue per region (ROADMAP Step 3.1, brought forward): wall mass, damping, stiffness per region, as
# multiples of VocalTractLab's one human value (2.4 g/cm2, 5000 dyn s/cm3, 100000 dyn/cm3). Ranges: human
# tissue measured relaxed..tense (Ishizaka et al. 1975: mass x0.6-0.9, damping x0.16-0.3, stiffness x0.3-3.3)
# widened for a small animal's thinner tissue (less mass per cm2, stiffer and more damped per cm2) and for
# bone under the hard palate (stiff). Plus the slit half-width for air friction (human 0.6 cm; his mouth
# and throat are narrower).
TISSUE = os.environ.get("TISSUE", "0") == "1"
if TISSUE:
    import bun_vtl as _BV
    for _r in _BV.TISSUE_KEYS:
        # stiffness per cm2 = tissue elasticity / thickness: 1-10 kPa-ish soft tissue over 1-3 mm gives x3-x100
        # of VocalTractLab's value (the cap was x30 until the buzz fit pressed against it, 2026-11-25)
        FP += [(f"{_r}_mass", 0.05, 2.0, True), (f"{_r}_damp", 0.1, 5.0, True), (f"{_r}_stiff", 0.2, 100.0, True)]
    FP += [("slit", 0.1, 0.6, False)]
SHAPE = os.environ.get("SHAPE", "0") == "1"   # also search the "ee" shape (off: his "ee" is held, step 1's)
BANDS = dict(tone=4.0, hnr=3.0, h1h2=3.0, f0=0.03)
# Buzz cells (scripts/listen/voice_cells.py; Da Boss 2026-11-25: "a tonal buzz that sounds purely like a
# computer"): the strongest 1-2.5 kHz and 2.5-5 kHz harmonics under the first, and harmonic purity per band.
BUZZ = os.environ.get("BUZZ", "1") == "1"
BUZZ_BANDS = {"mid_buzz": 3.0, "upper": 3.0, "purity_1-2.5k": 4.0, "purity_2.5-5k": 4.0, "purity_5-9k": 4.0}
# his windows for them (the listening file's: each sound's middle)
BUZZ_WIN = {0.73: (0.74, 0.78), 1.52: (1.53, 1.59), 1.77: (1.78, 1.89), 2.09: (2.10, 2.29)}
# Every sound starts the way he starts one: folds at rest, then his breath rising over ONSET_MS (raised cosine).
# (2026-11-24: with breath switched on all at once, the fit found folds pressed shut that only a jolt of air
# could start: they never voiced with a natural rise, even 5 ms.)
ONSET_MS = float(os.environ.get("ONSET_MS", 30.0))
REST_MS = 10.0


def breath(nframes, step_s):
    t = np.arange(nframes) * step_s * 1000.0 - REST_MS
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(t / ONSET_MS, 0, 1))
# His side anatomy (windpipe, nose, sinuses, throat pockets) inside the engine: bun_vtl. HUMAN_SIDE=1 gives the
# old behaviour (VocalTractLab's human side parts, nose branching after section 16), for comparison only.
HUMAN_SIDE = os.environ.get("HUMAN_SIDE", "0") == "1"
_W = {}


def fold_static(q):
    s = q["s"]; d = dict(HUMAN)
    for k in ("COL", "IL", "OL"):
        d[k] = HUMAN[k] * s
    for k in ("LRT", "URT"):
        d[k] = HUMAN[k] * s * q["thick"]
    for k in ("LRM", "URM"):
        d[k] = HUMAN[k] * s ** 3 * q["mass"]
    for k in ("LSK", "USK", "LCK", "UCK", "CSK"):
        d[k] = HUMAN[k] * s * q["stiff"]
    for k in ("LDR", "UDR"):
        d[k] = HUMAN[k] * q["damp"]
    if SPLIT:   # the upper part relative to the lower (mass, spring, thickness, damping), contacts, coupling, inlet/outlet
        d["URM"] *= q["upper_mass"]; d["USK"] *= q["upper_spring"]; d["URT"] *= q["upper_thick"]; d["UDR"] *= q["upper_damp"]
        d["LCK"] *= q["contact"]; d["UCK"] *= q["upper_contact"]; d["CSK"] *= q["coupling"]
        d["IL"] *= q["inlet"]; d["OL"] *= q["outlet"]
    d["NF0"] = HUMAN["NF0"] / s * np.sqrt(q["stiff"] / q["mass"]); d["dF0"] = HUMAN["dF0"] / s * np.sqrt(q["stiff"] / q["mass"])
    return d


def apply_tissue(q):
    if TISSUE and not HUMAN_SIDE:
        import bun_vtl as BV
        BV.set_his_tissue({r: (q[f"{r}_mass"], q[f"{r}_damp"], q[f"{r}_stiff"]) for r in BV.TISSUE_KEYS}, slit=q["slit"])


def pmask():
    m = np.zeros(M.NP, bool); m[M.PO["iː"]] = True; m[M.EX["iː"]] = True; m[M.SC["iː"]] = True
    return m


def setup():
    import vtl_tube as V
    import voice_quality as Q
    M.BUNSIZE[0] = 0.8; M._cache.clear()
    z = M.pad(json.load(open("models/vtl_folds.json"))["z"])   # start: the step-1 "ee" (open, 0.029 cm2)
    if os.environ.get("START_FROM") and "z" in json.load(open(os.environ["START_FROM"])):   # or an earlier result's
        z = M.pad(json.load(open(os.environ["START_FROM"]))["z"])
    x, sr = sf.read("reference/source/prince_reference.wav"); x = x.mean(1)
    tg = []
    for t in M.T:
        if t["lab"] == "iː" or (t["lab"] == "n" and abs(t["t"][0] - 0.73) < 0.01):
            seg = (Q.HIS_EE[[1.52, 1.77, 2.09].index(round(t["t"][0], 2))] if t["lab"] == "iː" else Q.HIS_HUM[1])
            tg.append(dict(t, his_q=Q.measure(x[int(seg[0] * sr): int(seg[1] * sr)], sr)))
            if BUZZ:
                import voice_cells as C
                a, b = BUZZ_WIN[round(t["t"][0], 2)]
                tg[-1]["his_c"] = C.cells(x[int(a * sr): int(b * sr)], sr, tg[-1]["his_q"]["f0"]); tg[-1]["buzz_len"] = b - a
                _W.setdefault("floor", C.recording_floor(x, sr))
                tg[-1]["one_sided"] = C.floor_limited(x, sr, (a, b), _W["floor"])
    an, *_ = M.area_of(z, M.pose_full(z, "n"))
    tip = np.flatnonzero(an[24:] < 0.003) + 24
    _W.update(V=V, Q=Q, z=z, tg=tg, tip=tip if len(tip) else np.arange(33, 37), pid=os.getpid())
    if not HUMAN_SIDE:
        import bun_vtl as BV
        BV.set_his_side(M.BUNSIZE[0], z[6])


def decode(u):
    out = {}
    for (n, lo, hi, lg), q in zip(FP, np.clip(u[: len(FP)], 0, 1)):
        out[n] = float(np.exp(np.log(lo) + q * (np.log(hi) - np.log(lo)))) if lg else lo + q * (hi - lo)
    return out


def tube_frames(z, lab, nport):
    V = _W["V"]
    a, L, frac, port = M.area_of(z, M.pose_full(z, "iː"))
    vel = 0.0
    if lab == "n":   # his "n" before the "i": tip sealed at the ridge, soft palate open, tongue body as for the "i"
        a = a.copy(); a[_W["tip"]] = 1e-6; vel = nport
    art = np.full(40, V.OTHER); art[12:38] = V.TONGUE; art[38] = V.INCISORS; art[39] = V.LOWER_LIP
    if HUMAN_SIDE:
        return dict(lengths=np.full(40, L / 40), areas=a, artic=art, incisor=L - 0.48, velum=vel)
    import bun_vtl as BV
    return BV.frame(a, L, frac, art, L - 0.48, vel)


def tones(y, f0, sr, nh=25):
    seg = y[int(0.15 * sr):]; S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1 / sr)
    k = np.arange(1, nh + 1) * f0
    h = np.array([S[(f > q - f0 / 3) & (f < q + f0 / 3)].max() if q < sr / 2 - f0 else 1e-12 for q in k])
    return 20 * np.log10(h / h[0] + 1e-12)


def evaluate(u, detail=False):
    if not _W:
        setup()
    V, Q = _W["V"], _W["Q"]
    q = decode(u)
    z = _W["z"].copy(); m = pmask()
    if len(u) > len(FP):
        z[m] = M.LO[m] + np.clip(u[len(FP):], 0, 1) * (M.HI[m] - M.LO[m])
    path = f"/tmp/claude-0/-home-user-VoiceClone/7e3261ab-22a0-5713-8c0c-f1044b891953/scratchpad/f2_{_W['pid']}.speaker"
    import bun_folds as BF
    BF.make_speaker(fold_static(q), path); V.use_speaker(path)
    apply_tissue(q)
    cells = {}
    F = int(0.45 * V.SR / V.STEP)
    for t in _W["tg"]:
        fr = tube_frames(z, t["lab"], q["nport"])
        g = V.glottis_shape("modal"); g[:6] = [t["f0"], q["PR"], q["XB"], q["XT"], q["AA"], q["AS"]]
        G = np.tile(g, (F, 1)); G[:, 1] *= breath(F, V.STEP / V.SR)
        y = V.synth([fr] * F, G)
        name = f"{t['lab']}@{t['t'][0]:.2f}"
        if not np.isfinite(y).all() or np.abs(y).max() > 10:   # the engine's solver went unstable
            return (1e3, {name: "unstable"}) if detail else 1e3
        seg = y[int(0.15 * V.SR):]
        mq = Q.measure(seg, V.SR)
        if not np.isfinite(mq["f0"]) or np.sqrt(np.mean(seg ** 2)) < 1e-5:
            return (1e3, {name: "does not vibrate"}) if detail else 1e3
        lv = tones(y, mq["f0"], V.SR); his = np.nan_to_num(t["level"][: len(lv)], nan=-58.0)
        cells[name + " tones"] = (float(np.sqrt(np.mean((np.maximum(lv[1:], -58) - np.maximum(his[1:], -58)) ** 2))), BANDS["tone"], 0.0)
        cells[name + " clean tone"] = (mq["hnr"], BANDS["hnr"], t["his_q"]["hnr"])
        cells[name + " hum"] = (mq["h1h2"], BANDS["h1h2"], t["his_q"]["h1h2"])
        cells[name + " pitch"] = (mq["f0"] / t["f0"] - 1, BANDS["f0"], 0.0)
        if BUZZ:
            import voice_cells as C
            w = seg[-int(t["buzz_len"] * V.SR):]   # same length as his window, from the steady part
            mc = C.cells(w, V.SR, mq["f0"])
            for k, band in BUZZ_BANDS.items():
                cells[f"{name} {k}"] = (mc[k], band, t["his_c"][k], 1 if t["one_sided"].get(k) else 0)
    ex = {}
    for k, c in cells.items():
        v, band, target = c[:3]
        if k.endswith("tones"):
            d = v
        elif len(c) > 3 and c[3] > 0:   # his value is floor-limited: only "too impure / too strong" counts
            d = max(0.0, target - v)
        else:
            d = abs(v - target)
        ex[k] = max(0.0, d - band) / band   # in units of its band
    J = 3 * max(ex.values()) + float(np.mean(list(ex.values())))
    if not np.isfinite(J):
        return (1e3, {"score": "not finite"}) if detail else 1e3
    if detail:
        return J, {k: (round(cells[k][0], 3), round(cells[k][2], 3), round(ex[k], 2)) + (("one-sided",) if len(cells[k]) > 3 and cells[k][3] else ()) for k in cells}
    return J


if __name__ == "__main__":
    import cma
    from multiprocessing import Pool
    start = dict(s=0.4, thick=1.0, mass=1.0, stiff=1.0, damp=1.0, XB=0.00495 * 0.4, XT=0.0004 * 0.4, AA=0.0002 * 0.16,
                 PR=8000.0, AS=-30.0, nport=0.08, upper_mass=1.0, upper_spring=1.0, contact=1.0, upper_contact=1.0,
                 coupling=1.0, upper_damp=1.0, upper_thick=1.0, inlet=1.0, outlet=1.0)
    if TISSUE:   # start: VocalTractLab's human tissue and slit
        import bun_vtl as _BV
        for _r in _BV.TISSUE_KEYS:
            start.update({f"{_r}_mass": 1.0, f"{_r}_damp": 1.0, f"{_r}_stiff": 1.0})
        start["slit"] = 0.6
    if os.environ.get("START_FROM"):   # continue from an earlier result's folds
        start.update(json.load(open(os.environ["START_FROM"]))["folds"])
    u0 = []
    for n, lo, hi, lg in FP:
        v = start[n]; u0.append((np.log(v) - np.log(lo)) / (np.log(hi) - np.log(lo)) if lg else (v - lo) / (hi - lo))
    setup(); m = pmask(); z0 = _W["z"]
    u0 = np.r_[np.clip(u0, 0, 1), np.clip((z0[m] - M.LO[m]) / (M.HI[m] - M.LO[m]), 0, 1)] if SHAPE else np.clip(u0, 0, 1)
    J0, d0 = evaluate(u0, detail=True); print(f"start: J {J0:.2f}", d0, flush=True)
    _W.clear()
    es = cma.CMAEvolutionStrategy(u0, float(os.environ.get("SIGMA", 0.15)), {"bounds": [0, 1], "popsize": 16, "maxiter": int(ARGS[0]) if ARGS else 40, "verbose": -9, "seed": 11})
    best = (J0, u0)
    with Pool(4, maxtasksperchild=6) as pool:   # (fresh workers often: the library leaks on speaker reloads)
        while not es.stop():
            U = es.ask(); Js = pool.map(evaluate, U); es.tell(U, Js)
            k = int(np.argmin(Js))
            if Js[k] < best[0]:
                best = (Js[k], np.array(U[k]))
            print(f"iter {es.countiter}: best J {best[0]:.3f}  " + " ".join(f"{n}={v:.4g}" for n, v in decode(best[1]).items()), flush=True)
            np.save(f"out/vtlbun/folds2_best_u{os.environ.get('TAG', '')}.npy", best[1])
    J, det = evaluate(best[1], detail=True)
    q = decode(best[1]); z = _W["z"].copy(); m = pmask()
    if SHAPE:
        z[m] = M.LO[m] + np.clip(best[1][len(FP):], 0, 1) * (M.HI[m] - M.LO[m])
    json.dump(dict(J=J, cells=det, folds=q, static=fold_static(q), z=z.tolist()), open(f"models/vtl_folds2{os.environ.get('TAG', '')}.json", "w"), indent=1)
    print("final", J, json.dumps(det, ensure_ascii=False))
