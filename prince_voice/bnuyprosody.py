"""Prosody planner: how a small creature would naturally say a phrase.

Not a template and not random: the shape follows from the phrase's structure,
using his measured habits from the reference clip.

  per syllable  pitch is set per syllable and only changes in the consonants
                between syllables, never sliding inside a vowel
  breath        a small body runs out of breath: each syllable sits a little
                lower than the last (step-wise declination); excited speech
                starts higher and each new word steps down (390 -> 350 -> 330)
  main stress   the phrase's last stressed syllable gets the main lift (his
                "nannar MUnis": +3.6 st); syllables after it stay near it
                ("-nis"), other stressed syllables get a small lift
  effort        higher syllables are a little louder (synth pitch_loud)
  start         a nasal start gets his hummed fall ("nnn"); vowels/bursts don't
  durations     stressed vowels long, unstressed short, phrase-final stretched
                and ending in his humming tail
  variation     small and natural (seeded): +-0.25 st per syllable, ~4 % timing

Input: phrase = list of words; word = list of (phonemes, stressed) syllables,
e.g. [[("m ũ", True), ("n iː ɕ", False)]]  ->  "munis"
"""

from __future__ import annotations

import numpy as np

from .bnuypitch import CALM, EXCITED, VOWELS, pitch_plan
from .bnuysynth import Unit

# base durations (ms) from the clip
STRESSED_V = {"ã": 145, "ũ": 120, "iː": 130, "ɐ˞": 120}
UNSTRESSED_V = {"ã": 100, "ũ": 90, "iː": 105, "ɐ˞": 95}
CONS = {"n": 72, "m": 90, "ɹ": 50, "ɕ": 145, "p": 62, "tʰ": 52}  # ɕ: hiss + voiced puff
INITIAL_SONORANT = 105
FINAL_STRETCH = 1.7
TAIL_MS = 100
CLOSURE_MS = 25

MOODS = {
    #           start Hz  per-syll  per-word  stressed  main stress  final
    "calm":    dict(L0=CALM, decl=0.35, decl_word=0.0, acc=0.3, nuc=4.2, final=0.0),
    "excited": dict(L0=EXCITED[0], decl=0.3, decl_word=1.5, acc=0.0, nuc=0.0, final=0.0),
    "curious": dict(L0=CALM, decl=0.25, decl_word=0.0, acc=0.6, nuc=2.0, final=2.5),
}


def plan(phrase, mood: str = "calm", speed: float = 1.0, seed: int | None = None,
         vary: float = 1.0, cat=None, natural: float = 0.7):
    """Returns (units, levels_hz, pitch_kwargs). See module docstring."""
    m = MOODS.get(mood, MOODS["calm"])
    rng = np.random.default_rng(seed)
    jit = (lambda sd: vary * float(rng.normal(0, sd))) if seed is not None else (lambda sd: 0.0)

    sylls = [(wi, si, phs.split(), st) for wi, word in enumerate(phrase) for si, (phs, st) in enumerate(word)]
    stressed_idx = [i for i, (_, _, _, st) in enumerate(sylls) if st]
    nuclear = stressed_idx[-1] if stressed_idx else -1

    def level_of(i):
        wi, _, _, st = sylls[i]
        x = -m["decl"] * i - m["decl_word"] * wi
        if i == nuclear:
            x += m["nuc"]
        elif nuclear >= 0 and i > nuclear:
            x += m["nuc"] - 0.2            # after the main lift: stays near it
        elif st:
            x += m["acc"]
        if i == len(sylls) - 1:
            x += m["final"]
        return m["L0"] * 2 ** ((x + jit(0.25)) / 12)

    units, levels = [], []
    for i, (wi, si, phs, stressed) in enumerate(sylls):
        lv = level_of(i)
        last_syll = i == len(sylls) - 1
        last_in_word = si == len(phrase[wi]) - 1
        for k, ph in enumerate(phs):
            if ph in VOWELS:
                ms = (STRESSED_V if stressed else UNSTRESSED_V).get(ph, 110)
                if last_syll:
                    ms *= FINAL_STRETCH
                if mood == "excited":
                    ms *= 0.9
                ms *= 2 ** jit(0.05)
                ends_word_on_vowel = k == len(phs) - 1 and last_in_word
                fade = TAIL_MS if ends_word_on_vowel and (last_syll or mood == "excited") else 0
                units.append(Unit(ph, ms / speed + fade, fade_ms=fade, stress=stressed))
            else:
                if ph in ("p", "tʰ") and units and units[-1].ph != "_":
                    units.append(Unit("_", CLOSURE_MS)); levels.append(lv)
                ms = CONS.get(ph, 70)
                if not units and ph in ("n", "m"):
                    ms = INITIAL_SONORANT
                ms *= 2 ** jit(0.05)
                units.append(Unit(ph, ms / speed, stress=stressed))
            levels.append(lv)
    if cat is not None and natural > 0:
        _natural_timing(units, cat, natural, levels)
    first = units[0].ph if units else ""
    onset = 1.0 if first in ("n", "m", "ɹ") else 0.0   # his hummed fall into a nasal start
    if levels and onset > 0:   # his hummed start peaks ~344 Hz: never start above ~360
        onset = float(np.clip(12 * np.log2(360.0 / levels[0]) / 8.6, 0.0, 1.0))
    kw = dict(onset=onset, seed=seed if seed is not None else 7, step_ms=55.0)
    return units, levels, kw


def _natural_timing(units, cat, natural, levels=None, w_pitch=5.0):
    """Choose each steady sound's recording by context and planned pitch (a calm
    word shouldn't get a recording from his excited peets); blend in its real length."""
    for i, u in enumerate(units):
        if u.ph == "_" or cat.dynamic.get(u.ph, False) or not cat.inst.get(u.ph):
            continue
        left = units[i - 1].ph if i > 0 else "#"
        right = "#" if i + 1 >= len(units) else ("_" if u.fade_ms else units[i + 1].ph)
        hz = float(levels[i]) if levels is not None else float("nan")
        c = cat.pick_half(u.ph, "L", left, hz, u.stress, i == 0, w_pitch=w_pitch)
        cr = cat.pick_half(u.ph, "R", right, hz, u.stress, i == len(units) - 1, same_as=c, w_join=1.0,
                           w_pitch=w_pitch)
        if c is None:
            continue
        rec = 1000 * (c["span"][1] - c["span"][0])
        if u.stress is not None and c["stress"] != u.stress:
            rec *= 1.25 if u.stress else 0.8
        body = u.ms - u.fade_ms
        u.ms = u.fade_ms + (1 - natural) * body + natural * rec * (body / max(body, 1e-3)) ** 0
        if c is cr:
            u.prefer = tuple(c["span"])


def phrase_pitch(phrase, mood="calm", seed=None, vary=1.0, cat=None, natural=0.7):
    """Convenience: (units, f0_fn) for a phrase."""
    units, levels, kw = plan(phrase, mood, seed=seed, vary=vary, cat=cat, natural=natural)
    return units, pitch_plan(units, levels, **kw)
