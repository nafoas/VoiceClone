"""His one neutral voice, recovered from the clip, as the source for his mouth.

1. recover: every voiced sound in the clip / that sound's mouth (reverse-
   engineered, models/mouth_inverse_A4.json: tube + nose + head) = what his voice
   box made during that sound
2. check: if the mouth were exact, every recovered voice would look the same;
   how they differ maps where the mouth is still wrong
3. one voice: the spectral shape all recovered voices share = his voice box's
   shape; every recovered cycle is corrected to it -> a bank of his real
   vocal-cord cycles (natural cycle-to-cycle life kept), ONE voice
4. rebuild: his voice-box cycles at the clip's pitch (pitch-synchronous
   overlap-add, source only), through the mouth moving between its positions;
   each sound voiced with cycles from OTHER sounds (honesty check)
   Voiced sounds only for now (soft S, p, t = phase C: silent gaps).

    python scripts/build/neutral_voice.py -> out/build/neutral_*.wav, analysis/physics/neutral_voice.png
"""
import json, os, sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from parselmouth.praat import call
from scipy.fft import idct
from scipy.ndimage import uniform_filter1d
from scipy.signal import fftconvolve, resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "scripts/build"))
sys.argv = sys.argv[:1]
os.environ.update(CHMIN="0.005", F1GUARD="1", SRC=os.environ.get("SRC", ""))
import mouth_inverse as M  # noqa: E402
from build_catalogue import PHRASES  # noqa: E402

SR = 48000
Z = np.array(json.loads((ROOT / os.environ.get("ZFILE", "models/mouth_inverse_A4.json")).read_text())["z"])
TAG = os.environ.get("TAG", "")
OUT = ROOT / "out/build"


def mouth_H(pose9, f):
    """His mouth (shared anatomy from A4) for any mouth position: tube + nose + head."""
    a0, L, frac, port = M.tube(pose9, Z[0], Z[M.SH["lar"]])
    dev = idct(np.r_[Z[M.SH["shape"]], np.zeros(M.NS - M.NF)], norm="ortho")
    a = a0 * np.exp(dev)
    H = M.B.tube_H_nose(a, L, np.maximum(f, 1.0), frac, port, Z[6], Z[7]) * M.B.head_baffle(np.maximum(f, 1.0), Z[1])
    # the plane-wave tube model only holds while wavelengths exceed the tube's width;
    # above ~8 kHz real air in a mouth this size stops behaving that way and losses
    # dominate: roll the model off there (both when recovering his voice and rebuilding)
    return H / (1 + (np.asarray(f, float) / 8000.0) ** 8)


def load():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    return resample_poly(x, SR, sr) if sr != SR else x


def segments():
    out = []
    for pi, ph in enumerate(PHRASES):
        for lab, s, e, _ in ph:
            out.append(dict(lab=lab, s=s, e=e, phrase=pi, voiced=lab in M.SOUNDS))
    return out


def pitch_marks(y):
    snd = pm.Sound(y, SR); pp = call(snd, "To PointProcess (periodic, cc)", 150, 700)
    n = call(pp, "Get number of points")
    return np.array([call(pp, "Get time from index", i + 1) for i in range(n)])


def smooth_env(spec_db, f, octave_frac=1 / 3):
    """Smooth a dB spectrum over ~1/3 octave (spectral envelope)."""
    out = np.empty_like(spec_db); lf = np.log2(np.maximum(f, 20))
    for i in range(len(f)):
        m = np.abs(lf - lf[i]) <= octave_frac / 2; out[i] = 10 * np.log10(np.mean(10 ** (spec_db[m] / 10)))
    return out


def main():
    x = load(); segs = segments()
    fq = np.fft.rfftfreq(8192, 1 / SR)
    # 1. recover each voiced sound's voice (inverse filter by its mouth, regularised)
    rec = []
    for g in segs:
        if not g["voiced"]:
            continue
        a, b = int((g["s"] - 0.01) * SR), int((g["e"] + 0.01) * SR); seg = x[a:b]
        n = len(seg); nf = 1 << int(np.ceil(np.log2(n + 8192)))
        f = np.fft.rfftfreq(nf, 1 / SR); H = mouth_H(Z[M.PO[g["lab"]]], f); H[0] = 1
        Hm = np.abs(H); floor = np.percentile(Hm[(f > 80) & (f < 9000)], 20)
        U = np.fft.rfft(seg, nf) * np.conj(H) / (Hm ** 2 + floor ** 2)
        u = np.fft.irfft(U, nf)[:n]
        rec.append(dict(g, u=u, a=a))
    # 2. check: spectral shape of each recovered voice (steady middle)
    shapes = []
    for r in rec:
        u = r["u"]; m = u[len(u) // 5: -len(u) // 5 or None]
        S = 10 * np.log10(np.abs(np.fft.rfft(m * np.hanning(len(m)), 8192)) ** 2 + 1e-20)
        E = smooth_env(S, fq); E -= np.max(E[(fq > 100) & (fq < 600)]); shapes.append(E)
    shapes = np.array(shapes); G = np.median(shapes, 0)
    bands = [(100, 600), (600, 1200), (1200, 2500), (2500, 4000), (4000, 6000), (6000, 9000)]
    print("recovered voice per sound: level by band, dB (vs its own 100-600 Hz); a perfect mouth -> all rows alike")
    print("          " + " ".join(f"{lo / 1000:.1f}-{hi / 1000:.1f}k" for lo, hi in bands))
    for r, E in zip(rec, shapes):
        print(f"  {r['lab']:3} {r['s']:.2f}s " + " ".join(f"{np.mean(E[(fq >= lo) & (fq < hi)]):8.1f}" for lo, hi in bands))
    print("  SHARED  " + " ".join(f"{np.mean(G[(fq >= lo) & (fq < hi)]):8.1f}" for lo, hi in bands))
    spread = np.std(shapes - G, 0)
    print("  disagreement (sd across sounds) " + " ".join(f"{np.mean(spread[(fq >= lo) & (fq < hi)]):6.1f}" for lo, hi in bands))
    # 3. one voice: correct every recovered voice to the shared shape, cut into cycles (the bank)
    bank = []   # (segment index, grain, period)
    for ri, (r, E) in enumerate(zip(rec, shapes)):
        u = r["u"]; n = len(u); nf = 1 << int(np.ceil(np.log2(n + 64)))
        f = np.fft.rfftfreq(nf, 1 / SR)
        corr = 10 ** (np.interp(f, fq, G - E) / 20)
        uc = np.fft.irfft(np.fft.rfft(u, nf) * corr, nf)[:n]
        pmk = pitch_marks(uc)
        for t0, t1, t2 in zip(pmk[:-2], pmk[1:-1], pmk[2:]):
            P = int(round((t2 - t0) / 2 * SR)); c = int(round(t1 * SR))
            if c - P < 0 or c + P >= n:
                continue
            gr = uc[c - P: c + P] * np.hanning(2 * P)
            bank.append((ri, gr / (np.sqrt(np.mean(gr ** 2)) + 1e-12), P))
    print(f"\nhis voice: {len(bank)} vocal-cord cycles from {len(rec)} sounds, one shared shape")
    # 4. rebuild: his pitch (smoothed, a voice-box control), his voice cycles from OTHER sounds, mouth moving
    snd = pm.Sound(x, SR); Pt = snd.to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff0 = Pt.selected_array["frequency"]
    I = snd.to_intensity(minimum_pitch=150, time_step=0.005)
    phrases_out = []
    for pi, ph in enumerate(PHRASES):
        s0, e0 = ph[0][1] - 0.02, ph[-1][2] + 0.03
        n = int((e0 - s0) * SR); src = np.zeros(n)
        vsegs = [r for r in rec if r["phrase"] == pi]
        # source: pitch-synchronous overlap-add of bank cycles, voiced segments only
        for vi, r in enumerate(vsegs):
            ri = rec.index(r); others = [b for b in bank if b[0] != ri]
            k = (ri * 37) % len(others)
            t = r["s"]
            inside = ff0[(tt >= r["s"]) & (tt <= r["e"]) & (ff0 > 0)]
            v0 = float(np.median(inside)) if len(inside) else 250.0      # the sound's own pitch if the tracker drops out
            while t < r["e"]:
                f0 = np.interp(t, tt, np.where(ff0 > 0, ff0, np.nan)); f0 = f0 if np.isfinite(f0) and 100 < f0 < 900 else v0
                _, gr, P = others[k % len(others)]; k += 1
                c = int((t - s0) * SR); lo = c - len(gr) // 2
                if 0 <= lo and lo + len(gr) < n:
                    src[lo: lo + len(gr)] += gr * (len(gr) / 2 / P) ** 0.0
                t += 1.0 / f0
        print(f"  [debug] phrase {pi}: source rms {np.sqrt(np.mean(src ** 2)):.3g}, nonzero {np.mean(src != 0):.2f}, segments {len(vsegs)}", flush=True)
        # loudness per voiced segment (a voice-box control): match the clip's level there
        # mouth positions per 5 ms frame; blend 30 ms across each boundary
        hop = 240; nfr = n // hop + 1; poses = np.zeros((nfr, 9)); w = np.zeros(nfr)
        for r in vsegs:
            a, b = int((r["s"] - s0) * SR / hop), int((r["e"] - s0) * SR / hop)
            poses[a:b] += Z[M.PO[r["lab"]]]; w[a:b] += 1
        idx = np.where(w > 0)[0]
        for j in range(9):
            poses[:, j] = np.interp(np.arange(nfr), idx, poses[idx, j] / w[idx])
        poses = uniform_filter1d(poses, 6, axis=0)                       # ~30 ms glide between positions
        NF = 4096; fH = np.fft.rfftfreq(NF, 1 / SR); win = np.hanning(2 * hop + 1)[:-1]
        y = np.zeros(n + NF); cache = {}
        for k in range(nfr):
            key = tuple(np.round(poses[k], 2))
            if key not in cache:
                H = mouth_H(poses[k], fH); H[0] = 0
                cache[key] = np.fft.irfft(H, NF) * np.hanning(2 * NF)[NF:]
            a = max(0, k * hop - hop); seg = src[a: a + 2 * hop]
            if len(seg) < 2 * hop:
                break
            y[a: a + 2 * hop + NF - 1] += fftconvolve(seg * win, cache[key])
        y = y[:n]
        print(f"  [debug] phrase {pi}: after mouth rms {np.sqrt(np.mean(y ** 2)):.3g}, max {np.abs(y).max():.3g}, finite {np.isfinite(y).all()}", flush=True)
        for r in vsegs:   # level per sound, from the clip (loudness is the voice box's)
            a, b = int((r["s"] - s0) * SR), int((r["e"] - s0) * SR)
            ref = x[int(r["s"] * SR): int(r["e"] * SR)]
            y[a:b] *= np.sqrt(np.mean(ref ** 2)) / (np.sqrt(np.mean(y[a:b] ** 2)) + 1e-12)
        print(f"  [debug] phrase {pi}: after levels rms {np.sqrt(np.mean(y ** 2)):.3g}, max {np.abs(y).max():.3g}; "
              + " ".join(f"{20 * np.log10(np.sqrt(np.mean(y[int(a * SR):int((a + 0.05) * SR)] ** 2)) + 1e-12):.0f}" for a in np.arange(0, n / SR - 0.05, 0.05)), flush=True)
        # only the voiced sounds are built so far: everything else (consonants, gaps) is silent, with 8 ms fades
        mask = np.zeros(n)
        for r in vsegs:
            a, b = int((r["s"] - s0) * SR), int((r["e"] - s0) * SR); mask[max(0, a):min(n, b)] = 1
        k8 = int(0.008 * SR); mask = np.convolve(mask, np.ones(k8) / k8, "same"); y = y * mask
        fade = np.clip(np.arange(n) / (0.01 * SR), 0, 1) * np.clip((n - np.arange(n)) / (0.02 * SR), 0, 1)
        phrases_out.append((y * fade, s0, e0))
    # write: gold, then model rebuild, per phrase
    gold, gsr = sf.read(ROOT / "reference/gold/rebuild_gold_v9.wav"); gold = gold.mean(1) if gold.ndim > 1 else gold
    pieces = []; gap = np.zeros(int(0.5 * 24000))
    for y, s0, e0 in phrases_out:
        clip = x[int(s0 * SR): int(e0 * SR)]
        pieces += [resample_poly(clip / np.abs(clip).max() * 0.7, 1, 2), gap,
                   resample_poly(y / (np.abs(y).max() + 1e-12) * 0.7, 1, 2), gap, gap]
    sf.write(OUT / f"neutral{TAG}_clip_vs_rebuild.wav", np.concatenate(pieces), 24000)
    model_only = np.concatenate([resample_poly(y / (np.abs(y).max() + 1e-12) * 0.7, 1, 2) for y, _, _ in phrases_out])
    sf.write(OUT / f"neutral{TAG}_rebuild.wav", model_only, 24000)
    # score against the clip, voiced sounds only (consonants are not built yet)
    import ee_decompose as DC
    print("\nrebuilt voiced sounds vs his (tone error, dB, tones above his floor):")
    errs = []
    for (y, s0, e0), pi in zip(phrases_out, range(len(PHRASES))):
        for r in [q for q in rec if q["phrase"] == pi]:
            a, b = int((r["s"] - s0 - 0.01) * SR), int((r["e"] - s0 + 0.01) * SR)
            try:
                dm = DC.decompose(y[max(0, a):b], SR, "nm"); dh = DC.decompose(x[int((r["s"] - 0.01) * SR): int((r["e"] + 0.01) * SR)], SR, "nh")
            except Exception:
                print(f"  {r['lab']:3} {r['s']:.2f}s: (too short or unvoiced in the rebuild to measure)"); continue
            lv = lambda d: (lambda A: np.nanmedian(20 * np.log10(A + 1e-12) - 20 * np.log10(A[:, :1] + 1e-12), 0)[:20])(d["A"][~np.isnan(d["A"][:, 0])])
            Lm, Lh = lv(dm), lv(dh); ok = Lh[1:] > -55
            e = float(np.sqrt(np.mean((np.maximum(Lm[1:], -58) - np.maximum(Lh[1:], -58))[ok] ** 2))); errs.append(e)
            print(f"  {r['lab']:3} {r['s']:.2f}s: {e:4.1f}")
    print(f"  overall {np.sqrt(np.mean(np.square(errs))):.2f} dB")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.figure(figsize=(12, 5))
    for r, E in zip(rec, shapes):
        plt.semilogx(fq[1:], E[1:], lw=0.8, alpha=0.6, label=f"{r['lab']} {r['s']:.2f}s")
    plt.semilogx(fq[1:], G[1:], "k", lw=2.5, label="his one voice (shared)")
    plt.xlim(80, 10000); plt.ylim(-80, 10); plt.xlabel("Hz"); plt.ylabel("dB")
    plt.title("His voice recovered from each sound (the clip with that sound's mouth undone)"); plt.legend(fontsize=7, ncol=3)
    plt.tight_layout(); plt.savefig(ROOT / f"analysis/physics/neutral_voice{TAG}.png", dpi=70)
    np.savez(ROOT / f"models/neutral_voice{TAG}.npz", G=G, fq=fq)


if __name__ == "__main__":
    main()
