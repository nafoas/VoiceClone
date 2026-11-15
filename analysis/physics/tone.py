"""What makes his tone warm and pure, compared with a model "ee".

For each sound:
  balance    level in bands (dB re the band holding his pitch): warm vs shrill
  harm/noise harmonic level and between-harmonic (noise) level per band, dB re H1
  pitch      micro-movement of pitch inside the hum: slow drift vs fast wobble (cents)
  loudness   micro-movement of loudness (dB), slow vs fast

    python analysis/physics/tone.py his|FILE.wav ...
"""
import sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
BANDS = [(0, 500), (500, 1500), (1500, 3000), (3000, 5000), (5000, 8000), (8000, 11000)]
HIS = [(0.79, 0.99), (1.52, 1.60), (1.77, 1.90), (2.09, 2.30)]


def analyse(x, sr, label):
    snd = pm.Sound(x, sr)
    P = snd.to_pitch_ac(time_step=0.002, pitch_floor=120, pitch_ceiling=900)
    f = P.selected_array["frequency"]; f = f[f > 0]
    f0 = float(np.median(f))
    # harmonic vs gap energy, long window over the steady middle
    n = len(x); seg = x[int(0.15 * n): int(0.85 * n)]
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 18)) ** 2
    fq = np.fft.rfftfreq(1 << 18, 1 / sr)
    k = fq / f0; frac = np.abs(k - np.round(k))
    harm, gap = frac < 0.12, (frac > 0.35) & (k > 0.6)
    h1 = S[(fq > 0.8 * f0) & (fq < 1.2 * f0)].sum()
    row = dict(label=label, f0=f0)
    for lo, hi in BANDS:
        b = (fq >= lo) & (fq < hi)
        hb = S[b & harm].sum(); gb = S[b & gap].mean() * (b & harm).sum() if (b & gap).any() else np.nan
        row[f"H{lo}"] = 10 * np.log10(hb / h1 + 1e-15)
        row[f"N{lo}"] = 10 * np.log10(gb / h1 + 1e-15)
        row[f"B{lo}"] = 10 * np.log10(S[b].sum() / h1 + 1e-15)
    # pitch micro-movement (cents): slow (<8 Hz) vs fast (>15 Hz)
    if len(f) > 20:
        c = 1200 * np.log2(f / f0); c = c - np.mean(c); fs = 500.0
        slow = sosfiltfilt(butter(2, 8 / (fs / 2), "low", output="sos"), c)
        fast = c - sosfiltfilt(butter(2, 15 / (fs / 2), "low", output="sos"), c)
        row["pitch_slow_c"] = float(np.std(slow)); row["pitch_fast_c"] = float(np.std(fast))
    it = snd.to_intensity(minimum_pitch=120, time_step=0.002).values[0]
    it = it[len(it) // 6: -len(it) // 6]
    if len(it) > 20:
        fs = 500.0
        slow = sosfiltfilt(butter(2, 8 / (fs / 2), "low", output="sos"), it)
        row["loud_fast_db"] = float(np.std(it - slow))
    return row


def show(rows):
    print(f"{'':16} {'pitch':>5} | level per band, dB re H1 (harmonics / noise between them)")
    print(f"{'':16} {'':>5} | " + " | ".join(f"{lo / 1000:.1f}-{hi / 1000:.1f}k" for lo, hi in BANDS)
          + " | pitch wobble slow/fast (cents) | loud flutter dB")
    for r in rows:
        print(f"{r['label']:16} {r['f0']:5.0f} | " + " | ".join(f"{r[f'H{lo}']:5.0f}/{r[f'N{lo}']:4.0f}" for lo, _ in BANDS)
              + f" | {r.get('pitch_slow_c', np.nan):5.1f}/{r.get('pitch_fast_c', np.nan):4.1f} | {r.get('loud_fast_db', np.nan):.2f}")


def his_rows():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    return [analyse(x[int(s * sr): int(e * sr)], sr, f"him ee {s:.2f}") for s, e in HIS]


if __name__ == "__main__":
    rows = his_rows()
    for p in sys.argv[1:]:
        y, sr = sf.read(p); y = y.mean(1) if y.ndim > 1 else y
        rows.append(analyse(y, sr, Path(p).stem[:16]))
    show(rows)
