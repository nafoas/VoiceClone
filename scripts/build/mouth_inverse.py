"""Reverse-engineer the one mouth that made "nannarmunis... peet teet tee".

Phase A: every voiced sound in the clip at its steady middle, fitted at once.
  shared (his anatomy): larynx depth, head radius, laryngeal cavity (4), nasal
      passage (length, damping), and a smooth SHAPE MAP of his tube (8 terms:
      where it is wider/narrower than a normal bun's; a small cost per unit)
  per sound (his movements): one mouth position per sound (jaw, tongue body /
      front / tip / root, lips, rounding, velum, larynx height), shared by every
      instance of that sound
  per instance (his voice): the vocal-fold puff (open share, rise, roundness,
      closing smoothness, easing shut)
  physics: vowels and r keep the mouth open (>= 0.02 cm^2); m and n close the
      mouth but must open the nose (sound has to get out)
Judged on every tone (2..20, above his noise floor) and the timing of his steady
low tones, of every voiced sound.

    python scripts/build/mouth_inverse.py -> models/mouth_inverse.json, analysis/physics/mouth_inverse.png
"""
import json, os, sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import idct
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/build"))
sys.path.insert(0, str(ROOT / "analysis/physics")); sys.argv = sys.argv[:1]
os.environ.setdefault("PULSE", "smooth")
import ee_decompose as DC  # noqa: E402
import ee_exact as X  # noqa: E402
import ee_bunfit as B  # noqa: E402   (head_baffle, tube_H_nose)
from build_catalogue import PHRASES  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402

NH = 20; FLOOR = -58.0; NS = 40; NF = 8
VOICED = ["n", "ã", "ɐ˞", "ɹ", "m", "ũ", "iː"]
#           jaw        body      front     tip       root      lips       round     velum     larynx
BOUNDS = {
    "iː": [(0, .45), (.3, 1), (.4, 1), (0, .35), (-1, 1), (.3, 1), (0, 1), (0, .3), (0, 1)],
    "ã":  [(.3, 1), (-1, 1), (0, 1), (0, .3), (-1, 1), (.4, 1), (0, .6), (0, 1), (0, 1)],
    "ɐ˞": [(.2, 1), (-1, 1), (0, 1), (0, .8), (-1, 1), (.3, 1), (0, .6), (0, .3), (0, 1)],
    "ɹ":  [(0, 1), (-1, 1), (0, 1), (.2, .9), (-1, 1), (.25, 1), (0, 1), (0, .3), (0, 1)],
    "ũ":  [(0, .6), (.3, 1), (0, .6), (0, .3), (-1, 1), (.05, .7), (.3, 1), (0, 1), (0, 1)],
    "n":  [(0, .6), (-1, 1), (0, 1), (.92, 1), (-1, 1), (.25, 1), (0, 1), (.3, 1), (0, 1)],
    "m":  [(0, .6), (-1, 1), (0, 1), (0, .5), (-1, 1), (0, .03), (0, 1), (.3, 1), (0, 1)],
}
START = {
    "iː": [.2, .6, .6, .05, .8, .9, .3, 0, .8], "ã": [.9, .4, .2, .05, -.6, 1, .1, .3, .3],
    "ɐ˞": [.8, .5, .3, .5, -.5, .6, .1, .05, .5], "ɹ": [.4, .6, .5, .6, 0, .6, .2, .05, .5],
    "ũ": [.15, .75, .1, .05, .5, .2, .9, .2, .5], "n": [.2, .4, .6, 1.0, 0, .5, .2, .6, .5],
    "m": [.2, .4, .5, .05, 0, .0, .3, .6, .5],
}
CLOSED = {"n", "m"}


def targets():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    out = []
    for ph in PHRASES:
        for lab, s, e, _ in ph:
            if lab not in VOICED:
                continue
            d = DC.decompose(x[int((s - 0.015) * sr): int((e + 0.015) * sr)], sr, f"inv{int(s * 1000)}")
            A = d["A"]; ok = ~np.isnan(A[:, 0])
            if ok.sum() < 4:
                continue
            n = ok.sum(); mid = slice(n // 5, n - n // 5 or None)
            dB = 20 * np.log10(A[ok][mid] + 1e-12); dB -= dB[:, :1]
            z = np.nanmean(np.exp(1j * d["rel"][ok][mid]), 0)
            out.append(dict(lab=lab, t=(s, e), f0=float(np.median(d["F0"])), level=np.nanmedian(dB, 0)[:NH],
                            phase=np.angle(z)[:NH], coh=np.abs(z)[:NH]))
    return out


T = targets()
SOUNDS = [s for s in VOICED if any(t["lab"] == s for t in T)]
NI = len(T)
# parameter layout
SH = dict(neck=0, head=1, lar=slice(2, 6), nlen=6, ndamp=7, shape=slice(8, 8 + NF))
NSH = 8 + NF
PO = {s: slice(NSH + 9 * i, NSH + 9 * i + 9) for i, s in enumerate(SOUNDS)}
PU0 = NSH + 9 * len(SOUNDS)
SHARED_SRC = os.environ.get("SRC", "") == "shared"
GK = np.geomspace(100, 10000, 14)                     # knots of his one voice's spectrum (Hz)
if SHARED_SRC:
    PU = [None] * NI; GS = slice(PU0, PU0 + len(GK)); NP = PU0 + len(GK)
else:
    PU = [slice(PU0 + 5 * i, PU0 + 5 * i + 5) for i in range(NI)]
    NP = PU0 + 5 * NI
LO = np.zeros(NP); HI = np.zeros(NP); Z0 = np.zeros(NP)
LO[0], HI[0], Z0[0] = 15, 45, 28
LO[1], HI[1], Z0[1] = 2.0, 4.0, 2.6
LO[2:6], HI[2:6], Z0[2:6] = [4, .5, 2, .08], [11, 1.5, 6, .35], [9, 1.0, 4, .15]
LO[6], HI[6], Z0[6] = .7, 1.4, 1.0
LO[7], HI[7], Z0[7] = .05, .5, .15
LO[SH["shape"]], HI[SH["shape"]] = -2.5, 2.5
for s in SOUNDS:
    b = np.array(BOUNDS[s]); LO[PO[s]], HI[PO[s]] = b[:, 0], b[:, 1]; Z0[PO[s]] = np.clip(START[s], b[:, 0], b[:, 1])
if SHARED_SRC:
    LO[GS], HI[GS] = -90.0, 20.0
    nv = ROOT / "models/neutral_voice.npz"
    if nv.exists():   # start from the shared shape recovered from the clip
        d = np.load(nv); Z0[GS] = np.interp(np.log(GK), np.log(np.maximum(d["fq"], 1)), d["G"])
else:
    for p in PU:
        LO[p], HI[p], Z0[p] = [.3, .3, .3, 0, 0], [.97, .95, 4, 1.5, 1], [.8, .5, 1.0, .2, .5]
_cache = {}


def tube(pose9, neck, lar):
    key = (tuple(np.round(pose9, 3)), round(float(neck), 1), tuple(np.round(lar, 2)))
    if key not in _cache:
        v = Pose().vec(); v[:9] = pose9
        m = BunMouth(0.75, neck_mm=float(neck), larcav=tuple(float(q) for q in lar))
        ar, ln, port, br = m.tube(Pose.from_vec(v))
        edges = np.r_[0, np.cumsum(ln)]; L = edges[-1]; e40 = np.linspace(0, L, NS + 1); a40 = np.empty(NS)
        for i in range(NS):
            ov = np.clip(np.minimum(edges[1:], e40[i + 1]) - np.maximum(edges[:-1], e40[i]), 0, None)
            a40[i] = np.sum(ov * ar) / max(ov.sum(), 1e-9)
        if len(_cache) > 50000:
            _cache.clear()
        _cache[key] = (np.maximum(a40, 1e-4), L, float(np.sum(ln[:br]) / L), max(float(port), 1e-4))
    return _cache[key]


def sound_model(z, s):
    a0, L, frac, port = tube(z[PO[s]], z[0], z[SH["lar"]])
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    return a0 * np.exp(dev), L, frac, port, dev


def tones(z, t):
    a, L, frac, port, _ = sound_model(z, t["lab"]); k = np.arange(1, NH + 1) * t["f0"]
    H = B.tube_H_nose(a, L, k, frac, port, z[6], z[7]) * B.head_baffle(k, z[1])
    if SHARED_SRC:   # his one voice: the same spectrum for every sound (phase from a simple pulse)
        gdb = np.interp(np.log(k), np.log(GK), z[GS])
        Zc = 10 ** (gdb / 20) * np.exp(1j * np.angle(X.puff_C(t["f0"], (0.8, 0.55, 1.0, 0.2, 0.4)))) * H
    else:
        q = tuple(z[PU[T.index(t)]])
        Zc = X.puff_C(t["f0"], q) * H
    lv = 20 * np.log10(np.abs(Zc) + 1e-15); lv -= lv[0]
    ph = np.angle(np.exp(1j * (np.angle(Zc) - np.arange(1, NH + 1) * np.angle(Zc[0]))))
    return lv, ph, a


def resid(z):
    r = []
    for t in T:
        lv, ph, a = tones(z, t)
        r.append(np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR))
        w = np.clip((t["coh"][1:] - 0.7) / 0.3, 0, 1)
        r.append(3.0 * w * np.angle(np.exp(1j * (ph[1:] - t["phase"][1:]))))
        if t["lab"] not in CLOSED:   # an open mouth, physically
            chmin = float(os.environ.get("CHMIN", "0.02"))
            r.append([3000 * max(0, chmin - a[4:].min())])
            if os.environ.get("F1GUARD", "") == "1":
                # acoustically open: the first resonance must stay clear of the sealed-tube
                # wall resonance (~200 Hz); a sealed mouth collapses onto it
                _, L, frac, port, _ = sound_model(z, t["lab"])
                ff = np.arange(120.0, 1200.0, 5.0)
                Hd = np.abs(X.tube_H(a, L, ff) / (1j * 2 * np.pi * ff))
                f1 = ff[int(np.argmax(Hd))]
                r.append([40.0 * max(0.0, 290.0 - f1) / 290.0])
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    r.append(1.0 * dev[::4] / 0.15)     # departures from a normal bun cost a little (preference, not a wall)
    if SHARED_SRC:   # his voice's spectrum is smooth
        r.append(0.5 * np.diff(z[GS], 2))
    return np.concatenate([np.atleast_1d(x) for x in r])


def report(z, tag=""):
    print(f"\n=== his mouth {tag} ===")
    print(f"larynx {z[0] * 0.075:.2f} cm lower; head radius {z[1]:.2f} cm; laryngeal cavity {z[2] * .75:.1f} mm x{z[3]:.2f}, "
          f"inlet {z[4] * .75:.1f} mm x{z[5]:.2f}; nose length x{z[6]:.2f}, damping {z[7]:.2f}")
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    print("shape map (x normal bun width, vocal folds -> lips): " + " ".join(f"{np.exp(v):.2f}" for v in dev[::4]))
    names = ["jaw", "body", "front", "tip", "root", "lips", "round", "velum", "larynx"]
    for s in SOUNDS:
        print(f"  {s:3} " + " ".join(f"{n}={v:.2f}" for n, v in zip(names, z[PO[s]])))
    errs = {}
    for t in T:
        lv, ph, a = tones(z, t); el = np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)
        e = float(np.sqrt(np.mean(el ** 2))); errs.setdefault(t["lab"], []).append(e)
        _, L_, fr_, po_, _ = sound_model(z, t["lab"]); ff = np.arange(120.0, 1200.0, 5.0)
        f1 = ff[int(np.argmax(np.abs(X.tube_H(a, L_, ff) / (1j * 2 * np.pi * ff))))]
        print(f"  {t['lab']:3} {t['t'][0]:.2f}s {t['f0']:.0f} Hz: tone error {e:4.1f} dB; narrowest {a[4:].min():.3f} cm2; first resonance {f1:.0f} Hz")
    allv = [v for vs in errs.values() for v in vs]
    print(f"overall: {np.sqrt(np.mean(np.square(allv))):.2f} dB rms over {len(allv)} sounds")
    return errs


def run_start(k):
    rng = np.random.default_rng(100 + k)
    z0 = Z0.copy()
    if k:
        z0 = np.clip(z0 + rng.normal(0, 0.12, NP) * (HI - LO), LO, HI)
        for s in SOUNDS:   # varied but sensible starting mouths
            z0[PO[s]] = np.clip(np.array(START[s]) + rng.normal(0, 0.15, 9), LO[PO[s]], HI[PO[s]])
    z0 = np.clip(z0, LO + 1e-6, HI - 1e-6)
    r = least_squares(resid, z0, bounds=(LO, HI), method="trf", max_nfev=int(os.environ.get("NFEV", "60")), diff_step=1e-3)
    return k, float(np.sum(r.fun ** 2)), r.x.tolist()


def main():
    print(f"{NI} voiced sounds, {len(SOUNDS)} distinct; {NP} unknowns, fitted at once", flush=True)
    rng = np.random.default_rng(0); best = None
    if os.environ.get("WARM"):   # continue from an earlier solution
        zw = np.array(json.loads((ROOT / os.environ["WARM"]).read_text())["z"])
        if SHARED_SRC and len(zw) != NP:   # from a per-sound-puff solution: keep anatomy + positions, start the voice from the clip
            zw = np.r_[zw[:PU0], Z0[GS]]
        zw = np.clip(zw, LO + 1e-6, HI - 1e-6)
        r = least_squares(resid, zw, bounds=(LO, HI), method="trf", max_nfev=int(os.environ.get("NFEV", "60")), diff_step=1e-3)
        best = (float(np.sum(r.fun ** 2)), r.x); print(f"  continued: cost {best[0]:.0f}", flush=True)
    from multiprocessing import Pool
    ks = list(range(int(os.environ.get("NSTART", "3"))))
    if ks:
        with Pool(4) as pool:
            for k, cost, x in pool.map(run_start, ks):
                print(f"  start {k}: cost {cost:.0f}", flush=True)
                if best is None or cost < best[0]:
                    best = (cost, np.array(x))
    z = best[1]; errs = report(z, "(phase A)")
    (ROOT / f"models/mouth_inverse{os.environ.get('TAG', '')}.json").write_text(json.dumps(dict(
        z=z.tolist(), sounds=SOUNDS, targets=[dict(lab=t["lab"], t=t["t"], f0=t["f0"]) for t in T],
        errors=errs), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
