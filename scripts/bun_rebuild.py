"""Rebuild the gold-standard clip with ONLY his little mouth (and one voice box).

Analysis by synthesis: for every 5 ms frame of the clip, find the mouth pose
(jaw, tongue, tip, root, lips, rounding, velum, larynx) whose sound matches
his, with the mouth only allowed to move smoothly.

The voice box (one for the whole clip):
  * a fixed source spectrum for his voiced sound, plus his HUM: harmonics 1-2
    strong, a cliff above them that follows his pitch (counted in harmonics)
  * one source spectrum for breath / frication noise
  * per frame, the voice box's own controls: loudness and brightness (spectral
    tilt above 500 Hz: a pressed vs relaxed voice), plus pitch and how voiced
    the frame is, taken from the clip

Every resonance, anti-resonance and movement is made by the mouth.

Search: a codebook of random mouth poses -> the best few per frame -> the
smoothest good path through them (Viterbi) -> local refinement.

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
TILT = np.maximum(0.0, np.log2(FQ / 500.0))        # brightness basis (per octave above 500 Hz)
LAMBDA = 2.5                                       # smoothness: dB of fit traded per unit of movement
N_CODE, TOPK = 4000, 50
HUM = dict(depth=25.0, start=1.5, end=3.2)         # his hum cliff (bnuysynth defaults, validated on gold)


def analyse(x):
    x = np.ascontiguousarray(x, np.float64)
    f0, t = pw.harvest(x, SR, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(x, f0, t, SR); ap = pw.d4c(x, f0, t, SR)
    return f0, t, sp, ap


def on_grid(sp):
    hz = np.linspace(0, SR / 2, sp.shape[1])
    return np.stack([np.interp(FQ, hz, 10 * np.log10(r + 1e-20)) for r in sp])


def hum_db(f0, fq=FQ):
    f0 = np.maximum(np.atleast_1d(f0), 60.0)
    x = np.clip((fq[None, :] / f0[:, None] - HUM["start"]) / (HUM["end"] - HUM["start"]), 0, 1)
    return -HUM["depth"] * x * x * (3 - 2 * x)


def model_db(m, pose, voiced, fq=FQ):
    if voiced:
        H = m.response(pose, fq, radiate=True)
    else:
        i, _ = m.constriction(pose)
        H = m.response(pose, fq, radiate=True, source_at=i)
    return 20 * np.log10(np.abs(H) + 1e-12)


def fit_gain_tilt(R):
    """Weighted least squares of residual(s) R (..., F) on [1, TILT]: the voice
    box's loudness and brightness. Returns (gain, tilt, rms error)."""
    X = np.stack([np.ones_like(FQ), TILT], 1); Wd = WF[:, None] * X
    beta = np.linalg.solve(X.T @ Wd, (R * WF) @ X)            # (..., 2)
    beta[..., 1] = np.clip(beta[..., 1], -18.0, 6.0)
    fit = beta @ X.T
    err = np.sqrt(np.average((R - fit) ** 2, weights=WF, axis=-1))
    return beta[..., 0], beta[..., 1], err


def codebook(m, seed=0):
    rng = np.random.default_rng(seed)
    Z = LO + (HI - LO) * rng.random((N_CODE, len(LO)))
    Z[:, NAMES.index("velum")] *= rng.random(N_CODE) < 0.35      # most poses: velum sealed
    Z[rng.random(N_CODE) < 0.15, NAMES.index("lips")] = 0.0       # some lip closures
    Z[rng.random(N_CODE) < 0.15, NAMES.index("tip")] = 1.0        # some tip closures
    Mv = np.stack([model_db(m, Pose.from_vec(z), True) for z in Z])
    Mn = np.stack([model_db(m, Pose.from_vec(z), False) for z in Z])
    return Z, Mv, Mn


def frame_targets(T, f0, voiced, S_v, S_n):
    """What the mouth must make in each frame: his spectrum minus the voice box."""
    hum = hum_db(np.where(voiced, f0, 300.0))
    return np.where(voiced[:, None], T - S_v - hum, T - S_n)


def viterbi(costs, Zc):
    """costs (n, K) fit error, Zc (n, K, P) candidate poses -> smoothest good path."""
    n, K = costs.shape
    acc = costs[0].copy(); back = np.zeros((n, K), int)
    for k in range(1, n):
        d = np.linalg.norm(Zc[k][:, None, :] - Zc[k - 1][None, :, :], axis=2)   # (K, K)
        tot = acc[None, :] + LAMBDA * d
        back[k] = np.argmin(tot, 1); acc = tot[np.arange(K), back[k]] + costs[k]
    path = np.zeros(n, int); path[-1] = int(np.argmin(acc))
    for k in range(n - 1, 0, -1):
        path[k - 1] = back[k, path[k]]
    return Zc[np.arange(n), path]


def fit_track(m, Tm, voiced, code, Z_prev=None, fev=120):
    Zcode, Mv, Mn = code
    n = len(Tm); Zc = np.zeros((n, TOPK, len(NAMES))); costs = np.zeros((n, TOPK))
    for k in range(n):
        M = Mv if voiced[k] else Mn
        _, _, err = fit_gain_tilt(Tm[k][None, :] - M)
        top = np.argsort(err)[:TOPK]
        Zc[k], costs[k] = Zcode[top], err[top]
        if Z_prev is not None:                       # keep last pass's answer in the running
            Zc[k, -1] = Z_prev[k]
            costs[k, -1] = fit_gain_tilt(Tm[k] - model_db(m, Pose.from_vec(Z_prev[k]), voiced[k]))[2]
    Z = viterbi(costs, Zc)
    # local refinement, staying near the neighbours on the path
    for k in range(n):
        nb = [Z[j] for j in (k - 1, k + 1) if 0 <= j < n]

        def cost(z):
            z = np.clip(z, LO, HI)
            e = fit_gain_tilt(Tm[k] - model_db(m, Pose.from_vec(z), voiced[k]))[2]
            return e + 0.5 * LAMBDA * sum(np.linalg.norm(z - q) for q in nb)
        r = minimize(cost, Z[k], method="Powell", options=dict(maxfev=fev, xtol=2e-3, ftol=1e-3))
        Z[k] = np.clip(r.x, LO, HI)
    return Z


def residuals(m, T, Z, voiced, f0, S_v, S_n):
    """Per frame: mouth model, voice-box gain and tilt, and what's left over."""
    G, Tl, E, R = [], [], [], []
    for k in range(len(Z)):
        md = model_db(m, Pose.from_vec(Z[k]), voiced[k])
        src = (S_v + hum_db(f0[k])[0]) if voiced[k] else S_n
        g, tl, e = fit_gain_tilt(T[k] - src - md)
        G.append(g); Tl.append(tl); E.append(e); R.append(T[k] - md - g - tl * TILT - (hum_db(f0[k])[0] if voiced[k] else 0))
    return np.array(G), np.array(Tl), np.array(E), np.array(R)


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--size", type=float, default=1.55)
    ap_.add_argument("--passes", type=int, default=3)
    a = ap_.parse_args()
    m = BunMouth(a.size)
    ref = I.reference()
    t0 = time.time(); code = codebook(m); print(f"codebook {N_CODE} poses ({time.time() - t0:.0f}s)", flush=True)
    data = []
    for s, e in SPANS:
        x = ref[int(s * SR): int(e * SR)]
        f0, t, sp, ap = analyse(x)
        en = 10 * np.log10(sp.sum(1) + 1e-20)
        data.append(dict(s=s, f0=f0, sp=sp, ap=ap, T=on_grid(sp), en=en, voiced=f0 > 0, act=en > en.max() - 30))
    S_v = np.zeros(len(FQ)); S_n = np.zeros(len(FQ)); Zs = [None] * len(data)
    for ps in range(a.passes):
        t0 = time.time()
        for i, d in enumerate(data):
            Tm = frame_targets(d["T"], d["f0"], d["voiced"], S_v, S_n)
            Zs[i] = fit_track(m, Tm, d["voiced"], code, Zs[i])
        # re-estimate the voice box from what the mouth leaves over
        Rv, Rn, errs = [], [], []
        for i, d in enumerate(data):
            G, Tl, E, R = residuals(m, d["T"], Zs[i], d["voiced"], d["f0"], S_v, S_n)
            Rv.append(R[d["voiced"] & d["act"]]); Rn.append(R[~d["voiced"] & d["act"]]); errs.append(E[d["en"] > d["en"].max() - 40])
        S_v = uniform_filter1d(np.median(np.vstack(Rv), 0), 5, mode="nearest"); S_v -= S_v.max()
        if sum(len(r) for r in Rn):
            S_n = uniform_filter1d(np.median(np.vstack(Rn), 0), 9, mode="nearest"); S_n -= S_n.max()
        print(f"pass {ps + 1}: mean fit error {np.mean(np.concatenate(errs)):.2f} dB  ({time.time() - t0:.0f}s)", flush=True)
    # synthesize: mouth spectra x voice box; pitch, loudness, brightness, voicing from the clip
    out = ROOT / "out" / "bunmouth"; out.mkdir(parents=True, exist_ok=True)
    phrases, extra = [], {}
    for i, d in enumerate(data):
        Z = uniform_filter1d(Zs[i], 3, axis=0)        # physical smoothness (~15 ms)
        G, Tl, E, _ = residuals(m, d["T"], Z, d["voiced"], d["f0"], S_v, S_n)
        Tl = uniform_filter1d(Tl, 5)
        nb = d["sp"].shape[1]; hz = np.linspace(0, SR / 2, nb)
        sp = np.zeros((len(Z), nb))
        for k in range(len(Z)):
            v = d["voiced"][k]
            db = (S_v + hum_db(d["f0"][k])[0] if v else S_n) + model_db(m, Pose.from_vec(Z[k]), v) + G[k] + Tl[k] * TILT
            sp[k] = 10 ** (np.interp(hz, FQ, db, left=db[0], right=db[-1] - 20) / 10)
        y = pw.synthesize(d["f0"], np.ascontiguousarray(sp), np.ascontiguousarray(d["ap"]), SR, 5.0)
        phrases.append((y, d["s"])); Zs[i] = Z; extra[f"tilt{i}"] = Tl; extra[f"gain{i}"] = G
    sc = I.score(phrases, ref)
    print(I.row("bun mouth only", sc))
    print("gold v9: LSD 3.4  LSDshape 3.0  flux 3.42  p95 7.13   H2..H4 -10 -30 -48 (clip -12 -32 -46)")
    pause = np.zeros(int(0.34 * SR))
    y = np.concatenate([phrases[0][0], pause, phrases[1][0]])
    sf.write(out / "rebuild.wav", y / np.abs(y).max() * 0.8, SR)
    np.savez(ROOT / "models/bun_trajectory.npz", size=a.size, names=NAMES, S_v=S_v, S_n=S_n, fq=FQ,
             Z0=Zs[0], Z1=Zs[1], v0=data[0]["voiced"], v1=data[1]["voiced"], t0=SPANS[0][0], t1=SPANS[1][0], **extra)
    print(out / "rebuild.wav")


if __name__ == "__main__":
    main()
