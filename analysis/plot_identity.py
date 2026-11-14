"""Figures for docs/PRINCE_IDENTITY.md."""
import csv
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
R = [dict(r) for r in csv.DictReader(open(ROOT / "analysis/identity_instances.csv"))]
for r in R:
    for k in ("F1", "F2", "F3", "f0", "dB", "HNR", "H2", "H3", "H4", "ms"):
        r[k] = float(r[k]) if r[k] not in ("", "nan") else np.nan
voiced = [r for r in R if np.isfinite(r["H3"])]
COL = {"n": "#39c", "m": "#36a", "ɹ": "#a6c", "ã": "#e07", "ɐ˞": "#f80", "ũ": "#2a8", "iː": "#c33"}

# 1. hum depth vs openness -------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
for r in voiced:
    ax[0].scatter(r["F1"], r["H3"], s=70, color=COL.get(r["sound"], "k"))
    ax[0].annotate(f"{r['sound']} ({r['f0']:.0f}Hz)", (r["F1"], r["H3"]), xytext=(5, 3), textcoords="offset points", fontsize=8)
    # where does F1 sit relative to his harmonics? (F1 / f0 = which harmonic it boosts)
    ax[1].scatter(r["F1"] / r["f0"], r["H3"], s=70, color=COL.get(r["sound"], "k"))
    ax[1].annotate(r["sound"], (r["F1"] / r["f0"], r["H3"]), xytext=(5, 3), textcoords="offset points", fontsize=8)
x = np.array([r["F1"] for r in voiced]); y = np.array([r["H3"] for r in voiced])
k = np.polyfit(x, y, 1); xx = np.linspace(250, 1250, 10)
ax[0].plot(xx, np.polyval(k, xx), "k--", lw=1, label=f"trend: {k[0]*100:.1f} dB per 100 Hz of F1")
ax[0].set_xlabel("F1 (Hz): mouth closed  →  open"); ax[0].set_ylabel("3rd harmonic vs 1st (dB): deeper hum ↓")
ax[0].set_title("His hum looks deeper the more closed the mouth is"); ax[0].legend(); ax[0].grid(alpha=.3)
ax[1].axvspan(0, 2.5, color="#2a8", alpha=.08); ax[1].text(0.15, -12, "F1 near his pitch:\nthe deepest hum", fontsize=9)
ax[1].set_xlabel("F1 ÷ pitch  (which harmonic the mouth's first resonance boosts)"); ax[1].set_ylabel("3rd harmonic vs 1st (dB)")
ax[1].set_title("…because an open mouth lifts the harmonics his source keeps quiet"); ax[1].grid(alpha=.3)
plt.tight_layout(); plt.savefig(ROOT / "analysis/identity_hum_vs_openness.png", dpi=80); plt.close()

# 2. his vowel space, recorded + derived + predicted ------------------------
EN = {"i": (437, 2761), "ɪ": (483, 2365), "ɛ": (731, 2058), "æ": (669, 2349), "ɑ": (936, 1551),
      "ɔ": (781, 1136), "ʊ": (519, 1225), "u": (459, 1105), "ʌ": (753, 1426), "ɝ": (523, 1588)}
HIS = {"i": (380, 3230), "æ": (1169, 2144), "ɝ": (810, 1951), "u": (384, 1337), "ɑ": (1169, 1700)}
SRC = {"i": "recorded iː", "æ": "recorded ã", "ɝ": "recorded ɐ˞", "u": "recorded ũ", "ɑ": "derived ɑ (your pick F)"}
e1 = np.array([EN[v][0] for v in HIS]); h1 = np.array([HIS[v][0] for v in HIS])
e2 = np.array([EN[v][1] for v in HIS]); h2 = np.array([HIS[v][1] for v in HIS])
o1, o2 = np.argsort(e1), np.argsort(e2)
pred = lambda f1, f2: (np.interp(f1, e1[o1], h1[o1]), np.interp(f2, e2[o2], h2[o2]))
fig, ax = plt.subplots(figsize=(11, 8))
for v, (f1, f2) in EN.items():
    ax.text(f2, f1, v, color="#aaa", fontsize=14, ha="center", va="center")
for v, (f1, f2) in HIS.items():
    ax.annotate("", xy=(f2, f1), xytext=(EN[v][1], EN[v][0]), arrowprops=dict(arrowstyle="->", color="#e07", lw=1.6))
    ax.plot(f2, f1, "o", color="#e07", ms=10); ax.text(f2 + 40, f1 - 40, f"{v}: {SRC[v]}", color="#b05", fontsize=9)
for v in ("ɪ", "ɛ", "ɔ", "ʊ", "ʌ"):
    p1, p2 = pred(*EN[v])
    ax.annotate("", xy=(p2, p1), xytext=(EN[v][1], EN[v][0]), arrowprops=dict(arrowstyle="->", color="#39c", lw=1, ls="--"))
    ax.plot(p2, p1, "o", mfc="white", mec="#39c", ms=10); ax.text(p2 + 40, p1 + 50, f"{v}: predicted", color="#36a", fontsize=9)
ax.set_xlim(3500, 900); ax.set_ylim(1300, 250); ax.grid(alpha=.3)
ax.set_xlabel("F2 (Hz)  ← front        back →"); ax.set_ylabel("F1 (Hz)  ← closed        open →")
ax.set_title("His vowel space: English (grey) → his (pink: recorded/derived, blue: predicted for vowels he never said)")
plt.tight_layout(); plt.savefig(ROOT / "analysis/identity_vowel_space.png", dpi=80); plt.close()

# 3. harmonic shape per sound -------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
seen = set()
for r in voiced:
    lab = r["sound"]
    ax.plot([1, 2, 3, 4], [0, r["H2"], r["H3"], r["H4"]], "-o", color=COL.get(lab, "k"), alpha=.8,
            label=None if lab in seen else lab); seen.add(lab)
ax.plot([1, 2, 3, 4], [0, -7, -11, -16], "k--", lw=2, label="ordinary speech")
ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["H1", "H2", "H3", "H4"]); ax.set_ylabel("dB relative to H1")
ax.set_title("The hum: harmonic shape of every recorded sound"); ax.legend(ncol=4, fontsize=8); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig(ROOT / "analysis/identity_harmonics.png", dpi=80); plt.close()
print("predicted vowels:", {v: tuple(round(float(q)) for q in pred(*EN[v])) for v in ("ɪ", "ɛ", "ɔ", "ʊ", "ʌ")})
print("hum trend:", k)
