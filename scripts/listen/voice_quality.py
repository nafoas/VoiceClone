"""His voice quality, measured the same way on his clip and on any model sound (roadmap Steps 2 and 4).

  hnr     how clean his tone is (harmonics-to-noise ratio, Praat cc, median, dB): high = little breath noise
  h1h2    his hum: first harmonic over the second (dB)
  jitter  pitch steadiness, cycle to cycle (%)
  shimmer loudness steadiness, cycle to cycle (dB)
  f0      median pitch (Hz)
"""
import numpy as np
import parselmouth as pm
from parselmouth.praat import call


def measure(w, sr, fmin=150, fmax=700):
    s = pm.Sound(np.asarray(w, float), sr)
    p = s.to_pitch_ac(pitch_floor=fmin, pitch_ceiling=fmax).selected_array["frequency"]; p = p[p > 0]
    if len(p) < 3:
        return dict(hnr=np.nan, h1h2=np.nan, jitter=np.nan, shimmer=np.nan, f0=np.nan)
    f0 = float(np.median(p))
    h = s.to_harmonicity_cc(time_step=0.01, minimum_pitch=fmin).values[0]; h = h[h > -100]
    pp = call(s, "To PointProcess (periodic, cc)", fmin, fmax)
    jit = call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3) * 100
    shim = call([s, pp], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    mid = np.asarray(w, float)[len(w) // 4: 3 * len(w) // 4]
    S = np.abs(np.fft.rfft(mid * np.hanning(len(mid)), 8 * len(mid))); f = np.fft.rfftfreq(8 * len(mid), 1 / sr)
    h1 = S[(f > f0 * 0.7) & (f < f0 * 1.3)].max(); h2 = S[(f > f0 * 1.7) & (f < f0 * 2.3)].max()
    return dict(hnr=float(np.median(h)) if len(h) else np.nan, h1h2=float(20 * np.log10(h1 / h2)), jitter=float(jit),
                shimmer=float(shim), f0=f0)


HIS_EE = [(1.53, 1.59), (1.79, 1.89), (2.11, 2.28)]   # the steady middles of his three "ee"s
HIS_HUM = [(0.07, 0.15), (0.74, 0.78)]                 # his first "n" hum and the "n" of "munis"
