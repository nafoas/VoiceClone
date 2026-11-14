"""The body transform: make a plain TTS voice come out of Prince.

Uses the WORLD vocoder, which splits speech into three independent parts:
  f0  - pitch contour
  sp  - spectral envelope (vocal tract resonances / formants)
  ap  - aperiodicity (how much is noise vs. tone)
so each can be reshaped on its own. Targets come from the reference clip
(analysis/REFERENCE_ANALYSIS.md):

  round tone     steep spectral tilt, dominant fundamental, NOT breathy
  forward mouth  upper resonances (F2, F3) raised ~40%, F1 not raised
  terraced pitch flat plateau per word, steps between words, onset fall,
                 little chirps on plosive onsets, small end flick
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pyworld as pw

FRAME_MS = 5.0


@dataclass
class WordPitch:
    start: float           # seconds, relative to the audio passed in
    end: float
    level_st: float = 0.0  # plateau level relative to the phrase
    chirp: bool = False    # plosive onset


@dataclass
class BodySettings:
    pitch_st: float = 0.0
    pitch_range: float = 1.0
    formant_low: float = 1.0
    formant_high: float = 1.0
    formant_low_hz: float = 700.0
    formant_high_hz: float = 2200.0
    roundness: float = 0.0
    roundness_hz: float = 320.0
    breathiness: float = 0.0
    nasality: float = 0.0
    nasal_pole_hz: float = 380.0
    nasal_zero_hz: float = 1100.0
    softness: float = 0.0
    de_ess_db: float = 0.0
    terrace: float = 0.0
    onset_fall_st: float = 0.0
    chirp_st: float = 0.0
    end_flick_st: float = 0.0
    end_rise_st: float = 0.0
    hum_db: float = 0.0          # pitch-locked cliff above the 2nd harmonic
    hum_start: float = 1.6       # cliff starts at this multiple of f0
    hum_end: float = 3.2         # ... and is fully down by this multiple
    transplant: float = 0.0
    transplant_jump: float = 0.6
    transplant_hold: float = 0.15
    transplant_ref: str = ""
    words: list[WordPitch] = field(default_factory=list)


# ---------------------------------------------------------------- spectrum --
def _ratio(freqs: np.ndarray, s: BodySettings) -> np.ndarray:
    lo, hi = np.log(s.formant_low_hz), np.log(s.formant_high_hz)
    w = np.clip((np.log(np.maximum(freqs, 1.0)) - lo) / (hi - lo), 0, 1)
    w = 0.5 - 0.5 * np.cos(np.pi * w)  # smooth blend
    return s.formant_low * (1 - w) + s.formant_high * w


def _warp(env: np.ndarray, freqs: np.ndarray, s: BodySettings) -> np.ndarray:
    """Move resonances: content at source f lands at f * ratio(f)."""
    if abs(s.formant_low - 1) < 1e-3 and abs(s.formant_high - 1) < 1e-3:
        return env
    g = freqs * _ratio(freqs, s)          # monotonic source -> output map
    src = np.interp(freqs, g, freqs)      # output bin -> source frequency
    pos = src / freqs[-1] * (len(freqs) - 1)
    i0 = np.clip(np.floor(pos).astype(int), 0, len(freqs) - 1)
    i1 = np.minimum(i0 + 1, len(freqs) - 1)
    frac = pos - i0
    return env[:, i0] * (1 - frac) + env[:, i1] * frac


def _gauss(x: np.ndarray, center: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - center) / width) ** 2)


# ------------------------------------------------------------------- pitch --
def _smooth(x: np.ndarray, n: int) -> np.ndarray:
    if n <= 1:
        return x
    k = np.ones(n) / n
    pad = np.pad(x, (n // 2, n - 1 - n // 2), mode="edge")
    return np.convolve(pad, k, mode="valid")


def _pitch(f0: np.ndarray, t: np.ndarray, s: BodySettings) -> np.ndarray:
    v = f0 > 0
    if not v.any():
        return f0
    S = np.zeros_like(f0)
    S[v] = 12 * np.log2(f0[v])
    med = np.median(S[v])
    M = S - med                                    # original melody

    # per-word plateau (P) and per-word mean of original melody (W)
    P = np.full_like(f0, np.nan)
    W = np.full_like(f0, np.nan)
    for w in s.words:
        m = (t >= w.start) & (t < w.end)
        if not (m & v).any():
            continue
        P[m] = w.level_st
        W[m] = np.median(M[m & v])
    known = ~np.isnan(P)
    if known.any():
        idx = np.arange(len(f0))
        P = np.interp(idx, idx[known], P[known])
        W = np.interp(idx, idx[known], W[known])
    else:
        P[:] = 0
        W[:] = 0
    n = max(1, int(30 / FRAME_MS))                 # ~30 ms step transitions
    P, W = _smooth(P, n), _smooth(W, n)

    terr = s.terrace
    new = (1 - terr) * M * s.pitch_range + terr * (P + (M - W) * s.pitch_range * 0.15)

    vt = t[v]
    t0, t1 = vt[0], vt[-1]
    if s.onset_fall_st:
        new += s.onset_fall_st * np.exp(-np.clip(t - t0, 0, None) / 0.05) * (t >= t0)
    if s.chirp_st:
        for w in s.words:
            if w.chirp:
                wv = vt[(vt >= w.start) & (vt < w.end)]
                if len(wv):
                    new += s.chirp_st * _gauss(t, wv[0] + 0.012, 0.012)
    if s.end_flick_st:
        new += s.end_flick_st * np.clip((t - (t1 - 0.07)) / 0.07, 0, 1)
    if s.end_rise_st:
        dur = t1 - t0
        new += s.end_rise_st * np.clip((t - (t0 + 0.65 * dur)) / (0.35 * dur + 1e-6), 0, 1)

    out = f0.copy()
    out[v] = 2.0 ** ((med + s.pitch_st + new[v]) / 12.0)
    return out


# --------------------------------------------------------------- transform --
def transform(x: np.ndarray, fs: int, s: BodySettings) -> np.ndarray:
    x = np.ascontiguousarray(x, dtype=np.float64)
    if len(x) < fs * 0.05:
        return x.astype(np.float32)
    f0, t = pw.harvest(x, fs, frame_period=FRAME_MS, f0_floor=60, f0_ceil=900)
    sp = pw.cheaptrick(x, f0, t, fs)
    ap = pw.d4c(x, f0, t, fs)
    freqs = np.linspace(0, fs / 2, sp.shape[1])

    f0 = _pitch(f0, t, s)

    sp = _warp(sp, freqs, s)
    ap = _warp(ap, freqs, s)

    if s.roundness > 0:   # steeper tilt: the round, humming tone
        f = np.maximum(freqs, s.roundness_hz)
        sp = sp * (10 ** (-s.roundness * np.log2(f / s.roundness_hz) / 10))[None, :]

    if s.nasality > 0:
        pole = 1.0 + s.nasality * 2.0 * _gauss(freqs, s.nasal_pole_hz, 110.0)
        zero = 1.0 - s.nasality * 0.7 * _gauss(freqs, s.nasal_zero_hz, 260.0)
        sp = sp * (pole * zero)[None, :]

    if s.breathiness > 0:
        w = np.clip((freqs - 400.0) / 3000.0, 0, 1) ** 0.6
        ap = ap + (1.0 - ap) * np.clip(s.breathiness * w, 0, 0.95)[None, :]

    if s.softness > 0:
        tilt = np.ones_like(freqs)
        hi = freqs > 5000
        tilt[hi] = (freqs[hi] / 5000.0) ** (-3.0 * s.softness)
        sp = sp * tilt[None, :] ** 2

    if s.transplant > 0:  # rebuild voiced frames from Prince's real sound
        from .transplant import transplant
        sp, ap = transplant(sp, ap, f0, fs, FRAME_MS, amount=s.transplant,
                            ref_path=s.transplant_ref or None,
                            jump_cost=s.transplant_jump, hold_cost=s.transplant_hold)

    if s.hum_db > 0:  # the hum: keep H1-H2, drop everything above by hum_db
        F = np.where(f0 > 0, f0, np.median(f0[f0 > 0]) if (f0 > 0).any() else 250.0)
        x = (freqs[None, :] / F[:, None] - s.hum_start) / (s.hum_end - s.hum_start)
        x = np.clip(x, 0, 1)
        x = x * x * (3 - 2 * x)  # smoothstep
        sp = sp * 10 ** (-s.hum_db * x / 10)

    if s.de_ess_db > 0:
        hf = freqs > 3500
        ratio = sp[:, hf].sum(1) / (sp.sum(1) + 1e-20)
        amount = np.clip((ratio - 0.35) / 0.4, 0, 1)
        att = 10 ** (-s.de_ess_db / 10.0)
        sp = sp * (1 - amount[:, None] * (1 - att) * hf[None, :])

    y = pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(ap), fs, FRAME_MS)
    return y.astype(np.float32)
