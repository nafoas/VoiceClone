"""Per-sound error of the rebuilt clip: spectral distance / loudness difference (dB)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import iterate as I
from prince_voice.bnuysynth import Catalogue, synth, SR

def breakdown(**kw):
    cat = Catalogue(); ref = I.reference()
    for units, t0, name in ((I.P1, I.T1, "phrase1"), (I.P2, I.T2, "peets")):
        y = synth(units, I.ref_f0(t0), cat, **kw)
        r = ref[int(t0 * SR): int(t0 * SR) + len(y)]
        _, Ly, ey = I.world(y); _, Lr, er = I.world(r); n = min(len(Ly), len(Lr))
        d = np.sqrt(np.mean((Ly[:n] - Lr[:n]) ** 2, 1)); de = ey[:n] - er[:n]
        out, f = [], 0
        for u in units:
            k = int(round(u.ms / 5)); seg = slice(f, min(f + k, n)); f += k
            out.append(f"{u.ph}:{np.mean(d[seg]):4.1f}/{np.mean(de[seg]):+4.0f}")
        print(f"{name:8} " + "  ".join(out))

if __name__ == "__main__":
    breakdown(hold=0.35, hold_cons=0.35, burst_wave=True, life=1.0)
