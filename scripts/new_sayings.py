"""New sayings, built from scratch with exactly the gold-standard technique.

The gold rebuild is: his catalogue, the synthesizer at its default settings
(sub-phonemes, real recorded movement, real bursts and tails, natural levels),
units written out like the transcription, and a pitch line. Nothing else:
no planner, no breath support, no hum boost, no register placement.

Here the units and durations are written by hand from his recorded lengths, and
each saying gets a simple pitch line from what his clip shows: a hummed fall
into a nasal start, steady syllables, pitch changing inside consonants.

    python scripts/new_sayings.py   -> out/fresh/*.wav
"""

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince_voice.bnuypitch import pitch_plan  # noqa: E402
from prince_voice.bnuysynth import SR, Catalogue, Unit as U, synth  # noqa: E402

# (units, pitch level per unit in Hz, hummed onset fall 0..1)
SAYINGS = {
    "munis": (
        [U("m", 90), U("ũ", 120), U("n", 60), U("iː", 210), U("ɕ", 150)],
        [265, 265, 265, 264, 262], 0.6),
    "nannar": (
        [U("n", 105), U("ã", 145), U("n", 75), U("ɐ˞", 95), U("ɹ", 50)],
        [216, 216, 215, 215, 214], 1.0),
    # mama: version F (Da Boss's pick): derived back "ah" (F2 1700), word-starting m
    "mama": (
        [U("m", 115, gain_db=-6, stress=True), U("ɑ", 145, stress=True), U("m", 85, gain_db=-5),
         U("ɑ", 200, fade_ms=100)],
        [218, 218, 216, 215], 1.0),
    "nanni": (
        [U("n", 105), U("ã", 145), U("n", 70), U("iː", 300, fade_ms=100)],
        [216, 216, 214, 213], 1.0),
    "mama_nanni": (
        [U("m", 115, gain_db=-6, stress=True), U("ɑ", 145, stress=True), U("m", 85, gain_db=-5), U("ɑ", 100),
         U("n", 75), U("ã", 140),
         U("n", 65), U("iː", 300, fade_ms=100)],
        [218, 218, 216, 216, 262, 265, 263, 262], 1.0),
    "meeni": (
        [U("m", 90), U("iː", 140), U("n", 60), U("iː", 300, fade_ms=100)],
        [264, 264, 263, 262], 0.6),
    "pee_tee": (
        [U("p", 65), U("iː", 180, fade_ms=100), U("_", 15), U("tʰ", 45),
         U("iː", 300, fade_ms=100)],
        [390, 390, 350, 350, 350], 0.0),
}

# utterances: sayings separated by short pauses
UTTERANCES = {
    "munis_nannar": ["munis", "nannar"],
    "mama_nanni": ["mama_nanni"],
    "nanni": ["nanni"],
    "pee_tee_meeni": ["pee_tee", "meeni"],
    "mama": ["mama"],
}


# the one addition to the gold settings: a vowel next to a different consonant
# than the one it was recorded beside gets that consonant's edge (lips closing
# for m/p), so "mama" isn't heard as "nana". Sounds next to their recorded
# neighbours are untouched.
FRESH = dict(recolor=0.6, lip_depth=0.28, crisp_release=True)


def say(name, cat):
    units, levels, onset = SAYINGS[name]
    return synth(units, pitch_plan(units, levels, onset=onset, step_ms=60.0), cat, **FRESH)


def main():
    cat = Catalogue()   # gold settings: each recording keeps its own loudness
    from prince_voice.bnuysynth import derive_vowel
    derive_vowel(cat, "ɑ", "ã", [(1200, 1200), (2160, 1700), (3700, 3600)])   # his "ah" (mama, version F)
    out = ROOT / "out" / "fresh"
    out.mkdir(parents=True, exist_ok=True)
    pause = np.zeros(int(0.3 * SR), np.float32)
    for name, parts in UTTERANCES.items():
        y = np.concatenate([x for p in parts for x in (say(p, cat), pause)][:-1])
        sf.write(out / f"{name}.wav", y / np.abs(y).max() * 0.8, SR)
        print(out / f"{name}.wav")


if __name__ == "__main__":
    main()
