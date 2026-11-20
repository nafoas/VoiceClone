"""His phrase from the airflow mouth (td_mouth): consonants rebuilt from scratch (2026-11-20).

Da Boss: "scrap the consonants and redo them entirely." Nothing of the old consonants is used (no noise
layers, no fitted consonant shapes, no consonant loudness copied from the clip). Each consonant is a
MOVEMENT of his mouth or cords, as measured in his clip (docs/PRINCE_IDENTITY.md, PRINCE_PHYSICS.md);
every hiss, burst and hum comes out of the air moving through his mouth:

  n   tongue tip sealed at the ridge, soft palate open (his hum goes out through the nose)
  m   lips shut (his split upper lip still leaks ~0.035 cm^2), soft palate open
  ɹ   an open, bunched r (his r-colouring, ~2.5 kHz), no contact
  ɕ   tongue blade raised ~2 cm behind the lips (tip down); cords part a little for the air; hum continues
  p   lips shut but leaking (split lip): little pressure, so no puff; his voice runs through it (weak, voiced)
  -t  (end of "peet", "teet") never closes: the tip rises to a near-closure, the vowel drops and hums on
  tʰ  (start of "teet", "tee") tip seals fully, cords part (aspiration); the release bursts by itself
  phrase start: his rest posture (lips shut, soft palate open, tongue up), the first sound moves out of it

Still from the clip (as before, provisional): his pitch, where his voice runs, the breath contour,
the timing of each movement (from his labels/pitch). Nothing is done to the sound afterwards.

    GEST=0 python scripts/build/render_td.py [state.json] -> out/td/td_render.npy (clip timeline)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MOUTH_V1", "1"); os.environ.setdefault("NH", "40"); os.environ.setdefault("SRC", "his")
os.environ.setdefault("TRANS", "models/transitions_F14.json"); os.environ.setdefault("ZFILE", "models/mouth_inverse_F14.json")
for p in (ROOT, ROOT / "scripts", ROOT / "scripts/build", ROOT / "analysis/physics"):
    sys.path.insert(0, str(p))
ARGS = sys.argv[1:]
sys.argv = sys.argv[:1]
import parselmouth as pm  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.ndimage import uniform_filter1d  # noqa: E402
from scipy.signal import resample_poly  # noqa: E402

import render_his as R  # noqa: E402
import td_mouth as TD  # noqa: E402
import transitions as TRm  # noqa: E402
import prince_voice.mouth as PM  # noqa: E402
from prince_voice.bunmouth import BunMouth  # noqa: E402

M = R.M
SR = 48000
HOP = 120                      # 2.5 ms: the mouth's position is computed this often
X, _ = sf.read(ROOT / "reference/source/prince_reference.wav"); X = X.mean(1)
_P = pm.Sound(X, SR).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
TT, FF0 = _P.xs(), _P.selected_array["frequency"]

# ---- his consonant settings (physical; fitted to his clip where marked)
S = dict(
    lip_leak=0.0452,      # cm^2: his split upper lip never seals (fitted; PRINCE_PHYSICS 7 said 0.03-0.04)
    tail_leak=0.0003,     # cm^2: the tip's near-closure ending "peet"/"teet" (fitted: nearly shut)
    blade=0.0123,         # cm^2: the soft S's blade gap ~2 cm behind the lips (fitted)
    ab_t=0.0384,          # cm^2: how far the cords part for the aspirated t (fitted)
    ab_s=0.0314,          # cm^2: how far they part for the soft S (fitted)
    gnoise=0.5080,        # turbulence strength (one constant for every jet; fitted)
    plung=8000.0,       # dyn/cm^2: soft-voice lung pressure (as the cord-gap physics)
    air=1.0,            # (1 = the airflow run as computed; for tests only)
    push_ms=10.0,       # ms: the mouth's pressure behind his cords, as it builds (smooth)
    ag_scale=4.0744,      # his cords' mean opening while voicing, x the fitted cord gap (fitted)
    rel_t=0.025,        # s: the tongue tip's opening movement
    rel_p=0.0547,         # s: the lips' opening movement (fitted: gentle)
    close=0.015,        # s: closing movements
)

# ---- his timeline (s), from his clip: release instants, where his voice runs, and his documented habits
PLAN = {
    0: dict(voice=[(0.050, 1.125)],
            tip=[(None, 0.155, "seal"), (0.290, 0.375, "seal"), (0.720, 0.790, "seal")],
            lips=[(0.510, 0.610)],
            velum=[(None, 0.165), (0.285, 0.385), (0.505, 0.620), (0.715, 0.800)],
            blade=[(0.995, 1.115)], ab=[(0.995, 1.13, "s")]),
    1: dict(voice=[(1.468, 1.680), (1.770, 1.940), (2.090, 2.330)],   # his voice starts as his lips part
            tip=[(1.595, 1.709, "tail"), (1.895, 2.037, "tail")],
            lips=[(None, 1.465)],
            velum=[], blade=[], ab=[(1.709 - 0.035, 1.770, "t"), (2.037 - 0.035, 2.090, "t")]),   # around each release, until his voice resumes
}
REL = {0: [], 1: [1.709, 2.037]}   # the crisp t releases (the tail seals fully just before each)


def load(state_path):
    st = json.loads((ROOT / state_path).read_text())
    z = M.pad(np.array(st["z"]))
    M.BUNSIZE[0] = float(st.get("size", 0.75)); M._cache.clear()
    if "rest" in st:
        M.REST[: len(st["rest"])] = st["rest"]
    R.Z[:] = z; TRm.Z[:] = z; M.body(z)
    tr = json.loads((ROOT / os.environ["TRANS"]).read_text())
    for k_, p_ in st.get("tp", {}).items():
        tr[k_]["par"] = p_
    return z, tr


def nose(z):
    na, nl = BunMouth(M.BUNSIZE[0]).nasal(); nl = nl * z[6]
    Ln = nl.sum(); n = max(2, int(Ln / 0.2)); e = np.r_[0, np.cumsum(nl)]; g = np.linspace(0, Ln, n + 1)
    a = np.array([np.interp(0.5 * (g[i] + g[i + 1]), 0.5 * (e[:-1] + e[1:]), na) for i in range(n)])
    return a, np.full(n, Ln / n)


def rc(u):
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))


def window(t, a, b, up, down):
    """0 -> 1 over [a, a+up], 1 until b, 1 -> 0 over [b, b+down]; a None = already on."""
    on = np.ones_like(t) if a is None else rc((t - a) / up)
    return np.minimum(on, 1 - rc((t - b) / down))


def mouth_track(ph, pi, z, tr, s0, nfr):
    """Areas (frames x 40), section length, nose port, branch index: vowels' path + consonant movements."""
    t = s0 + np.arange(nfr) * HOP / SR
    vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
    for i, v in enumerate(vs):   # n and m have no shape of their own: the mouth around them is their neighbours'
        if v["lab"] in ("n", "m"):
            nb = [q for q in (vs[i - 1] if i > 0 else None, vs[i + 1] if i + 1 < len(vs) else None) if q and q["lab"] not in ("n", "m")]
            v["pose"] = np.mean([M.pose_full(z, q["lab"]) for q in nb], 0) if nb else M.REST[: len(M.pose_full(z, "ã"))]
            v["pose"] = v["pose"].copy(); v["pose"][7] = 0.0   # the velum is a movement of its own (below)
        else:
            v["pose"] = M.pose_full(z, v["lab"])
    trp = tr.get(str(pi))
    bnd = [(int(i), float(tb)) for i, tb in trp["bounds"]] if trp else []
    par = np.array(trp["par"]) if trp else np.zeros((0, 4))
    poses = np.array([TRm.pose_at(q, vs, bnd, par) for q in t])
    # phrase start: his rest posture, the tongue leaving it as the first sound begins
    rest = M.REST[: poses.shape[1]]
    t_rel = 0.155 if pi == 0 else 1.465        # the first release (the n's tip, the p's lips): jaw and tongue leave rest with it
    w0 = 1 - rc((t - (t_rel - 0.03)) / 0.06)
    poses = w0[:, None] * rest + (1 - w0[:, None]) * poses
    A = np.zeros((nfr, 40)); port = np.zeros(nfr); L = np.zeros(nfr); fr = np.zeros(nfr)
    for k in range(nfr):
        a, L[k], fr[k], port[k] = M.area_of(z, poses[k])
        A[k] = a
        port[k] = port[k] if poses[k, 7] > 0.02 else 0.0
    # the anatomy of the movements: where his tip meets the ridge, where his blade rises, his lips
    an, *_ = M.area_of(z, M.pose_full(z, "n"))
    tip = np.flatnonzero(an[24:] < 0.003) + 24
    tip = tip if len(tip) else np.arange(33, 37)
    Lm = float(np.median(L)); kb = int(round(40 * (1 - 2.0 / Lm)))
    blade = np.arange(kb - 1, kb + 1)
    lips = np.arange(38, 40)
    P = PLAN[pi]
    nport = M.area_of(z, M.pose_full(z, "n"))[3]
    for (a_, b_) in P["velum"]:                      # soft palate opened for the nasals (his n port)
        w = window(t, a_, b_, S["close"], S["close"]); port = (1 - w) * port + w * nport
    if pi == 0:                                      # before the first n, at rest, the palate is open too
        port = np.maximum(port, (1 - rc((t - 0.165) / 0.02)) * nport)
    def squeeze(idx, w, target):
        for i in idx:
            A[:, i] = np.exp((1 - w) * np.log(np.maximum(A[:, i], 1e-6)) + w * np.log(target))
    for (a_, b_, kind) in P["tip"]:
        if kind == "seal":
            squeeze(tip, window(t, a_, b_, S["close"], S["rel_t"]), 1e-6)
        else:   # a final t: near-closure, then (if a t follows) the full seal just before its release
            rel = [r for r in REL[pi] if abs(r - b_) < 0.01]
            w = window(t, a_, b_, 0.02, S["rel_t"])
            squeeze(tip, w, S["tail_leak"])
            if rel:
                squeeze(tip, window(t, rel[0] - 0.02, rel[0], 0.008, S["rel_t"]), 1e-6)
    for (a_, b_) in P["lips"]:
        squeeze(lips, window(t, a_, b_, S["close"], S["rel_p"]), S["lip_leak"])   # (his lips part gently: rel_p fitted)
    for (a_, b_) in P["blade"]:
        squeeze(blade, window(t, a_, b_, 0.02, 0.02), S["blade"])
    return A, float(np.median(L)), port, int(np.clip(round(np.median(fr) * 40), 1, 39)), vs


def voice(ph, vs, s0, n48, breath):
    """His voice: his own cycles at his pitch (as render_his), as a list of (start sample, flow shape x breath)."""
    BK = R.bank()
    for v in vs:
        ins = FF0[(TT >= v["s"]) & (TT <= v["e"]) & (FF0 > 0)]; v["f0"] = float(np.median(ins)) if len(ins) else 250.0
        v["src"] = min(BK, key=lambda b: abs(np.log(b["f0"] / v["f0"])))
    cycles = []
    for a, b in PLAN[R.PHRASES.index(ph)]["voice"]:
        i0, i1 = int(np.ceil((a - s0) * SR)), int((b - s0) * SR)
        tn = s0 + np.arange(i0, i1) / SR
        mids = np.array([0.5 * (v["s"] + v["e"]) for v in vs])
        who = np.array([int(np.argmin([0 if v["s"] <= q <= v["e"] else min(abs(q - v["s"]), abs(q - v["e"])) for v in vs])) for q in tn[::48]])
        who = np.repeat(who, 48)[: len(tn)]
        f0 = np.interp(tn, TT, np.where(FF0 > 0, FF0, np.nan))
        bad = ~np.isfinite(f0)
        if bad.any():   # outside his tracked pitch: hold his nearest pitch
            good = np.flatnonzero(~bad)
            f0[bad] = np.interp(np.flatnonzero(bad), good, f0[good]) if len(good) else 250.0
        phs = np.cumsum(f0 / SR); k = np.floor(phs).astype(int)
        cut = np.r_[0, np.flatnonzero(np.diff(k)) + 1, len(k)]
        prev = None; xf = 0
        nxt = lambda q: (q["cyc"][q["order"][q["k"] % len(q["order"])]], q.__setitem__("k", q["k"] + 1))[0]
        for c0, c1 in zip(cut[:-1], cut[1:]):
            tc = tn[c0]; src = vs[who[c0]]["src"]
            if prev is not None and src is not prev and xf == 0:
                xf, old = R.XF, prev
            cyc = nxt(src)
            if xf > 0:
                u_ = 1 - xf / (R.XF + 1); cyc = (1 - u_) * nxt(old) + u_ * cyc; xf -= 1
            prev = src
            g = 10 ** (np.interp(tc, breath[0], breath[1]) / 20) if breath is not None else 1.0
            g *= min(1.0, rc((tc - a) / 0.012), rc((b - tc) / 0.015))
            fl = cyc - cyc.min()
            u = phs[c0: c1] - k[c0]
            cycles.append((i0 + c0, np.interp(u, np.linspace(0, 1, len(fl), endpoint=False), fl) * g))
    return cycles


_IR = {}


def fd_ir(a, L, kv, port, z):
    """His mouth's response at this instant (the fitted frequency-domain mouth, exactly as the voice always
    went through it): sound at the listener per unit of air through the cords."""
    key = (tuple(np.round(np.log(np.maximum(a, 1e-6)), 2)), round(float(L), 3), round(float(port), 4))
    if key not in _IR:
        f = np.maximum(R.fH, 1.0); a_ = np.maximum(a, 1e-4)
        H = M.B.tube_H_nose(a_, L, f, kv / 40.0, max(port, 1e-4), z[6], z[7]) * M.B.head_baffle(f, z[1])
        fc = 1.84 * 35000 / (np.pi * 2 * np.sqrt(a_.max() / np.pi)); H = H / (1 + (f / fc) ** 8); H[0] = 0
        h = np.fft.irfft(H, R.NFT); h *= np.r_[np.ones(R.NFT // 2), np.hanning(R.NFT)[R.NFT // 2:]]
        if len(_IR) > 6000:
            _IR.clear()
        _IR[key] = h
    return _IR[key]


def render_phrase(pi, z, tr, breath=None, seed=0, parts=False):
    """Voice through his mouth (frequency-domain, as always) + air through his mouth (time-domain, new): the
    same mouth shapes. The air run carries his lungs' steady flow (no voice) through the moving mouth and the
    parting cords: every hiss, burst and pop comes from it, and it says how much push is left across his cords
    (a sealed mouth fills up), which sets how strongly his voice sounds at each moment."""
    ph = R.PHRASES[pi]
    s0, e0 = ph[0][1] - 0.03, ph[-1][2] + 0.06
    n48 = int((e0 - s0) * SR); nfr = n48 // HOP + 2
    A, L, port, kv, vs = mouth_track(ph, pi, z, tr, s0, nfr)
    t48 = s0 + np.arange(n48) / SR
    ag_mean = 10 ** z[M.NG] * S["ag_scale"]   # his cords' mean opening while voicing
    venv = np.zeros(n48)
    for a_, b_ in PLAN[pi]["voice"]:
        venv = np.maximum(venv, window(t48, a_, b_ - 0.015, 0.012, 0.015))   # his voice is gone where his pitch ends
    ab48 = np.zeros(n48)
    for a_, b_, kind in PLAN[pi]["ab"]:              # the cords part (aspiration / the soft S's airflow)
        if kind == "t":
            mid = 0.5 * (a_ + b_); half = 0.5 * (b_ - a_)
            ab48 = ab48 + S["ab_t"] * rc(1 - np.abs(t48 - mid) / half)
        else:
            ab48 = ab48 + S["ab_s"] * window(t48, a_, b_, 0.03, 0.03)
    ag48 = ag_mean * venv + ab48
    # parted cords barely touch: the buzz weakens (and turns breathy) as their resting gap grows (HLsyn's rule)
    vib = ag_mean / (ag_mean + ab48)
    ag = np.repeat(ag48, TD.SRT // SR)
    T = len(ag)
    na, ndx = nose(z)
    y_air, p0, remax, reidx = TD._sim(np.ascontiguousarray(A), np.full(40, L / 40), kv, port, ag, np.full(T, S["plung"]), na, ndx,
                        PM.TISSUE["visc"] * M.B.NOSE_SURF ** 2, z[7], 1.0, 1.0, 1.0, True, S["gnoise"], seed,
                        HOP * (TD.SRT // SR), True, TD.LC0, TD.LCK, TD.LPK, S.get("pump", 1.0))
    y_air = TD.to48(TD.head_filter(y_air, z[1], TD.SRT))[:n48] * S["air"]
    push = np.sqrt(np.clip(1 - uniform_filter1d(p0, int(S["push_ms"] * 192))[::TD.SRT // SR][:n48] / S["plung"], 0, 1))   # pressure left across the cords (the mouth's pressure changes smoothly)
    # the voice: his cycles, in physical units (mean opening x lung-driven speed), through his mouth at that instant
    cycles = voice(ph, vs, s0, n48, breath)
    allf = np.concatenate([c for _, c in cycles]) if cycles else np.ones(1)
    unit = ag_mean * np.sqrt(2 * S["plung"] / PM.RHO) / max(np.mean(allf[allf > 0]), 1e-12)
    y_v = np.zeros(n48 + R.NFT)
    rng = np.random.default_rng(100 + seed + pi)
    cmean = max(np.mean(allf[allf > 0]), 1e-12)
    for i0, c in cycles:
        k = min(nfr - 1, i0 // HOP)
        j = min(i0, n48 - 1)
        U = c * unit * push[j] * vib[j]                       # cm^3/s through the cords over this cycle
        # his breath: turbulence where the air jets through his opening cords (the same law as every jet)
        ag_c = np.maximum(c / cmean * ag_mean, 1e-6)
        Re = 2 * U / (TD.NU * np.sqrt(np.pi * ag_c))
        if S["gnoise"] > 0 and Re.max() > TD.RE_C:
            v_ = U / ag_c; d_ = 2 * np.sqrt(ag_c / np.pi); fc = float(np.mean(0.2 * v_ / d_))
            ka = np.exp(-2 * np.pi * fc / SR); w_ = rng.standard_normal(len(c))
            from scipy.signal import lfilter
            nz = lfilter([(1 - ka) ** 2], [1, -2 * ka, ka * ka], w_)
            Pn = S["gnoise"] * np.maximum(Re ** 2 - TD.RE_C ** 2, 0) * 1e-6 * nz
            U = U + Pn * ag_c ** 2 / (PM.RHO * np.maximum(U, 1e-6))   # through the cords' own resistance (rho U / A^2)
        o = np.convolve(U, fd_ir(A[k], L, kv, port[k], z))
        y_v[i0: i0 + len(o)] += o[: len(y_v) - i0]
    y_v = y_v[:n48]
    render_phrase.diag = (remax, reidx, s0)
    if parts:
        return y_v, y_air, s0, vs, push
    return y_v + y_air, s0, vs


def env_db(sig, t0, times, win=0.025):
    w = int(win * SR); out = []
    for t in times:
        c = int((t - t0) * SR); seg = sig[max(0, c - w // 2): c + w // 2]
        out.append(10 * np.log10(np.mean(seg ** 2) + 1e-20) if len(seg) else -200.0)
    return np.array(out)


def render(z, tr, seed=0):
    """Both phrases on the clip's timeline, each at his loudness over his voiced sounds."""
    y = np.zeros(len(X))
    for pi, ph in enumerate(R.PHRASES):
        y1, s0, vs = render_phrase(pi, z, tr, None, seed)
        bt = np.arange(vs[0]["s"], vs[-1]["e"] + 0.005, 0.005)
        ins = np.array([any(v["s"] <= q <= v["e"] for v in vs) for q in bt])
        bd = env_db(X, 0.0, bt) - env_db(y1, s0, bt); bd = uniform_filter1d(bd[ins], 5); bd -= bd.max()
        yy, s0, vs = render_phrase(pi, z, tr, (bt[ins], bd), seed)
        rx = np.sqrt(np.mean(np.concatenate([X[int(v["s"] * SR): int(v["e"] * SR)] for v in vs]) ** 2))
        ry = np.sqrt(np.mean(np.concatenate([yy[int((v["s"] - s0) * SR): int((v["e"] - s0) * SR)] for v in vs]) ** 2))
        i0 = int(s0 * SR); y[i0: i0 + len(yy)] += yy[: len(y) - i0] * rx / ry
    return y


if __name__ == "__main__":
    z, tr = load(ARGS[0] if ARGS else "models/perc_state_td.json")
    y = render(z, tr)
    (ROOT / "out/td").mkdir(parents=True, exist_ok=True)
    np.save(ROOT / "out/td/td_render.npy", y)
    print("ok", float(np.abs(y).max()))
