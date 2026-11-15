"""His voice box and a moving mouth: the model-only renderer.

Source: glottal flow pulses (KLGLOTT88 shape), every cycle slightly different
(the folds never close exactly the same way twice), slow smooth pitch drift,
gentle breath-pressure swells, and a small amount of glottal turbulence (in
puffs, while the folds are open).

Filter: his bun mouth, re-computed every 5 ms from a pose track, applied with
overlap-add, so the mouth can move (coarticulation, never perfectly still).

Nothing from any recording goes in. Every control is a physical setting.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfiltfilt

from .bunmouth import BunMouth, Pose

SR = 48000
HOP = 240                                   # 5 ms
NFFT = 4096


@dataclass
class Voice:
    Oq: float = 0.61                        # fraction of each cycle the folds are open
    am: float = 0.59                        # fraction of the open phase spent opening
    Ta_ms: float = 0.0                      # closure smoothness
    shape_var: float = 0.0                  # cycle-to-cycle variation of how the folds close (sd, fraction)
    cycle_jitter: float = 0.0005            # cycle-to-cycle period variation (sd, fraction)
    cycle_shimmer: float = 0.003            # cycle-to-cycle amplitude variation
    drift_cents: float = 6.0                # slow pitch drift (sd)
    swell_db: float = 0.0                   # slow breath-pressure swell (sd, dB)
    turbulence: float = 0.0                 # glottal turbulence noise (relative to flow)


def pulse(n, Oq, am):
    x = np.arange(n, dtype=float); To = Oq * n; Tp = am * To
    return np.clip(np.where(x < Tp, 0.5 * (1 - np.cos(np.pi * x / Tp)),
                            np.where(x < To, np.cos(0.5 * np.pi * (x - Tp) / max(To - Tp, 1)), 0.0)), 0, None)


def slow_noise(n_ms, sd, rng, hz=6.0):
    """Smooth random movement, below `hz`, with standard deviation `sd` (1 sample per ms)."""
    v = sosfiltfilt(butter(2, hz / 500, "low", output="sos"), rng.standard_normal(n_ms + 50))[:n_ms]
    return v / (v.std() + 1e-12) * sd


def source(f0_ms: np.ndarray, amp_ms: np.ndarray, v: Voice, rng) -> np.ndarray:
    """Glottal flow at SR for pitch and loudness tracks given per millisecond."""
    n_ms = len(f0_ms); n = int(n_ms * SR / 1000)
    drift = slow_noise(n_ms, v.drift_cents, rng)
    swell = 10 ** (slow_noise(n_ms, v.swell_db, rng, 4.0) / 20) if v.swell_db > 0 else np.ones(n_ms)
    u = np.zeros(n); t = 0.0
    while True:
        i = min(int(t * 1000), n_ms - 1)
        if f0_ms[i] <= 0:
            t += 0.001
            if t * 1000 >= n_ms - 1:
                break
            continue
        F = f0_ms[i] * 2 ** (drift[i] / 1200)
        T = 1.0 / F * (1 + v.cycle_jitter * rng.standard_normal())
        L = int(round(T * SR)); s0 = int(round(t * SR))
        if s0 + L >= n:
            break
        Oq = np.clip(v.Oq * (1 + v.shape_var * rng.standard_normal()), 0.3, 0.95)
        am = np.clip(v.am * (1 + v.shape_var * rng.standard_normal()), 0.4, 0.95)
        u[s0:s0 + L] = pulse(L, Oq, am) * (1 + v.cycle_shimmer * rng.standard_normal()) * amp_ms[i] * swell[i]
        t += T
    if v.Ta_ms > 0:
        a = np.exp(-1.0 / (v.Ta_ms * 1e-3 * SR)); u = lfilter([1 - a], [1, -a], u)
    if v.turbulence > 0:
        bb, ab = butter(2, 1500 / (SR / 2), "high")
        nz = lfilter(bb, ab, rng.standard_normal(n))
        u = u + v.turbulence * nz * (u / (u.max() + 1e-12))       # only while air flows through the folds
    return u


def render(m: BunMouth, poses: list[Pose], f0_ms, amp_ms, v: Voice, seed=0) -> np.ndarray:
    """poses: one per 5 ms frame. f0_ms, amp_ms: per millisecond."""
    rng = np.random.default_rng(seed)
    u = source(np.asarray(f0_ms, float), np.asarray(amp_ms, float), v, rng)
    f = np.fft.rfftfreq(NFFT, 1 / SR); win = np.hanning(2 * HOP + 1)[:-1]
    y = np.zeros(len(u) + NFFT)
    cache = {}
    for k in range(len(u) // HOP):
        p = poses[min(k, len(poses) - 1)]
        key = tuple(np.round(p.vec(), 3))
        if key not in cache:
            H = m.response(p, np.maximum(f, 1.0), radiate=True); H[0] = 0
            cache[key] = np.fft.irfft(H, NFFT) * np.hanning(2 * NFFT)[NFFT:]
        a = max(0, k * HOP - HOP); seg = u[a: a + 2 * HOP]
        if len(seg) < 2 * HOP:
            break
        y[a: a + 2 * HOP + NFFT - 1] += fftconvolve(seg * win, cache[key])
    return y[: len(u)]


def pose_track(n_frames, target: Pose, rng, drift: dict | None = None, start: Pose | None = None, tau_ms=25.0,
               end: Pose | None = None, end_frames=0):
    """A mouth that approaches its target from where it was (start), wanders a
    little around it (drift: articulator -> sd), and at the end moves toward
    `end` over the last end_frames."""
    tv = target.vec(); z = (start.vec() if start is not None else tv).copy()
    names = list(Pose().__dict__.keys())
    D = {k: slow_noise(n_frames * 5, sd, rng, 6.0)[::5] for k, sd in (drift or {}).items()}
    out = []
    for i in range(n_frames):
        goal = tv.copy()
        if end is not None and i >= n_frames - end_frames:
            goal = end.vec()
        z = z + (goal - z) * (1 - np.exp(-5.0 / tau_ms))
        q = z.copy()
        for kname, d in D.items():
            q[names.index(kname)] += d[i]
        out.append(Pose.from_vec(q))
    return out
