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
        H = M.B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * M.B.head_baffle(f, Z[1])
        H = H / (1 + (f / 8000.0) ** 8); H[0] = 0          # the tube model holds below ~8 kHz
        h = np.fft.irfft(H, NFT); h *= np.r_[np.ones(NFT // 2), np.hanning(NFT)[NFT // 2:]]   # ring dies fully
        _ir[key] = h
    return _ir[key]


def bank():
    d = np.load(ROOT / "models/his_voice.npz"); B = []
    for i, cl in enumerate(d["clean"]):
        if cl:
            cyc = np.split(d[f"cyc_{i}"] * (SR / 48000), np.cumsum(d[f"len_{i}"])[:-1])
            B.append(dict(f0=float(d["f0"][i]), cyc=cyc, order=list(range(len(cyc))) + list(range(len(cyc) - 2, 0, -1)), k=0))
    return B


def at_period(c, P):
    """His cycle, played at period P samples (same shape, faster or slower)."""
    return np.interp(np.linspace(0, 1, P, endpoint=False), np.linspace(0, 1, len(c), endpoint=False), c)


def render_phrase(ph, x, tt, ff0, BK, gain_db=None):
    s0, e0 = ph[0][1] - 0.02, ph[-1][2] + 0.03; n = int((e0 - s0) * SR)
    vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
    hop = 240; nfr = n // hop + 1; poses = np.zeros((nfr, 9)); w = np.zeros(nfr)
    for v in vs:
        a, b = int((v["s"] - s0) * SR / hop), int((v["e"] - s0) * SR / hop); poses[a:b] += Z[M.PO[v["lab"]]]; w[a:b] += 1
    idx = np.where(w > 0)[0]
    for j in range(9):
        poses[:, j] = np.interp(np.arange(nfr), idx, poses[idx, j] / w[idx])
    poses = uniform_filter1d(poses, int(os.environ.get("GLIDE", "3")), axis=0)   # short glides: every position is reached
    y = np.zeros(n + NFT + 2000)
    for vi, v in enumerate(vs):
        ins = ff0[(tt >= v["s"]) & (tt <= v["e"]) & (ff0 > 0)]; v0 = float(np.median(ins)) if len(ins) else 250.0
        g = 10 ** ((gain_db[vi] if gain_db is not None else 0.0) / 20)
        t = v["s"]
        src = min(BK, key=lambda b: abs(np.log(b["f0"] / v0)))              # one run of his own cycles per sound
        while t < v["e"]:
            f0 = np.interp(t, tt, np.where(ff0 > 0, ff0, np.nan)); f0 = f0 if np.isfinite(f0) and 100 < f0 < 900 else v0
            P = int(round(SR / f0)); c = int((t - s0) * SR)
            cyc = src["cyc"][src["order"][src["k"] % len(src["order"])]]; src["k"] += 1
            pulse = at_period(cyc, P) * g
            h = mouth_ir(poses[min(c // hop, nfr - 1)], v["lab"] == "m")
            if c >= 0:
                out = np.convolve(pulse, h); y[c: c + len(out)] += out[: len(y) - c]
            t += 1.0 / f0
    return y[:n], s0, e0, vs


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    x = resample_poly(x, SR, sr) if sr != SR else x
    Pt = pm.Sound(x, SR).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff0 = Pt.selected_array["frequency"]
    outs = []
    for pi, ph in enumerate(PHRASES):
        y1, s0, e0, vs = render_phrase(ph, x, tt, ff0, bank())
        gd = []
        for v in vs:   # breath pressure per sound, from the clip's loudness
            a, b = int((v["s"] - s0) * SR), int((v["e"] - s0) * SR)
            gd.append(20 * np.log10(np.sqrt(np.mean(x[int(v["s"] * SR): int(v["e"] * SR)] ** 2)) / (np.sqrt(np.mean(y1[a:b] ** 2)) + 1e-12)))
        gd = np.array(gd) - max(gd)
        print(f"  phrase {pi + 1} breath (dB): " + " ".join(f"{v['lab']}{g:+.0f}" for v, g in zip(vs, gd)))
        y, s0, e0, vs = render_phrase(ph, x, tt, ff0, bank(), gd)
        outs.append((y, s0, e0, vs))
    nz = lambda v: v / np.abs(v).max() * 0.7
    gap = np.zeros(int(0.6 * SR)); pieces = []
    for y, s0, e0, _ in outs:
        pieces += [nz(x[int(s0 * SR): int(e0 * SR)]), gap, nz(y), gap, gap]
    sf.write(ROOT / f"out/build/render_his{TAG}_clip_vs_model.wav", np.concatenate(pieces), SR)
    sf.write(ROOT / f"out/build/render_his{TAG}_model.wav", np.concatenate([q for y, *_ in outs for q in (nz(y), gap)]), SR)
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


if __name__ == "__main__":
    main()
