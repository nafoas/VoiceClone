"""His pitch dial (ROADMAP Step 2 note, 2026-11-25): which fold tension he uses for the pitch he wants.

VocalTractLab turns a pitch command into fold tension Q = 1 + (command - NF0) / dF0 (masses / Q, springs x Q,
length x sqrt Q). NF0 and dF0 are a calibration, set for HUMAN folds in a human throat; scaled to his folds by
a rule of thumb they miss by -6..+3 %. Here they are measured from HIS folds in HIS mouth: run his "ee" and his
"n" over his pitch range, measure the pitch each tension gives, fit pitch = NF0 + dF0 (Q - 1), keep the line.
What a single line cannot follow (his "ee" and "n" differ near his first resonance: the folds and the mouth
pulling on each other) is physics and stays.

Not a per-utterance correction: two numbers, measured once per set of folds (each fit re-measures them).

    python scripts/build/pitch_dial.py models/vtl_folds2_X.json [out.json]   (out defaults to in place)
"""
import json
import os
import sys

MODEL = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else MODEL
sys.argv = sys.argv[:1]
for p in (".", "scripts", "scripts/build", "scripts/listen", "analysis/physics"):
    sys.path.insert(0, p)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
d = json.load(open(MODEL))
if any(k.endswith("_stiff") for k in d["folds"]):
    os.environ["TISSUE"] = "1"
import numpy as np  # noqa: E402

import bun_folds as BF  # noqa: E402
import vtl_folds2 as F  # noqa: E402

COMMANDS = (230.0, 270.0, 310.0, 350.0, 390.0, 430.0)


def measure(q, z):
    """(Q, measured pitch) pairs for his "ee" and "n" across his range."""
    F._W["z"] = F.M.pad(z); V = F._W["V"]; Q = F._W["Q"]
    st = F.fold_static(q)
    path = f"/tmp/claude-0/-home-user-VoiceClone/7e3261ab-22a0-5713-8c0c-f1044b891953/scratchpad/dial_{os.getpid()}.speaker"
    BF.make_speaker(st, path); V.use_speaker(path)
    import bun_vtl as BV
    BV.set_his_side(0.8, F._W["z"][6]); F.apply_tissue(q)
    N = int(0.45 * V.SR / V.STEP); pts = []
    for lab in ("iː", "n"):
        fr = F.tube_frames(F._W["z"], lab, q["nport"])
        for cmd in COMMANDS:
            G = np.tile(V.glottis_shape("modal"), (N, 1)); G[:, :6] = [cmd, q["PR"], q["XB"], q["XT"], q["AA"], q["AS"]]
            G[:, 1] *= F.breath(N, V.STEP / V.SR)
            f = Q.measure(V.synth([fr] * N, G)[-int(0.2 * V.SR):], V.SR)["f0"]
            if np.isfinite(f):
                pts.append((lab, cmd, 1.0 + (cmd - st["NF0"]) / st["dF0"], f))
    return pts


if __name__ == "__main__":
    F.setup()
    q = dict(d["folds"]); z = d["z"]
    for rnd in range(3):   # the line moves the tension each pitch uses; re-measure until it settles
        pts = measure(q, z)
        Qs = np.array([p[2] for p in pts]); fs = np.array([p[3] for p in pts])
        b, a = np.polyfit(Qs - 1.0, fs, 1)
        err = [(lab, cmd, round((f / cmd - 1) * 100, 1)) for lab, cmd, _, f in pts]
        print(f"round {rnd}: dial was NF0 {F.fold_static(q)['NF0']:.1f} dF0 {F.fold_static(q)['dF0']:.1f}; "
              f"pitch error % {err}", flush=True)
        q["dial_NF0"], q["dial_dF0"] = float(a), float(b)
        if max(abs(e[2]) for e in err) < 1.5:
            break
    pts = measure(q, z)
    err = {f"{lab}@{cmd:.0f}": round((f / cmd - 1) * 100, 2) for lab, cmd, _, f in pts}
    print(f"his dial: NF0 {q['dial_NF0']:.1f} Hz, dF0 {q['dial_dF0']:.1f} Hz per unit tension; pitch error % {err}")
    d["folds"] = q; d["dial_check_pct"] = err
    json.dump(d, open(OUT, "w"), indent=1)
    print("wrote", OUT)
