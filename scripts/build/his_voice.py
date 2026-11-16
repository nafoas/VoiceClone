"""PLAN step 1: recover his real voice (the airflow through his vocal cords) from the clip.

Method: IAIF (iterative adaptive inverse filtering, Alku 1992). It estimates the mouth's
effect from his own recording (a throwaway stand-in), removes it, and leaves the
sound his vocal cords made. A measurement, done once on the clip; it never touches output.

Checks: pitched? pulse-shaped (open, close, rest)? the same voice under every sound?
And the cross-check: does IAIF's stand-in mouth agree with his mouth model on each sound?

    python scripts/build/his_voice.py -> out/build/his_voice_*.wav/png, models/his_voice.npz
"""
import json, os, sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.linalg import solve_toeplitz
from scipy.signal import lfilter, resample_poly, firwin, filtfilt, freqz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_catalogue import PHRASES  # noqa: E402

FS = int(os.environ.get("FS", "48000"))   # the clip's own rate: keeps his top end (to 24 kHz)
P_VT = int(os.environ.get("P_VT", str(FS // 1000 + 2)))   # stand-in mouth detail (LPC order)
METHOD = os.environ.get("METHOD", "qcp")
P_G = 4               # glottal tilt detail
LEAK = 0.99


def lpc(x, p):
    x = x * np.hanning(len(x))
    r = np.correlate(x, x, "full")[len(x) - 1: len(x) + p]
    r[0] *= 1.0 + 1e-6
    a = solve_toeplitz(r[:p], -r[1: p + 1])
    return np.r_[1.0, a]


def integ(x):
    return lfilter([1.0], [1.0, -LEAK], x)


def iaif(s):
    """Return (glottal flow, stand-in mouth LPC) for one steady stretch."""
    g1 = lpc(s, 1); y = lfilter(g1, 1, s)
    a1 = lpc(y, P_VT); g = integ(lfilter(a1, 1, s))
    ag = lpc(g, P_G); y = integ(lfilter(ag, 1, s))
    a2 = lpc(y, P_VT); flow = integ(lfilter(a2, 1, s))
    return flow, a2


def wlpc(x, p, w):
    """Weighted linear prediction (covariance form): minimise sum w(n) e(n)^2."""
    n = len(x); X = np.array([x[p - i - 1: n - i - 1] for i in range(p)]).T; y = x[p:]; ww = w[p:]
    A = (X * ww[:, None]).T @ X; b = (X * ww[:, None]).T @ y
    A += 1e-9 * np.trace(A) / p * np.eye(p)
    return np.r_[1.0, -np.linalg.solve(A, b)]


def qcp(s, f0):
    """Quasi-closed-phase analysis (Airaksinen et al. 2014): read the mouth mostly while the
    vocal cords are shut, by down-weighting the instants they snap closed. Built inside IAIF."""
    flow0, _ = iaif(s)
    _, gci = cycles(flow0, f0, cut="gci")
    P = FS / f0; w = np.ones(len(s)); d = 1e-5; PQ, DQ, ramp = 0.05, 0.7, max(2, int(0.07 * P))
    w[:] = d
    for g in gci:   # weight 1 over the quasi-closed stretch: from PQ*T after a closure for DQ*T
        a = int(g + PQ * P); b = int(a + DQ * P)
        for j in range(a, min(b, len(s))):
            w[j] = 1.0
        for j in range(ramp):
            if a - ramp + j >= 0 and a - ramp + j < len(s): w[a - ramp + j] = max(w[a - ramp + j], d + (1 - d) * j / ramp)
            if b + j < len(s): w[b + j] = max(w[b + j], 1 - (1 - d) * j / ramp)
    if len(gci) == 0:
        w[:] = 1.0
    g1 = lpc(s, 1); y = lfilter(g1, 1, s)
    a1 = wlpc(y, P_VT, w); g = integ(lfilter(a1, 1, s))
    ag = lpc(g, P_G); y = integ(lfilter(ag, 1, s))
    a2 = wlpc(y, P_VT, w); flow = integ(lfilter(a2, 1, s))
    return flow, a2


def cycles(flow, f0, cut="closed"):
    """Cut into single cycles at each closing instant (sharpest drop in flow)."""
    d = np.diff(flow); P = FS / f0; out = []; marks = []
    i = int(np.argmin(d[: int(P) + 1]))
    while i + 1.5 * P < len(d):
        j0, j1 = int(i + 0.7 * P), int(i + 1.3 * P)
        j = j0 + int(np.argmin(d[j0:j1])); marks.append(j); i = j
    if cut == "gci":
        return None, marks
    # cut where the cords rest shut (the flow's lowest point just after each closure): flat, so
    # cycles join seamlessly; each cycle's slow drift removed so it starts and ends at rest
    rest = []
    for m in marks:
        j1 = min(len(flow), int(m + 0.45 * P)); rest.append(m + int(np.argmin(flow[m:j1])))
    for a, b in zip(rest[:-1], rest[1:]):
        c = flow[a:b + 1].copy(); c -= np.linspace(c[0], c[-1], len(c)); out.append(c[:-1])
    return out, marks


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    x = resample_poly(x, FS, sr)
    hp = firwin(1201, 60, fs=FS, pass_zero=False); x = filtfilt(hp, [1.0], x)   # remove rumble, keep shape
    Pt = pm.Sound(x, FS).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff = Pt.selected_array["frequency"]
    segs = [(l, s, e) for ph in PHRASES for l, s, e, _ in ph if l in ("n", "ã", "ɐ˞", "ɹ", "m", "ũ", "iː")]
    res = []
    for l, s, e in segs:
        seg = x[int(s * FS): int(e * FS)]
        if len(seg) < int(0.04 * FS):
            continue
        f0s = ff[(tt >= s) & (tt <= e) & (ff > 0)]
        if len(f0s) < 3:
            continue
        f0 = float(np.median(f0s))
        flow, a2 = qcp(seg, f0) if METHOD == "qcp" else iaif(seg)
        cyc, marks = cycles(flow, f0)
        # harmonic levels of the flow (rel. H1), from a pitch-synchronous stretch
        k = np.arange(1, int(8000 // f0) + 1)
        if len(marks) >= 4:
            st = flow[marks[0]: marks[-1]]; n = len(st); per = n / (len(marks) - 1)
            S = np.fft.rfft(st * np.hanning(n)); fq = np.fft.rfftfreq(n, 1 / FS)
            lev = np.array([np.abs(S[np.argmin(np.abs(fq - kk * FS / per))]) for kk in k])
            lev = 20 * np.log10(lev / lev[0] + 1e-12)
        else:
            lev = np.full(len(k), np.nan)
        w, h = freqz([1.0], a2, worN=2048, fs=FS)
        hv = pm.Sound(np.diff(flow), FS).to_harmonicity_cc(time_step=0.01, minimum_pitch=150).values[0]
        hv = hv[hv > -100]
        res.append(dict(lab=l, s=s, e=e, f0=f0, flow=flow, cyc=cyc, k=k, lev=lev, vt=(w, 20 * np.log10(np.abs(h) + 1e-12)),
                        hnr=float(np.median(hv)) if len(hv) else np.nan))
        print(f"{l:3} {s:.2f}s {f0:4.0f} Hz: {len(cyc):3d} cycles; periodicity {res[-1]['hnr']:5.1f} dB; "
              f"tones H2..H6 {' '.join(f'{v:5.1f}' for v in lev[1:6])} dB", flush=True)

    # consistency: the same voice under every sound? compare flow tone levels on a common frequency grid
    grid = np.geomspace(500, 6000, 12)
    L = np.array([np.interp(np.log(grid), np.log(r["k"] * r["f0"]), r["lev"], left=np.nan, right=np.nan) for r in res])
    med = np.nanmedian(L, 0)
    print("\nhis voice (median over sounds), flow tone level vs H1:")
    print("  " + "  ".join(f"{g:5.0f}Hz {m:5.1f}" for g, m in zip(grid, med)))
    print("  slope: %.1f dB/octave" % np.polyfit(np.log2(grid[np.isfinite(med)]), med[np.isfinite(med)], 1)[0])
    print("disagreement of each sound's voice from the median (rms dB):")
    for r, row in zip(res, L):
        ok = np.isfinite(row); print(f"  {r['lab']:3} {r['s']:.2f}s: {np.sqrt(np.mean((row[ok] - med[ok]) ** 2)):5.1f}")

    # which recoveries are clean: the voice agrees with the median (<= 8 dB) and the sound has no nose
    # (IAIF's stand-in mouth has no nose; it cannot undo a nasal sound)
    dis = [float(np.sqrt(np.nanmean((row - med) ** 2))) for row in L]
    for r, d in zip(res, dis):
        r["clean"] = bool(d <= 8.0 and r["lab"] not in ("n", "m", "ũ"))
    print("clean recoveries: " + ", ".join(f"{r['lab']} {r['s']:.2f}" for r in res if r["clean"]))

    # save the bank
    np.savez(ROOT / "models/his_voice.npz", labs=[r["lab"] for r in res], clean=[r["clean"] for r in res], t=[r["s"] for r in res], f0=[r["f0"] for r in res],
             grid=grid, levels=L, median=med,
             **{f"cyc_{i}": np.concatenate([c for c in r["cyc"]]) for i, r in enumerate(res)},
             **{f"len_{i}": np.array([len(c) for c in r["cyc"]]) for i, r in enumerate(res)})

    # pictures: average pulse per sound; flow spectra; stand-in mouths
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
    for r in res:
        if len(r["cyc"]) < 3:
            continue
        P = int(np.median([len(c) for c in r["cyc"]])); C = np.array([np.interp(np.linspace(0, 1, 200), np.linspace(0, 1, len(c)), c) for c in r["cyc"]])
        m = np.median(C, 0); m = (m - m.min()) / (np.ptp(m) + 1e-12)
        ax[0].plot(np.linspace(0, 1, 200), m, lw=1, label=f"{r['lab']} {r['s']:.2f}")
        ax[1].plot(r["k"] * r["f0"], r["lev"], "o-", ms=2, lw=0.8)
        ax[2].plot(r["vt"][0], r["vt"][1] - r["vt"][1].max(), lw=0.8)
    ax[0].set_title("his vocal-cord airflow, one cycle (closing instant at 0 and 1)"); ax[0].set_xlabel("fraction of cycle")
    ax[0].legend(fontsize=6)
    ax[1].plot(grid, med, "k-", lw=2.5, label="median"); ax[1].set_xscale("log"); ax[1].set_title("his voice's tones (flow), dB vs 1st tone")
    ax[1].set_xlabel("Hz"); ax[1].legend()
    ax[2].set_title("IAIF stand-in mouth per sound (dB)"); ax[2].set_xlabel("Hz"); ax[2].set_xlim(0, 10000)
    fig.tight_layout(); fig.savefig(ROOT / "out/build/his_voice.png", dpi=110)

    # listening (slow): per clean sound, held 1.5 s: old buzz | his voice as airflow | his voice leaving the lips
    os.environ.setdefault("ZFILE", "models/mouth_inverse_P1.json"); os.environ.setdefault("SRC", "puff")
    sys.path.insert(0, str(ROOT / "scripts/build")); sys.argv = sys.argv[:1]
    import rebuild_tones as R
    rng = np.random.default_rng(0); HOLD = 1.5; out = [np.zeros(int(0.5 * FS))]; t0 = 0.5; marks = []
    fade = lambda v: v * np.minimum(1, np.minimum(np.arange(len(v)), len(v) - np.arange(len(v))) / (0.03 * FS))
    for r in res:
        if not r["clean"] or len(r["cyc"]) < 3:
            continue
        cyc = r["cyc"]; order = list(range(len(cyc))) + list(range(len(cyc) - 2, 0, -1)); his = []; k = 0
        while sum(map(len, his)) < HOLD * FS:
            his.append(cyc[order[k % len(order)]]); k += 1
        his = np.concatenate(his)
        P = int(round(48000 / r["f0"])); b = np.zeros(int(HOLD * 48000) + 4 * P); tt_ = P / 48000
        while tt_ * 48000 + P < len(b):
            c = int(tt_ * 48000); b[c - P: c + P] += R.cycle(P, r["f0"], rng); tt_ += 1 / r["f0"]
        buzz = resample_poly(b, FS, 48000)[: int(HOLD * FS)]
        for name, v, pause in (("old buzz (airflow)", buzz, 1.0), ("his voice (airflow)", his, 1.0),
                               ("his voice leaving the lips", np.diff(his, prepend=his[0]), 2.5)):
            marks.append(f"{t0:5.1f}s  {r['lab']} ({r['f0']:.0f} Hz): {name}")
            v = v - np.mean(v); out += [fade(v / np.abs(v).max() * 0.6), np.zeros(int(pause * FS))]; t0 += len(v) / FS + pause
    sf.write(ROOT / f"out/build/his_voice_{METHOD}_slow.wav", np.concatenate(out), FS)
    print("\n".join(marks))

if __name__ == "__main__":
    main()
