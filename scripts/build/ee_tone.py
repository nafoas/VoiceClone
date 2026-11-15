"""Step 1c: his "ee" as a warm, pure hum (Da Boss: step 1b was breathy, jittery,
airy, almost shrill).

What the measurements showed (analysis/physics/tone.py):
  - his bright 3-5 kHz band is HARMONIC (noise 17-23 dB below it): no breath
  - his top (5-8 kHz) is quiet; the model's was 15-20 dB too loud (shrill)
  - his pitch drifts slowly and smoothly (5-25 cents, < 8 Hz) with almost no
    cycle-to-cycle wobble (2-3 cents); random per-cycle jitter sounds rough
  - his "ee" F2 (3.3 kHz) belongs to the throat: larynx depth and voice box
    must be fitted together

Fit: ONE "ee" mouth shape + larynx depth (1.5-3 cm) + ONE voice box, judged on
band levels of harmonics (0-8 kHz) and his hum harmonics, for all four "ee"s.
Render: no breath; slow smooth pitch drift; tiny cycle-to-cycle variation.

    python scripts/build/ee_tone.py -> out/build/ee_tone_*.wav, models/build_ee_tone.json
"""
import json, sys, warnings
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.optimize import minimize
from scipy.signal import butter, sosfiltfilt, resample_poly

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics"))
sys.argv = sys.argv[:1] + ["30"]
import ee as E  # noqa: E402
import tone as T  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose, NAMES  # noqa: E402

SR = E.SR
BANDS = T.BANDS[:5]
LARCAV = (7, 1.0, 4, 0.15)
OUT = ROOT / "out" / "build"


def mouth_for(neck):
    return BunMouth(0.75, neck_mm=neck, larcav=LARCAV)


def model_harmonics(m, pose, f0, src, K=40):
    k = np.arange(1, K + 1) * f0
    H = 20 * np.log10(np.abs(m.response(pose, k, radiate=True)) + 1e-12)
    U = np.abs(np.fft.rfft(E.pulse(4096, src[0], src[1])))[1: K + 1]
    tilt = 1 / np.sqrt(1 + (2 * np.pi * k * src[2] * 1e-3) ** 2)
    return k, 20 * np.log10(U * tilt + 1e-12) + H


def band_levels(k, L):
    P = 10 ** (L / 10)
    return np.array([10 * np.log10(P[(k >= lo) & (k < hi)].sum() / P[0] + 1e-15) for lo, hi in BANDS])


def unpack(z):
    pose = np.clip(z[:9], E.EE_LO, E.EE_HI); v = Pose().vec(); v[:9] = pose
    neck = float(np.clip(z[9], 20.0, 40.0))
    src = (float(np.clip(z[10], 0.3, 0.9)), float(np.clip(z[11], 0.45, 0.9)), float(np.clip(z[12], 0.0, 2.0)))
    return Pose.from_vec(v), neck, src


def main():
    hisT = T.his_rows(); hisE = E.his_ees()
    tgt = [np.array([r[f"H{lo}"] for lo, _ in BANDS]) for r in hisT]
    cache = {}

    def cost(z):
        pose, neck, src = unpack(z)
        key = round(neck, 1)
        m = cache.setdefault(key, mouth_for(key))
        e = 0.0
        for h, t in zip(hisE, tgt):
            k, L = model_harmonics(m, pose, h["f0"], src)
            eb = band_levels(k, L)[1:] - t[1:]                         # band balance (warm vs shrill)
            eh = (L[1:4] - L[0]) - (h["harm"][1:4] - h["harm"][0])     # the hum: H2..H4
            e += np.sqrt(np.mean(eb ** 2)) + 0.5 * np.sqrt(np.mean(eh ** 2))
        return e / len(hisE)

    prev = json.loads((ROOT / "models/build_ee_larcav.json").read_text())
    starts = []
    for neck in (22.0, 26.0, 30.0):
        for src in ((0.45, 0.6, 0.0), (0.6, 0.7, 0.2), (0.4, 0.8, 0.1)):
            starts.append(np.r_[np.array(prev["pose"])[:9], neck, src])
    best = min((minimize(cost, z, method="Powell", options=dict(maxfev=3000, xtol=1e-4, ftol=1e-5)) for z in starts),
               key=lambda r: r.fun)
    pose, neck, src = unpack(best.x)
    m = mouth_for(neck)
    print(f"fit: error {best.fun:.2f} dB; larynx {neck * 0.075:.1f} cm lower; voice box Oq {src[0]:.2f} am {src[1]:.2f} "
          f"Ta {src[2]:.2f} ms; resonances {[round(x) for x in m.formants(pose, fmax=8000)[:4] if x == x]}")
    for h, t in zip(hisE, tgt):
        k, L = model_harmonics(m, pose, h["f0"], src)
        print(f"  {int(h['f0'])} Hz  him {np.round(t).astype(int)}  model {np.round(band_levels(k, L)).astype(int)}  "
              f"hum H2-4 him {np.round(h['harm'][1:4] - h['harm'][0]).astype(int)} model {np.round(L[1:4] - L[0]).astype(int)}")

    # render: no breath; slow smooth pitch drift (~6 cents, < 6 Hz); tiny cycle variation
    def render(f0, ms, seed):
        rng = np.random.default_rng(seed)
        dur = ms / 1000 + 0.06; n = int(dur * 1000) + 10
        sos = butter(2, 6 / 500, "low", output="sos")
        drift = sosfiltfilt(sos, rng.standard_normal(n)); drift = drift / (drift.std() + 1e-9) * 6.0
        ldrift = sosfiltfilt(sos, rng.standard_normal(n)); ldrift = ldrift / (ldrift.std() + 1e-9) * 0.15
        ftrack = lambda t: f0 * 2 ** (drift[min(int(t * 1000), n - 1)] / 1200)
        atk, rel = 0.03, 0.05
        amp = lambda t: np.clip(t / atk, 0, 1) * np.clip((dur - 0.01 - t) / rel, 0, 1) * 10 ** (ldrift[min(int(t * 1000), n - 1)] / 20)
        u = E.flow(ftrack, dur, src[0], src[1], src[2], 0.0005, 0.003, 0.0, amp, rng)
        nfft = 8192; f = np.fft.rfftfreq(nfft, 1 / SR)
        H = m.response(pose, np.maximum(f, 1.0), radiate=True); H[0] = 0
        ir = np.fft.irfft(H, nfft) * np.hanning(2 * nfft)[nfft:]
        from scipy.signal import fftconvolve
        y = fftconvolve(u, ir)[: len(u)]
        return y / (np.abs(y).max() + 1e-12) * 0.7

    import soundfile as sf
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    gap = np.zeros(int(0.35 * 24000)); pieces = []; files = []
    for i, h in enumerate(hisE):
        y = render(h["f0"], max(h["ms"], 150), i)
        p = OUT / f"ee_tone_{int(h['f0'])}.wav"; sf.write(p, resample_poly(y, 1, 2), 24000); files.append(str(p))
        s, e = h["span"]
        real = resample_poly(x[int((s - 0.02) * sr): int((e + 0.03) * sr)], 1, 2)
        pieces += [real / np.abs(real).max() * 0.7, gap, resample_poly(y, 1, 2), gap, gap]
    sf.write(OUT / "ee_tone_him_vs_model.wav", np.concatenate(pieces), 24000)
    rows = T.his_rows() + [T.analyse(sf.read(f)[0], 24000, Path(f).stem) for f in files]
    T.show(rows)
    (ROOT / "models/build_ee_tone.json").write_text(json.dumps(dict(
        pose=pose.vec().tolist(), neck=neck, larcav=LARCAV, source=dict(Oq=src[0], am=src[1], Ta_ms=src[2]),
        breath=0.0, drift_cents=6.0, cycle_jitter=0.0005, err=float(best.fun)), indent=1))


if __name__ == "__main__":
    main()
