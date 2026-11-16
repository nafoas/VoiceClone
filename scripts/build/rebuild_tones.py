"""Rebuild the clip's voiced sounds from ONE voice through the reverse-engineered mouth.

Voice (the source): his one voice from the joint fit (mouth_inverse SRC=shared2):
  tone strengths = tilt over frequency (G_f) + his vocal cords' puff shape over
  harmonic number (G_h), the same for every sound; base timing of the tones from
  a puff; each cycle's closing moment shifts ~0.1 ms (scrambles only the high
  tones: his measured life). Cycles laid at the clip's pitch (a voice-box control),
  overlap-added (source only).
Mouth: the reverse-engineered mouth, moving between the sounds' positions (30 ms
  glides), tube + nose + head, valid below ~8 kHz.
Consonants (soft S, p, t) are phase C: silent for now.

    ZFILE=models/mouth_inverse_S4.json python scripts/build/rebuild_tones.py -> out/build/rebuild_tones_*.wav
"""
import json, os, sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.fft import idct
from scipy.ndimage import uniform_filter1d
from scipy.signal import fftconvolve, resample_poly

_zf = json.loads((Path(__file__).resolve().parents[2] / os.environ.get("ZFILE", "models/mouth_inverse_P1.json")).read_text())["z"]
os.environ.update(SRC=os.environ.get("SRC", "puff"), CHMIN="0.005", F1GUARD="1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/build"))
sys.path.insert(0, str(ROOT / "analysis/physics")); sys.argv = sys.argv[:1]
import mouth_inverse as M  # noqa: E402
import ee_decompose as DC  # noqa: E402
from build_catalogue import PHRASES  # noqa: E402

SR = 48000
Z = np.array(_zf)
PUFF = os.environ["SRC"] == "puff"
TAG = os.environ.get("TAG", "")
CLOSE_MS = float(os.environ.get("CLOSE_MS", "0.1"))


def mouth_H(pose9, f):
    a0, L, frac, port = M.tube(pose9, Z[0], Z[M.SH["lar"]])
    a = a0 * np.exp(idct(np.r_[Z[M.SH["shape"]], np.zeros(M.NS - M.NF)], norm="ortho"))
    f = np.maximum(np.asarray(f, float), 1.0)
    H = M.B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * M.B.head_baffle(f, Z[1])
    return H / (1 + (f / 8000.0) ** 8)


def voice_db(f0, K):
    k = np.arange(1, K + 1); fk = k * f0
    g = np.interp(np.log(fk), np.log(M.GK), Z[M.GS])
    gh = np.r_[0.0, Z[M.GH]]
    return g + np.where(k <= len(gh), gh[np.minimum(k, len(gh)) - 1], gh[-1])


def cycle(P, f0, rng):
    """One 2-period grain of his voice at period P samples (Hann windowed)."""
    K = int(9000 // f0)
    if PUFF:   # his one pair of vocal cords: the shared physical puff, tones and their timing
        C = M.X.puff_C(f0, tuple(Z[M.PU0:M.PU0 + 5]))
        C = np.r_[C, np.zeros(max(0, K - len(C)), complex)][:K] if len(C) < K else C[:K]
        if len(C) < K or K > M.NH:
            q = Z[M.PU0:M.PU0 + 5]; kk = np.arange(1, K + 1) * f0
            C = np.fft.rfft(M.X.pulse_flex(4096, q[0], q[1], q[2], q[4]))[1: K + 1] / (1 + 1j * 2 * np.pi * kk * q[3] * 1e-3)
        amp, base = np.abs(C), np.angle(C)
    else:
        amp = 10 ** (voice_db(f0, K) / 20)
        base = np.angle(np.fft.rfft(M.X.pulse_flex(4096, 0.8, 0.55, 1.0, 0.4))[1: K + 1])
    k = np.arange(1, K + 1)
    d = CLOSE_MS * 1e-3 * rng.standard_normal()                 # this cycle's closing moment
    w = np.clip((k - 2) / 4.0, 0, 1)                             # only the high tones feel it
    ph = base + 2 * np.pi * k * f0 * d * w
    n = np.arange(-P, P); tt = n / SR
    g = np.sum(amp[:, None] * np.cos(2 * np.pi * k[:, None] * f0 * tt[None, :] + ph[:, None]), 0)
    return g * np.hanning(2 * P)


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    x = resample_poly(x, SR, sr) if sr != SR else x
    snd = pm.Sound(x, SR); Pt = snd.to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff0 = Pt.selected_array["frequency"]
    rng = np.random.default_rng(3)
    outs = []; srcs = []
    for pi, ph in enumerate(PHRASES):
        s0, e0 = ph[0][1] - 0.02, ph[-1][2] + 0.03; n = int((e0 - s0) * SR)
        vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
        def build_src(gain_db):
          src = np.zeros(n)
          for vi, v in enumerate(vs):
            ins = ff0[(tt >= v["s"]) & (tt <= v["e"]) & (ff0 > 0)]; v0 = float(np.median(ins)) if len(ins) else 250.0
            t = v["s"]
            while t < v["e"]:
                f0 = np.interp(t, tt, np.where(ff0 > 0, ff0, np.nan))
                f0 = f0 if np.isfinite(f0) and 100 < f0 < 900 else v0
                P = int(round(SR / f0)); c = int((t - s0) * SR)
                g = cycle(P, f0, rng) * 10 ** (np.interp(t, gain_db[0], gain_db[1]) / 20)   # breath pressure
                if c - P >= 0 and c + P < n:
                    src[c - P: c + P] += g
                t += 1.0 / f0
          return src
        hop = 240; nfr = n // hop + 1; poses = np.zeros((nfr, 9)); w = np.zeros(nfr)
        for v in vs:
            a, b = int((v["s"] - s0) * SR / hop), int((v["e"] - s0) * SR / hop); poses[a:b] += Z[M.PO[v["lab"]]]; w[a:b] += 1
        idx = np.where(w > 0)[0]
        for j in range(9):
            poses[:, j] = np.interp(np.arange(nfr), idx, poses[idx, j] / w[idx])
        poses = uniform_filter1d(poses, 6, axis=0)
        NFT = 4096; fH = np.fft.rfftfreq(NFT, 1 / SR); win = np.hanning(2 * hop + 1)[:-1]; cache = {}

        def mouth(src):
          y = np.zeros(n + NFT)
          for k in range(nfr):
            key = tuple(np.round(poses[k], 2))
            if key not in cache:
                H = mouth_H(poses[k], fH); H[0] = 0
                cache[key] = np.fft.irfft(H, NFT) * np.hanning(2 * NFT)[NFT:]
            a = k * hop - hop; seg = src[max(a, 0): a + 2 * hop]
            if a < 0 or len(seg) < 2 * hop:
                continue
            y[a: a + 2 * hop + NFT - 1] += fftconvolve(seg * win, cache[key])
          return y[:n]
        # loudness = breath pressure behind the voice, set per sound from the clip (smooth, on the source only)
        mids = np.array([(v["s"] + v["e"]) / 2 for v in vs])
        st = np.random.get_state(); rs = rng.bit_generator.state
        y1 = mouth(build_src((mids, np.zeros(len(vs)))))
        rng.bit_generator.state = rs
        gd = []
        for v in vs:
            a, b = int((v["s"] - s0) * SR), int((v["e"] - s0) * SR)
            ref = x[int(v["s"] * SR): int(v["e"] * SR)]
            gd.append(20 * np.log10(np.sqrt(np.mean(ref ** 2)) / (np.sqrt(np.mean(y1[a:b] ** 2)) + 1e-12)))
        gd = np.array(gd); print(f"  phrase {pi + 1} breath (dB, rel): " + " ".join(f"{v['lab']}{g - gd.max():+.0f}" for v, g in zip(vs, gd)))
        srcf = build_src((mids, gd)); y = mouth(srcf)
        outs.append((y, s0, e0, vs)); srcs.append(srcf)
    gap = np.zeros(int(0.5 * 24000)); pieces = []
    for y, s0, e0, _ in outs:
        clip = x[int(s0 * SR): int(e0 * SR)]
        pieces += [resample_poly(clip / np.abs(clip).max() * 0.7, 1, 2), gap, resample_poly(y / np.abs(y).max() * 0.7, 1, 2), gap, gap]
    nz = lambda v: resample_poly(v / np.abs(v).max() * 0.7, 1, 2)
    sf.write(ROOT / f"out/build/rebuild_tones{TAG}_source.wav", np.concatenate([q for v in srcs for q in (nz(v), gap)]), 24000)
    sf.write(ROOT / f"out/build/rebuild_tones{TAG}_source_then_mouth.wav",
             np.concatenate([q for v, (y, *_ ) in zip(srcs, outs) for q in (nz(v), gap, nz(y), gap, gap)]), 24000)
    sf.write(ROOT / f"out/build/rebuild_tones{TAG}_clip_vs_model.wav", np.concatenate(pieces), 24000)
    sf.write(ROOT / f"out/build/rebuild_tones{TAG}_model.wav",
             np.concatenate([resample_poly(y / np.abs(y).max() * 0.7, 1, 2) for y, _, _, _ in outs]), 24000)
    # checks: pitched? tones vs his
    yy = np.concatenate([y for y, _, _, _ in outs]); P2 = pm.Sound(yy, SR).to_pitch_ac(time_step=0.01, pitch_floor=150, pitch_ceiling=700)
    fp = P2.selected_array["frequency"]
    print(f"pitched frames: {(fp > 0).sum()} (median {np.median(fp[fp > 0]) if (fp > 0).any() else 0:.0f} Hz)")
    errs = []
    for y, s0, e0, vs in outs:
        for v in vs:
            try:
                dm = DC.decompose(y[int((v["s"] - s0 - 0.005) * SR): int((v["e"] - s0 + 0.005) * SR)], SR, "rm")
                dh = DC.decompose(x[int((v["s"] - 0.005) * SR): int((v["e"] + 0.005) * SR)], SR, "rh")
            except Exception:
                print(f"  {v['lab']:3} {v['s']:.2f}s: not measurable"); continue
            def lv(d):
                A = d["A"][~np.isnan(d["A"][:, 0])]; L = 20 * np.log10(A + 1e-12); return np.nanmedian(L - L[:, :1], 0)[:20]
            Lm, Lh = lv(dm), lv(dh); ok = Lh[1:] > -55
            e = float(np.sqrt(np.mean((np.maximum(Lm[1:], -58) - np.maximum(Lh[1:], -58))[ok] ** 2))); errs.append(e)
            print(f"  {v['lab']:3} {v['s']:.2f}s: tone error {e:4.1f} dB")
    if errs:
        print(f"  overall {np.sqrt(np.mean(np.square(errs))):.2f} dB")


if __name__ == "__main__":
    main()
