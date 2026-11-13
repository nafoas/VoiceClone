"""English IPA -> Bnuy realization, as observed in the reference clip."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROWS = [  # english, bnuy, kind, note
    ("n",        "n",      "same",    "long, humming nasal murmur"),
    ("m",        "m",      "same",    "smooth; pitch steps up on it"),
    ("æ",        "æ",      "shifted", "upper resonances raised (smaller mouth)"),
    ("ɚ  (unstressed -er)", "ɑɹ", "changed", "no vowel reduction: full vowel kept"),
    ("ʌ  (mOney)", "ʉ",    "changed", "rounded, pushed forward"),
    ("i",        "iː",     "shifted", "F2 +37%, F3 +50%; F1 lower. Very forward"),
    ("z  (-eys)", "ɕ",     "changed", "devoiced, soft, ~4.4 kHz, ~20 dB under vowel"),
    ("p  (1st)", "p",      "same",    "soft burst + little pitch chirp"),
    ("t  (word-final)", "t̚ / ∅", "dropped", "unreleased or gone"),
    ("p  (after -t)", "t",  "changed", "final t carries onto next word: peet peet → pee tee"),
]
COL = {"same": "#4a9", "shifted": "#39c", "changed": "#e07", "dropped": "#999"}

fig, ax = plt.subplots(figsize=(13, 0.62 * len(ROWS) + 1.6))
ax.set_xlim(0, 13); ax.set_ylim(-1.5, len(ROWS)); ax.axis("off")
ax.text(1.4, len(ROWS) - 0.2, "English", ha="center", fontsize=13, fontweight="bold")
ax.text(5.0, len(ROWS) - 0.2, "Bnuy", ha="center", fontsize=13, fontweight="bold")
for i, (en, bn, kind, note) in enumerate(ROWS):
    y = len(ROWS) - 1 - i - 0.3
    ax.text(1.4, y, en, ha="center", va="center", fontsize=13, family="DejaVu Sans")
    ax.annotate("", xy=(4.3, y), xytext=(2.7, y), arrowprops=dict(arrowstyle="->", color=COL[kind], lw=2.2))
    ax.text(5.0, y, bn, ha="center", va="center", fontsize=15, fontweight="bold", color=COL[kind])
    ax.text(6.0, y, note, va="center", fontsize=10.5, color="#333")
for k, (name, c) in enumerate(COL.items()):
    ax.text(0.3 + k * 2.4, -1.25, f"■ {name}", color=c, fontsize=11)
ax.set_title("Observed English → Bnuy sound changes (reference clip, 9 of ~40 phonemes covered)", fontsize=12)
plt.savefig("analysis/english_to_bnuy.png", dpi=85, bbox_inches="tight")
