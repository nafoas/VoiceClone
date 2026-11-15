"""Step 1e: back to 1c's tone, with breath and roughness put back in steps.

1c (no breath, almost no roughness) was "very computery"; 1b (breath 0.05) was
"breathy, jittery". 1c over-corrected. Everything here is 1c (same mouth,
voice box, slow pitch drift); only breath and cycle-to-cycle roughness change,
in equal steps from 1c (0) to 1b's level (4).

    python scripts/build/ee_ladder.py -> out/build/ee_ladder.wav
"""
import json, sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, resample_poly, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build")); sys.path.insert(0, str(ROOT / "analysis/physics"))
sys.argv = sys.argv[:1] + ["30"]
import ee as E  # noqa: E402
import tone as T  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402

FIT = json.loads((ROOT / "models/build_ee_tone.json").read_text())
M = BunMouth(0.75, neck_mm=FIT["neck"], larcav=tuple(FIT["larcav"]))
POSE = Pose.from_vec(FIT["pose"]); S = FIT["source"]; SRC = (S["Oq"], S["am"], S["Ta_ms"])
#        breath   cycle jitter  cycle shimmer
STEPS = [(0.0,    0.0005,       0.003),      # 0 = 1c
         (0.0125, 0.001,        0.006),
         (0.025,  0.0015,       0.010),
         (0.0375, 0.002,        0.015),
         (0.05,   0.002,        0.020)]      # 4 = 1b's breath level


def render(f0, ms, breath, jit, shim, seed=3):
    rng = np.random.default_rng(seed)
    dur = ms / 1000 + 0.06; n = int(dur * 1000) + 10
    sos = butter(2, 6 / 500, "low", output="sos")
    drift = sosfiltfilt(sos, rng.standard_normal(n)); drift = drift / (drift.std() + 1e-9) * 6.0
    ld = sosfiltfilt(sos, rng.standard_normal(n)); ld = ld / (ld.std() + 1e-9) * 0.15
    ftrack = lambda t: f0 * 2 ** (drift[min(int(t * 1000), n - 1)] / 1200)
    amp = lambda t: np.clip(t / 0.03, 0, 1) * np.clip((dur - 0.01 - t) / 0.05, 0, 1) * 10 ** (ld[min(int(t * 1000), n - 1)] / 20)
    u = E.flow(ftrack, dur, *SRC, jit, shim, breath, amp, rng)
    f = np.fft.rfftfreq(8192, 1 / E.SR); H = M.response(POSE, np.maximum(f, 1.0), radiate=True); H[0] = 0
    ir = np.fft.irfft(H, 8192) * np.hanning(16384)[8192:]
    y = fftconvolve(u, ir)[: len(u)]
    return resample_poly(y / (np.abs(y).max() + 1e-12) * 0.7, 1, 2)


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    gap = np.zeros(int(0.3 * 24000)); big = np.zeros(int(0.9 * 24000)); out = []; rows = T.his_rows()[:1]
    for (s, e), f0, ms in (((0.79, 0.99), 264.0, 200), ((2.09, 2.30), 331.0, 210)):
        real = resample_poly(x[int((s - 0.02) * sr): int((e + 0.03) * sr)], 1, 2)
        out += [real / np.abs(real).max() * 0.7, gap]
        for k, (b, j, sh) in enumerate(STEPS):
            y = render(f0, ms, b, j, sh); out += [y, gap]
            if f0 == 264.0:
                rows.append(T.analyse(y, 24000, f"step {k}"))
        out.append(big)
    sf.write(ROOT / "out/build/ee_ladder.wav", np.concatenate(out), 24000)
    T.show(rows)


if __name__ == "__main__":
    main()
