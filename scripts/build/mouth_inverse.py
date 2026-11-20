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

# MOUTH_V1=1: exactly the mouth Da Boss judged best (listen3c, F14): no movement mapping, the free
# bends on, the lip spread kept. The base that later improvements are added to one at a time.
if os.environ.get("MOUTH_V1", "0") == "1":
    for _k, _v in dict(TOOL="0", KC="6", ARTW="0", LIPSPREAD="1").items():
        os.environ.setdefault(_k, _v)
NH = int(os.environ.get("NH", "20")); FLOOR = -58.0; NS = 40; NF = 8
HUMW = float(os.environ.get("HUMW", "1"))   # weight on his 2nd and 3rd tones vs the 1st (the hum)
VOICED = ["n", "ã", "ɐ˞", "ɹ", "m", "ũ", "iː"]
# The "i" ending "munis" (0.79 s, unstressed) is not the stressed "ee" of "peet teet tee": it wants
# a clearly lower first resonance (his hum there), the ee's do not. SPLIT_I=1 gives it its own position.
SPLIT_I = os.environ.get("SPLIT_I", "1") == "1"
# The final open "tee" (2.09 s, long, phrase-final) is more open (his F1 ~530 Hz) than the "ee" of
# "peet" and "teet" (closed by t, F1 ~400 Hz). SPLIT_E=1 gives it its own position ("iːf").
SPLIT_E = os.environ.get("SPLIT_E", "0") == "1"
if SPLIT_E:
    VOICED.append("iːf")
    for _ph in PHRASES:
        for _j, _q in enumerate(_ph):
            if _q[0] == "iː" and abs(_q[1] - 2.09) < 0.005:
                _ph[_j] = ("iːf",) + tuple(_q[1:])
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
BOUNDS["i"] = BOUNDS["iː"]; BOUNDS["iːf"] = BOUNDS["iː"]
START = {
    "iː": [.2, .6, .6, .05, .8, .9, .3, 0, .8], "ã": [.9, .4, .2, .05, -.6, 1, .1, .3, .3],
    "ɐ˞": [.8, .5, .3, .5, -.5, .6, .1, .05, .5], "ɹ": [.4, .6, .5, .6, 0, .6, .2, .05, .5],
    "ũ": [.15, .75, .1, .05, .5, .2, .9, .2, .5], "n": [.2, .4, .6, 1.0, 0, .5, .2, .6, .5],
    "m": [.2, .4, .5, .05, 0, .0, .3, .6, .5],
}
START["i"] = START["iː"]; START["iːf"] = START["iː"]
CLOSED = {"n", "m"}
# GEST=1 (2026-11-20, Da Boss: "why does it always make L and K sounds"): a consonant is made by ITS
# articulator, and the rest of the mouth is carried by the sounds around it (coarticulation; Ohman 1966,
# articulatory phonology). Before, "m" and "n" were whole fitted shapes: the fit shut "m" with the
# tongue (at 80% of the tube) instead of the lips, and sealed the tongue tip in "ɹ" - the gestures of
# "n" and "l" - because a steady hum barely shows WHERE a mouth is shut. The ear hears that from the
# movement, so it heard "l".
#   m: lips shut + soft palate open (jaw helps the lips); tongue: where the neighbours put it, never sealing
#   n: tongue tip sealed at the ridge + soft palate open (jaw helps the tip); tongue body: from the neighbours
#   open sounds (vowels, ɹ): no contact anywhere in the mouth
GEST = os.environ.get("GEST", "0") == "1"
OWN = {"m": [0, 5, 7], "n": [0, 2, 3, 7]}                  # m: jaw, lips, soft palate; n: jaw, tongue front (backs the tip), tip, soft palate
OPEN_MIN = float(os.environ.get("OPEN_MIN", "0.008"))      # cm^2: narrower than this is contact
GESTW = float(os.environ.get("GESTW", "10"))
# Before a phrase, his mouth is at REST: a rabbit breathes only through its nose, so the lips are shut,
# the soft palate is open to the nose and the tongue fills the mouth. One shared rest posture (jaw, tongue
# body, front, root fitted; tip down, lips shut, palate open): a phrase-initial consonant starts from it.
REST = np.r_[[0.0, 0.8, 0.8, 0.0, 0.0, 0.0, 0.0, 1.0, 0.5], np.zeros(12)]
REST_FREE = [0, 1, 2, 4]
CTX = {}   # (consonant, start) -> (voiced sound just before, voiced sound just after)
for _ph in PHRASES:
    for _j, _q in enumerate(_ph):
        if _q[0] in OWN:
            _l = _ph[_j - 1][0] if _j > 0 and _ph[_j - 1][0] in VOICED and abs(_ph[_j - 1][2] - _q[1]) < 0.003 else None
            _r = _ph[_j + 1][0] if _j + 1 < len(_ph) and _ph[_j + 1][0] in VOICED and abs(_ph[_j + 1][1] - _q[2]) < 0.003 else None
            CTX[(_q[0], round(_q[1], 3))] = ("rest" if _j == 0 else _l, _r)


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
KC = int(os.environ.get("KC", "0"))
# The inversion tool (SPARC, docs/INVERSION_FINDINGS.md) reads his articulators from the clip. Each
# mapped bun control follows its pattern across sounds: control = offset + scale * feature (scale >= 0).
#   control index : feature (from the tool's 12 channels, per sound, mean over the sound)
ART_MAP = {0: "jaw", 1: "tbody_y", 2: "tbody_fwd", 5: "lip_gap", 6: "lip_fwd"}   # tip not mapped: the tool's tip rides with the tongue body
ARTW = float(os.environ.get("ARTW", "8"))
ARTW_LIP = float(os.environ.get("ARTW_LIP", "1"))
# TOOL=1: the mapped controls ARE his measured movements (control = offset + scale x tool reading);
# the fit adapts his mouth (anatomy, conversions) around them instead of overriding them.
TOOL = os.environ.get("TOOL", "1") == "1"
TUNE = float(os.environ.get("TUNE", "0.15"))   # how far each sound may fine-tune around his measured movement
GAPW = float(os.environ.get("GAPW", "60")); GAPMIN = float(os.environ.get("GAPMIN", "0.6"))   # open sounds keep a real gap (mm)   # extra weight on the lips (both tools agree on them)   # per-sound free bends: off (compensations; the inversion tools give real targets)     # his real voice, recovered from the clip (PLAN step 1), held fixed


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
    NM0 = NC0 + KC * len(SOUNDS)
    NLW = NM0 + 2 * len(ART_MAP)   # + per mapped control: offset and scale from the inversion tool's units
    NPAL = NLW + 1                 # + his mouth opening's width (anatomy, shared): a rabbit's mouth is a narrow slit
    NP = NPAL + 1                  # + his palate's arch height (anatomy, shared; mm)
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
        if os.environ.get("LIPSPREAD", "0") != "1":
            LO[EX[s_].start + 2], HI[EX[s_].start + 2] = -1e-4, 1e-4   # no lip spread: both tools say his lips narrow or round, never spread
    LO[NLW], HI[NLW], Z0[NLW] = np.log(0.1), np.log(1.2), 0.0   # log width factor of the lip opening
    LO[NPAL], HI[NPAL], Z0[NPAL] = 0.0, 3.0, 0.0                 # palate arch raised, mm (reference animal)
    if TOOL:   # the mapped controls' stored values are now each sound's small fine-tune around his movement
        for s_ in SOUNDS:
            for ci in ART_MAP:
                k_ = PO[s_].start + ci; LO[k_], HI[k_], Z0[k_] = -max(TUNE, 1e-4), max(TUNE, 1e-4), 0.0
    for j_ in range(len(ART_MAP)):
        LO[NM0 + 2 * j_], HI[NM0 + 2 * j_], Z0[NM0 + 2 * j_] = -6.0, 6.0, 0.0
        LO[NM0 + 2 * j_ + 1], HI[NM0 + 2 * j_ + 1], Z0[NM0 + 2 * j_ + 1] = 0.05, 4.0, 1.0   # how strongly his movement moves the bun control
elif not SHARED_SRC:
    for p in PU:
        LO[p], HI[p], Z0[p] = [.3, .3, .3, 0, 0], [.97, .95, 4, 1.5, 1], [.8, .5, 1.0, .2, .5]
_cache = {}
_rawgap = {}


def raw_gap(pose9, neck, lar, z=None):
    """The narrowest oral gap (mm) before clamping: negative = the tongue pressing into the roof."""
    if z is not None:
        PALATE[0] = float(z[NPAL]) if HIS_SRC and len(z) >= NP else 0.0
    tube(pose9, neck, lar)
    return _rawgap[(tuple(np.round(pose9, 6)), round(float(neck), 6), tuple(np.round(lar, 6)), round(PALATE[0], 6), BUNSIZE[0])]


def pad(z):
    """An older solution, extended with the newer body settings at their starting values."""
    z = np.asarray(z, float)
    if HIS_SRC and SPLIT_E:   # a layout from before the final "tee" had its own position: it starts as the ee
        old = [q for q in SOUNDS if q != "iːf"]; no = len(old)
        if len(z) == NSH + 9 * no + 2 + 3 * no + KC * no:
            po = lambda q: z[NSH + 9 * old.index(q): NSH + 9 * old.index(q) + 9]
            ex = lambda q: z[NSH + 11 * no + 2 + 3 * old.index(q) - 2 * no: NSH + 11 * no + 2 + 3 * old.index(q) - 2 * no + 3]
            nx0 = NSH + 9 * no + 2; sc0 = nx0 + 3 * no
            ex = lambda q: z[nx0 + 3 * old.index(q): nx0 + 3 * old.index(q) + 3]
            sc = lambda q: z[sc0 + KC * old.index(q): sc0 + KC * old.index(q) + KC]
            m = lambda q: "iː" if q == "iːf" else q
            z = np.r_[z[:NSH], np.concatenate([po(m(q)) for q in SOUNDS]), z[NSH + 9 * no: nx0],
                      np.concatenate([ex(m(q)) for q in SOUNDS]), np.concatenate([sc(m(q)) for q in SOUNDS])]
    if HIS_SRC and len(z) == NC0 + 6 * len(SOUNDS) and KC == 0:   # layout with 6 free bends per sound: dropped
        z = z[:NC0]
    if HIS_SRC and len(z) >= NC0 and os.environ.get("LIPSPREAD", "0") != "1":   # lip spread off
        z = z.copy()
        for s_ in SOUNDS:
            z[EX[s_].start + 2] = 0.0
    if SPLIT_I and len(z) in (NX - 9, NX - 10) and len(z) > PU0 - 9:   # older layout: the "i" starts as the ee
        z = np.r_[z[: PU0 - 9], z[PO["iː"]], z[PU0 - 9:]]
    return np.r_[z[:NP], Z0[len(z):NP]] if len(z) < NP else z[:NP] if HIS_SRC else z


def body(z):
    """His fixed body settings that live in the tube model (nose lining, cord gap)."""
    if HIS_SRC:
        B.NOSE_SURF = float(z[NV]) if len(z) > NV else 1.0
        B.GLOTTIS_AG = float(10 ** z[NG]) if len(z) > NG else 0.0


PALATE = [0.0]
BUNSIZE = [float(os.environ.get("BUNSIZE", "0.75"))]   # his size vs the reference rabbit (anatomy; +-15% natural variation)


def tube(pose9, neck, lar):
    # fine rounding: a coarse key erased the fit's small test steps, freezing the larynx depth and cavity
    key = (tuple(np.round(pose9, 6)), round(float(neck), 6), tuple(np.round(lar, 6)), round(PALATE[0], 6), BUNSIZE[0])
    if key not in _cache:
        v = Pose().vec(); v[:9] = pose9
        m = BunMouth(BUNSIZE[0], neck_mm=float(neck), larcav=tuple(float(q) for q in lar), palate_mm=PALATE[0])
        ar, ln, port, br = m.tube(Pose.from_vec(v))
        edges = np.r_[0, np.cumsum(ln)]; L = edges[-1]; e40 = np.linspace(0, L, NS + 1); a40 = np.empty(NS)
        for i in range(NS):
            ov = np.clip(np.minimum(edges[1:], e40[i + 1]) - np.maximum(edges[:-1], e40[i]), 0, None)
            a40[i] = np.sum(ov * ar) / max(ov.sum(), 1e-9)
        if len(_cache) > 50000:
            _cache.clear()
        _cache[key] = (np.maximum(a40, 1e-4), L, float(np.sum(ln[:br]) / L), max(float(port), 1e-4))
        _rawgap[key] = float(np.min(m._raw_gap))
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
LIPW = _win(0.965, 1.0, 0.02)


def tool_pose(z, p9, feats):
    """The mapped controls set from his measured movements through the fitted conversions."""
    p9 = np.array(p9, float)
    if TOOL and HIS_SRC and len(z) >= NP and feats is not None:
        for j_, (ci, fn) in enumerate(ART_MAP.items()):   # S-shaped: near the ends, never past them (his order kept)
            lo_, hi_ = CRANGE[ci]
            base = lo_ + (hi_ - lo_) / (1 + np.exp(-(z[NM0 + 2 * j_] + z[NM0 + 2 * j_ + 1] * feats[fn])))
            # + a small per-sound fine-tune around his movement (the stored pose value; costed, +-TUNE)
            p9[ci] = float(np.clip(base + (p9[ci] if TUNE > 0 else 0.0), lo_, hi_))
    return p9


CRANGE = {0: (0.0, 1.0), 1: (-1.0, 1.0), 2: (0.0, 1.0), 5: (0.0, 1.0), 6: (0.0, 1.0)}


def pose_full(z, s):
    """A sound's whole position: the 9 bun controls (the mapped ones from his measured movements)
    + the 3 anatomical controls."""
    ex = z[EX[s]] if HIS_SRC and len(z) >= NC0 else np.zeros(3)
    sc = z[SC[s]] if HIS_SRC and KC and len(z) >= NP else np.zeros(KC)
    return np.r_[tool_pose(z, z[PO[s]], SPF.get(s)), ex, sc]


def area_of(z, p):
    """His tube for a position p (9 or 12 controls): anatomy, shape map, then the anatomical controls."""
    PALATE[0] = float(z[NPAL]) if HIS_SRC and len(z) >= NP else 0.0
    a0, L, frac, port = tube(p[:9], z[0], z[SH["lar"]])
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    a = a0 * np.exp(dev)
    if len(p) > 9:
        a = a * np.exp(sum(v * w for v, w in zip(p[9:12], EXW)))
    if HIS_SRC and len(z) >= NP:   # his mouth opening's width (anatomy): the last ~3 mm of the tube
        a = a * np.exp(z[NLW] * LIPW)
    if len(p) > 12 and np.any(p[12:]):   # the sound's own smooth shape (a few slow bends along the tube)
        a = a * np.exp(idct(np.r_[p[12:], np.zeros(NS - len(p[12:]))], norm="ortho"))
    return a, L, frac, port


def pose_inst(z, s, ctx=None):
    """One instance's position. GEST: a consonant sets only its own controls (OWN); everything else is
    the mouth the neighbouring sounds are carrying it through (their mean)."""
    p = pose_full(z, s)
    if not GEST or s not in OWN or not ctx or not any(ctx):
        return p
    base = np.mean([REST[: len(p)] if q == "rest" else pose_full(z, q) for q in ctx if q], 0)
    base[OWN[s]] = p[OWN[s]]
    return base


def sound_model(z, s, ctx=None):
    a, L, frac, port = area_of(z, pose_inst(z, s, ctx))
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    return seal(a, s), L, frac, port, dev


def tones(z, t):
    body(z)
    a, L, frac, port, _ = sound_model(z, t["lab"], CTX.get((t["lab"], round(t["t"][0], 3)))); k = np.arange(1, NH + 1) * t["f0"]
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
        if GEST:   # who closes the mouth (from the soft palate, half way along, to the lips)
            kv = NS // 2
            if t["lab"] == "m":     # the lips shut; behind them the mouth stays open (the tongue does not seal)
                r.append([GESTW * max(0.0, np.log(OPEN_MIN / a[kv: NS - 2].min()))])
            elif t["lab"] == "n":   # the tip seals at the ridge; behind it the mouth stays open
                kr = int(0.80 * NS)
                r.append([GESTW * max(0.0, np.log(OPEN_MIN / a[kv: kr].min())), GESTW * max(0.0, np.log(a[kr:].min() / 0.002))])
            else:                   # open sounds: no contact anywhere
                r.append([GESTW * max(0.0, np.log(OPEN_MIN / a[kv:].min()))])
        if t["lab"] not in CLOSED:   # an open mouth, physically
            chmin = float(os.environ.get("CHMIN", "0.02"))
            r.append([3000 * max(0, chmin - a[4:].min())])
            # and a slope back to open even when the tongue is pressed into the roof (gap >= 0.4 mm)
            g_ = raw_gap(pose_full(z, t["lab"])[:9], z[0], z[SH["lar"]], z)
            r.append([GAPW * max(0.0, GAPMIN - g_)])
            if os.environ.get("F1GUARD", "") == "1":
                # acoustically open: the first resonance must stay clear of the sealed-tube
                # wall resonance (~200 Hz); a sealed mouth collapses onto it
                _, L, frac, port, _ = sound_model(z, t["lab"], CTX.get((t["lab"], round(t["t"][0], 3))))
                ff = np.arange(120.0, 1200.0, 5.0)
                Hd = np.abs(X.tube_H(a, L, ff) / (1j * 2 * np.pi * ff))
                f1 = ff[int(np.argmax(Hd))]
                r.append([40.0 * max(0.0, 290.0 - f1) / 290.0])
    if FMTW > 0:   # his resonances (F1, F2) per sound, read the same way from his measured mouth and the tube
        for t in T:
            ft = FMT.get((t["lab"], round(t["t"][0], 3)))
            if ft is None:
                continue
            fm = model_formants(z, t["lab"], CTX.get((t["lab"], round(t["t"][0], 3))))
            for j in range(len(ft)):
                if j == 2:   # the third: his r-colouring, matched to the nearest resonance above the first (so a weak
                    cand = list(fm[1:]) or [8000.0]   # or missing one still pulls the right way)
                    fq = min(cand, key=lambda q: abs(bark(q) - bark(ft[j])))
                    r.append([FMTW * (bark(fq) - bark(ft[j]))])
                    continue
                r.append([FMTW * (bark(fm[j]) - bark(ft[j])) if len(fm) > j else FMTW * 3.0])
    if RESPW > 0:   # his measured mouth response (from the voice recovery), at every frequency, 1/3-octave smooth
        for t in T:
            rt = RESP.get((t["lab"], round(t["t"][0], 3)))
            if rt is None:
                continue
            a, L, frac, port, _ = sound_model(z, t["lab"], CTX.get((t["lab"], round(t["t"][0], 3))))
            Hm = 20 * np.log10(np.abs(B.tube_H_nose(a, L, RF, frac, port, z[6], z[7]) * B.head_baffle(RF, z[1])) + 1e-12)
            Hm = np.convolve(Hm, RK, mode="same")[RSEL]; d = (Hm - Hm.mean()) - rt
            r.append(RESPW * d / np.sqrt(len(d)) * np.sqrt(NH))
    if HIS_SRC and ARTW > 0 and not TOOL and len(z) >= NP:   # his articulators as the inversion tool reads them
        for s_ in SOUNDS:
            f_ = SPF.get(s_)
            if f_ is None:
                continue
            p_ = z[PO[s_]]
            for j_, (ci, fn) in enumerate(ART_MAP.items()):
                a_, b_ = z[NM0 + 2 * j_], z[NM0 + 2 * j_ + 1]
                r.append([ARTW * (ARTW_LIP if ci in (5, 6) else 1.0) * (p_[ci] - (a_ + b_ * f_[fn]))])
    if HIS_SRC and TOOL and TUNE > 0 and len(z) >= NP:   # fine-tuning away from his movement costs
        r.append(np.array([z[PO[s_].start + ci] for s_ in SOUNDS for ci in ART_MAP]) / max(TUNE, 1e-4) * 2.0)
    if HIS_SRC and len(z) >= NC0:   # each anatomical control costs a little: used only where it earns it
        r.append(0.3 * z[NX:NC0])
    if HIS_SRC and KC and len(z) >= NP:   # the free shape terms cost more (no named muscle)
        r.append(0.5 * z[NC0:NP])
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    r.append(float(os.environ.get("SHAPEW", "1")) * dev[::4] / 0.15)     # departures from a normal bun cost (no widened throat as a compensation)
    if SHARED_SRC:   # his voice's spectrum is smooth
        r.append(0.5 * np.diff(z[GS], 2))
    if SRC2:         # the puff shape may dip, but stays modest
        r.append(0.15 * z[GH])
    return np.concatenate([np.atleast_1d(x) for x in r])


FMTW = float(os.environ.get("FMTW", "6"))   # weight per Bark of F1/F2 error (vowel identity)
FMT_SOUNDS = ("ã", "ɐ˞", "ɹ", "ũ", "i", "iː", "iːf")


def his_formants():
    """His F1, F2 per vowel target: Praat (Burg, 5 formants to 5.5 kHz), median over its middle."""
    import parselmouth as _pm
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    Fo = _pm.Sound(x, sr).to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=5500)
    out = {}
    for t in T:
        if t["lab"] in FMT_SOUNDS:
            s_, e_ = t["t"]; m_ = (e_ - s_) * 0.25; ts = np.arange(s_ + m_, e_ - m_, 0.005)
            out[(t["lab"], round(s_, 3))] = [float(np.nanmedian([Fo.get_value_at_time(k, q) for q in ts])) for k in (1, 2)]
    return out


def _lpc_formants(f, P, order=10, fmax=5500.0):
    """Formants of a power spectrum (as Praat reads them): LPC on 0..fmax, roots."""
    g = np.linspace(0, fmax, 512); Pg = np.interp(g, f, P)
    r = np.fft.irfft(Pg)[: order + 1]
    from scipy.linalg import solve_toeplitz
    a = np.r_[1, -solve_toeplitz(r[:order], r[1: order + 1])]
    z_ = np.roots(a); z_ = z_[np.imag(z_) > 0]
    fr = np.angle(z_) * fmax / np.pi; bw = -np.log(np.abs(z_)) * 2 * fmax / np.pi
    fr = np.sort(fr[(bw < 700) & (fr > 150)])
    return fr


_FF = np.linspace(20, 5500, 600)


def model_formants(z, s, ctx=None):
    a, L, frac, port, _ = sound_model(z, s, ctx)
    H = B.tube_H_nose(a, L, _FF, frac, port, z[6], z[7]) * B.head_baffle(_FF, z[1])
    return _lpc_formants(_FF, np.abs(H) ** 2)


def bark(f):
    return 26.81 * f / (1960 + f) - 0.53


RESPW = float(os.environ.get("RESPW", "0"))
RESP = {}
if RESPW > 0:
    _rd = json.loads((ROOT / "models/his_mouth_response.json").read_text())
    RF = np.array(_rd["f"]); RK = np.ones(13) / 13; RSEL = slice(8, -8, 3)   # ~1/3 octave smoothing
    for _s in _rd["sounds"]:
        _T = np.convolve(np.array(_s["T"]), RK, mode="same")[RSEL]; RESP[(_s["lab"], round(_s["s"], 3))] = _T - _T.mean()


FMT = {}
if FMTW > 0 and HIS_SRC:
    _fd = json.loads((ROOT / "models/his_mouth_response.json").read_text()); _ff = np.array(_fd["f"])
    for _s in _fd["sounds"]:
        _lab = "i" if (SPLIT_I and _s["lab"] == "iː" and abs(_s["s"] - 0.79) < 0.01) else _s["lab"]
        _lab = "iːf" if (SPLIT_E and _s["lab"] == "iː" and abs(_s["s"] - 2.09) < 0.01) else _lab
        # FMT3 (2026-11-20): his r-colouring lives in the THIRD resonance (~2.6 kHz in "ɐ˞", "ɹ" and the "m"
        # between them; a high third resonance is what makes an "l"), so it is a target there too
        _nf = 3 if (os.environ.get("FMT3", "0") == "1" and _lab in ("ɐ˞", "ɹ", "m")) else 2
        FMT[(_lab, round(_s["s"], 3))] = _lpc_formants(_ff, 10 ** (np.array(_s["T"]) / 10))[:_nf].tolist()


def _sparc_features():
    d = np.load(ROOT / "models/sparc_articulation.npz"); E = d["ema"]; t = np.arange(len(E)) * 0.02
    feats = {}
    for tg in T:
        s_, e_ = tg["t"]; k = (t >= s_) & (t < e_)
        if not k.any():
            continue
        m = E[k].mean(0)
        f = dict(jaw=-m[7], tbody_y=m[3], tbody_fwd=-m[2], ttip_y=m[5], lip_gap=m[9] - m[11], lip_fwd=-(m[8] + m[10]) / 2)
        feats.setdefault(tg["lab"], []).append(f)
    return {lab: {k_: float(np.mean([q[k_] for q in v])) for k_ in v[0]} for lab, v in feats.items()}


SPF = _sparc_features() if (HIS_SRC and (ARTW > 0 or TOOL)) else {}


def report(z, tag=""):
    print(f"\n=== his mouth {tag} ===")
    if FMT:
        print("resonances F1/F2 model (his): " + "; ".join(f"{t['lab']} {t['t'][0]:.2f} " + "/".join(f"{q:.0f}" for q in model_formants(z, t['lab'])[:2]) + " (" + "/".join(f"{q:.0f}" for q in FMT[(t['lab'], round(t['t'][0], 3))]) + ")" for t in T if (t['lab'], round(t['t'][0], 3)) in FMT))
    if HIS_SRC and len(z) >= NC0:
        print("anatomical controls (x width): " + "; ".join(f"{s_} " + ", ".join(f"{n} {np.exp(v):.2f}" for n, v in zip(EXNAMES, z[EX[s_]])) for s_ in SOUNDS))
    print((f"nose turbinate surface x{z[NV]:.1f}; " if HIS_SRC and len(z) > NV else "") + f"larynx {z[0] * 0.075:.2f} cm lower; head radius {z[1]:.2f} cm; laryngeal cavity {z[2] * .75:.1f} mm x{z[3]:.2f}, "
          f"inlet {z[4] * .75:.1f} mm x{z[5]:.2f}; nose length x{z[6]:.2f}, damping {z[7]:.2f}")
    dev = idct(np.r_[z[SH["shape"]], np.zeros(NS - NF)], norm="ortho")
    print("shape map (x normal bun width, vocal folds -> lips): " + " ".join(f"{np.exp(v):.2f}" for v in dev[::4]))
    names = ["jaw", "body", "front", "tip", "root", "lips", "round", "velum", "larynx"]
    for s in SOUNDS:
        print(f"  {s:3} " + " ".join(f"{n}={v:.2f}" for n, v in zip(names, pose_full(z, s)[:9])))
    errs = {}
    for t in T:
        lv, ph, a = tones(z, t); el = np.maximum(lv[1:], FLOOR) - np.maximum(np.nan_to_num(t["level"][1:], nan=FLOOR), FLOOR)
        e = float(np.sqrt(np.mean(el ** 2))); errs.setdefault(t["lab"], []).append(e)
        _, L_, fr_, po_, _ = sound_model(z, t["lab"], CTX.get((t["lab"], round(t["t"][0], 3)))); ff = np.arange(120.0, 1200.0, 5.0)
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
        _wj = json.loads((ROOT / os.environ["WARM"]).read_text()); zw = np.array(_wj["z"])
        if "rest" in _wj:
            REST[: len(_wj["rest"])] = _wj["rest"]
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
        if os.environ.get("FREE"):   # refit only some sounds (whole positions) / only a consonant's own controls (m*, n*) / nose
            mask = np.zeros(NP, bool)
            for it in os.environ["FREE"].split(","):
                if it == "nose":
                    mask[[6, 7, NV]] = True
                elif it.endswith("*"):
                    mask[[PO[it[:-1]].start + c for c in OWN[it[:-1]]]] = True
                else:
                    mask[PO[it]] = True; mask[EX[it]] = True; mask[SC[it]] = True
            print(f"  refitting {mask.sum()} of {NP} settings: {os.environ['FREE']}", flush=True)

            def resid_sub(x):
                zz = zw.copy(); zz[mask] = x; return resid(zz)
            print(f"  start: cost {np.sum(resid(zw) ** 2):.0f}", flush=True)
            r = least_squares(resid_sub, zw[mask], bounds=(LO[mask], HI[mask]), method="trf", max_nfev=int(os.environ.get("NFEV", "60")), diff_step=1e-3, x_scale="jac", xtol=1e-12, ftol=1e-10)
            zz = zw.copy(); zz[mask] = r.x; best = (float(np.sum(r.fun ** 2)), zz)
        else:
            r = least_squares(resid, zw, bounds=(LO, HI), method="trf", max_nfev=int(os.environ.get("NFEV", "60")), diff_step=1e-3, x_scale="jac", xtol=1e-12, ftol=1e-10)
            best = (float(np.sum(r.fun ** 2)), r.x)
        print(f"  continued: cost {best[0]:.0f}", flush=True)
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
        z=z.tolist(), sounds=SOUNDS, rest=REST[:9].tolist(), targets=[dict(lab=t["lab"], t=t["t"], f0=t["f0"]) for t in T],
        errors=errs), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
