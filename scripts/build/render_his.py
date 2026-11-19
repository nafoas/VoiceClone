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
from scipy.signal import resample_poly

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
Z = np.array(json.loads((ROOT / os.environ.get("ZFILE", "models/mouth_inverse_H1.json")).read_text())["z"])
TAG = os.environ.get("TAG", "")
fH = np.fft.rfftfreq(NFT, 1 / SR)
_ir = {}


def mouth_ir(pose9, sealed):
    key = (tuple(np.round(pose9, 2)), sealed)
    if key not in _ir:
        a0, L, frac, port = M.tube(pose9, Z[0], Z[M.SH["lar"]])
        a = a0 * np.exp(idct(np.r_[Z[M.SH["shape"]], np.zeros(M.NS - M.NF)], norm="ortho"))
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


XF = int(os.environ.get("XF", "4"))   # cycles over which the voice blends when it changes pool
HOLD = float(os.environ.get("HOLD", "0.4"))   # share of each sound the mouth holds its position (the rest is glide)


def pose_track(vs, s0, n, hop):
    """Each sound's position held through its middle; smooth (raised-cosine) glides across each
    boundary, from one held position to the next. The mouth never jumps."""
    t = (np.arange(n // hop + 1) * hop) / SR + s0
    knots = []
    for v in vs:
        mid, half = (v["s"] + v["e"]) / 2, (v["e"] - v["s"]) * HOLD / 2
        knots += [(mid - half, Z[M.PO[v["lab"]]]), (mid + half, Z[M.PO[v["lab"]]])]
    P = np.zeros((len(t), 9))
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
    s0, e0 = ph[0][1] - 0.02, ph[-1][2] + 0.03; n = int((e0 - s0) * SR)
    vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
    hop = 240
    if os.environ.get("TRANS"):   # fitted movement between sounds (transitions.py)
        import transitions as TR
        tr = json.loads((ROOT / os.environ["TRANS"]).read_text()).get(str(PHRASES.index(ph)))
        if tr:
            bnd = [(int(i), float(tb)) for i, tb in tr["bounds"]]; par = np.array(tr["par"])
            poses = np.array([TR.pose_at(s0 + k * hop / SR, vs, bnd, par) for k in range(n // hop + 1)])
        else:
            poses = pose_track(vs, s0, n, hop)
    else:
        poses = pose_track(vs, s0, n, hop)
    nfr = len(poses)
    runs = voiced_runs(vs); RAMP = float(os.environ.get("RAMP", "0.012")); RAMP_OFF = float(os.environ.get("RAMP_OFF", "0.03"))
    y = np.zeros(n + NFT + 2000)
    for v in vs:                                    # one run of his own cycles per sound
        ins = ff0[(tt >= v["s"]) & (tt <= v["e"]) & (ff0 > 0)]; v["f0"] = float(np.median(ins)) if len(ins) else 250.0
        v["src"] = min(BK, key=lambda b: abs(np.log(b["f0"] / v["f0"])))
    for a, b in runs:
        # the folds keep one continuous rhythm through a voiced stretch; each buzz starts at its exact
        # instant (between samples where it falls), so no rounding jitter and no restart at sound joins
        i0, i1 = int(np.ceil((a - s0) * SR)), int((b - s0) * SR)
        tn = s0 + np.arange(i0, i1) / SR
        who = np.array([next((j for j, v in enumerate(vs) if v["s"] - 1e-6 <= q <= v["e"] + 1e-6), 0) for q in tn])
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
            u = ph[c0: c1] - k[c0]
            pulse = np.interp(u, np.linspace(0, 1, len(cyc), endpoint=False), cyc) * g
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
            fl = TR.clip_floor(x, t); ok = bh > fl   # judged wherever his sound stands above the hiss
            w = np.clip((bh - fl) / 40.0, 0.05, 1.0)[ok]   # each band counts as much as it is audible
            d = (np.maximum(bm, fl) - bh)[ok]
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
        outs.append((y, s0, e0, vs))
    nz = lambda v: v / np.abs(v).max() * 0.7
    gap = np.zeros(int(0.6 * SR)); pieces = []
    for y, s0, e0, _ in outs:
        pieces += [nz(x[int(s0 * SR): int(e0 * SR)]), gap, nz(y), gap, gap]
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
