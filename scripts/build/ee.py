"""Step 1 of the model-only build: his "ee", from his own mouth and voice box.

Nothing from the clip goes into the output. The clip's four "ee"s are only
MEASURED (pitch level, harmonic amplitudes, voice measures) to judge the model.

The model:
  mouth      his one-change bun mouth (small bun, larynx lower), ONE shared "ee" pose
  voice box  a glottal flow pulse, ONE shared setting for all four:
               Oq  how long the folds stay open each cycle
               am  how much of that is opening (vs closing)
               Ta  how gently they close (ms)
               steadiness: jitter / shimmer; breath noise
  per "ee"   only its pitch level (a plateau, as he does) and its loudness

The hum is NOT stamped on: whatever hum there is comes out of the physics.

    python scripts/build/ee.py  -> out/build/ee_*.wav, models/build_ee.json
"""
import json, sys, warnings
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.optimize import minimize
from scipy.signal import fftconvolve, lfilter, resample_poly

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "analysis"))
from prince_voice.bunmouth import BunMouth, Pose, LO, HI, NAMES  # noqa: E402
from fingerprint import source_measures  # noqa: E402

SR = 48000
OUT = ROOT / "out" / "build"; OUT.mkdir(parents=True, exist_ok=True)
EES = [(0.79, 0.99), (1.52, 1.60), (1.77, 1.90), (2.09, 2.30)]   # his four "ee"s (transcription)
NH = 18                                                            # harmonics compared (up to ~6 kHz)
SIZE = 0.75                                                        # a small bun, his real size
NECK = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0           # larynx lower (ref mm): 30 = 2.2 cm, what his "ee" asks for
FREE_POSE = ["jaw", "body", "front", "tip", "root", "lips", "round", "velum", "larynx"]
# what an "ee" physically requires (same as the rebuild's NEEDS): tongue body high and
# forward, tip down, lips open, not rounded, nose (nearly) sealed, jaw fairly closed
EE_LO = np.array([0.0, 0.3, 0.4, 0.0, -1.0, 0.3, 0.0, 0.0, 0.0])
EE_HI = np.array([0.45, 1.0, 1.0, 0.35, 1.0, 1.0, 0.5, 0.3, 1.0])


# ---- his "ee"s: measured, never used as material -------------------------------------
def his_ees():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav")
    x = x.mean(1) if x.ndim > 1 else x
    snd = pm.Sound(x, sr)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    out = []
    for s, e in EES:
        d = e - s; a, b = s + 0.3 * d, e - 0.2 * d                 # the steady middle
        f0 = float(np.nanmedian([P.get_value_at_time(t) for t in np.arange(a, b, 0.005)]))
        seg = x[int(a * sr): int(b * sr)]
        h = harmonics(seg, sr, f0)
        r = source_measures(snd, s, e, F, P)
        r["F1"] = float(np.nanmedian([F.get_value_at_time(1, t) for t in np.arange(a, b, 0.005)]))
        r["B1"] = float(np.nanmedian([F.get_bandwidth_at_time(1, t) for t in np.arange(a, b, 0.005)]))
        out.append(dict(span=(s, e), f0=f0, ms=int(round(1000 * d)), harm=h, meas=r))
        print(f"his ee {s:.2f}-{e:.2f}: pitch {f0:.0f} Hz, H2..H4 {np.round(h[1:4] - h[0], 1)}, F1 {r['F1']:.0f}", flush=True)
    return out


def harmonics(seg, sr, f0, nh=NH):
    n = len(seg); S = np.abs(np.fft.rfft(seg * np.hanning(n), 1 << 18)); fq = np.fft.rfftfreq(1 << 18, 1 / sr)
    return np.array([20 * np.log10(S[(fq > f0 * (k - .25)) & (fq < f0 * (k + .25))].max() + 1e-12) for k in range(1, nh + 1)])


# ---- the voice box --------------------------------------------------------------------
def pulse(n, Oq, am):
    """One cycle of glottal flow, n samples (KLGLOTT88-style shape)."""
    x = np.arange(n, dtype=float); To = Oq * n; Tp = am * To
    return np.clip(np.where(x < Tp, 0.5 * (1 - np.cos(np.pi * x / Tp)),
                            np.where(x < To, np.cos(0.5 * np.pi * (x - Tp) / max(To - Tp, 1)), 0.0)), 0, None)


def source_harm(f0, Oq, am, Ta, nh=NH):
    """Harmonic amplitudes (dB) of the flow, including the gentle-closure low-pass."""
    n = 4096; U = np.abs(np.fft.rfft(pulse(n, Oq, am)))[1: nh + 1]
    k = np.arange(1, nh + 1) * f0
    tilt = 1.0 / np.sqrt(1 + (2 * np.pi * k * Ta * 1e-3) ** 2)
    return 20 * np.log10(U * tilt + 1e-12)


def flow(f0_track, dur, Oq, am, Ta, jit, shim, asp, amp_track, rng):
    n = int(dur * SR); u = np.zeros(n); t = 0.0
    while True:
        T = 1.0 / f0_track(t) * (1 + jit * rng.standard_normal())
        L = int(round(T * SR)); s0 = int(round(t * SR))
        if s0 + L >= n:
            break
        u[s0:s0 + L] = pulse(L, Oq, am) * (1 + shim * rng.standard_normal()) * amp_track(t)
        t += T
    if Ta > 0:
        a = np.exp(-1.0 / (Ta * 1e-3 * SR)); u = lfilter([1 - a], [1, -a], u)
    if asp > 0:
        # breath = turbulence at the glottis: strongest at high frequencies (made
        # by the jet; ~2nd-order rise below ~1.5 kHz), and it comes in puffs, while
        # the folds are open (gated by the flow)
        from scipy.signal import butter
        bb, ab = butter(2, 1500 / (SR / 2), "high")
        nz = lfilter(bb, ab, rng.standard_normal(n))
        env = np.array([amp_track(i / SR) for i in range(0, n)])
        u = u + asp * nz * env * (0.05 + u / (u.max() + 1e-12))
    return u


# ---- model harmonics: source x mouth ----------------------------------------------------
def model_harm(m, pose, f0, src):
    k = np.arange(1, NH + 1) * f0
    H = m.response(pose, k, radiate=True)
    return source_harm(f0, *src) + 20 * np.log10(np.abs(H) + 1e-12)


def unpack(z):
    pose = np.clip(z[:9], EE_LO, EE_HI)
    v = Pose().vec(); v[:9] = pose; v[NAMES.index("cheeks")] = 0.0
    Oq = float(np.clip(z[9], 0.35, 0.95)); am = float(np.clip(z[10], 0.4, 0.9)); Ta = float(np.clip(z[11], 0.0, 3.0))
    return Pose.from_vec(v), (Oq, am, Ta)


def fit(m, his):
    """In stages, so the search can't wander off: (1) the mouth shape from his
    resonances, (2) the voice box from his harmonics with the mouth fixed,
    (3) both together, starting from there."""
    import sys as _s; _s.path.insert(0, str(ROOT / "scripts")); from fit_mouth import bark
    W = np.r_[np.full(6, 2.0), np.ones(NH - 6)]                     # the low harmonics carry the hum
    import os
    BAND = float(os.environ.get("EE_BAND_HZ", "0"))                 # >0: judge the voice box only below this
    def hcost(pose, src):
        e = 0.0
        for h in his:
            d = model_harm(m, pose, h["f0"], src) - h["harm"]
            w = W * ((np.arange(1, NH + 1) * h["f0"] < BAND) if BAND > 0 else 1.0)
            d = d - np.average(d, weights=w)                         # loudness is free per "ee"
            e += np.sqrt(np.average(d ** 2, weights=w))
        return e / len(his)
    T = np.array([np.median([h["meas"]["F1"] for h in his]), 3323.0, 4119.0])   # his ee resonances (fingerprint)
    def fcost(z):
        pose, _ = unpack(np.r_[z, 0.7, 0.7, 1.0])
        F = np.array(m.formants(pose, fmax=7000, df=10)[:3]); F = np.where(np.isfinite(F), F, 9000)
        return np.sqrt(np.sum(np.array([1, 1, .7]) * (bark(F) - bark(T)) ** 2))
    prev = Pose.from_vec(json.loads((ROOT / "models/bun_vowels.json").read_text())["vowels"]["iː"]["pose"])
    starts = [prev.vec()[:9], Pose(jaw=.15, body=.8, front=.8, lips=.6, root=1).vec()[:9],
              Pose(jaw=.05, body=1, front=.6, lips=.5, root=.5, larynx=1).vec()[:9], Pose(jaw=.3, body=.6, front=1, lips=1, root=1).vec()[:9]]
    # also search where along the mouth the tongue narrows it (front), which sets F3
    for fr in np.linspace(0.4, 1.0, 7):
        for b in (0.5, 0.8, 1.0):
            starts.append(Pose(jaw=.1, body=b, front=fr, lips=.6, root=1, larynx=.5).vec()[:9])
    r1 = min((minimize(fcost, z, method="Powell", options=dict(maxfev=2500)) for z in starts), key=lambda r: r.fun)
    zp = r1.x
    print(f"  stage 1 (mouth from resonances): {[int(x) for x in m.formants(unpack(np.r_[zp, .7, .7, 1])[0])[:3]]}, err {r1.fun:.2f}", flush=True)
    pose0 = unpack(np.r_[zp, .7, .7, 1])[0]
    r2 = min((minimize(lambda q: hcost(pose0, unpack(np.r_[zp, q])[1]), q0, method="Powell", options=dict(maxfev=1500))
              for q0 in ([0.8, 0.7, 1.0], [0.65, 0.66, 0.4], [0.9, 0.6, 2.0])), key=lambda r: r.fun)
    print(f"  stage 2 (voice box from harmonics): {hcost(pose0, unpack(np.r_[zp, r2.x])[1]):.2f} dB", flush=True)
    def jcost(z):   # both, with the resonances still held to his
        pose, src = unpack(z); return hcost(pose, src) + 3.0 * fcost(z[:9])
    r3 = minimize(jcost, np.r_[zp, r2.x], method="Powell", options=dict(maxfev=4000, xtol=1e-4, ftol=1e-5))
    pose, src = unpack(r3.x)
    return (pose, src), hcost(pose, src)


# ---- render and measure ----------------------------------------------------------------
def render(m, pose, src, f0, ms, steady, rng):
    Oq, am, Ta = src; jit, shim, asp = steady
    dur = ms / 1000.0 + 0.06
    atk, rel = 0.03, 0.05                                           # breath swells in, fades out
    amp = lambda t: np.clip(t / atk, 0, 1) * np.clip((dur - 0.01 - t) / rel, 0, 1)
    u = flow(lambda t: f0, dur, Oq, am, Ta, jit, shim, asp, amp, rng)
    nfft = 8192; f = np.fft.rfftfreq(nfft, 1 / SR)
    H = m.response(pose, np.maximum(f, 1.0), radiate=True); H[0] = 0
    ir = np.fft.irfft(H, nfft) * np.hanning(2 * nfft)[nfft:]
    y = fftconvolve(u, ir)[: len(u)]
    return y / (np.abs(y).max() + 1e-12) * 0.7


def measure(y, f0):
    snd = pm.Sound(y, SR)
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
    d = snd.duration; r = source_measures(snd, 0.03, d - 0.05, F, P)
    ts = np.arange(0.3 * d, 0.7 * d, 0.005)
    r["F1"] = float(np.nanmedian([F.get_value_at_time(1, t) for t in ts]))
    r["B1"] = float(np.nanmedian([F.get_bandwidth_at_time(1, t) for t in ts]))
    seg = y[int(0.3 * d * SR): int(0.75 * d * SR)]
    return r, harmonics(seg, SR, f0)


def main():
    his = his_ees()
    import os
    anat = os.environ.get("EE_ANAT", "")
    kw = {"larcav": dict(larcav=(7, 1.0, 4, 0.15)), "buccal": dict(buccal=(20, 0.5, 44)), "": {}}[anat]
    m = BunMouth(SIZE, neck_mm=NECK, **kw)
    print("anatomy:", kw or "plain")
    (pose, src), err = fit(m, his)
    print(f"\nfit: mean harmonic error {err:.2f} dB; voice box Oq {src[0]:.2f}, am {src[1]:.2f}, Ta {src[2]:.2f} ms")
    print("     mouth:", {n: round(float(v), 2) for n, v in zip(NAMES, pose.vec()) if abs(v) > 0.01})
    print("     mouth resonances:", [round(x) for x in m.formants(pose)[:4] if x == x])
    # gentleness and breath, judged on the model's own audio (breath noise rings
    # his upper resonances; the hum region stays pure), then steadiness
    tgt = {k: float(np.nanmedian([h["meas"][k] for h in his])) for k in ("HNR_0_500", "jitter_pct", "shimmer_dB")}
    best = None
    for Ta in (0.6, 1.0, 1.5, 2.0, 3.0):
        for asp in (0.05, 0.1, 0.15, 0.25, 0.4, 0.6):
            e = 0.0
            for h in his:
                y = render(m, pose, (src[0], src[1], Ta), h["f0"], max(h["ms"], 150), (0.003, 0.01, asp), np.random.default_rng(1))
                _, hm = measure(y, h["f0"])
                d = (hm - hm[0]) - (h["harm"] - h["harm"][0]); e += np.sqrt(np.mean(d[1:] ** 2))
            if best is None or e < best[0]:
                best = (e, Ta, asp)
    src = (src[0], src[1], best[1]); asp = best[2]
    print(f"     gentleness Ta {best[1]} ms, breath {asp}: harmonic error on the model's audio {best[0] / len(his):.2f} dB")
    best = None
    for jit in (0.0005, 0.001, 0.002, 0.004):
        for shim in (0.005, 0.01, 0.02, 0.04):
            r, _ = measure(render(m, pose, src, 264.0, 300, (jit, shim, asp), np.random.default_rng(0)), 264.0)
            e = np.nansum([abs(r[k] - v) / sc for (k, v), sc in zip(tgt.items(), (3, 0.1, 0.2))])
            if best is None or e < best[0]:
                best = (e, (jit, shim, asp), r)
    steady = best[1]
    print(f"     steadiness: jitter {steady[0]}, shimmer {steady[1]}, breath {steady[2]}  "
          f"(target {', '.join(f'{k} {v:.1f}' for k, v in tgt.items())})")
    rng = np.random.default_rng(7)
    rows, pieces = [], []
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1) if x.ndim > 1 else x
    gap = np.zeros(int(0.35 * 24000))
    print(f"\n{'':10} {'pitch':>6} {'F1':>5} {'B1':>5} {'H1-H2':>6} {'H2':>5} {'H3':>5} {'H4':>5} {'H1-A3':>6} "
          f"{'HNR<500':>7} {'HNR1.5-2.5k':>11} {'jitter':>6} {'shimmer':>7}")
    for i, h in enumerate(his):
        y = render(m, pose, src, h["f0"], h["ms"], steady, rng)
        r, hm = measure(y, h["f0"])
        sf.write(OUT / f"ee_model_{int(h['f0'])}.wav", resample_poly(y, 1, 2), 24000)
        for who, rr, hh in (("him", h["meas"], h["harm"]), ("model", r, hm)):
            print(f"{who + ' ' + str(int(h['f0'])):10} {h['f0']:6.0f} {rr['F1']:5.0f} {rr['B1']:5.0f} {rr['H1H2']:6.1f} "
                  f"{hh[1] - hh[0]:5.0f} {hh[2] - hh[0]:5.0f} {hh[3] - hh[0]:5.0f} {rr['H1A3']:6.1f} {rr['HNR_0_500']:7.1f} "
                  f"{rr.get('HNR_1500_2500', np.nan):11.1f} {rr['jitter_pct']:6.2f} {rr['shimmer_dB']:7.2f}")
        rows.append(dict(f0=h["f0"], him=h["meas"], him_harm=(h["harm"] - h["harm"][0]).tolist(),
                         model=r, model_harm=(hm - hm[0]).tolist()))
        s, e = h["span"]
        real = resample_poly(x[int((s - 0.02) * sr): int((e + 0.03) * sr)], 1, 2)
        pieces += [real / np.abs(real).max() * 0.7, gap, resample_poly(y, 1, 2), gap, gap]
    import os
    tag = ("_band" if float(os.environ.get("EE_BAND_HZ", "0")) > 0 else "") + (f"_{anat}" if anat else "")
    sf.write(OUT / f"ee_him_vs_model{tag}.wav", np.concatenate(pieces), 24000)
    (ROOT / f"models/build_ee{('_' + anat) if anat else ''}.json").write_text(json.dumps(dict(
        size=SIZE, neck=NECK, anatomy={k: list(v) for k, v in kw.items()}, pose=pose.vec().tolist(), source=dict(Oq=src[0], am=src[1], Ta_ms=src[2]),
        steady=dict(jitter=steady[0], shimmer=steady[1], breath=steady[2]), fit_err_db=err, rows=rows), indent=1, default=float))
    print("\n", OUT / "ee_him_vs_model.wav")


if __name__ == "__main__":
    main()
