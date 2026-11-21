"""Listening file for VTL path step 1: his three "ee"s, checkpoint 8's, and VocalTractLab with his bun mouth
and his calibrated vocal folds (models/vtl_folds.json). The pitch follows his (this test only); the breath
rises and falls at each end; nothing is done to the sound except one playback gain per piece.

    python scripts/build/vtl_ee_demo.py -> reference/archive/vtl_ee_step1.wav
"""
import json
import os
import sys

os.environ.update(SRC="his", MOUTH_V1="1", NH="40", BUNSIZE="0.8")
for p in (".", "scripts", "scripts/build", "analysis/physics"):
    sys.path.insert(0, p)
sys.argv = sys.argv[:1]
import numpy as np  # noqa: E402
import parselmouth as pm  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import resample_poly  # noqa: E402

import vtl_calib as VC  # noqa: E402

VC.setup()
d = json.load(open("models/vtl_folds.json")); p = d["folds"]
if "z" in d:
    VC.set_pose(VC.M.pad(d["z"]))
V = VC._W["V"]
path = "/tmp/claude-0/-home-user-VoiceClone/7e3261ab-22a0-5713-8c0c-f1044b891953/scratchpad/bun_demo.speaker"
open(path, "w").write(VC.speaker_text(p)); V.use_speaker(path)
import vocaltractlab_cython as cy  # noqa: E402

X, sr = sf.read("reference/source/prince_reference.wav"); X = X.mean(1)
P = pm.Sound(X, sr).to_pitch_ac(time_step=0.0025, pitch_floor=150, pitch_ceiling=700); tt = P.xs(); f0 = P.selected_array["frequency"]
ck8 = np.load("out/listen/ck8_render.npy")
SEG = [(1.50, 1.62), (1.76, 1.93), (2.08, 2.33)]
rc = lambda u: 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))
pieces = []; gap = np.zeros(int(0.35 * 48000))
for a, b in SEG:
    T = np.arange(a, b, V.STEP / V.SR)
    ok = f0 > 0; fv = np.interp(T, tt[ok], f0[ok])
    G = []
    for t, fq in zip(T, fv):
        g = np.array(cy.get_shape("modal", "glottis"), float)
        g[VC.GI["F0"]] = fq; g[VC.GI["DP"]] = 0.0; g[VC.GI["FL"]] = 10.0
        for n in ("PR", "XB", "XT", "CA", "PL", "RA", "PS", "AS"):
            g[VC.GI[n]] = p[n]
        g[VC.GI["PR"]] *= min(rc((t - a) / 0.02), 1 - rc((t - (b - 0.03)) / 0.03))   # breath in, breath out
        G.append(g)
    y = V.synth([VC._W["fr"]] * len(T), np.array(G))
    y = resample_poly(y, 48000 // 300, V.SR // 300)
    his = X[int(a * 48000): int(b * 48000)]; old = ck8[int(a * 48000): int(b * 48000)]
    rms = lambda w: np.sqrt(np.mean(w ** 2)) + 1e-12
    y = y[: len(his)] * rms(his) / rms(y[: len(his)]); old = old * rms(his) / rms(old)
    k = 0.6 / max(np.abs(his).max(), np.abs(old).max(), np.abs(y).max())
    pieces += [his * k, gap, old * k, gap, y * k, gap, gap]
sf.write("reference/archive/vtl_ee_step1.wav", np.concatenate(pieces), 48000)
print("wrote reference/archive/vtl_ee_step1.wav")
