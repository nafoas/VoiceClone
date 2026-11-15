"""Take his "ee" apart into the tones it is made of.

A voiced sound = harmonics (tones at 1x, 2x, 3x... his pitch) + noise. For
every harmonic: its amplitude, exact frequency and phase, moment by moment
(windows of 3 cycles, every 2.5 ms). What's left after removing them is the
noise: its spectrum and how it moves in time.

Then a rebuild from the measurements alone (the check that nothing was
missed) and the same decomposition of any model "ee" for comparison.

    python analysis/physics/ee_decompose.py [model.wav ...]
      -> analysis/physics/ee_decomp_*.npz / .png, out/build/decomp_*.wav
"""
import sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis/physics"
K = 40                                   # harmonics tracked (264 Hz x 40 = 10.6 kHz)
HOP = 0.0025


def f0_track(x, sr):
    P = pm.Sound(x, sr).to_pitch_ac(time_step=0.001, pitch_floor=150, pitch_ceiling=700, very_accurate=True)
    t = P.xs(); f = P.selected_array["frequency"]
    ok = f > 0
    return t[ok], f[ok]


def decompose(x, sr, label):
    tt, ff = f0_track(x, sr)
    times = np.arange(tt[0] + 0.006, tt[-1] - 0.006, HOP)
    A = np.full((len(times), K), np.nan); PH = np.full((len(times), K), np.nan); F0 = np.interp(times, tt, ff)
    for i, (t, f0) in enumerate(zip(times, F0)):
        L = 3.0 / f0; a, b = int((t - L / 2) * sr), int((t + L / 2) * sr)
        if a < 0 or b > len(x):
            continue
        seg = x[a:b]; n = np.arange(len(seg)) / sr - L / 2; w = np.hanning(len(seg))
        ks = np.arange(1, K + 1); ks = ks[ks * f0 < sr / 2 * 0.95]
        M = np.concatenate([np.cos(2 * np.pi * np.outer(n, ks * f0)), np.sin(2 * np.pi * np.outer(n, ks * f0))], 1)
        c, *_ = np.linalg.lstsq(M * w[:, None], seg * w, rcond=None)
        z = c[:len(ks)] - 1j * c[len(ks):]
        A[i, :len(ks)] = np.abs(z); PH[i, :len(ks)] = np.angle(z)
    # the harmonic part, rebuilt sample by sample from the tracks (phase-continuous)
    tsamp = np.arange(len(x)) / sr
    f0s = np.interp(tsamp, times, F0)
    phase1 = 2 * np.pi * np.cumsum(f0s) / sr
    # relative phase of each harmonic to the fundamental (the shape of each cycle)
    rel = PH - np.arange(1, K + 1)[None, :] * PH[:, :1]
    rel = np.angle(np.exp(1j * rel))
    # align absolute phase of H1 at the first frame
    i0 = np.argmin(np.abs(tsamp - times[0])); off = PH[0, 0] - phase1[i0]
    harm = np.zeros(len(x))
    for k in range(K):
        if np.all(np.isnan(A[:, k])):
            continue
        ak = np.interp(tsamp, times, np.nan_to_num(A[:, k]))
        rk = np.interp(tsamp, times, np.unwrap(np.nan_to_num(rel[:, k])))
        harm += ak * np.cos((k + 1) * (phase1 + off) + rk)
    inside = (tsamp >= times[0]) & (tsamp <= times[-1])
    noise = np.where(inside, x - harm, 0.0)
    np.savez(OUT / f"ee_decomp_{label}.npz", times=times, F0=F0, A=A, PH=PH, rel=rel, sr=sr)
    return dict(times=times, F0=F0, A=A, rel=rel, harm=harm, noise=noise, inside=inside, x=x, sr=sr)


def summary(d, label):
    A = d["A"]; ok = ~np.isnan(A[:, 0]); A = A[ok]; dB = 20 * np.log10(A + 1e-12); dB = dB - dB[:, :1]
    mid = slice(len(dB) // 5, -len(dB) // 5)
    prof = np.nanmedian(dB[mid], 0)
    flick = np.nanstd(dB[mid] - np.nanmedian(dB[mid], 0), 0)
    rel = d["rel"][ok][mid]; coh = np.abs(np.nanmean(np.exp(1j * rel), 0))   # 1 = this harmonic keeps its phase
    x, h, nz, ins = d["x"], d["harm"], d["noise"], d["inside"]
    hn = 10 * np.log10(np.sum(h[ins] ** 2) / np.sum(nz[ins] ** 2))
    print(f"\n{label}: pitch {np.median(d['F0']):.1f} Hz; harmonic/noise energy {hn:.1f} dB")
    print("  harmonic        " + " ".join(f"{k:4d}" for k in range(1, 21)))
    print("  level dB re H1  " + " ".join(f"{v:4.0f}" for v in prof[:20]))
    print("  flicker (sd dB) " + " ".join(f"{v:4.1f}" for v in flick[:20]))
    print("  phase steadiness" + " ".join(f"{v:5.2f}"[1:] for v in coh[:20]))
    return prof, flick, coh


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    seg = x[int(0.77 * sr): int(1.01 * sr)]
    d = decompose(seg, sr, "him")
    out = ROOT / "out/build"
    sf.write(out / "decomp_him_original.wav", seg / np.abs(seg).max() * 0.7, sr)
    sf.write(out / "decomp_him_tones_only.wav", d["harm"] / np.abs(seg).max() * 0.7, sr)
    sf.write(out / "decomp_him_rebuilt.wav", (d["harm"] + d["noise"]) / np.abs(seg).max() * 0.7, sr)
    sf.write(out / "decomp_him_noise_only.wav", d["noise"] / np.abs(seg).max() * 0.7 * 4, sr)
    res = {"him": summary(d, "HIM")}
    for p in sys.argv[1:]:
        y, ysr = sf.read(p); y = y.mean(1) if y.ndim > 1 else y
        res[Path(p).stem] = summary(decompose(y, ysr, Path(p).stem), Path(p).stem)
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    A = d["A"]; dB = 20 * np.log10(A + 1e-12); dB = dB - np.nanmax(dB)
    fig, ax = plt.subplots(1, 3, figsize=(20, 6))
    im = ax[0].imshow(dB[:, :30].T, aspect="auto", origin="lower", vmin=-70, vmax=0, cmap="magma",
                      extent=[d["times"][0], d["times"][-1], 0.5, 30.5])
    ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("harmonic number"); ax[0].set_title("his 'ee': every tone over time (dB)")
    plt.colorbar(im, ax=ax[0])
    for lab, (prof, flick, coh) in res.items():
        ax[1].plot(range(1, 31), prof[:30], "-o", ms=3, label=lab)
        ax[2].plot(range(1, 31), coh[:30], "-o", ms=3, label=lab)
    ax[1].set_xlabel("harmonic"); ax[1].set_ylabel("dB re H1"); ax[1].set_title("level of each tone (steady middle)"); ax[1].legend()
    ax[2].set_xlabel("harmonic"); ax[2].set_ylabel("phase steadiness (1 = locked)"); ax[2].set_title("does each tone keep its place in the cycle?")
    plt.tight_layout(); plt.savefig(OUT / "ee_decomp.png", dpi=70)


if __name__ == "__main__":
    main()
