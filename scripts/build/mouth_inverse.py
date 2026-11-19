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

NH = int(os.environ.get("NH", "20")); FLOOR = -58.0; NS = 40; NF = 8
HUMW = float(os.environ.get("HUMW", "1"))   # weight on his 2nd and 3rd tones vs the 1st (the hum)
VOICED = ["n", "ã", "ɐ˞", "ɹ", "m", "ũ", "iː"]
# The "i" ending "munis" (0.79 s, unstressed) is not the stressed "ee" of "peet teet tee": it wants
# a clearly lower first resonance (his hum there), the ee's do not. SPLIT_I=1 gives it its own position.
SPLIT_I = os.environ.get("SPLIT_I", "1") == "1"
if SPLIT_I:
    VOICED.append("i")
    for _ph in PHRASES:
        for _j, _q in enumerate(_ph):
            if _q[0] == "iː" and abs(_q[1] - 0.79) < 0.005:
                _ph[_j] = ("i",) + tuple(_q[1:])
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
BOUNDS["i"] = BOUNDS["iː"]
START = {
    "iː": [.2, .6, .6, .05, .8, .9, .3, 0, .8], "ã": [.9, .4, .2, .05, -.6, 1, .1, .3, .3],
    "ɐ˞": [.8, .5, .3, .5, -.5, .6, .1, .05, .5], "ɹ": [.4, .6, .5, .6, 0, .6, .2, .05, .5],
    "ũ": [.15, .75, .1, .05, .5, .2, .9, .2, .5], "n": [.2, .4, .6, 1.0, 0, .5, .2, .6, .5],
    "m": [.2, .4, .5, .05, 0, .0, .3, .6, .5],
}
START["i"] = START["iː"]
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
SHARED_SRC = os.environ.get("SRC", "") in ("shared", "shared2")
HIS_SRC = os.environ.get("SRC", "") == "his"
KC = int(os.environ.get("KC", "6"))   # per-sound smooth shape terms (Da Boss approved); 0 = none     # his real voice, recovered from the clip (PLAN step 1), held fixed


CYC_AVG = int(os.environ.get("CYC_AVG", "3"))   # Da Boss approved: each cycle averaged with its neighbours


def his_cycles(d, i, L=1024):
    """Bank sound i's cycles, each at a common length, each averaged with its CYC_AVG-1 nearest
    neighbours: recovery error changes from cycle to cycle and averages away; his own changes are
    slower and stay. 3 matches the clarity of his upper tones in the clip (2-5 kHz 16.7 dB vs 18.9;
    5-9 kHz 4.7 vs 7.1; as recovered 13.6 / 0.2)."""
    C = np.array([np.interp(np.linspace(0, 1, L, endpoint=False), np.linspace(0, 1, len(c), endpoint=False), c)
                  for c in np.split(d[f"cyc_{i}"], np.cumsum(d[f"len_{i}"])[:-1])])
    h = CYC_AVG // 2
    return [C[max(0, j - h): j + h + 1].mean(0) for j in range(len(C))]


def bank_pools(d, tol=0.05):
    """His recovered sounds grouped by pitch: sounds within 5% of each other's pitch are one
    pool (at one pitch his voice box makes one sound; what differs between them is each vowel's
    mouth left over from the recovery, which pooling averages out). POOL=0: one per sound."""
    idx = [i for i, cl in enumerate(d["clean"]) if cl]
    if os.environ.get("POOL", "1") != "1":
        return [(float(d["f0"][i]), [i]) for i in idx]
    pools = []
    for i in sorted(idx, key=lambda i: d["f0"][i]):
        if pools and d["f0"][i] / pools[-1][1][0] - 1 < tol:
            pools[-1][1].append(float(d["f0"][i])); pools[-1][0].append(i)
        else:
            pools.append(([i], [float(d["f0"][i])]))
    return [(float(np.mean(f)), sorted(ii)) for ii, f in pools]


def his_voice_bank_tones(path=ROOT / "models/his_voice.npz", nh=NH):
    """Per pool (his cycles at that pitch): (pitch, tones). The render draws each sound's
    cycles from the pool nearest in pitch; the fit uses the same."""
    d = np.load(path)
    return [(f0, his_voice_tones(path, nh, only=ii)) for f0, ii in bank_pools(d)]


def his_voice_tones(path=ROOT / "models/his_voice.npz", nh=NH, only=None):
    """His average cycle's tones, by harmonic number (cycles keep their shape at any pitch):
    each clean cycle's tones normalised to its 1st (level and timing), then averaged."""
    d = np.load(path); acc = []
    for i, cl in enumerate(d["clean"]):
        if not cl or (only is not None and i not in np.atleast_1d(only)):
            continue
        for c in his_cycles(d, i):
            C = np.fft.rfft(c)[1: nh + 1]
            k = np.arange(1, nh + 1); acc.append(C / np.abs(C[0]) * np.exp(-1j * k * np.angle(C[0])))
    acc = np.array(acc)
    # strength and timing averaged separately (averaging the waves lets out-of-step cycles cancel)
    lev = np.median(20 * np.log10(np.abs(acc) + 1e-12), 0)
    return 10 ** (lev / 20) * np.exp(1j * np.angle(np.mean(acc / (np.abs(acc) + 1e-15), 0)))


def seal(a, lab):
    """m: the lips meet (sound leaves by the nose only)."""
    if lab == "m":
        a = a.copy(); a[-2:] = 1e-4
    return a
SRC2 = os.environ.get("SRC", "") == "shared2"            # + his vocal cords' puff shape (per harmonic number)
GK = np.geomspace(100, 10000, 14)                     # knots of his one voice's spectrum (Hz)
if SHARED_SRC:
    PU = [None] * NI; GS = slice(PU0, PU0 + len(GK)); NP = PU0 + len(GK)
    if SRC2:
        GH = slice(NP, NP + NH - 1); NP = NP + NH - 1
elif os.environ.get("SRC", "") == "puff":   # his one pair of vocal cords: one puff shape for every sound
    PU = [slice(PU0, PU0 + 5)] * NI
    NP = PU0 + 5
elif HIS_SRC:
    PU = [None] * NI; HISC = his_voice_tones(); HISB = his_voice_bank_tones(); NV = PU0; NG = PU0 + 1; NX = PU0 + 2   # + nose turbinate surface, cord-gap opening
    EX = {s_: slice(NX + 3 * i_, NX + 3 * i_ + 3) for i_, s_ in enumerate(SOUNDS)}   # + 3 anatomical controls per sound
    NC0 = NX + 3 * len(SOUNDS)
    SC = {s_: slice(NC0 + KC * i_, NC0 + KC * i_ + KC) for i_, s_ in enumerate(SOUNDS)}   # + KC smooth shape terms per sound
    NP = NC0 + KC * len(SOUNDS)
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
    if SRC2:
        LO[GH], HI[GH], Z0[GH] = -30.0, 30.0, 0.0
if HIS_SRC:
    LO[NV], HI[NV], Z0[NV] = 1.0, 25.0, 16.0   # turbinate channels: wall loss x1 (smooth tube) .. x25
    LO[NG], HI[NG], Z0[NG] = -3.5, -1.0, -2.7  # log10 mean cord-gap opening, cm^2 (0.0003 .. 0.1)
    for s_ in SOUNDS:   # log factors: throat width, soft palate into the passage, lip spread (0 = none)
        LO[EX[s_]], HI[EX[s_]], Z0[EX[s_]] = [-1.6, -1.6, -0.7], [1.0, 0.3, 1.0], 0.0
        LO[SC[s_]], HI[SC[s_]], Z0[SC[s_]] = -2.5, 2.5, 0.0
elif not SHARED_SRC:
    for p in PU:
        LO[p], HI[p], Z0[p] = [.3, .3, .3, 0, 0], [.97, .95, 4, 1.5, 1], [.8, .5, 1.0, .2, .5]
_cache = {}


def pad(z):
    """An older solution, extended with the newer body settings at their starting values."""
    z = np.asarray(z, float)
    if SPLIT_I and len(z) in (NX - 9, NX - 10) and len(z) > PU0 - 9:   # older layout: the "i" starts as the ee
        z = np.r_[z[: PU0 - 9], z[PO["iː"]], z[PU0 - 9:]]
    return np.r_[z[:NP], Z0[len(z):NP]] if len(z) < NP else z[:NP] if HIS_SRC else z


def body(z):
    """His fixed body settings that live in the tube model (nose lining, cord gap)."""
    if HIS_SRC:
        B.NOSE_SURF = float(z[NV]) if len(z) > NV else 1.0
        B.GLOTTIS_AG = float(10 ** z[NG]) if len(z) > NG else 0.0


def tube(pose9, neck, lar):
    # fine rounding: a coarse key erased the fit's small test steps, freezing the larynx depth and cavity
    key = (tuple(np.round(pose9, 6)), round(float(neck), 6), tuple(np.round(lar, 6)))
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


_x = (np.arange(NS) + 0.5) / NS


def _win(a, b, e=0.05):
    return np.clip((_x - a + e) / (2 * e), 0, 1) * np.clip((b + e - _x) / (2 * e), 0, 1)


# Where each anatomical control acts along his tube (vocal folds = 0, lips = 1):
#  soft palate: his long soft palate lowered into the passage behind the tongue (palatoglossus;
#               a rabbit's palate rests low, sealing the mouth from the airway)
#  throat:      pharyngeal constrictors narrow it, the hyoid lowering widens it
#  lip spread:  the lips drawn wide (levator labii, zygomaticus), as for "ee"
EXW = [_win(0.12, 0.45), _win(0.45, 0.62), _win(0.88, 1.0)]
EXNAMES = ["throat", "soft palate", "lip spread"]


def pose_full(z, s):
    """A sound's whole position: the 9 bun controls + the 3 anatomical controls."""
    ex = z[EX[s]] if HIS_SRC and len(z) >= NC0 else np.zeros(3)
    sc = z[SC[s]] if HIS_SRC and KC and len(z) >= NP else np.zeros(KC)
    return np.r_[z[PO[s]], ex, sc]


def area_of(z, p):
    """His tube for a position p (9 or 12 controls): anatomy, shape map, then the anatomical controls."""
    a0, L, frac, port = tube(p[:9], z[0], z[SH["lar"]])
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    a = a0 * np.exp(dev)
    if len(p) > 9:
        a = a * np.exp(sum(v * w for v, w in zip(p[9:12], EXW)))
    if len(p) > 12 and np.any(p[12:]):   # the sound's own smooth shape (a few slow bends along the tube)
        a = a * np.exp(idct(np.r_[p[12:], np.zeros(NS - len(p[12:]))], norm="ortho"))
    return a, L, frac, port


def sound_model(z, s):
    a, L, frac, port = area_of(z, pose_full(z, s))
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    return seal(a, s), L, frac, port, dev


def tones(z, t):
    body(z)
    a, L, frac, port, _ = sound_model(z, t["lab"]); k = np.arange(1, NH + 1) * t["f0"]
    H = B.tube_H_nose(a, L, k, frac, port, z[6], z[7]) * B.head_baffle(k, z[1])
    if HIS_SRC:      # his real voice (tones and their timing), the same for every sound
        Zc = (min(HISB, key=lambda b: abs(np.log(b[0] / t["f0"])))[1] if os.environ.get("VOICE", "bank") == "bank" else HISC) * H
    elif SHARED_SRC:   # his one voice: the same spectrum for every sound (phase from a simple pulse)
        gdb = np.interp(np.log(k), np.log(GK), z[GS])
        if SRC2:
            gdb = gdb + np.r_[0.0, z[GH]]
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
        wl = np.ones(NH - 1); wl[:2] = HUMW
        r.append(wl * (np.maximum(lv[1:], FLOOR) - np.maximum(np.nan_to_num(t["level"][1:], nan=FLOOR), FLOOR)))
        w = np.clip((np.nan_to_num(t["coh"][1:]) - 0.7) / 0.3, 0, 1)
        r.append(3.0 * w * np.angle(np.exp(1j * (ph[1:] - np.nan_to_num(t["phase"][1:])))))
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
    if RESPW > 0:   # his measured mouth response (from the voice recovery), at every frequency, 1/3-octave smooth
        for t in T:
            rt = RESP.get((t["lab"], round(t["t"][0], 3)))
            if rt is None:
                continue
            a, L, frac, port, _ = sound_model(z, t["lab"])
            Hm = 20 * np.log10(np.abs(B.tube_H_nose(a, L, RF, frac, port, z[6], z[7]) * B.head_baffle(RF, z[1])) + 1e-12)
            Hm = np.convolve(Hm, RK, mode="same")[RSEL]; d = (Hm - Hm.mean()) - rt
            r.append(RESPW * d / np.sqrt(len(d)) * np.sqrt(NH))
    if HIS_SRC and len(z) >= NC0:   # each anatomical control costs a little: used only where it earns it
        r.append(0.3 * z[NX:NC0])
    if HIS_SRC and KC and len(z) >= NP:   # the free shape terms cost more (no named muscle)
        r.append(0.5 * z[NC0:NP])
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    r.append(1.0 * dev[::4] / 0.15)     # departures from a normal bun cost a little (preference, not a wall)
    if SHARED_SRC:   # his voice's spectrum is smooth
        r.append(0.5 * np.diff(z[GS], 2))
    if SRC2:         # the puff shape may dip, but stays modest
        r.append(0.15 * z[GH])
    return np.concatenate([np.atleast_1d(x) for x in r])


RESPW = float(os.environ.get("RESPW", "0"))
RESP = {}
if RESPW > 0:
    _rd = json.loads((ROOT / "models/his_mouth_response.json").read_text())
    RF = np.array(_rd["f"]); RK = np.ones(13) / 13; RSEL = slice(8, -8, 3)   # ~1/3 octave smoothing
    for _s in _rd["sounds"]:
        _T = np.convolve(np.array(_s["T"]), RK, mode="same")[RSEL]; RESP[(_s["lab"], round(_s["s"], 3))] = _T - _T.mean()


def report(z, tag=""):
    print(f"\n=== his mouth {tag} ===")
    if HIS_SRC and len(z) >= NC0:
        print("anatomical controls (x width): " + "; ".join(f"{s_} " + ", ".join(f"{n} {np.exp(v):.2f}" for n, v in zip(EXNAMES, z[EX[s_]])) for s_ in SOUNDS))
    print((f"nose turbinate surface x{z[NV]:.1f}; " if HIS_SRC and len(z) > NV else "") + f"larynx {z[0] * 0.075:.2f} cm lower; head radius {z[1]:.2f} cm; laryngeal cavity {z[2] * .75:.1f} mm x{z[3]:.2f}, "
          f"inlet {z[4] * .75:.1f} mm x{z[5]:.2f}; nose length x{z[6]:.2f}, damping {z[7]:.2f}")
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    print("shape map (x normal bun width, vocal folds -> lips): " + " ".join(f"{np.exp(v):.2f}" for v in dev[::4]))
    names = ["jaw", "body", "front", "tip", "root", "lips", "round", "velum", "larynx"]
    for s in SOUNDS:
        print(f"  {s:3} " + " ".join(f"{n}={v:.2f}" for n, v in zip(names, z[PO[s]])))
    errs = {}
    for t in T:
        lv, ph, a = tones(z, t); el = np.maximum(lv[1:], FLOOR) - np.maximum(np.nan_to_num(t["level"][1:], nan=FLOOR), FLOOR)
        e = float(np.sqrt(np.mean(el ** 2))); errs.setdefault(t["lab"], []).append(e)
        _, L_, fr_, po_, _ = sound_model(z, t["lab"]); ff = np.arange(120.0, 1200.0, 5.0)
        f1 = ff[int(np.argmax(np.abs(X.tube_H(a, L_, ff) / (1j * 2 * np.pi * ff))))]
        print(f"  {t['lab']:3} {t['t'][0]:.2f}s {t['f0']:.0f} Hz: tone error {e:4.1f} dB; 1st over 2nd {-lv[1]:5.1f} (his {-t['level'][1]:5.1f}); narrowest {a[4:].min():.3f} cm2; first resonance {f1:.0f} Hz")
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
    r = least_squares(resid, z0, bounds=(LO, HI), method="trf", max_nfev=int(os.environ.get("NFEV", "60")), diff_step=1e-3, x_scale="jac", xtol=1e-12, ftol=1e-10)
    return k, float(np.sum(r.fun ** 2)), r.x.tolist()


def main():
    print(f"{NI} voiced sounds, {len(SOUNDS)} distinct; {NP} unknowns, fitted at once", flush=True)
    rng = np.random.default_rng(0); best = None
    if os.environ.get("WARM"):   # continue from an earlier solution
        zw = np.array(json.loads((ROOT / os.environ["WARM"]).read_text())["z"])
        if HIS_SRC:
            zw = pad(zw)
        if os.environ.get("SRC", "") == "puff" and len(zw) != NP:   # anatomy + positions kept; one puff from the median of theirs
            q = np.median(np.array(zw[PU0:]).reshape(-1, 5), 0) if (len(zw) - PU0) % 5 == 0 and len(zw) > PU0 else Z0[PU0:PU0 + 5]
            zw = np.r_[zw[:PU0], q]
        if SHARED_SRC and len(zw) != NP:   # keep anatomy + positions (+ voice if present); new parts start neutral
            if SRC2 and len(zw) == PU0 + len(GK):
                zw = np.r_[zw, Z0[GH]]
            else:
                zw = np.r_[zw[:PU0], Z0[GS]] if not SRC2 else np.r_[zw[:PU0], Z0[GS], Z0[GH]]
        zw = np.clip(zw, LO + 1e-6, HI - 1e-6)
        r = least_squares(resid, zw, bounds=(LO, HI), method="trf", max_nfev=int(os.environ.get("NFEV", "60")), diff_step=1e-3, x_scale="jac", xtol=1e-12, ftol=1e-10)
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
