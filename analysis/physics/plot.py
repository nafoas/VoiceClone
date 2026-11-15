"""Graphs for the physics experiments, with his real measurements overlaid.
    python analysis/physics/plot.py -> analysis/physics/physics_*.png"""
import csv, json, sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
R = json.loads((ROOT / "analysis/physics/results.json").read_text())
VOW = json.loads((ROOT / "models/bun_vowels.json").read_text())["vowels"]
HIS = [r for r in csv.DictReader(open(ROOT / "analysis/fingerprint_sounds.csv"))]
INST = [r for r in csv.DictReader(open(ROOT / "analysis/identity_instances.csv"))]
OUT = ROOT / "analysis/physics"
C = {"iː": "#c0392b", "ũ": "#16a085", "ã": "#d81b60", "ɐ˞": "#f39c12", "n": "#2e86c1", "m": "#1f4e79", "ɹ": "#8e44ad"}


def f(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return np.nan


def rows(e, v=None):
    return [r for r in R[e] if v is None or r.get("vowel") == v]


fig, ax = plt.subplots(2, 3, figsize=(18, 10.5))

# 1. the hum = F1 on the pitch (resonance tuning)
a = ax[0, 0]
for v in ("iː", "ũ", "ã"):
    F1 = VOW[v]["formants"][0]
    rr = rows("E3", v); x = [F1 / r["value"] for r in rr]
    a.plot(x, [r["H1H2"] for r in rr], "-o", color=C[v], alpha=0.6, label=f"model {v} (pitch 180-440 Hz)")
for r in HIS:
    if r["sound"] in C and np.isfinite(f(r, "H1H2")):
        a.plot(f(r, "F1") / f(r, "f0"), f(r, "H1H2"), "*", ms=15, color=C[r["sound"]], mec="k")
        a.annotate(f"{r['sound']} {f(r, 'f0'):.0f}Hz", (f(r, "F1") / f(r, "f0"), f(r, "H1H2")), fontsize=7, xytext=(4, 2),
                   textcoords="offset points")
a.axvspan(0.9, 1.45, color="#e8f6f0"); a.set_xlim(0.3, 6); a.set_ylim(-15, 35)
a.set_xlabel("F1 ÷ pitch"); a.set_ylabel("H1–H2 (dB): the hum")
a.set_title("1. The hum: when the mouth's first resonance sits on his pitch,\nthe 1st harmonic towers (stars = him; lines = physics model)")
a.legend(fontsize=7)

# 2. the cliff: H3 vs F1/f0
a = ax[0, 1]
for v in ("iː", "ũ", "ã"):
    F1 = VOW[v]["formants"][0]; rr = rows("E3", v)
    a.plot([F1 / r["value"] for r in rr], [r["H3"] for r in rr], "-o", color=C[v], alpha=0.6, label=f"model {v}")
for r in INST:
    if r["sound"] in C:
        a.plot(f(r, "F1") / f(r, "f0"), f(r, "H3"), "*", ms=13, color=C[r["sound"]], mec="k")
a.axvspan(0.9, 1.45, color="#e8f6f0"); a.set_xlim(0.3, 6)
a.set_xlabel("F1 ÷ pitch"); a.set_ylabel("H3 vs H1 (dB): the cliff")
a.set_title("2. The cliff follows the same rule:\ndeepest for closed sounds, light for his open 'a'")
a.legend(fontsize=7)

# 3. source shape: smooth closure and open phase add to the hum
a = ax[0, 2]
for e, lab, key in (("E1", "closure smoothness Ta (ms)", "Ta"), ("E2", "open quotient", "Oq")):
    for v, ls in (("iː", "-"), ("ã", "--")):
        rr = rows(e, v); x = [r["value"] for r in rr]
        if key == "Oq":
            x = [1 + 1.5 * (q - 0.4) / 0.55 for q in x]
        a.plot(x, [r["H1H2"] for r in rr], ls + ("o" if e == "E1" else "s"), color=C[v],
               label=f"{v}: {lab}" + (" (scaled 1-2.5)" if key == "Oq" else ""))
a.axhspan(5.3, 5.6, color=C["ã"], alpha=0.25); a.axhspan(9.6, 9.6 + 0.4, color=C["iː"], alpha=0.3)
a.set_xlabel("knob"); a.set_ylabel("H1–H2 (dB)")
a.set_title("3. A gentle voice adds to it: gradual closure and a long\nopen phase raise H1–H2 by ~5-9 dB (bands = his a, his ee @264 Hz)")
a.legend(fontsize=7)

# 4. bandwidth: oral narrow, nasal vowels broad
a = ax[1, 0]
for v in ("iː", "ã"):
    rr = rows("E4", v); a.plot([r["value"] for r in rr], [r["B1"] for r in rr], "-o", color=C[v], label=f"model {v}: velum open")
for s, x in (("iː", 0.0), ("ũ", 0.3), ("ã", 0.3)):
    for r in HIS:
        if r["sound"] == s and f(r, "f0") < 300:
            a.plot(x, f(r, "B1"), "*", ms=16, color=C[s], mec="k"); a.annotate(f"his {s}", (x, f(r, "B1")), fontsize=8,
                                                                                 xytext=(5, 0), textcoords="offset points")
rr = rows("E5", "ã"); a.plot([0.6] * len(rr), [r["B1"] for r in rr], "x", color="gray", label="model ã, glottal leak (spread)")
a.set_xlabel("velum opening"); a.set_ylabel("B1 (Hz)")
a.set_title("4. UNRESOLVED: his nasal vowels (ã, ũ) have a broad F1, oral ee a narrow one.\nNose coupling (lines) does not broaden it here; a slightly open glottis (x) does")
a.legend(fontsize=7)

# 5. purity: steadiness vs breath
a = ax[1, 1]
rr = rows("E6", "iː"); x = [max(r["value"], 1e-3) for r in rr]
a.semilogx(x, [r["HNR_0_500"] for r in rr], "-o", color="#2c3e50", label="breath noise -> purity <500 Hz")
a.semilogx(x, [r["HNR_1500_2500"] for r in rr], "-s", color="#e67e22", label="breath noise -> purity 1.5-2.5 kHz")
rr = rows("E7", "iː"); x = [max(r["value"], 1e-3) for r in rr]
a.semilogx(x, [r["HNR_0_500"] for r in rr], "--o", color="#7f8c8d", label="pitch variation (jitter) -> purity <500 Hz")
rr = rows("E7b", "iː"); x = [max(r["value"], 1e-3) for r in rr]
a.semilogx(x, [r["HNR_0_500"] for r in rr], "--^", color="#16a085", label="loudness variation (shimmer) -> purity <500 Hz")
a.axhspan(29, 36, color="#2c3e50", alpha=0.12); a.axhspan(12, 17, color="#e67e22", alpha=0.15)
a.text(1.1e-3, 33, "his low band", fontsize=8); a.text(1.1e-3, 13, "his high band", fontsize=8)
a.set_xlabel("amount (breath noise / cycle variation)"); a.set_ylabel("HNR (dB)")
a.set_title("5. Pure low, slightly breathy high: only very steady folds (no shimmer)\nreach his low-band purity; a little breath shows only up high")
a.legend(fontsize=7)

# 6. consonants: soft S place + lip leak
a = ax[1, 2]
rr = R["E8"]; a.plot([r["front_cm"] for r in rr], [r["peak"] / 1000 for r in rr], "-o", color="#8e44ad", label="noise peak (kHz)")
xx = np.linspace(1.0, 3.0, 50); a.plot(xx, 35000 / (4 * xx) / 1000, ":", color="#8e44ad", label="quarter-wave c/4L")
a.axhspan(3.9, 4.4, color="#8e44ad", alpha=0.18); a.text(2.2, 4.6, "his soft S (3.9-4.4 kHz)", fontsize=8)
a.axhspan(7, 9.5, color="gray", alpha=0.12); a.text(2.2, 8.0, "an ordinary s (7-9 kHz)", fontsize=8)
a.set_xlabel("noise made this far behind the lips (cm)"); a.set_ylabel("kHz")
b = a.inset_axes([0.55, 0.55, 0.42, 0.38]); e9 = R["E9"]
b.plot([r["leak_cm2"] for r in e9], [r["across_folds"] for r in e9], "-o", color="#16a085", ms=3)
b.axhline(3, color="r", lw=0.8); b.set_title("lip leak -> voicing (p)", fontsize=7); b.tick_params(labelsize=6)
b.set_xlabel("leak cm²", fontsize=6); b.set_ylabel("cmH2O across folds", fontsize=6)
a.set_title("6. Soft S: noise made ~2 cm back (tongue blade at the palate)\n=> peak ~4 kHz. Inset: a leaky (split) lip keeps p voiced")
a.legend(fontsize=7, loc="lower left")

plt.tight_layout(); plt.savefig(OUT / "physics_overview.png", dpi=75); plt.close()
print(OUT / "physics_overview.png")
