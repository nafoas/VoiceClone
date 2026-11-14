"""Where each English vowel lands in Prince's mouth (reference clip)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

# English adult female averages (Hillenbrand et al. 1995): F1, F2
EN = {"i": (437, 2761), "ɪ": (483, 2365), "ɛ": (731, 2058), "æ": (669, 2349), "ɑ": (936, 1551),
      "ɔ": (781, 1136), "ʊ": (519, 1225), "u": (459, 1105), "ʌ": (753, 1426), "ɝ": (523, 1588)}
# Prince, measured (Praat, analysis/ipa_frames.csv)
PR = [("æ", "nAnner", (1115, 2164), "[ã]  jaw wide open"),
      ("ɝ", "nannER", (793, 1969), "[ɐ˞]  open, central, r-coloured"),
      ("ʌ", "mOneys", (360, 1303), "[ũ]  'hummy u': lips nearly closed"),
      ("i", "monEYS", (359, 3275), "[iː]"),
      ("i", "pEEt ×3", (393, 3170), "[iː]  same vowel every time")]

fig, ax = plt.subplots(figsize=(11, 8))
for v, (f1, f2) in EN.items():
    ax.text(f2, f1, v, fontsize=15, color="#999", ha="center", va="center")
for en, word, (f1, f2), note in PR:
    e1, e2 = EN[en]
    ax.annotate("", xy=(f2, f1), xytext=(e2, e1),
                arrowprops=dict(arrowstyle="->", color="#e07", lw=2, shrinkA=10, shrinkB=6))
    ax.plot(f2, f1, "o", color="#e07", ms=9)
    dy = -40 if word == "monEYS" else 35
    ax.text(f2 + 40, f1 + dy, f"{word}  {note}", fontsize=10, color="#b05")
ax.set_xlim(3500, 900); ax.set_ylim(1250, 250)
ax.set_xlabel("F2 (Hz)  ← front                back →"); ax.set_ylabel("F1 (Hz)  ← mouth closed / open →")
ax.set_title("English vowel (grey) → Prince's version (pink), from the reference clip")
ax.grid(alpha=0.3)
plt.savefig("analysis/vowel_map.png", dpi=80, bbox_inches="tight")
