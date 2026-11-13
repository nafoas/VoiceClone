"""The body transform: make a plain TTS voice come out of a small round bun.

Uses the WORLD vocoder, which splits speech into three independent parts:
  f0  - pitch contour
  sp  - spectral envelope (vocal tract resonances / formants)
  ap  - aperiodicity (how much is noise vs. tone, i.e. breathiness)
so pitch, body size and breath can each be moved on their own. Moving pitch
and formants together is what produces the chipmunk/child effect; here they
are separate knobs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyworld as pw

FRAME_MS = 5.0


@dataclass
class BodySettings:
    pitch_st: float
    pitch_range: float
    formant_shift: float
    breathiness: float
    nasality: float
    nasal_pole_hz: float
    nasal_zero_hz: float
    softness: float
    de_ess_db: float
    end_rise_st: float = 0.0


def _warp(env: np.ndarray, alpha: float) -> np.ndarray:
    """Stretch a (frames x bins) envelope along frequency. alpha > 1 moves
    resonances up (smaller vocal tract)."""
    if abs(alpha - 1.0) < 1e-3:
        return env
    k = env.shape[1]
    src = np.clip(np.arange(k) / alpha, 0, k - 1)
    i0 = np.floor(src).astype(int)
    i1 = np.minimum(i0 + 1, k - 1)
    frac = src - i0
    return env[:, i0] * (1 - frac) + env[:, i1] * frac


def _gauss(f: np.ndarray, center: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((f - center) / width) ** 2)


def transform(x: np.ndarray, fs: int, s: BodySettings) -> np.ndarray:
    x = np.ascontiguousarray(x, dtype=np.float64)
    if len(x) < fs * 0.05:
        return x
    f0, t = pw.harvest(x, fs, frame_period=FRAME_MS, f0_floor=60, f0_ceil=900)
    sp = pw.cheaptrick(x, f0, t, fs)
    ap = pw.d4c(x, f0, t, fs)
    nbins = sp.shape[1]
    freqs = np.linspace(0, fs / 2, nbins)
    voiced = f0 > 0

    # --- pitch: shift, flatten/expand around the median, optional end rise
    if voiced.any():
        logf = np.log2(f0[voiced])
        med = np.median(logf)
        logf = med + (logf - med) * s.pitch_range + s.pitch_st / 12.0
        if s.end_rise_st:
            n = len(logf)
            ramp = np.clip((np.arange(n) - 0.65 * n) / (0.35 * n), 0, 1)
            logf = logf + ramp * s.end_rise_st / 12.0
        f0 = f0.copy()
        f0[voiced] = 2.0 ** logf

    # --- body size: move resonances up, independent of pitch
    sp = _warp(sp, s.formant_shift)
    ap = _warp(ap, s.formant_shift)

    # --- nasality: add a low nasal resonance and an anti-resonance
    if s.nasality > 0:
        pole = 1.0 + s.nasality * 2.0 * _gauss(freqs, s.nasal_pole_hz, 110.0)
        zero = 1.0 - s.nasality * 0.7 * _gauss(freqs, s.nasal_zero_hz, 260.0)
        sp = sp * (pole * zero)[None, :]

    # --- breathiness: more aperiodic energy, mostly above ~500 Hz
    if s.breathiness > 0:
        w = np.clip((freqs - 400.0) / 3000.0, 0, 1) ** 0.6
        ap = ap + (1.0 - ap) * np.clip(s.breathiness * w, 0, 0.95)[None, :]

    # --- softness: gentle roll-off of the top end (no sharp edges anywhere)
    if s.softness > 0:
        tilt = np.ones_like(freqs)
        hi = freqs > 5000
        tilt[hi] = (freqs[hi] / 5000.0) ** (-3.0 * s.softness)
        sp = sp * tilt[None, :] ** 2

    # --- de-ess: frames dominated by high-frequency noise get it pulled down
    if s.de_ess_db > 0:
        hf = freqs > 3500
        ratio = sp[:, hf].sum(1) / (sp.sum(1) + 1e-20)
        amount = np.clip((ratio - 0.35) / 0.4, 0, 1)
        att = 10 ** (-s.de_ess_db / 10.0)  # power domain
        gain = 1 - amount[:, None] * (1 - att) * hf[None, :]
        sp = sp * gain

    y = pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(ap), fs, FRAME_MS)
    return y.astype(np.float32)
