"""Harmonic amplitudes measured straight from the waveform (no vocoder model).
    python analysis/harmonics.py file.wav [...]"""
import sys, numpy as np, soundfile as sf, pyworld as pw

def harm(path, nh=8):
    a, sr = sf.read(path)
    if a.ndim > 1: a = a.mean(1)
    f0, t = pw.harvest(a.astype(float), sr, frame_period=10, f0_floor=80, f0_ceil=1200)
    n = int(0.06 * sr) // 2 * 2; win = np.hanning(n); rows = []
    for k in np.where(f0 > 0)[0]:
        c = int(t[k] * sr); seg = a[c - n // 2: c + n // 2]
        if len(seg) < n or np.sqrt(np.mean(seg ** 2)) < 0.1 * np.abs(a).max() * 0.3: continue
        S = np.abs(np.fft.rfft(seg * win, 8 * n)); fq = np.fft.rfftfreq(8 * n, 1 / sr)
        h = []
        for m in range(1, nh + 1):
            band = (fq > f0[k] * (m - 0.3)) & (fq < f0[k] * (m + 0.3)); h.append(20 * np.log10(S[band].max() + 1e-12))
        rows.append(np.array(h) - h[0])
    return np.median(rows, 0)

if __name__ == "__main__":
    print(f"{'':30}  H1   H2   H3   H4   H5   H6   H7   H8   (dB relative to H1)")
    for p in sys.argv[1:]:
        h = harm(p); print(f"{p[-30:]:30} " + " ".join(f"{x:4.0f}" for x in h))
