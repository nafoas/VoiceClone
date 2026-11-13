"""Annotated analysis figure for the Prince reference clip."""
import numpy as np, soundfile as sf, pyworld as pw, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

a, sr = sf.read("reference/source/prince_reference.wav"); a = a.mean(1)
f0, t = pw.harvest(a, sr, frame_period=5, f0_floor=80, f0_ceil=1500)

# segmentation read from spectrogram / energy / pitch (seconds)
SEGS = [(0.04, 0.15, "n"), (0.15, 0.30, "æ"), (0.30, 0.38, "n"), (0.38, 0.48, "ɑ"),
        (0.48, 0.61, "ɹ"), (0.61, 0.66, "m"), (0.66, 0.75, "ʉ"), (0.75, 0.80, "n"),
        (0.80, 1.00, "i"), (1.00, 1.12, "ɕ"),
        (1.44, 1.48, "p"), (1.48, 1.68, "iː (t̚)"), (1.72, 1.76, "t"), (1.76, 1.94, "iː (t̚)"),
        (2.04, 2.08, "t"), (2.08, 2.34, "iː")]
WORDS = [(0.04, 0.61, '"nannar"   ← nanner'), (0.61, 1.12, '"munis"   ← moneys'),
         (1.44, 1.68, '"pee"'), (1.72, 1.94, '"tee"'), (2.04, 2.34, '"tee"')]

fig = plt.figure(figsize=(18, 13))
gs = fig.add_gridspec(3, 3, height_ratios=[2.2, 1.0, 1.2], hspace=0.45, wspace=0.3)
ax = fig.add_subplot(gs[0, :])
ax.specgram(a, NFFT=1024, Fs=sr, noverlap=1024 - 96, cmap="magma", vmin=-135)
ax.set_ylim(0, 6000); ax.set_ylabel("Hz")
ax.set_title('Prince reference clip  ("nanner moneys... peet peet peet" → heard as "nannarmunis... pee tee tee")', fontsize=13)
v = f0 > 0
ax.plot(t[v], f0[v] * 4, ".", color="cyan", ms=2.5, label="pitch × 4")
for s, e, ph in SEGS:
    ax.axvline(s, color="w", lw=0.5, alpha=0.5)
    ax.text((s + e) / 2, 5650, ph, color="w", ha="center", fontsize=13, fontweight="bold")
for s, e, w in WORDS:
    ax.annotate("", xy=(s, 5250), xytext=(e, 5250), arrowprops=dict(arrowstyle="<->", color="#9fe"))
    ax.text((s + e) / 2, 5000, w, color="#9fe", ha="center", fontsize=10)
ax.legend(loc="lower right")

ax2 = fig.add_subplot(gs[1, :], sharex=ax)
ax2.plot(t[v], f0[v], ".", ms=3, color="tab:blue")
ax2.set_ylabel("pitch Hz"); ax2.set_ylim(150, 700); ax2.grid(alpha=0.3); ax2.set_xlabel("seconds")
for x, y, txt in [(0.05, 360, "onset fall"), (0.35, 230, "flat plateau ~215"), (0.75, 285, "step up → plateau ~265"),
                  (1.47, 600, "onset chirp"), (1.8, 395, "~390 → 350 → 330\n(terraced descent)")]:
    ax2.annotate(txt, (x, y), fontsize=9)

M = {  # measured (see REFERENCE_ANALYSIS.md)
    "Spectral tilt\n(dB/oct, more negative = rounder)": (-16.1, -10.0, -11.8),
    "H1–H2 (dB)\nfundamental dominance": (9.9, 5.8, 6.2),
    "Voiced time (%)": (87, 56, 61),
}
cols = ["#e07", "#888", "#4a9"]
for k, (name, vals) in enumerate(M.items()):
    b = fig.add_subplot(gs[2, k])
    b.bar(["reference", "English TTS", "Prince v1"], vals, color=cols)
    b.set_title(name, fontsize=10); b.grid(axis="y", alpha=0.3)
    for i, val in enumerate(vals):
        b.text(i, val, f"{val:g}", ha="center", va="bottom" if val > 0 else "top", fontsize=9)
plt.savefig("analysis/reference_analysis.png", dpi=80, bbox_inches="tight")
