"""Step 3f: his "ee" tones from HIS BUN MOUTH plus natural variation only.

A free tube can hit his ~19 tone levels with many shapes, some not bun-like
(ripples, an inflated front: step 3e). So the bun mouth is the starting point:
  tube = the bun "ee" shape (tongue, jaw, lips, larynx depth: the bun model)
         x smooth departures (8 shape terms), each point within ~+-15% of the
         bun's width (natural variation), with a cost on every departure
  puff = per "ee" (open share, rise, roundness, closing smoothness, easing)
Least squares, every tone its own residual.

    python scripts/build/ee_bunfit.py -> models/ee_bunfit.json, out/build/ee_bunfit_his_tones_vs_model.wav,
                                        analysis/physics/ee_bunfit.png
"""
import json, os, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import idct
from scipy.optimize import least_squares
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics"))
os.environ.setdefault("PULSE", "smooth")
import ee_exact as X  # noqa: E402
import ee as E  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402

NH = X.NH; FLOOR = X.FLOOR; T = X.T; NS = X.NS
ND = 8                  # smooth departure terms
HEAD = os.environ.get("HEAD", "") == "1"      # radiate from his small round head (sphere), not an infinite wall
HEAD_R = float(os.environ.get("HEAD_R", "0"))  # >0: his head radius is fixed (cm)
NAT_W = float(os.environ.get("NAT_W", "1.5"))  # cost of departing from the bun shape
NOSE = os.environ.get("NOSE", "") == "1"         # the nasal passage as a side branch (velum slightly open)
LARV = os.environ.get("LARV", "") == "1"         # the laryngeal cavity's size may vary (natural variation)
CHEEK = os.environ.get("CHEEK", "") == "1"
SUB = os.environ.get("SUB", "") == "1"
HEADX = os.environ.get("HEADX", "") == "1"
F1W = float(os.environ.get("F1W", "0"))          # >0: the first resonance must sit where his does (dB per 5% off)
HIS_F1 = {264: 362.0, 389: 393.0, 350: 373.0, 331: 408.0}   # his F1 per "ee" (Praat, fingerprint)       # exact radiation from a mouth on his round head (sphere), at a listening angle           # his windpipe and lungs below the folds (coupled while the folds are open)       # cheek pockets (between cheek teeth and cheeks), a pair of small bottles
TAG = os.environ.get("TAG", "")
SIGMA = 0.15            # natural variation of width (~15%)
LARCAV = tuple(float(v) for v in os.environ.get("LARCAV", "7,1.0,4,0.15").split(","))
_cache = {}


def bun_tube40(pose9, neck, larcav=None):
    larcav = tuple(np.round(larcav, 2)) if larcav is not None else LARCAV
    key = (tuple(np.round(pose9, 3)), round(neck, 1), larcav)
    if key not in _cache:
        v = Pose().vec(); v[:9] = np.clip(pose9, E.EE_LO, _EE_HI)
        m = BunMouth(0.75, neck_mm=neck, larcav=larcav); ar, ln, _, brx = m.tube(Pose.from_vec(v))
        edges = np.r_[0, np.cumsum(ln)]; L = edges[-1]; e40 = np.linspace(0, L, NS + 1); a40 = np.empty(NS)
        for i in range(NS):
            ov = np.clip(np.minimum(edges[1:], e40[i + 1]) - np.maximum(edges[:-1], e40[i]), 0, None)
            a40[i] = np.sum(ov * ar) / max(ov.sum(), 1e-9)
        if len(_cache) > 20000:
            _cache.clear()
        _cache[key] = (np.maximum(a40, 1e-4), L, float(np.sum(ln[:brx]) / L))
    return _cache[key][:2]


def port_frac(pose9, neck):
    bun_tube40(pose9, neck)
    return _cache[(tuple(np.round(pose9, 3)), round(neck, 1), LARCAV)][2]


NOSE_SURF = 1.0   # turbinate surface: the nasal passage's wall losses vs a smooth round tube (set by the fit)


GLOTTIS_AG = 0.0  # mean opening of the vocal-cord gap while voicing (cm^2); 0 = cords as a closed wall
PS_SOFT = 8000.0  # lung pressure behind the cords, dyn/cm^2 (0.8 kPa: soft, relaxed voice; later set by effort)
FOLD_T = 0.15     # depth of the gap through the cords (cm), small-bun folds
import os as _os
import prince_voice.mouth as _PMm
_PMm.AREA_LOSS = _os.environ.get("AREA_LOSS", "1") == "1"   # losses grow as his small tubes narrow (physics)
WALLS = True      # his yielding walls (cheeks, throat) radiate the sound that moves them


def _wall_Y(area, w):
    """Flow into the yielding wall per unit pressure, per cm of tube (Sondhi & Schroeter's wall term)."""
    import prince_voice.mouth as _PM
    a, b, w0sq = 130 * np.pi * _PM.TISSUE["wall_r"], (30 * np.pi) ** 2, (406 * np.pi) ** 2 * _PM.TISSUE["wall_m"] ** 2
    jw = 1j * w[None, :]
    return area[:, None] / (_PM.RHO * _PM.C ** 2) * jw * w0sq / ((jw + a) * jw + b)


def tube_H_nose(a, L, f, frac, port, nlen, damp):
    """The tube with the nasal passage branching off at the velum (frac of the
    length): sound leaves by the lips AND the nostrils AND, through his yielding
    walls, the cheeks and throat (they move with the pressure inside and radiate it).
    Nasal passage: the bun model's (length x nlen), lined with turbinate scrolls
    (wall losses x NOSE_SURF; damping at the nostril)."""
    import prince_voice.mouth as _PM
    from prince_voice.mouth import _section_matrices, _chain, _radiation, RHO, C
    w = 2 * np.pi * np.asarray(f, float); n = len(a); br = int(np.clip(round(frac * n), 1, n - 1))
    ls = np.full(n, L / n)
    A, Bm, Cm, D = _section_matrices(a, ls, w); Yw = _wall_Y(a, w) * ls[:, None]
    P = _radiation(a[-1], w) * (1.0 + 0j); U = np.ones_like(w, dtype=complex); Ul = U.copy(); Uw = np.zeros_like(U)
    for s_ in range(n - 1, br - 1, -1):          # lips back to the velum
        Pi = A[s_] * P + Bm[s_] * U; Ui = Cm[s_] * P + D[s_] * U; Uw += 0.5 * (P + Pi) * Yw[s_]; P, U = Pi, Ui
    m = BunMouth(0.75); na, nl = m.nasal(); nl = nl * nlen
    _old = _PM.TISSUE["visc"]; _PM.TISSUE["visc"] = _old * NOSE_SURF ** 2
    try:
        Kn = _chain(np.r_[port, na], np.r_[0.3, nl], w)
    finally:
        _PM.TISSUE["visc"] = _old
    Zn = _radiation(na[-1], w) + RHO * C / na[-1] * damp
    Un = P / (Kn[0, 0] * Zn + Kn[0, 1]); U = U + P * (Kn[1, 0] * Zn + Kn[1, 1]) / (Kn[0, 0] * Zn + Kn[0, 1])
    for s_ in range(br - 1, -1, -1):             # velum back to the vocal folds
        Pi = A[s_] * P + Bm[s_] * U; Ui = Cm[s_] * P + D[s_] * U; Uw += 0.5 * (P + Pi) * Yw[s_]; P, U = Pi, Ui
    Hm = 1j * w * (Ul + Un + (Uw if WALLS else 0)) / U
    if GLOTTIS_AG > 0:   # the cords' gap is a real opening (Flanagan): its resistance and air mass load the tube
        Zg = RHO * np.sqrt(2 * PS_SOFT / RHO) / GLOTTIS_AG + 1j * w * RHO * FOLD_T / GLOTTIS_AG
        Hm = Hm * Zg / (Zg + P / U)
    return Hm


def head_baffle(f, radius_cm):
    """A mouth on a small sphere: low frequencies wrap around the head and spread
    everywhere (up to -6 dB on axis vs an infinite wall); highs beam forward.
    First-order step between them, centred near c / (2 pi a)."""
    s = 1j * 2 * np.pi * np.asarray(f, float) * radius_cm / 35000.0
    return (1 + s) / (2 + s) * 2.0 / 2.0


def cheek_H(a, L, f, pos, neck_a, neck_l, cav_a, cav_l):
    """The tube with a pair of cheek pockets joining at `pos` (fraction of the
    length): each a narrow neck (the gaps between the teeth) into a pocket."""
    from prince_voice.mouth import _chain, _radiation
    w = 2 * np.pi * np.asarray(f, float); n = len(a); j = int(np.clip(round(pos * n), 1, n - 1))
    ls = np.full(n, L / n)
    nb = max(2, int(round(cav_l / 0.1)))
    Kb = _chain(np.r_[np.full(2, neck_a), np.full(nb, cav_a)], np.r_[np.full(2, neck_l / 2), np.full(nb, cav_l / nb)], w)
    Y = 2.0 * Kb[1, 0] / Kb[0, 0]                         # a pair of closed pockets
    K1 = _chain(a[:j], ls[:j], w); K2 = _chain(a[j:], ls[j:], w)
    one = np.ones_like(Y); zero = np.zeros_like(Y)
    S = np.array([[one, zero], [Y, one]])
    K = np.einsum("ijf,jkf->ikf", np.einsum("ijf,jkf->ikf", K1, S), K2)
    return 1j * w / (K[1, 0] * _radiation(a[-1], w) + K[1, 1])


def sub_factor(a, L, f, Lt, At, lung, log_zg):
    """Coupling to the windpipe below the folds. The folds are a pressure source
    behind the glottal resistance Zg; the flow into the mouth is reduced where
    the mouth's or the windpipe's input impedance is high:
        U = U_source * Zg / (Zg + Z_mouth + Z_windpipe)
    Windpipe: a tube (length Lt, area At) ending in the lungs (a resistive load)."""
    from prince_voice.mouth import _chain, _radiation, RHO, C
    w = 2 * np.pi * np.asarray(f, float); n = len(a); ls = np.full(n, L / n)
    K = _chain(np.maximum(a, 1e-4), ls, w); Zl = _radiation(a[-1], w)
    Zm = (K[0, 0] * Zl + K[0, 1]) / (K[1, 0] * Zl + K[1, 1])
    nt = max(4, int(round(Lt / 0.25)))
    Kt = _chain(np.full(nt, At), np.full(nt, Lt / nt), w)
    Zlung = lung * RHO * C / At
    Zt = (Kt[0, 0] * Zlung + Kt[0, 1]) / (Kt[1, 0] * Zlung + Kt[1, 1])
    Zg = 10 ** log_zg
    return Zg / (Zg + Zm + Zt)


def head_sphere(f, radius_cm, theta_deg, mouth_area):
    """Far-field sound of a small vibrating cap (his mouth) on a rigid sphere (his
    head), heard at angle theta from where the mouth points (Morse & Ingard).
    Includes the diffraction ripples a real round head makes. Returned relative to
    an ideal source's j*omega so it can replace the plain radiation term."""
    from scipy.special import spherical_jn, spherical_yn, eval_legendre
    f = np.atleast_1d(np.asarray(f, float)); k = 2 * np.pi * f / 35000.0; ka = k * radius_cm
    alpha = np.sqrt(max(mouth_area, 1e-4) / np.pi) / radius_cm
    ca, ct = np.cos(alpha), np.cos(np.radians(theta_deg))
    N = int(np.max(ka) * 2 + 25)
    p = np.zeros_like(f, dtype=complex)
    for n in range(N):
        Pm = 1.0 if n == 0 else eval_legendre(n - 1, ca)
        cn = (Pm - eval_legendre(n + 1, ca)) * eval_legendre(n, ct)
        hd = spherical_jn(n, ka, derivative=True) + 1j * spherical_yn(n, ka, derivative=True)
        p += (-1j) ** (n + 1) * cn / hd
    p = p / k / mouth_area                   # per unit volume flow
    return p / (1j * 2 * np.pi * f)          # the tube response already contains j*omega


def unpack(z):
    pose9 = z[:9]; neck = z[9]; d = z[10:10 + ND]; q = tuple(z[10 + ND:15 + ND])
    a0, L = bun_tube40(pose9, neck, (z[24 + ND:28 + ND] if LARV else None))
    th = float(os.environ.get("THROAT", "1"))
    if th != 1:   # the throat behind the tongue (back ~45% of the tube) wider by this factor
        a0 = a0.copy(); a0[:int(0.45 * NS)] *= th
    dev = idct(np.r_[d, np.zeros(NS - ND)], norm="ortho")
    return a0 * np.exp(dev), L, q, dev


_EE_HI = E.EE_HI.copy()
if os.environ.get("ROUND", "") == "1":      # lips may round/push forward (how he says it, not anatomy)
    _EE_HI[6] = 1.0
LO = np.r_[E.EE_LO, 15.0, np.full(ND, -3.0), 0.3, 0.3, 0.3, 0.0, 0.0, (HEAD_R - 1e-3 if HEAD_R > 0 else 1.8), 0.0, 0.85, 0.05]
HI = np.r_[_EE_HI, 45.0, np.full(ND, 3.0), 0.97, 0.95, 4.0, 1.5, 1.0, (HEAD_R + 1e-3 if HEAD_R > 0 else 3.0), (0.12 if NOSE else 1e-4), 1.15, 0.4]
LO = np.r_[LO, ([0.45, 0.004, 0.1, 0.03, 0.5] if CHEEK else [])]
HI = np.r_[HI, ([0.8, 0.04, 0.5, 0.3, 2.0] if CHEEK else [])]
if LARV:   # cavity length (ref mm), cavity width vs throat, inlet length, inlet width vs throat
    if not CHEEK:
        LO = np.r_[LO, [0.45, 0.004, 0.1, 0.03, 0.5]]; HI = np.r_[HI, [0.45 + 1e-3, 0.004 + 1e-4, 0.1 + 1e-3, 0.03 + 1e-3, 0.5 + 1e-3]]
    if os.environ.get("LARV_GESTURE", "") == "1":
        # size = his anatomy (shared, fixed); only how narrow the inlet is held varies (the "twang" ring)
        LO = np.r_[LO, [9.0 - 1e-3, 1.0 - 1e-3, 4.0 - 1e-3, 0.08]]; HI = np.r_[HI, [9.0 + 1e-3, 1.0 + 1e-3, 4.0 + 1e-3, 0.35]]
    else:
        LO = np.r_[LO, [4.0, 0.5, 2.0, 0.08]]; HI = np.r_[HI, [11.0, 1.5, 6.0, 0.35]]
if HEADX:  # listening angle from where the mouth points (deg); head radius is the existing head entry
    LO = np.r_[LO, [0.0]]; HI = np.r_[HI, [100.0]]
    LO[15 + ND], HI[15 + ND] = 2.0, 3.2
if SUB:    # windpipe length (cm), area (cm^2), lung load (x rho c / A), log10 glottal resistance (cgs)
    LO = np.r_[LO, [3.0, 0.15, 0.05, 1.0]]; HI = np.r_[HI, [8.0, 0.45, 3.0, 6.0]]


def resid(z, t):
    a, L, q, dev = unpack(z)
    k = np.arange(1, NH + 1) * t["f0"]
    TH = (tube_H_nose(a, L, k, port_frac(z[:9], z[9]), z[16 + ND], z[17 + ND], z[18 + ND]) if NOSE else X.tube_H(a, L, k))
    if CHEEK:
        TH = cheek_H(a, L, k, *z[19 + ND:24 + ND])
    if SUB:
        TH = TH * sub_factor(a, L, k, *z[28 + ND:32 + ND])
    if HEADX:
        Zc = X.puff_C(t["f0"], q) * TH * head_sphere(k, z[15 + ND], z[-1], a[-1])
    else:
        Zc = X.puff_C(t["f0"], q) * TH * (head_baffle(k, z[15 + ND]) if HEAD else 1.0)
    lv = 20 * np.log10(np.abs(Zc) + 1e-15); lv -= lv[0]
    ph = np.angle(np.exp(1j * (np.angle(Zc) - np.arange(1, NH + 1) * np.angle(Zc[0]))))
    r_lv = np.maximum(lv[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)
    w = np.clip((t["coh"][1:] - 0.7) / 0.3, 0, 1)
    r_ph = 3.0 * w * np.angle(np.exp(1j * (ph[1:] - t["phase"][1:])))
    r_nat = NAT_W * dev[::4] / SIGMA                                   # natural variation: ~15% costs as much as ~1.5 dB
    r_ch = [float(os.environ.get("CHW", "300")) * max(0, float(os.environ.get("CHMIN", "0.006")) - a[4:].min())]
    r_f1 = []
    if F1W > 0:
        ff = np.arange(150.0, 900.0, 4.0); Hd = np.abs(X.tube_H(a, L, ff) / (1j * 2 * np.pi * ff))
        f1 = ff[int(np.argmax(Hd))]; tgt = HIS_F1[min(HIS_F1, key=lambda q: abs(q - t["f0"]))]
        r_f1 = [F1W * (f1 - tgt) / tgt / 0.05]
    return np.r_[r_lv, r_ph, r_nat, r_ch, r_f1]


def fit_one(j):
    t = T[j]; prev = json.loads((ROOT / "models/ee_recipe.json").read_text()); rng = np.random.default_rng(j)
    best = None
    warm = os.environ.get("WARM")
    if warm:   # start from an earlier best solution; new parts start out (nearly) inactive
        zw = np.array(json.loads((ROOT / warm).read_text())["per_ee"][j]["z"])
        pad = {"SUB": [5.0, 0.28, 1.0, 5.9]}
        z0 = np.r_[zw, pad["SUB"]] if (SUB and len(zw) == len(LO) - 4) else zw
        if HEADX and len(z0) == len(LO) - 1:
            z0 = np.r_[z0, float(os.environ.get("THETA0", "0"))]
        if len(z0) == len(LO):
            z0 = np.clip(z0, LO + 1e-6, HI - 1e-6)
            r = least_squares(resid, z0, args=(t,), bounds=(LO, HI), method="trf", max_nfev=6000, diff_step=1e-3)
            best = (float(np.sqrt(np.mean(r.fun[:NH - 1] ** 2))), r.x.tolist())
            print(f"  warm start {t['f0']:.0f} Hz: from {float(np.sqrt(np.mean(resid(z0, t)[:NH - 1] ** 2))):.2f} to {best[0]:.2f} dB", flush=True)
    for k in range(int(os.environ.get("NSTART", "6"))):
        if os.environ.get("OPEN_STARTS", "") == "1":
            # an open "ee": tongue high but not touching the palate (checked)
            for _ in range(200):
                p0 = np.r_[rng.uniform(0.1, 0.35), rng.uniform(0.3, 0.75), rng.uniform(0.4, 0.9), rng.uniform(0, 0.2),
                           rng.uniform(0, 1), rng.uniform(0.5, 1), rng.uniform(0, 0.4), 0.0, rng.uniform(0, 1)]
                a_try, _ = bun_tube40(p0, 25.0)
                if a_try[4:].min() > float(os.environ.get("CHMIN", "0.006")) * 1.5:
                    break
        else:
            p0 = np.array(prev["pose"][:9]) if k == 0 else np.array(prev["pose"][:9]) + rng.normal(0, 0.2, 9)
        z0 = np.r_[p0, rng.uniform(20, 40), np.zeros(ND), rng.uniform(0.6, 0.95), rng.uniform(0.4, 0.7), 1.0, 0.3, rng.uniform(0, 1), (HEAD_R if HEAD_R > 0 else 2.4), (rng.uniform(0.01, 0.08) if NOSE else 0.0), 1.0, 0.15,
                   *([rng.uniform(0.5, 0.75), 0.015, 0.25, 0.1, 1.2] if CHEEK else ([0.45, 0.004, 0.1, 0.03, 0.5] if LARV else [])),
                   *(([9.0, 1.0, 4.0, rng.uniform(0.1, 0.3)] if os.environ.get("LARV_GESTURE", "") == "1" else
                     [rng.uniform(5, 10), rng.uniform(0.7, 1.3), rng.uniform(2.5, 5), rng.uniform(0.1, 0.3)]) if LARV else []),
                   *([rng.uniform(4, 7), 0.28, rng.uniform(0.2, 1.5), rng.uniform(1.5, 2.8)] if SUB else [])]
        z0 = np.clip(z0, LO + 1e-6, HI - 1e-6)
        r = least_squares(resid, z0, args=(t,), bounds=(LO, HI), method="trf", max_nfev=3000, diff_step=1e-3)
        e = float(np.sqrt(np.mean(r.fun[:NH - 1] ** 2)))
        if best is None or e < best[0]:
            best = (e, r.x.tolist())
    return j, best


def main():
    with Pool(4) as pool:
        res = sorted(pool.map(fit_one, range(4)))
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    import ee_decompose as DC
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(4, 2, figsize=(18, 13)); gap = np.zeros(int(0.35 * 24000)); pieces = []; out = []
    names = ["jaw", "body", "front", "tip", "root", "lips", "round", "velum", "larynx"]
    for (j, (e, z)), t, (s, en) in zip(res, T, X.R.SPANS):
        z = np.array(z); a, L, q, dev = unpack(z); a0, _ = bun_tube40(z[:9], z[9], (z[24 + ND:28 + ND] if LARV else None))
        if LARV:
            print(f"  laryngeal cavity: {z[24 + ND] * 0.75:.1f} mm long, {z[25 + ND]:.2f}x the throat's width; inlet {z[26 + ND] * 0.75:.1f} mm at {z[27 + ND]:.2f}x")
        kk = np.arange(1, NH + 1) * t["f0"]
        TH = (tube_H_nose(a, L, kk, port_frac(z[:9], z[9]), z[16 + ND], z[17 + ND], z[18 + ND]) if NOSE else X.tube_H(a, L, kk))
        if CHEEK:
            TH = cheek_H(a, L, kk, *z[19 + ND:24 + ND])
            print(f"  cheek pockets: at {z[19 + ND]:.2f} of the length, neck {z[20 + ND]:.3f} cm2 x {z[21 + ND]:.2f} cm, pocket {z[22 + ND]:.2f} cm2 x {z[23 + ND]:.2f} cm")
        if SUB:
            TH = TH * sub_factor(a, L, kk, *z[28 + ND:32 + ND])
            print(f"  windpipe: {z[28 + ND]:.1f} cm long, {z[29 + ND]:.2f} cm2 ({2 * np.sqrt(z[29 + ND] / np.pi) * 10:.1f} mm across), "
                  f"lung load {z[30 + ND]:.2f}, glottal resistance {10 ** z[31 + ND]:.0f}")
        if HEADX:
            Zc = X.puff_C(t["f0"], q) * TH * head_sphere(kk, z[15 + ND], z[-1], a[-1])
            print(f"  head: radius {z[15 + ND]:.2f} cm, heard {z[-1]:.0f} deg from where the mouth points")
        else:
            Zc = X.puff_C(t["f0"], q) * TH * (head_baffle(kk, z[15 + ND]) if HEAD else 1.0)
        lv = 20 * np.log10(np.abs(Zc)); lv -= lv[0]
        if NOSE:
            print(f"  nose: port {z[16 + ND]:.3f} cm2, passage length x{z[17 + ND]:.2f}, turbinate damping {z[18 + ND]:.2f}")
        ffx = np.arange(150.0, 900.0, 2.0); f1m = ffx[int(np.argmax(np.abs(X.tube_H(a, L, ffx) / (1j * 2 * np.pi * ffx))))]
        print(f"\n{t['f0']:.0f} Hz: first resonance {f1m:.0f} Hz (his {HIS_F1[min(HIS_F1, key=lambda q: abs(q - t['f0']))]:.0f}); narrowest channel {a[4:].min():.3f} cm2")
        print(f"{t['f0']:.0f} Hz: tone error {e:.2f} dB | larynx {z[9] * 0.075:.2f} cm lower, tube {L:.2f} cm | "
              f"departures from the bun shape: up to {100 * (np.exp(np.abs(dev).max()) - 1):.0f}% (typical {100 * (np.exp(np.sqrt(np.mean(dev ** 2))) - 1):.0f}%)")
        print("  mouth: " + str({n: round(float(v), 2) for n, v in zip(names, z[:9])}))
        if HEAD:
            print(f"  head radius {z[15 + ND]:.2f} cm")
        print(f"  puff: open {q[0]:.2f}, rise {q[1]:.2f}, roundness {q[2]:.2f}, smooth {q[3]:.2f} ms, eases shut {q[4]:.2f}")
        print("  his  " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print("  model" + " ".join(f"{v:4.0f}" for v in lv))
        pos = (np.arange(NS) + 0.5) * L / NS
        ax[j, 0].fill_between(pos, -np.sqrt(a / np.pi), np.sqrt(a / np.pi), step="mid", color="#e58c9a", label="fitted")
        ax[j, 0].plot(pos, np.sqrt(a0 / np.pi), "k-", lw=1, label="bun 'ee' shape"); ax[j, 0].plot(pos, -np.sqrt(a0 / np.pi), "k-", lw=1)
        ax[j, 0].set_title(f"{t['f0']:.0f} Hz: tube (vocal folds left, lips right), radius cm"); ax[j, 0].legend(fontsize=7)
        ax[j, 1].plot(range(1, NH + 1), t["level"], "-o", color="#c0392b", label="his tones")
        ax[j, 1].plot(range(1, NH + 1), lv, "-s", color="#2c3e50", label=f"model ({e:.1f} dB)"); ax[j, 1].legend(fontsize=7)
        ax[j, 1].set_ylim(-80, 5)
        d = DC.decompose(x[int((s - 0.02) * sr): int((en + 0.02) * sr)], sr, f"b{j}")
        his_t = resample_poly(d["harm"], 1, 2); his_t = his_t / np.abs(his_t).max() * 0.7
        y = X.render(a, L, q, t["f0"], max(int((en - s) * 1000), 150), seed=j)
        if HEAD or HEADX or NOSE or SUB or CHEEK:   # the same physics (small head, nasal branch) applied to the model's sound
            Y = np.fft.rfft(y); ff = np.maximum(np.fft.rfftfreq(len(y), 1 / X.SR), 1.0)
            G = head_sphere(ff, z[15 + ND], z[-1], a[-1]) if HEADX else (head_baffle(ff, z[15 + ND]) if HEAD else 1.0)
            if CHEEK:
                G = G * cheek_H(a, L, ff, *z[19 + ND:24 + ND]) / X.tube_H(a, L, ff)
            if SUB:
                G = G * sub_factor(a, L, ff, *z[28 + ND:32 + ND])
            if NOSE:
                G = G * tube_H_nose(a, L, ff, port_frac(z[:9], z[9]), z[16 + ND], z[17 + ND], z[18 + ND]) / X.tube_H(a, L, ff)
            y = np.fft.irfft(Y * G, len(y)); y = y / np.abs(y).max() * 0.7
        pieces += [his_t, gap, resample_poly(y, 1, 2), gap, gap]
        out.append(dict(f0=t["f0"], err=e, z=z.tolist(), areas=a.tolist(), L=L, puff=list(q),
                        max_departure_pct=float(100 * (np.exp(np.abs(dev).max()) - 1))))
    plt.tight_layout(); plt.savefig(ROOT / f"analysis/physics/ee_bunfit{TAG}.png", dpi=60)
    sf.write(ROOT / f"out/build/ee_bunfit{TAG}_his_tones_vs_model.wav", np.concatenate(pieces), 24000)
    (ROOT / f"models/ee_bunfit{TAG}.json").write_text(json.dumps(dict(ND=ND, SIGMA=SIGMA, per_ee=out), indent=1, default=float))


if __name__ == "__main__":
    main()
