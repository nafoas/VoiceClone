"""Is the hum continuous, and is the loudness carried by the breath?

voiced%     voiced frames between the first and last voiced frame of a phrase
breaks      number of voicing breaks (>=10 ms) inside the phrase, excluding
            those at real unvoiced consonants when unit info is given
env_range   loudness range across the phrase body (10th-90th pct, dB)
env_jump95  95th percentile of frame-to-frame loudness change (dB)
"""
import numpy as np, parselmouth as pm, soundfile as sf
from scipy.signal import resample_poly

def breath(y, sr=24000, step=0.005):
    s = pm.Sound(y.astype(np.float64), sr)
    p = s.to_pitch_ac(time_step=step, pitch_floor=120, pitch_ceiling=900)
    it = s.to_intensity(minimum_pitch=120, time_step=step)
    f = p.selected_array["frequency"]; t = p.xs()
    v = f > 0
    if not v.any():
        return None
    a, b = np.where(v)[0][[0, -1]]
    body = v[a:b + 1]
    runs, cur = 0, 0
    for x in body:
        if not x:
            cur += 1
        else:
            if cur * step * 1000 >= 10: runs += 1
            cur = 0
    e = np.array([it.get_value(tt) for tt in t[a:b + 1]])
    e = e[np.isfinite(e)]
    body_e = e[int(0.1 * len(e)): int(0.85 * len(e))] if len(e) > 10 else e
    return dict(voiced=100 * body.mean(), breaks=runs,
                env_range=np.percentile(body_e, 90) - np.percentile(body_e, 10),
                env_jump95=np.percentile(np.abs(np.diff(e)), 95))

def from_file(path, a=None, b=None, sr=24000):
    x, s0 = sf.read(path)
    if x.ndim > 1: x = x.mean(1)
    if s0 != sr: x = resample_poly(x, sr, s0)
    if a is not None: x = x[int(a * sr): int(b * sr)]
    return breath(x, sr)


def hum_track(y, sr=24000):
    """Level of the hum itself (1st harmonic, dB) per 5 ms frame, voiced only."""
    import pyworld as pw
    y = y.astype(np.float64)
    f0, t = pw.harvest(y, sr, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(y, f0, t, sr); fq = np.linspace(0, sr / 2, sp.shape[1])
    h1 = np.array([10 * np.log10(np.interp(f, fq, s) + 1e-20) if f > 0 else np.nan for f, s in zip(f0, sp)])
    tot = 10 * np.log10(sp.sum(1) + 1e-20)
    return h1, tot, f0 > 0


def hum_report(y, sr=24000):
    h1, tot, v = hum_track(y, sr)
    idx = np.where(v)[0]
    if len(idx) < 10:
        return None
    a, b = idx[0], idx[-1]
    h = h1[a:b + 1]; T = tot[a:b + 1]
    core = slice(int(0.1 * len(h)), int(0.85 * len(h)))
    hc = h[core][np.isfinite(h[core])]
    dh = np.abs(np.diff(h)); dh = dh[np.isfinite(dh)]
    # dips: hum drops >= 4 dB below its local (60 ms) median
    k = 12
    dips = 0
    for i in range(k, len(h) - k):
        if np.isfinite(h[i]) and h[i] < np.nanmedian(h[i - k:i + k]) - 4:
            dips += 1
    return dict(hum_range=np.percentile(hc, 90) - np.percentile(hc, 10),
                hum_jump95=np.percentile(dh, 95), hum_dips=100 * dips / max(1, len(h)),
                loud_range=np.percentile(T[core], 90) - np.percentile(T[core], 10))
