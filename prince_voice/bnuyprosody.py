"""Prosody planner: syllables with stress -> timed units + pitch levels,
following the patterns measured in the reference clip.

  durations   stressed vowels long (ã 145 ms, ũ 120), unstressed short
              (ɐ˞ 95); the phrase-final syllable is stretched (~1.8x);
              a phrase-initial sonorant is long (his opening "nnn": 105 ms)
  pitch       flat within a word; a new word steps (calm: 215 -> 265, then
              a gentle drift down); excited: 390 -> 350 -> 330 per word.
              Movement happens in consonants (see bnuypitch).
  fades       a final syllable ending in a vowel gets his humming tail

Input: phrase = list of words; word = list of (phonemes, stressed) syllables,
e.g. [[("m ũ", True), ("n iː ɕ", False)]]  ->  "munis"
"""

from __future__ import annotations

from .bnuypitch import CALM, EXCITED, RAISED, VOWELS
from .bnuysynth import Unit

# base durations (ms) from the clip
STRESSED_V = {"ã": 145, "ũ": 120, "iː": 130, "ɐ˞": 120}
UNSTRESSED_V = {"ã": 100, "ũ": 90, "iː": 105, "ɐ˞": 95}
CONS = {"n": 72, "m": 90, "ɹ": 50, "ɕ": 90, "p": 62, "tʰ": 52}
INITIAL_SONORANT = 105
FINAL_STRETCH = 1.8
TAIL_MS = 100
CLOSURE_MS = 25


def plan(phrase, mood: str = "calm", speed: float = 1.0):
    """Returns (units, levels_hz)."""
    units, levels = [], []
    n_words = len(phrase)
    for wi, word in enumerate(phrase):
        if mood == "excited":
            level = EXCITED[min(wi, len(EXCITED) - 1)]
        else:
            level = CALM if wi == 0 else RAISED * (0.95 ** max(0, wi - 1))
        for si, (phs, stressed) in enumerate(word):
            phs = phs.split()
            last_syll = wi == n_words - 1 and si == len(word) - 1
            for k, ph in enumerate(phs):
                if ph in VOWELS:
                    ms = (STRESSED_V if stressed else UNSTRESSED_V).get(ph, 110)
                    if last_syll:
                        ms *= FINAL_STRETCH
                    if mood == "excited":
                        ms *= 0.9
                    fade = TAIL_MS if (k == len(phs) - 1 and (last_syll or mood == "excited")) else 0
                    units.append(Unit(ph, ms / speed + fade, fade_ms=fade, stress=stressed))
                else:
                    if ph in ("p", "tʰ") and units and units[-1].ph != "_":
                        units.append(Unit("_", CLOSURE_MS)); levels.append(level)
                    ms = CONS.get(ph, 70)
                    if not units and ph in ("n", "m"):
                        ms = INITIAL_SONORANT
                    units.append(Unit(ph, ms / speed, stress=stressed))
                levels.append(level)
    return units, levels
