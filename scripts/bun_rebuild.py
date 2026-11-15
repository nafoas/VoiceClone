"""Rebuild the gold-standard clip with ONLY his little mouth.

Analysis by synthesis: for every 5 ms frame of the clip, find the mouth pose
(jaw, tongue, tip, root, lips, rounding, velum, larynx) whose sound matches
his, with the mouth only allowed to move smoothly. One voice box is shared by
the whole clip: a single source spectrum for his voiced sound (the hum lives
here) and one for breath/frication noise.

What comes from the clip, and nothing else: pitch, loudness per frame and how
voiced vs breathy each frame is (the voice box's controls). Every spectral
shape is made by the mouth.

    python scripts/bun_rebuild.py [--size 1.55] [--passes 3]
        -> out/bunmouth/rebuild.wav, models/bun_trajectory.npz, score
"""
import argparse, sys, time
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "analysis"))
from prince_voice.bunmouth import BunMouth, Pose, LO, HI, NAMES  # noqa: E402
import iterate as I  # noqa: E402

SR = I.SR
SPANS = [(I.T1, 1.16), (I.T2, 2.42)]
FQ = np.geomspace(90, 7500, 140)                   # fitting grid
WF = np.where(FQ < 5000, 1.0, 0.4)                 # trust the clip less up high
SMOOTH = 0.6                                       # pull toward the previous pose (dB per unit)


def analyse(x):
    x = np.ascontiguousarray(x, np.float64)
    f0, t = pw.harvest(x, SR, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(x, f0, t, SR); ap = pw.d4c(x, f0, t, SR)
    return f0, t, sp, ap


def on_grid(sp):
    hz = np.linspace(0, SR / 2, sp.shape[1])
    return np.stack([np.interp(FQ, hz, 10 * np.log10(r + 1e-20)) for r in sp])


def model_db(m, pose, voiced):
    if voiced:
        H = m.response(pose, FQ, radiate=True)
    else:
        i, _ = m.constriction(pose)
        H = m.response(pose, FQ, radiate=True, source_at=i)
    return 20 * np.log10(np.abs(H) + 1e-12)


def frame_cost(m, z, T, S, voiced, prev):
    pose = Pose.from_vec(np.clip(z, LO, HI))
    d = T - S - model_db(m, pose, voiced)
    d = d - np.average(d, weights=WF)              # loudness is the voice box's, not the mouth's
    c = np.sqrt(np.average(d ** 2, weights=WF))
    if prev is not None:
        c += SMOOTH * np.sqrt(np.sum((z - prev) ** 2))
    return c


def fit_track(m, T, voiced, S_v, S_n, init=None, fev=160):
    n = len(T); Z = np.zeros((n, len(NAMES))); err = np.zeros(n)
    prev = None
    for k in range(n):
        S = S_v if voiced[k] else S_n
        starts = [prev] if prev is not None else [Pose().vec(), Pose(jaw=1, body=0.9, front=0, lips=1, root=-1).vec()]
        if init is not None:
            starts = [init[k]] + starts
        best = None
        for z0 in starts:
            r = minimize(lambda z: frame_cost(m, z, T[k], S, voiced[k], prev), z0, method="Powell",
                         options=dict(maxfev=fev, xtol=2e-3, ftol=1e-3))
            if best is None or r.fun < best.fun:
                best = r
        Z[k] = np.clip(best.x, LO, HI); prev = Z[k]
        err[k] = frame_cost(m, Z[k], T[k], S, voiced[k], None)
    return Z, err


def estimate_source(m, T, Z, mask):
    """His voice box: what's left of his spectrum once the mouth is taken out,
    the same for every frame (median), smoothed across ~1/3 octave."""
    R = []
    for k in np.where(mask)[0]:
        d = T[k] - model_db(m, Pose.from_vec(Z[k]), True)
        R.append(d - d.mean())
    S = np.median(np.array(R), 0)
    return uniform_filter1d(S, 7, mode="nearest")


def synth_span(m, Z, voiced, gains, S_v, S_n, f0, ap, nb):
    hz = np.linspace(0, SR / 2, nb)
    sp = np.zeros((len(Z), nb))
    for k in range(len(Z)):
        S = S_v if voiced[k] else S_n
        db = S + model_db(m, Pose.from_vec(Z[k]), voiced[k]) + gains[k]
        sp[k] = 10 ** (np.interp(hz, FQ, db, left=db[0], right=db[-1] - 20) / 10)
    return pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(ap), SR, 5.0)


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--size", type=float, default=1.55)
    ap_.add_argument("--passes", type=int, default=3)
    a = ap_.parse_args()
    m = BunMouth(a.size)
    ref = I.reference()
    data = []
    for s, e in SPANS:
        x = ref[int(s * SR): int(e * SR)]
        f0, t, sp, ap = analyse(x)
        T = on_grid(sp)
        en = 10 * np.log10(sp.sum(1) + 1e-20)
        data.append(dict(s=s, x=x, f0=f0, sp=sp, ap=ap, T=T, en=en, voiced=f0 > 0))
    S_v = np.zeros(len(FQ)); S_n = np.zeros(len(FQ))
    Zs = [None] * len(data)
    for ps in range(a.passes):
        t0 = time.time(); errs = []
        for i, d in enumerate(data):
            Zs[i], err = fit_track(m, d["T"], d["voiced"], S_v, S_n, init=Zs[i])
            act = d["en"] > d["en"].max() - 40
            errs.append(err[act])
        allT = np.vstack([d["T"] for d in data]); allZ = np.vstack(Zs)
        allv = np.concatenate([d["voiced"] for d in data])
        alla = np.concatenate([d["en"] > d["en"].max() - 30 for d in data])
        S_v = estimate_source(m, allT, allZ, allv & alla)
        # noise source: same idea on unvoiced frames, with the frication filter
        R = []
        for k in np.where(~allv & alla)[0]:
            dd = allT[k] - model_db(m, Pose.from_vec(allZ[k]), False); R.append(dd - dd.mean())
        if R:
            S_n = uniform_filter1d(np.median(np.array(R), 0), 9, mode="nearest")
        print(f"pass {ps + 1}: mean fit error {np.mean(np.concatenate(errs)):.2f} dB  ({time.time() - t0:.0f}s)")
    # synthesize: the mouth's spectra; pitch, loudness, voicing from the clip
    out = ROOT / "out" / "bunmouth"; out.mkdir(parents=True, exist_ok=True)
    phrases = []
    for i, d in enumerate(data):
        Z = uniform_filter1d(Zs[i], 3, axis=0)        # physical smoothness (~15 ms)
        gains = []
        for k in range(len(Z)):
            S = S_v if d["voiced"][k] else S_n
            md = S + model_db(m, Pose.from_vec(Z[k]), d["voiced"][k])
            gains.append(np.average(d["T"][k] - md, weights=WF))
        y = synth_span(m, Z, d["voiced"], np.array(gains), S_v, S_n, d["f0"], d["ap"], d["sp"].shape[1])
        phrases.append((y, d["s"])); Zs[i] = Z
    sc = I.score(phrases, ref)
    print(I.row("bun mouth only", sc))
    print("gold v9: LSD 3.4  LSDshape 3.0  flux 3.42  p95 7.13   H2..H4 -10 -30 -48 (clip -12 -32 -46)")
    pause = np.zeros(int(0.34 * SR))
    y = np.concatenate([phrases[0][0], pause, phrases[1][0]])
    sf.write(out / "rebuild.wav", y / np.abs(y).max() * 0.8, SR)
    np.savez(ROOT / "models/bun_trajectory.npz", size=a.size, names=NAMES, S_v=S_v, S_n=S_n, fq=FQ,
             Z0=Zs[0], Z1=Zs[1], v0=data[0]["voiced"], v1=data[1]["voiced"], t0=SPANS[0][0], t1=SPANS[1][0])
    print(out / "rebuild.wav")


if __name__ == "__main__":
    main()
