"""Measurable cells for what Da Boss hears as "a tonal buzz that sounds purely like a computer" vs his hum
(ROADMAP Step 4, brought forward 2026-11-25; first validated against the vtl_step2_ee_n verdict).

Found by comparing his clip, checkpoint 8 and the engine on the same sounds:
- mid_buzz: how far his strongest 1-2.5 kHz harmonic sits under his first (his 42-49 dB in "ee"; the buzzing
  engine 31-34). The average tone error hid it: a few loud mid harmonics among many decent ones.
- upper: the same for 2.5-5 kHz (his "ee" cluster: his 22-27 dB under H1).
- purity_<band>: harmonic peaks over the noise between them, per band (dB). His voice above 1 kHz is partly
  airy and irregular (his "n" at 2.5-5 kHz: 2 dB); the buzzing engine's upper harmonics are pure lines (28 dB).
  The overall clean-tone number (HNR) is ruled by the low harmonics and could not see this.

    cells(w, sr, f0) -> dict
    floor_limited(x, sr, window) -> {cell: True} for the cells of a window of his clip that are within FLOOR_DB of
        the recording's own noise floor (room + microphone): there his true value is at least as clean / as weak
        as measured, so a cell there is one-sided (never teach the voice to copy the recording's hiss).
"""
import numpy as np

BANDS = ((1000, 2500), (2500, 5000), (5000, 9000))


def cells(w, sr, f0):
    w = np.asarray(w, float)
    n = len(w); S = np.abs(np.fft.rfft(w * np.hanning(n), 8 * n)) ** 2; fr = np.fft.rfftfreq(8 * n, 1 / sr)
    hb = np.zeros_like(fr, bool)
    for h in np.arange(1, int(sr / 2 / f0)) * f0:
        hb |= np.abs(fr - h) < f0 * 0.12
    mid = np.abs(((fr / f0) % 1) - 0.5) < 0.25   # the space halfway between harmonics
    out = {}
    for lo, hi in BANDS:
        band = (fr >= lo) & (fr < hi)
        out[f"purity_{lo // 1000 if lo % 1000 == 0 else lo / 1000:g}-{hi / 1000:g}k"] = float(
            10 * np.log10(S[band & hb].mean() / (S[band & ~hb & mid].mean() + 1e-30)))
    H = np.array([S[np.abs(fr - k * f0) < f0 / 3].max() for k in range(1, int(sr / 2 / f0))])
    hz = np.arange(1, len(H) + 1) * f0; Hd = 10 * np.log10(H / H[0] + 1e-30)
    for name, (lo, hi) in (("mid_buzz", (1000, 2500)), ("upper", (2500, 5000))):
        k = (hz >= lo) & (hz < hi)
        out[name] = float(-Hd[k].max()) if np.any(k) else float("nan")
    return out


FLOOR_DB = 15.0
_BAND_ALL = ((1000, 2500), (2500, 5000), (5000, 9000))


def _band_psd(w, sr):
    win = np.hanning(len(w)); S = np.abs(np.fft.rfft(w * win)) ** 2 / np.sum(win ** 2); f = np.fft.rfftfreq(len(w), 1 / sr)
    return np.array([10 * np.log10(S[(f >= lo) & (f < hi)].mean() + 1e-30) for lo, hi in _BAND_ALL])


def recording_floor(x, sr, L_s=0.04, n=6):
    """Per-band noise floor of a recording: the mean of its n quietest windows."""
    L = int(L_s * sr); hop = L // 2
    e = np.array([np.mean(x[i:i + L] ** 2) for i in range(0, len(x) - L, hop)])
    return np.mean([_band_psd(x[i * hop: i * hop + L], sr) for i in np.argsort(e)[:n]], axis=0)


def floor_limited(x, sr, window, floor=None):
    floor = recording_floor(x, sr) if floor is None else floor
    a, b = window; above = _band_psd(x[int(a * sr): int(b * sr)], sr) - floor
    out = {}
    for (lo, hi), d in zip(_BAND_ALL, above):
        if d < FLOOR_DB:
            out[f"purity_{lo // 1000 if lo % 1000 == 0 else lo / 1000:g}-{hi / 1000:g}k"] = True
            if (lo, hi) == (2500, 5000):
                out["upper"] = True
            if (lo, hi) == (1000, 2500):
                out["mid_buzz"] = True
    return out
