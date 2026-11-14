"""Per-instance measurements of every recorded sound in the clip, for the
identity table (docs/PRINCE_IDENTITY.md). Writes analysis/identity_instances.csv."""
import json, sys
from pathlib import Path
import numpy as np, parselmouth as pm, soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_catalogue import PHRASES  # noqa: E402

SR = 24000
snd = pm.Sound(str(ROOT / "reference/source/prince_reference.wav")).convert_to_mono()
F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
P = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
I = snd.to_intensity(minimum_pitch=120, time_step=0.005)
H = snd.to_harmonicity_cc(time_step=0.005, minimum_pitch=120)
a, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = a.mean(1)

def harm(s, e):
    n = int(0.04 * sr) // 2 * 2; win = np.hanning(n); rows = []
    for t in np.arange(s + 0.02, e - 0.02, 0.01):
        f0 = P.get_value_at_time(t)
        if not np.isfinite(f0): continue
        c = int(t * sr); seg = x[c - n // 2: c + n // 2]
        S = np.abs(np.fft.rfft(seg * win, 8 * n)); fq = np.fft.rfftfreq(8 * n, 1 / sr)
        h = [20 * np.log10(S[(fq > f0 * (m - .3)) & (fq < f0 * (m + .3))].max() + 1e-12) for m in range(1, 6)]
        rows.append(np.array(h) - h[0])
    return np.median(rows, 0) if rows else np.full(5, np.nan)

rows = []
for ph in PHRASES:
    for lab, s, e, st in ph:
        if lab == "_": continue
        d = e - s; ts = np.arange(s + 0.25 * d, e - 0.25 * d + 1e-9, 0.005)
        med = lambda f: float(np.nanmedian([f(t) for t in ts]))
        h = harm(s, e)
        rows.append(dict(sound=lab, start=s, ms=round(1000 * d), stressed=st,
                         F1=med(lambda t: F.get_value_at_time(1, t)), F2=med(lambda t: F.get_value_at_time(2, t)),
                         F3=med(lambda t: F.get_value_at_time(3, t)), f0=med(P.get_value_at_time),
                         dB=med(I.get_value), HNR=med(H.get_value), H2=h[1], H3=h[2], H4=h[3]))
import csv
with open(ROOT / "analysis/identity_instances.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    print(f"{r['sound']:3} {r['start']:.2f} {r['ms']:4}ms str={int(r['stressed'])} F1 {r['F1']:5.0f} F2 {r['F2']:5.0f} F3 {r['F3']:5.0f} "
          f"f0 {r['f0']:4.0f} {r['dB']:4.1f}dB HNR {r['HNR']:5.1f} H2/H3/H4 {r['H2']:4.0f} {r['H3']:4.0f} {r['H4']:4.0f}")
