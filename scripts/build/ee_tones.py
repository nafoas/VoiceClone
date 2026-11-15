"""Step 1f: make his "ee" tone by tone (analysis/physics/ee_decompose.py).

His "ee" decomposed, all four instances agree:
  - levels: a very deep valley (harmonics 4-11 at -43..-63 dB re H1) between
    the hum and a bright cluster near 3.2-4 kHz, then a quiet top
  - phase: only harmonics 1-2(-3) keep their place in the cycle; higher ones
    wander (steadiness 0.1-0.8). Physically: the folds' closing instant varies
    ~0.1 ms from cycle to cycle (high tones scramble, low ones stay locked)
  - flicker: higher harmonics' levels flicker 2-6 dB

Stage A: brute-force the mouth shape + larynx depth + voice box on every
         harmonic's level (H2..H20), all four "ee"s at once (fast, analytic)
Stage B: closing-instant variation and breath, judged by decomposing the
         model's audio exactly like his (phase steadiness, flicker, levels)

    python scripts/build/ee_tones.py -> out/build/ee_tones_*.wav, models/build_ee_tones.json
"""
import itertools, json, sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.optimize import minimize
from scipy.signal import fftconvolve, resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "analysis/physics")); sys.path.insert(0, str(ROOT / "scripts/build"))
sys.argv = sys.argv[:1] + ["30"]
import ee_decompose as DC  # noqa: E402
import ee as E  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402
from prince_voice import voicebox as VB  # noqa: E402

SR = 48000
NHA = 20
FLOOR = -58.0                     # below this his harmonic is lost in noise: don't chase it
SPANS = [(0.79, 0.99), (1.52, 1.60), (1.77, 1.90), (2.09, 2.30)]
LARCAV = (7, 1.0, 4, 0.15)


def his_targets():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    out = []
    for s, e in SPANS:
        d = DC.decompose(x[int((s - 0.02) * sr): int((e + 0.02) * sr)], sr, f"t{int(s * 100)}")
        A = d["A"]; ok = ~np.isnan(A[:, 0]); dB = 20 * np.log10(A[ok] + 1e-12); dB -= dB[:, :1]
        mid = slice(len(dB) // 5, -len(dB) // 5 or None)
        rel = d["rel"][ok][mid]
        out.append(dict(f0=float(np.median(d["F0"])), ms=int((e - s) * 1000), level=np.nanmedian(dB[mid], 0)[:NHA],
                        flick=np.nanstd(dB[mid] - np.nanmedian(dB[mid], 0), 0)[:NHA],
                        coh=np.abs(np.nanmean(np.exp(1j * rel), 0))[:NHA]))
    return out


def model_levels(m, pose, f0, src):
    k = np.arange(1, NHA + 1) * f0
    H = 20 * np.log10(np.abs(m.response(pose, k, radiate=True)) + 1e-12)
    U = np.abs(np.fft.rfft(VB.pulse(4096, src[0], src[1])))[1: NHA + 1]
    tilt = 1 / np.sqrt(1 + (2 * np.pi * k * src[2] * 1e-3) ** 2)
    L = 20 * np.log10(U * tilt + 1e-12) + H
    return L - L[0]


def unpack(z):
    v = Pose().vec(); v[:9] = np.clip(z[:9], E.EE_LO, E.EE_HI)
    return Pose.from_vec(v), float(np.clip(z[9], 15.0, 45.0)), (float(np.clip(z[10], 0.3, 0.9)),
                                                                 float(np.clip(z[11], 0.45, 0.92)), float(np.clip(z[12], 0.0, 2.0)))


def stage_a(T):
    cache = {}

    def cost(z):
        pose, neck, src = unpack(z); key = round(neck, 1)
        m = cache.setdefault(key, BunMouth(0.75, neck_mm=key, larcav=LARCAV))
        e = 0.0
        for t in T:
            L = model_levels(m, pose, t["f0"], src)
            tgt = np.maximum(t["level"], FLOOR); mod = np.maximum(L, FLOOR)
            e += np.sqrt(np.mean((mod[1:] - tgt[1:]) ** 2))
        return e / len(T)
    prev = json.loads((ROOT / "models/ee_tone_approved.json").read_text())
    starts = []
    for neck in (20.0, 26.0, 32.0):
        for src in ((0.61, 0.59, 0.0), (0.5, 0.7, 0.3), (0.7, 0.8, 0.6)):
            starts.append(np.r_[np.array(prev["pose"])[:9], neck, src])
        for fr in (0.4, 0.7, 1.0):
            starts.append(np.r_[Pose(jaw=.1, body=.8, front=fr, lips=.6, root=1, larynx=.5).vec()[:9], neck, 0.6, 0.6, 0.2])
    rs = [minimize(cost, z, method="Powell", options=dict(maxfev=2500, xtol=1e-4, ftol=1e-5)) for z in starts]
    r = min(rs, key=lambda r: r.fun)
    return unpack(r.x), r.fun


def render(m, pose, src, f0, ms, close_ms, breath, shim, seed):
    """The bulk airflow of each cycle is steady; only the closing moment (which
    makes the high tones) shifts by ~close_ms from cycle to cycle. Built as a
    steady flow (kept below ~1.2 kHz) + the same flow with each cycle's
    closing shifted (kept above ~1.2 kHz)."""
    from scipy.signal import butter, sosfiltfilt
    n_ms = ms + 60; rng = np.random.default_rng(seed)
    dur = n_ms / 1000; n = int(dur * SR)
    sos = butter(2, 6 / 500, "low", output="sos")
    drift = sosfiltfilt(sos, rng.standard_normal(n_ms + 20))[:n_ms]; drift = drift / (drift.std() + 1e-9) * 6.0
    tt = np.arange(n_ms); amp = np.clip(tt / 30, 0, 1) * np.clip((n_ms - 10 - tt) / 50, 0, 1)
    u0 = np.zeros(n); u1 = np.zeros(n); t = 0.0
    while True:
        i = min(int(t * 1000), n_ms - 1)
        T = 1.0 / (f0 * 2 ** (drift[i] / 1200)) * (1 + 0.002 * rng.standard_normal())
        L = int(round(T * SR)); s0 = int(round(t * SR))
        if s0 + L + 50 >= n:
            break
        a = amp[i] * (1 + shim * rng.standard_normal())
        p = VB.pulse(L, src[0], src[1]) * a
        u0[s0:s0 + L] += p
        d = int(round(close_ms * 1e-3 * SR * rng.standard_normal()))          # this cycle's closing moment
        Lc = int(np.clip(round(src[0] * L) + d, 4, L - 1))                     # open phase ends earlier/later
        pc = np.zeros(L); To = src[0] * L; Tp = src[1] * To; x = np.arange(L, dtype=float)
        pc = np.where(x < Tp, 0.5 * (1 - np.cos(np.pi * x / Tp)),
                      np.where(x < Lc, np.cos(0.5 * np.pi * (x - Tp) / max(Lc - Tp, 1)), 0.0))
        u1[s0:s0 + L] += np.clip(pc, 0, None) * a
        t += T
    lo = butter(4, 1200 / (SR / 2), "low", output="sos"); hi = butter(4, 1200 / (SR / 2), "high", output="sos")
    u = sosfiltfilt(lo, u0) + sosfiltfilt(hi, u1)
    if src[2] > 0:
        from scipy.signal import lfilter
        aa = np.exp(-1.0 / (src[2] * 1e-3 * SR)); u = lfilter([1 - aa], [1, -aa], u)
    if breath > 0:
        from scipy.signal import lfilter
        bb, ab = butter(2, 1500 / (SR / 2), "high")
        u = u + breath * lfilter(bb, ab, rng.standard_normal(n)) * (u / (u.max() + 1e-12))
    f = np.fft.rfftfreq(8192, 1 / SR); H = m.response(pose, np.maximum(f, 1.0), radiate=True); H[0] = 0
    ir = np.fft.irfft(H, 8192) * np.hanning(16384)[8192:]
    y = fftconvolve(u, ir)[: len(u)]
    return y / (np.abs(y).max() + 1e-12) * 0.7


def describe(y, label):
    d = DC.decompose(y, SR, label)
    A = d["A"]; ok = ~np.isnan(A[:, 0]); dB = 20 * np.log10(A[ok] + 1e-12); dB -= dB[:, :1]
    mid = slice(len(dB) // 5, -len(dB) // 5 or None); rel = d["rel"][ok][mid]
    return dict(level=np.nanmedian(dB[mid], 0)[:NHA], flick=np.nanstd(dB[mid] - np.nanmedian(dB[mid], 0), 0)[:NHA],
                coh=np.abs(np.nanmean(np.exp(1j * rel), 0))[:NHA])


def main():
    T = his_targets()
    cache = ROOT / "models/build_ee_tones_stageA.json"
    if cache.exists():
        c = json.loads(cache.read_text()); pose, neck, src, err = Pose.from_vec(c["pose"]), c["neck"], tuple(c["src"]), c["err"]
    else:
        (pose, neck, src), err = stage_a(T)
        cache.write_text(json.dumps(dict(pose=pose.vec().tolist(), neck=neck, src=list(src), err=err)))
    m = BunMouth(0.75, neck_mm=neck, larcav=LARCAV)
    print(f"stage A: level error {err:.2f} dB; larynx {neck * 0.075:.2f} cm lower; Oq {src[0]:.2f} am {src[1]:.2f} Ta {src[2]:.2f}; "
          f"resonances {[round(x) for x in m.formants(pose, fmax=8000)[:4] if x == x]}")
    for t in T:
        L = model_levels(m, pose, t["f0"], src)
        print(f"  {t['f0']:.0f} Hz him   " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print(f"  {t['f0']:.0f} Hz model " + " ".join(f"{v:4.0f}" for v in L))
    # stage B: closing-instant variation, breath, cycle strength variation
    best = None
    for sv, br, sh in itertools.product((0.0, 0.05, 0.1, 0.15, 0.2), (0.0, 0.01, 0.025), (0.005, 0.015)):
        e = 0.0
        for j in (0, 3):
            t = T[j]; ds = describe(render(m, pose, src, t["f0"], t["ms"], sv, br, sh, seed=j), "m")
            hi = slice(2, NHA)
            e += np.nanmean(np.abs(ds["coh"][hi] - t["coh"][hi])) / 0.15 + np.nanmean(np.abs(ds["flick"][hi] - t["flick"][hi])) / 1.5
            e += np.sqrt(np.nanmean((np.maximum(ds["level"][1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)) ** 2)) / 5
        if best is None or e < best[0]:
            best = (e, sv, br, sh)
    _, sv, br, sh = best
    print(f"stage B: closing moment varies {sv} ms (sd), breath {br}, cycle strength {sh}")
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    gap = np.zeros(int(0.35 * 24000)); pieces = []
    for j, (t, (s, e)) in enumerate(zip(T, SPANS)):
        y = render(m, pose, src, t["f0"], t["ms"] if t["ms"] > 120 else 150, sv, br, sh, seed=40 + j)
        ds = describe(y, f"final{j}")
        print(f"  {t['f0']:.0f} Hz phase him   " + " ".join(f"{v:4.2f}"[1:] for v in t["coh"]))
        print(f"  {t['f0']:.0f} Hz phase model " + " ".join(f"{v:4.2f}"[1:] for v in ds["coh"]))
        print(f"  {t['f0']:.0f} Hz flick him   " + " ".join(f"{v:4.1f}" for v in t["flick"]))
        print(f"  {t['f0']:.0f} Hz flick model " + " ".join(f"{v:4.1f}" for v in ds["flick"]))
        sf.write(ROOT / f"out/build/ee_tones_{int(t['f0'])}.wav", resample_poly(y, 1, 2), 24000)
        real = resample_poly(x[int((s - 0.02) * sr): int((e + 0.03) * sr)], 1, 2)
        pieces += [real / np.abs(real).max() * 0.7, gap, resample_poly(y, 1, 2), gap, gap]
    sf.write(ROOT / "out/build/ee_tones_him_vs_model.wav", np.concatenate(pieces), 24000)
    (ROOT / "models/build_ee_tones.json").write_text(json.dumps(dict(
        pose=pose.vec().tolist(), neck=neck, larcav=LARCAV, source=dict(Oq=src[0], am=src[1], Ta_ms=src[2]),
        shape_var=sv, breath=br, cycle_shimmer=sh, cycle_jitter=0.002, drift_cents=6.0, level_err=err), indent=1))


if __name__ == "__main__":
    main()
