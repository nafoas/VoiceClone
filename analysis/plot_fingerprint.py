"""Figures for the voice fingerprint (run analysis/fingerprint.py first)."""
import csv, sys
from pathlib import Path
import numpy as np, parselmouth as pm, matplotlib, warnings
warnings.filterwarnings("ignore")
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis")); sys.path.insert(0, str(ROOT))
from fingerprint import REF, vtl, source_measures, noise_measures, overall  # noqa: E402

rows = list(csv.DictReader(open(ROOT / "analysis/fingerprint_sounds.csv")))
num = lambda r, k: float(r[k]) if r.get(k) not in (None, "", "nan") else np.nan
voiced = [r for r in rows if r["sound"] not in ("ɕ", "p", "tʰ")]

# whole-clip source measures, same method, for Prince and the ordinary voice
def whole(path):
    s = pm.Sound(str(path)).convert_to_mono()
    F = s.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000 if "prince" in str(path) else 5500)
    P = s.to_pitch_ac(time_step=0.005, pitch_floor=80, pitch_ceiling=900)
    return source_measures(s, 0.0, s.duration, F, P), overall(s, P)
pr_src, pr_ov = whole(ROOT / "reference/source/prince_reference.wav")
en_src, en_ov = whole(ROOT / "out/english_ref.wav")
vt = {g: np.mean([vtl(f)[1] for f in d.values()]) for g, d in REF.items()}
pr_vtl = np.nanmean([num(r, "VTL_cm") for r in voiced])

# ---- 1. fingerprint panels -------------------------------------------------
M = [("Pitch (median Hz)", pr_ov["f0_median"], en_ov["f0_median"], "higher = smaller/younger"),
     ("H1–H2 (dB)", pr_src["H1H2"], en_src["H1H2"], "fundamental over 2nd harmonic"),
     ("H1–A3 (dB)", pr_src["H1A3"], en_src["H1A3"], "fundamental over the 3rd resonance: the hum cliff"),
     ("CPPS (dB)", pr_src["CPPS"], en_src["CPPS"], "clarity / periodicity"),
     ("Jitter (%)", pr_src["jitter_pct"], en_src["jitter_pct"], "pitch roughness"),
     ("Shimmer (dB)", pr_src["shimmer_dB"], en_src["shimmer_dB"], "loudness roughness"),
     ("HNR 0–500 Hz (dB)", pr_src["HNR_0_500"], en_src["HNR_0_500"], "purity where the hum lives"),
     ("HNR 1.5–2.5 kHz (dB)", pr_src["HNR_1500_2500"], en_src["HNR_1500_2500"], "purity higher up"),
     ("Vocal tract length (cm)", pr_vtl, vt["women"], "from formant spacing"),
     ("Voiced (% of clip)", pr_ov["voiced_pct"], en_ov["voiced_pct"], "how much he hums"),
     ("Loudness per semitone (dB)", pr_ov["loud_per_semitone"], en_ov["loud_per_semitone"], "does loudness follow pitch?")]
fig, axs = plt.subplots(3, 4, figsize=(17, 10)); axs = axs.ravel()
for ax, (name, p, e, note) in zip(axs, M):
    vals = [p, e]; labels = ["Prince", "ordinary\nadult"]; cols = ["#e07", "#999"]
    if name.startswith("Vocal"):
        vals.append(vt["children"]); labels.append("children"); cols.append("#39c")
    b = ax.bar(labels, vals, color=cols)
    for bi, v in zip(b, vals):
        ax.text(bi.get_x() + bi.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=10)
    ax.set_title(name, fontsize=11); ax.text(0.5, -0.22, note, transform=ax.transAxes, ha="center", fontsize=8, color="#555")
    ax.grid(axis="y", alpha=.3); ax.axhline(0, color="k", lw=.5)
axs[-1].axis("off")
axs[-1].text(0, 0.5, "Ordinary adult = English TTS (adult female)\nsaying the same words, same methods.\nChildren / women VTL from Hillenbrand\net al. (1995) vowel averages.", fontsize=10)
fig.suptitle("Prince's voice fingerprint vs an ordinary voice", fontsize=14)
plt.tight_layout(); plt.savefig(ROOT / "analysis/fingerprint_overview.png", dpi=75); plt.close()

# ---- 2. per-sound heatmap ----------------------------------------------------
cols = ["H1H2", "H1A3", "CPPS", "jitter_pct", "shimmer_dB", "HNR_0_500", "HNR_500_1500", "HNR_1500_2500", "B1", "B2", "F1", "F2"]
lab = [f"{r['sound']} ({float(r['start']):.2f}s)" for r in voiced]
Mx = np.array([[num(r, c) for c in cols] for r in voiced])
Z = (Mx - np.nanmean(Mx, 0)) / (np.nanstd(Mx, 0) + 1e-9)
fig, ax = plt.subplots(figsize=(15, 6.5))
ax.imshow(np.nan_to_num(Z), cmap="coolwarm", aspect="auto", vmin=-2, vmax=2)
for i in range(Mx.shape[0]):
    for j in range(Mx.shape[1]):
        v = Mx[i, j]
        ax.text(j, i, "–" if not np.isfinite(v) else (f"{v:.0f}" if abs(v) >= 10 else f"{v:.1f}"), ha="center", va="center", fontsize=8)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(["H1–H2", "H1–A3", "CPPS", "jitter %", "shimmer dB", "HNR <500", "HNR .5–1.5k", "HNR 1.5–2.5k", "B1 Hz", "B2 Hz", "F1", "F2"])
ax.set_yticks(range(len(lab))); ax.set_yticklabels(lab)
ax.set_title("Every voiced sound he made, every measure (colour = relative to his own average)")
plt.tight_layout(); plt.savefig(ROOT / "analysis/fingerprint_sounds.png", dpi=75); plt.close()

# ---- 3. size ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
vrows = [r for r in voiced if np.isfinite(num(r, "VTL_cm"))]
ax.bar([f"{r['sound']} {float(r['start']):.2f}" for r in vrows], [num(r, "VTL_cm") for r in vrows], color="#e07", label="Prince (per vowel)")
ax.axhline(vt["women"], color="#999", ls="--", label=f"women avg {vt['women']:.1f} cm")
ax.axhline(vt["children"], color="#39c", ls="--", label=f"children avg {vt['children']:.1f} cm")
ax.set_ylabel("vocal tract length (cm)"); ax.set_title("How big he sounds: vocal tract length from his resonance spacing")
ax.legend(); ax.grid(axis="y", alpha=.3)
plt.tight_layout(); plt.savefig(ROOT / "analysis/fingerprint_size.png", dpi=75); plt.close()

# ---- 4. transitions -------------------------------------------------------------
tr = list(csv.DictReader(open(ROOT / "analysis/fingerprint_transitions.csv")))
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.bar([t["transition"] for t in tr], [abs(float(t["F2_speed"])) for t in tr], color="#2a8")
ax.set_ylabel("|F2 speed| (Hz per ms)"); ax.set_title("How fast his mouth moves between sounds (F2, first/last 30 ms of the vowel)")
ax.grid(axis="y", alpha=.3)
plt.tight_layout(); plt.savefig(ROOT / "analysis/fingerprint_transitions.png", dpi=75); plt.close()

print("Prince whole:", {k: round(v, 1) for k, v in pr_src.items()})
print("English whole:", {k: round(v, 1) for k, v in en_src.items()})
print("VTL: prince %.1f, women %.1f, children %.1f" % (pr_vtl, vt["women"], vt["children"]))
