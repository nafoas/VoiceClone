"""Listening file for ROADMAP Step 2.4 (+ 3.1): his three "ee"s and his "n" hum, each as
his clip | checkpoint 8 | VocalTractLab with his bun mouth, his own side anatomy, his tissue and his
self-oscillating vocal folds (one fit for all four: models/vtl_folds2{TAG}.json).

The pitch follows his for this comparison only (his way of setting pitch is ROADMAP Step 7); breath rises
and falls at each end (lung pressure); nothing is done to the sound except one playback gain per piece
(matched loudness, so the comparison is of quality, not level). His folds reach a little under the pitch
they are asked for (the fit's pitch cells): the pitch command is his contour divided by one constant, the
fit's mean ratio, the same for all four sounds (test only, like following his contour). At the end: the model alone, an "ee" and a
"nnn" held for 0.6 s at his pitch, to hear the hum itself.

    python scripts/build/vtl_listen2.py [models/vtl_folds2_tissue.json] -> reference/archive/vtl_step2_ee_n.wav
"""
import json
import os
import sys

MODEL = sys.argv[1] if len(sys.argv) > 1 else "models/vtl_folds2_tissue.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "reference/archive/vtl_step2_ee_n.wav"
sys.argv = sys.argv[:1]
for p in (".", "scripts", "scripts/build", "scripts/listen", "analysis/physics"):
    sys.path.insert(0, p)
d = json.load(open(MODEL))
if any(k.endswith("_stiff") for k in d["folds"]):
    os.environ["TISSUE"] = "1"
import numpy as np  # noqa: E402
import parselmouth as pm  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import resample_poly  # noqa: E402

import bun_folds as BF  # noqa: E402
import vtl_folds2 as F  # noqa: E402

q = d["folds"]
_pc = [v[0] for k, v in d["cells"].items() if k.endswith("pitch")]
CMD = 1.0 / (1.0 + float(np.mean(_pc)))   # pitch command per Hz wanted (his folds land this much low)
print(f"pitch command x{CMD:.3f} (the fit's pitch cells: {np.round(_pc, 3).tolist()})")
F.setup(); F._W["z"] = F.M.pad(d["z"]); V = F._W["V"]
path = "/tmp/claude-0/-home-user-VoiceClone/7e3261ab-22a0-5713-8c0c-f1044b891953/scratchpad/listen2.speaker"
BF.make_speaker(F.fold_static(q), path); V.use_speaker(path)
if not F.HUMAN_SIDE:
    import bun_vtl as BV
    BV.set_his_side(0.8, F._W["z"][6])
F.apply_tissue(q)

X, sr = sf.read("reference/source/prince_reference.wav"); X = X.mean(1)
P = pm.Sound(X, sr).to_pitch_ac(time_step=0.0025, pitch_floor=150, pitch_ceiling=700)
tt = P.xs(); f0 = P.selected_array["frequency"]; ok = f0 > 0
ck8 = np.load("out/listen/ck8_render.npy")
rc = lambda u: 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))
rms = lambda w: np.sqrt(np.mean(w ** 2)) + 1e-12
gap = np.zeros(int(0.35 * 48000))


def model(lab, T, fv, his_len):
    fr = F.tube_frames(F._W["z"], lab, q["nport"])
    G = []
    for t, fq in zip(T, fv):
        g = V.glottis_shape("modal"); g[:6] = [fq * CMD, q["PR"], q["XB"], q["XT"], q["AA"], q["AS"]]
        g[1] *= min(rc((t - T[0]) / (F.ONSET_MS / 1000)), 1 - rc((t - (T[-1] - 0.03)) / 0.03))   # breath in (as in the fit), out
        G.append(g)
    lead = int(0.1 * V.SR / V.STEP)   # 100 ms run-in at rest (folds settle), cut off afterwards
    y = V.synth([fr] * (lead + len(T)), np.r_[np.tile(np.r_[G[0][:1], 0.0, G[0][2:]], (lead, 1)), np.array(G)])
    y = y[(lead - 1) * V.STEP:]
    return resample_poly(y, 160, 147)[:his_len]


pieces = []
for t in F._W["tg"]:
    a, b = t["t"]; a -= 0.02; b += 0.02
    T = np.arange(a, b, V.STEP / V.SR); fv = np.interp(T, tt[ok], f0[ok])
    his = X[int(a * 48000): int(b * 48000)]; old = ck8[int(a * 48000): int(b * 48000)]
    y = model(t["lab"], T, fv, len(his))
    y = y * rms(his) / rms(y); old = old * rms(his) / rms(old)
    k = 0.6 / max(np.abs(his).max(), np.abs(old).max(), np.abs(y).max())
    pieces += [his * k, gap, old * k, gap, y * k, gap, gap]
    print(f"{t['lab']}@{t['t'][0]:.2f}: his | checkpoint 8 | VocalTractLab", flush=True)
for lab, fq in (("iː", 350.0), ("n", 265.0)):   # the model alone, held
    T = np.arange(0, 0.6, V.STEP / V.SR)
    y = model(lab, T, np.full(len(T), fq), int(0.6 * 48000))
    pieces += [y * 0.25 / max(np.abs(y).max(), 1e-9), gap]
    print(f"held {lab} at {fq:.0f} Hz (model alone)", flush=True)
sf.write(OUT, np.concatenate(pieces), 48000)
print("wrote", OUT)
