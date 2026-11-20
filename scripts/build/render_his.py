"""PLAN steps 2-3: his real voice, buzz by buzz, through his one mouth.

Voice: his voice bank (models/his_voice.npz, recovered from the clip by quasi-closed-
  phase inverse filtering). Each cycle is one of his real cycles, taken in his own order
  (forward, then back) from the bank sound nearest in pitch (one per sound), and played at the pitch
  wanted (a real cycle keeps its shape at a higher pitch; it just runs faster).
Mouth: the one mouth fitted to that voice (mouth_inverse SRC=his). Every buzz goes
  through the mouth's shape at the instant it happens, and its ring is left to die
  away fully; all rings add. "m" has the lips sealed.
Loudness: breath pressure per sound, set from the clip (scales whole buzzes).
Nothing is done to the sound afterwards. Consonants are phase C (silent here).

    ZFILE=models/mouth_inverse_H1.json python scripts/build/render_his.py
"""
import json, os, sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.fft import idct
from scipy.ndimage import uniform_filter1d
from scipy.signal import lfilter, resample_poly

os.environ.update(SRC="his", CHMIN="0.005", F1GUARD="1")
ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "scripts", ROOT / "scripts/build", ROOT / "analysis/physics"):
    sys.path.insert(0, str(p))
sys.argv = sys.argv[:1]
import mouth_inverse as M  # noqa: E402
import transitions as TR  # noqa: E402
import ee_decompose as DC  # noqa: E402
from build_catalogue import PHRASES  # noqa: E402

SR = 48000; NFT = 8192
_zj = json.loads((ROOT / os.environ.get("ZFILE", "models/mouth_inverse_H1.json")).read_text())
Z = M.pad(_zj["z"])   # brought up to the current layout
if "rest" in _zj:
    M.REST[: len(_zj["rest"])] = _zj["rest"]
TAG = os.environ.get("TAG", "")
fH = np.fft.rfftfreq(NFT, 1 / SR)
_ir = {}


def mouth_ir(pose9, sealed):
    key = (tuple(np.round(pose9, 2)), sealed)
    if key not in _ir:
        a, L, frac, port = M.area_of(Z, pose9)
        if sealed:
            a = M.seal(a, "m")
        f = np.maximum(fH, 1.0)
        M.body(Z)
        H = M.B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * M.B.head_baffle(f, Z[1])
        fc = 1.84 * 35000 / (np.pi * 2 * np.sqrt(a.max() / np.pi))   # plane waves hold below the first cross-mode
        H = H / (1 + (f / fc) ** 8); H[0] = 0
        h = np.fft.irfft(H, NFT); h *= np.r_[np.ones(NFT // 2), np.hanning(NFT)[NFT // 2:]]   # ring dies fully
        _ir[key] = h
    return _ir[key]


def bank():
    d = np.load(ROOT / "models/his_voice.npz"); B = []
    for f0, ii in M.bank_pools(d):          # his cycles pooled by pitch, in the clip's order
        cyc = []
        for i in ii:
            c = M.his_cycles(d, i)   # his cycles, recovery error averaged away (Da Boss approved)
            # loudness is the breath's job: each cycle's slow level drift (from where it was recorded,
            # ~9 cycles) is taken out; its fast cycle-to-cycle flicker (his shimmer) stays
            lv = np.log(np.array([np.ptp(q) for q in c]))
            slow = np.convolve(np.pad(lv, 4, mode="edge"), np.ones(9) / 9, mode="valid")
            cyc += [q / np.exp(sl) for q, sl in zip(c, slow)]
        B.append(dict(f0=f0, cyc=cyc, order=list(range(len(cyc))) + list(range(len(cyc) - 2, 0, -1)), k=0))
    return B


def at_period(c, P):
    """His cycle, played at period P samples (same shape, faster or slower)."""
    return np.interp(np.linspace(0, 1, P, endpoint=False), np.linspace(0, 1, len(c), endpoint=False), c)


_TR_OVERRIDE = None   # transitions handed in directly (perceptual tuning)
CONS = os.environ.get("CONS", "1") == "1"   # the consonants (provisional, Da Boss: test whether their absence is the problem)
TR_VEL = 7
WANDER = float(os.environ.get("WANDER", "0"))   # PLAN step 4 ladder: 0 = frozen ... 1 = full amount
TAU_CL = float(os.environ.get("TAU_CL", "0.01" if M.GEST else "1e9"))   # s: how fast the voice's push falls once the mouth closes (pressure builds up)
FLOOR_CL = float(os.environ.get("FLOOR_CL", "0.5" if M.GEST else "1.0"))   # the push it settles at (fraction) once the closure holds
CL_LEAD = float(os.environ.get("CL_LEAD", "0.015"))
ONSET_EARLY = os.environ.get("ONSET_EARLY", "1") == "1"   # voicing starts with his own pitch, before the vowel label   # s: closure movement starts this much before the vowel label ends
BREATH = float(os.environ.get("BREATH", "0.003"))   # pulsed aspiration (vocal-fold turbulence); 0.003 matches his measured noise between tones
_BRNG = np.random.default_rng(11)
XF = int(os.environ.get("XF", "4"))   # cycles over which the voice blends when it changes pool
HOLD = float(os.environ.get("HOLD", "0.4"))   # share of each sound the mouth holds its position (the rest is glide)


# GEST stops (2026-11-20): a stop is its articulator closing and opening on top of whatever the rest of
# the mouth is doing. t: the tongue tip seals at the ridge (the same tip gesture as "n"), soft palate shut;
# p: the lips (the same lip gesture as "m"). Before, a "t" closure pulled the WHOLE tongue into the fitted
# "n" shape and the vowel after it started already open, with no tip release: the tongue body's swing
# read as a "k" and nothing said "tip".
STOPG = {"tʰ": ("n", [0, 2, 3]), "p": ("m", [0, 5])}         # whose gesture (the same as n, m), which controls (jaw (+ tongue front) + articulator)
CLOSE_T = float(os.environ.get("CLOSE_T", "0.015"))          # s: closing movement (tip and lips are fast)
REL_T = float(os.environ.get("REL_T", "0.025"))              # s: opening movement after the release
TAU_OFF = float(os.environ.get("TAU_OFF", "0.02"))           # s: how fast the voice dies inside a sealed mouth (fitted to his two closures)
REL_TP = float(os.environ.get("REL_TP", str(REL_T)))       # s: the lips' opening movement (lips are heavier than the tip)
REST_OUT = float(os.environ.get("REST_OUT", "0.04"))        # s: the tongue body leaving rest (his "p": 2nd resonance rises ~40 ms)
SEAL_A = 0.003                                               # cm^2: an opening this wide lets the air burst through


def stop_gestures(ph, vs, poses, s0, hop):
    """Superimpose each stop's closure-and-release on the mouth's movement. Weight w: 0 = the vowel
    path, 1 = the stop's own position for its controls (soft palate shut)."""
    poses = poses.copy(); t = s0 + np.arange(len(poses)) * hop / SR
    for j, (lab, s, e, _) in enumerate(ph):
        if lab not in STOPG:
            continue
        own_s, own = STOPG[lab]; g = M.pose_full(Z, own_s)
        prev = [v for v in vs if v["e"] <= s + 0.003 and s - v["e"] < 0.25]
        tc = prev[-1]["e"] - CL_LEAD if prev else -1.0                      # closing starts (or: shut from the start)
        tr = s - 0.003 if lab == "tʰ" else s + 0.01                            # the release (the burst)
        rc = lambda u: 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))
        # the seal breaks part-way through the opening movement (a tip pressed into the ridge has to come
        # off it first): find that point, and time the movement so the seal breaks AT the release
        kr = int(np.clip(round((tr - s0) * SR / hop), 0, len(poses) - 1))

        def gap(wq):
            p_ = poses[kr].copy(); p_[own] = (1 - wq) * p_[own] + wq * g[own]; p_[TR_VEL] *= (1 - wq)
            a_ = M.area_of(Z, p_)[0]
            if lab == "p":   # the lips seal below 0.04 (as in the voiced render)
                return a_[-1] if p_[5] >= 0.04 else 0.0
            return a_[int(0.8 * len(a_)): -2].min()
        lo_, hi_ = 0.0, 1.0                     # w at which the gap first exceeds a real opening (bisection)
        for _ in range(14):
            mid = 0.5 * (lo_ + hi_)
            lo_, hi_ = (mid, hi_) if gap(mid) > SEAL_A else (lo_, mid)
        wb = lo_ if gap(lo_) > SEAL_A else 0.0
        rel_t = REL_TP if lab == "p" else REL_T
        t_open = tr - np.arccos(np.clip(2 * wb - 1, -1, 1)) / np.pi * rel_t   # the movement starts here
        w = np.where(t < t_open, rc((t - tc) / CLOSE_T), 1 - rc((t - t_open) / rel_t))
        for c in own:
            poses[:, c] = (1 - w) * poses[:, c] + w * g[c]
        poses[:, TR_VEL] = (1 - w) * poses[:, TR_VEL]
    return poses


def pose_track(vs, s0, n, hop):
    """Each sound's position held through its middle; smooth (raised-cosine) glides across each
    boundary, from one held position to the next. The mouth never jumps."""
    t = (np.arange(n // hop + 1) * hop) / SR + s0
    knots = []
    for v in vs:
        mid, half = (v["s"] + v["e"]) / 2, (v["e"] - v["s"]) * HOLD / 2
        pv = v.get("pose", M.pose_full(Z, v["lab"]))
        knots += [(mid - half, pv), (mid + half, pv)]
    P = np.zeros((len(t), len(knots[0][1])))
    for i, ti in enumerate(t):
        if ti <= knots[0][0]:
            P[i] = knots[0][1]; continue
        if ti >= knots[-1][0]:
            P[i] = knots[-1][1]; continue
        k = max(j for j in range(len(knots) - 1) if knots[j][0] <= ti)
        (ta, pa), (tb, pb) = knots[k], knots[k + 1]
        u = 0.0 if tb <= ta else (ti - ta) / (tb - ta); u = 0.5 - 0.5 * np.cos(np.pi * u)
        P[i] = pa + u * (pb - pa)
    return P


def voiced_runs(vs):
    runs = []
    for v in vs:
        if runs and abs(v["s"] - runs[-1][1]) < 0.003:
            runs[-1][1] = v["e"]
        else:
            runs.append([v["s"], v["e"]])
    return runs


def render_phrase(ph, x, tt, ff0, BK, breath=None):
    """breath: (times, dB) smooth breath-pressure contour; None = steady."""
    global _BRNG
    _BRNG = np.random.default_rng(11 + PHRASES.index(ph))   # the same mouth makes the same sound: fixed breath noise
    s0, e0 = ph[0][1] - 0.02, ph[-1][2] + 0.03; n = int((e0 - s0) * SR)
    vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
    for v in vs:   # each instance's position (GEST: a consonant's own gesture on the mouth its neighbours carry)
        v["pose"] = M.pose_inst(Z, v["lab"], M.CTX.get((v["lab"], round(v["s"], 3))))
    hop = 240
    if os.environ.get("TRANS"):   # fitted movement between sounds (transitions.py)
        import transitions as TR
        _all = _TR_OVERRIDE if _TR_OVERRIDE is not None else json.loads((ROOT / os.environ["TRANS"]).read_text())
        tr = _all.get(str(PHRASES.index(ph)))
        if tr:
            bnd = [(int(i), float(tb)) for i, tb in tr["bounds"]]; par = np.array(tr["par"])
            poses = np.array([TR.pose_at(s0 + k * hop / SR, vs, bnd, par) for k in range(n // hop + 1)])
        else:
            poses = pose_track(vs, s0, n, hop)
    else:
        poses = pose_track(vs, s0, n, hop)
    nfr = len(poses)
    if WANDER > 0:   # a mouth that isn't frozen (PLAN step 4): slow smooth wanders of jaw, tongue and lips
        rng_w = np.random.default_rng(23 + PHRASES.index(ph)); tw = np.arange(nfr) * hop / SR
        for j_, amp in ((0, 0.06), (1, 0.10), (2, 0.06), (5, 0.04)):      # jaw, tongue body, tongue front, lips
            w_ = np.zeros(nfr)
            for _ in range(4):                                           # a few slow components, 1-6 Hz
                w_ += np.sin(2 * np.pi * rng_w.uniform(1.0, 6.0) * tw + rng_w.uniform(0, 2 * np.pi)) / 2.0
            poses[:, j_] = poses[:, j_] + WANDER * amp * w_
    runs = voiced_runs(vs); RAMP = float(os.environ.get("RAMP", "0.012")); RAMP_OFF = float(os.environ.get("RAMP_OFF", "0.03"))
    if CONS:   # voiced closures: his voice keeps humming while the mouth closes for the next consonant
        labs = [q[0] for q in ph]
        for r_ in runs:
            b = r_[1]; te = b
            while te - b < 0.1 and np.interp(te + 0.005, tt, ff0) > 0:
                te += 0.005
            if te - b < 0.015:
                continue
            v = [q for q in vs if abs(q["e"] - b) < 0.003][0]
            j = next((i for i, q in enumerate(ph) if q[1] >= b - 0.003 and q[0] not in M.SOUNDS), None)
            nxt = ph[j][0] if j is not None else None
            if M.GEST:   # the stop is a gesture of its own (below); the voice keeps going while his pitch does
                stop = nxt in STOPG or nxt == "_"
                r_.append(b - CL_LEAD + CLOSE_T if stop else 1e9)   # sealed from here: the push across the folds falls
                r_[1] = te
                if stop:     # ... and then fades inside the sealed mouth until the release, never cut dead
                    rel = [q[1] for q in ph if q[0] in STOPG and q[1] > b]
                    if rel and rel[0] - te > 0.005:
                        r_.append(te); r_[1] = rel[0] - 0.004
                continue
            close = M.pose_full(Z, v["lab"]).copy()
            if nxt in ("_", "tʰ"):            # tongue tip seals at the ridge (the "n" position, nose shut)
                close = M.pose_full(Z, "n").copy(); close[TR_VEL] = 0.0
            k0 = int((b - CL_LEAD - s0) * SR) // hop; k1 = min(nfr - 1, int((te - s0) * SR) // hop)   # the tongue starts closing CL_LEAD before the label
            p0 = poses[min(k0, nfr - 1)].copy()
            for k in range(k0, k1 + 1):
                u = min(1.0, (k - k0) * hop / SR / 0.015); u = 0.5 - 0.5 * np.cos(np.pi * u)
                poses[k] = p0 + u * (close - p0)
            r_.append(b)   # where the mouth starts closing: the voice's push falls from here
            r_[1] = te
        if ONSET_EARLY:   # his voice starts when his own pitch starts, even if that is before the vowel's label
            for r_ in runs:
                a = r_[0]; ta = a
                while a - ta < 0.04 and np.interp(ta - 0.005, tt, ff0) > 0:
                    ta -= 0.005
                if a - ta >= 0.005:
                    v = [q for q in vs if abs(q["s"] - a) < 0.003][0]
                    pb = [q for q in ph if q[2] >= a - 0.003 and q[2] <= a + 0.01 and q[0] not in M.SOUNDS]
                    pre = M.pose_full(Z, v["lab"]).copy()
                    if pb and pb[-1][0] == "p":   # still at the lips: they are just opening
                        pre[5] = 0.05
                    k0 = max(0, int((ta - s0) * SR) // hop); k1 = int((a - s0) * SR) // hop
                    p1 = poses[min(k1, nfr - 1)].copy()
                    for k in range(k0, min(k1, nfr)):
                        u = (k - k0) / max(1, k1 - k0); u = 0.5 - 0.5 * np.cos(np.pi * u)
                        poses[k] = pre + u * (p1 - pre)
                    r_[0] = ta
    if CONS and M.GEST and ph[0][0] in STOPG:   # a phrase that opens with a stop starts from REST (as the first "n"
        tq = s0 + np.arange(nfr) * hop / SR      # does): the tongue leaves rest as the lips/tip let go
        rel0 = ph[0][1] + (0.01 if ph[0][0] == "p" else -0.003)
        wr = np.where(tq < rel0, 1.0, 1 - (0.5 - 0.5 * np.cos(np.pi * np.clip((tq - rel0) / REST_OUT, 0, 1))))
        rest = M.REST[: poses.shape[1]]
        poses[:] = wr[:, None] * rest + (1 - wr[:, None]) * poses
    if CONS and M.GEST:   # stops as gestures on the moving mouth (articulatory phonology)
        poses[:] = stop_gestures(ph, vs, poses, s0, hop)
    render_phrase.poses = (poses, s0, hop)   # the mouth's movement, for the consonant noises
    render_phrase.onsets = sorted(r_[0] for r_ in runs)   # where the voice starts (the breath stops there)
    y = np.zeros(n + NFT + 2000)
    for v in vs:                                    # one run of his own cycles per sound
        ins = ff0[(tt >= v["s"]) & (tt <= v["e"]) & (ff0 > 0)]; v["f0"] = float(np.median(ins)) if len(ins) else 250.0
        v["src"] = min(BK, key=lambda b: abs(np.log(b["f0"] / v["f0"])))
    for rr_ in runs:
        a, b = rr_[0], rr_[1]
        # the folds keep one continuous rhythm through a voiced stretch; each buzz starts at its exact
        # instant (between samples where it falls), so no rounding jitter and no restart at sound joins
        i0, i1 = int(np.ceil((a - s0) * SR)), int((b - s0) * SR)
        tn = s0 + np.arange(i0, i1) / SR
        who = np.array([max([j for j, v in enumerate(vs) if v["s"] - 1e-6 <= q] or [0]) for q in tn])
        f0 = np.interp(tn, tt, np.where(ff0 > 0, ff0, np.nan))
        bad = ~(np.isfinite(f0) & (f0 > 100) & (f0 < 900)); f0[bad] = np.array([vs[j]["f0"] for j in who])[bad]
        ph = np.cumsum(f0 / SR); k = np.floor(ph).astype(int)
        cut = np.r_[0, np.flatnonzero(np.diff(k)) + 1, len(k)]
        prev, xf = None, 0
        nxt = lambda q: (q["cyc"][q["order"][q["k"] % len(q["order"])]], q.__setitem__("k", q["k"] + 1))[0]
        for c0, c1 in zip(cut[:-1], cut[1:]):
            t = tn[c0]; v = vs[who[c0]]; src = v["src"]
            if prev is not None and src is not prev and xf == 0:
                xf, old_src = XF, prev            # the voice changes pool: blend over a few cycles, no jump
            cyc = nxt(src)
            if xf > 0:
                u = 1 - xf / (XF + 1); cyc = (1 - u) * nxt(old_src) + u * cyc; xf -= 1
            prev = src
            g = 10 ** (np.interp(t, breath[0], breath[1]) / 20) if breath is not None else 1.0
            g *= min(1.0, 0.5 - 0.5 * np.cos(np.pi * min(1.0, (t - a) / RAMP)), 0.5 - 0.5 * np.cos(np.pi * min(1.0, max(0.0, b - t) / RAMP_OFF)))
            if len(rr_) > 2 and t > rr_[2]:   # closed mouth: air builds up behind the closure, the push across the folds falls
                g *= FLOOR_CL + (1 - FLOOR_CL) * np.exp(-(t - rr_[2]) / TAU_CL)   # falls quickly, then holds (walls yield, a little air keeps flowing)
            if len(rr_) > 3 and t > rr_[3]:   # GEST: past his last clear pitch the folds keep buzzing, ever weaker, as the
                g *= np.exp(-(t - rr_[3]) / TAU_OFF)   # pressure behind the sealed mouth evens out (no dead cut)
            u = ph[c0: c1] - k[c0]
            pulse = np.interp(u, np.linspace(0, 1, len(cyc), endpoint=False), cyc) * g
            if BREATH > 0:   # pulsed aspiration: turbulence through the open fold gap, riding on this cycle's airflow
                fl = pulse - pulse.min()                                    # the cycle's airflow (0 when shut)
                nz_ = lfilter([1.0], [1.0, -0.95], _BRNG.standard_normal(len(pulse)))   # turbulence as flow: falls with
                nz_ /= nz_.std() + 1e-12                                    # frequency, so after radiation it is broad
                pulse = pulse + BREATH * nz_ * fl
            c = i0 + c0; pz = poses[min(c // hop, nfr - 1)]
            h = mouth_ir(pz, bool(pz[5] < 0.04))           # the lips seal as they actually close
            out = np.convolve(pulse, h); y[c: c + len(out)] += out[: len(y) - c]
    return y[:n], s0, e0, vs


def envelope_db(sig, t0, times, win=0.025):
    w = int(win * SR); out = []
    for t in times:
        c = int((t - t0) * SR); seg = sig[max(0, c - w // 2): c + w // 2]
        out.append(10 * np.log10(np.mean(seg ** 2) + 1e-14) if len(seg) else -140.0)
    return np.array(out)


def frame_score(x, y, s0, vs, f0s):
    """Whole-phrase likeness, transitions included: every 10 ms of voiced sound, his spectrum
    shape vs the model's (third-octave bands 100 Hz-12 kHz, each frame's level removed), rms dB."""
    edges = 200 * 2 ** (np.arange(0, 19) / 3); edges = edges[edges <= 12800]
    N = 2048; f = np.fft.rfftfreq(N, 1 / SR); out = []
    for v in vs:
        for t in np.arange(v["s"] + 0.005, v["e"] - 0.005, 0.01):
            def bands(sig, c):
                seg = sig[c - N // 2: c + N // 2]
                if len(seg) < N:
                    return None
                S = np.abs(np.fft.rfft(seg * np.hanning(N))) ** 2
                b = np.array([10 * np.log10(S[(f >= lo) & (f < hi)].mean() + 1e-14) for lo, hi in zip(edges[:-1], edges[1:])])
                return b - b.max()
            bh = bands(x, int(t * SR)); bm = bands(y, int((t - s0) * SR))
            if bh is None or bm is None:
                continue
            ok = bh > -50
            old = float(np.sqrt(np.mean((np.maximum(bm, -50) - bh)[ok] ** 2)))
            fl = TR.clip_floor(x, t); mb = np.maximum(bm, fl)
            ok = (bh > fl) | (mb > fl + 3)   # judged where his sound, or the model's, stands above the hiss
            w = np.clip((np.maximum(bh, mb) - fl) / 40.0, 0.05, 1.0)[ok]   # audible: his or the model's
            d = (mb - np.maximum(bh, fl))[ok]
            out.append((v["lab"], t, float(np.sqrt(np.sum(w * d ** 2) / np.sum(w))), old, float(np.sqrt(np.mean(d ** 2)))))
    return out


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    x = resample_poly(x, SR, sr) if sr != SR else x
    Pt = pm.Sound(x, SR).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff0 = Pt.selected_array["frequency"]
    outs = []
    for pi, ph in enumerate(PHRASES):
        y1, s0, e0, vs = render_phrase(ph, x, tt, ff0, bank())
        # breath pressure: follows his own loudness contour, as smooth as breath is (25 ms), over voiced stretches
        bt = np.arange(vs[0]["s"], vs[-1]["e"] + 0.005, 0.005)
        inside = np.array([any(v["s"] <= q <= v["e"] for v in vs) for q in bt])
        bd = envelope_db(x, 0.0, bt) - envelope_db(y1, s0, bt); bd = bd[inside]; bt = bt[inside]
        from scipy.ndimage import uniform_filter1d as uf
        bd = uf(bd, 5); bd -= bd.max()
        print(f"  phrase {pi + 1} breath range {bd.min():.0f}..0 dB")
        y, s0, e0, vs = render_phrase(ph, x, tt, ff0, bank(), (bt, bd))
        if CONS:   # his consonants, from the same mouth (provisional)
            import consonants as CN
            CN.POSES = render_phrase.poses; CN.ONSETS = render_phrase.onsets
            y = y + CN.layer(ph, s0, len(y), x, M, Z, y)
        outs.append((y, s0, e0, vs))
    nz = lambda v: v / np.abs(v).max() * 0.7
    gap = np.zeros(int(0.6 * SR)); pieces = []
    for y, s0, e0, vs_ in outs:   # played at the same loudness (rms over his voiced sounds), not the same peak
        xs = x[int(s0 * SR): int(e0 * SR)]
        rx = np.sqrt(np.mean(np.concatenate([x[int(v["s"] * SR): int(v["e"] * SR)] for v in vs_]) ** 2))
        ry = np.sqrt(np.mean(np.concatenate([y[int((v["s"] - s0) * SR): int((v["e"] - s0) * SR)] for v in vs_]) ** 2))
        k = 0.7 / max(np.abs(xs).max(), np.abs(y).max() * rx / ry)
        pieces += [xs * k, gap, y * rx / ry * k, gap, gap]
    sf.write(ROOT / f"out/build/render_his{TAG}_clip_vs_model.wav", np.concatenate(pieces), SR)
    sf.write(ROOT / f"out/build/render_his{TAG}_model.wav", np.concatenate([q for y, *_ in outs for q in (nz(y), gap)]), SR)
    np.save(ROOT / f"out/build/render_his{TAG}_outs.npy", np.array([dict(y=y, s0=s0, e0=e0, vs=vs) for y, s0, e0, vs in outs], dtype=object), allow_pickle=True)
    # checks
    errs = []
    for y, s0, e0, vs in outs:
        for v in vs:
            seg = y[int((v["s"] - s0) * SR): int((v["e"] - s0) * SR)]
            p = pm.Sound(seg, SR).to_pitch_cc(time_step=0.01, pitch_floor=100, pitch_ceiling=900).selected_array["frequency"]
            h = pm.Sound(seg, SR).to_harmonicity_cc(time_step=0.01, minimum_pitch=150).values[0]; h = h[h > -100]
            hc = pm.Sound(x[int(v["s"] * SR): int(v["e"] * SR)], SR).to_harmonicity_cc(time_step=0.01, minimum_pitch=150).values[0]; hc = hc[hc > -100]
            try:
                dm = DC.decompose(y[int((v["s"] - s0 - 0.005) * SR): int((v["e"] - s0 + 0.005) * SR)], SR, "rm")
                dh = DC.decompose(x[int((v["s"] - 0.005) * SR): int((v["e"] + 0.005) * SR)], SR, "rh")

                def lv(d):
                    A = d["A"][~np.isnan(d["A"][:, 0])]; L = 20 * np.log10(A + 1e-12); return np.nanmedian(L - L[:, :1], 0)[:20]
                Lm, Lh = lv(dm), lv(dh); ok = Lh[1:] > -55
                e = float(np.sqrt(np.mean((np.maximum(Lm[1:], -58) - np.maximum(Lh[1:], -58))[ok] ** 2))); errs.append(e); es = f"{e:4.1f}"
            except Exception:
                es = " n/a"
            print(f"  {v['lab']:3} {v['s']:.2f}s: pitched {np.mean(p > 0) * 100:3.0f}%  clean-tone {np.median(h) if len(h) else np.nan:4.1f} dB (his {np.median(hc) if len(hc) else np.nan:4.1f})  tone error {es} dB")
    if errs:
        print(f"  overall tone error {np.sqrt(np.mean(np.square(errs))):.2f} dB")
    fs = [q for y, s0, e0, vs in outs for q in frame_score(x, y, s0, vs, None)]
    per = {}
    for lab, t, e, *_ in fs:
        per.setdefault(lab, []).append(e)
    print("  whole-phrase likeness (every 10 ms, transitions included), rms dB: " + "  ".join(f"{k} {np.sqrt(np.mean(np.square(v))):.1f}" for k, v in per.items()))
    print(f"  WHOLE-PHRASE: {np.sqrt(np.mean(np.square([q[2] for q in fs]))):.2f} dB over {len(fs)} frames "
          f"(bands weighted by audibility; all bands above the hiss equally: {np.sqrt(np.mean(np.square([q[4] for q in fs]))):.2f}; "
          f"old judge, bands within 50 dB of the loudest: {np.sqrt(np.mean(np.square([q[3] for q in fs]))):.2f})")


if __name__ == "__main__":
    main()
