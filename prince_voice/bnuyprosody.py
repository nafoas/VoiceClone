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

import numpy as np

from .bnuypitch import CALM, EXCITED, RAISED, VOWELS, pitch_plan
from .bnuysynth import Unit

# base durations (ms) from the clip
STRESSED_V = {"ã": 145, "ũ": 120, "iː": 130, "ɐ˞": 120}
UNSTRESSED_V = {"ã": 100, "ũ": 90, "iː": 105, "ɐ˞": 95}
CONS = {"n": 72, "m": 90, "ɹ": 50, "ɕ": 145, "p": 62, "tʰ": 52}  # ɕ: hiss + voiced puff
INITIAL_SONORANT = 105
FINAL_STRETCH = 1.8
TAIL_MS = 100
CLOSURE_MS = 25


def plan(phrase, mood: str = "calm", speed: float = 1.0, seed: int | None = None,
         vary: float = 1.0, cat=None, natural: float = 0.7):
    """Returns (units, levels_hz, pitch_kwargs).

    seed/vary: he doesn't say things the same way twice. With a seed, each
    phrase gets its own natural reading within his range (vary 0 = the exact
    template measured from the clip):
      base level +-0.7 st, word steps 2-4.5 st (sometimes none / down),
      onset fall 0-100 %, durations +-8 %, final stretch 1.4-1.9x,
      and an ending that may flick up, fall or stay level.
    cat/natural: with a catalogue, each sound's recording is chosen here by
      context, and its natural recorded length is blended in (natural 0..1);
      the synth is told to use that same recording (Unit.prefer).
    """
    rng = np.random.default_rng(seed)
    r = (lambda lo, hi, mid: mid + vary * (rng.uniform(lo, hi) - mid)) if seed is not None else \
        (lambda lo, hi, mid: mid)
    base = CALM * 2 ** (r(-0.5, 0.5, 0.0) / 12)
    step = r(1.0, 2.8, 2.0)    # smaller than the clip's one big step: not every word steps
    if seed is not None and vary > 0:
        u = rng.uniform()
        step = -0.5 * step if u < 0.15 * vary else (0.0 if u < 0.45 * vary else step)
    final_stretch = r(1.4, 1.9, FINAL_STRETCH)
    units, levels = [], []
    n_words = len(phrase)
    for wi, word in enumerate(phrase):
        if mood == "excited":
            level = EXCITED[min(wi, len(EXCITED) - 1)] * 2 ** (r(-1.0, 1.0, 0.0) / 12)
        else:
            level = base if wi == 0 else base * 2 ** ((step - 0.8 * max(0, wi - 1)) / 12)
        for si, (phs, stressed) in enumerate(word):
            phs = phs.split()
            last_syll = wi == n_words - 1 and si == len(word) - 1
            for k, ph in enumerate(phs):
                if ph in VOWELS:
                    ms = (STRESSED_V if stressed else UNSTRESSED_V).get(ph, 110)
                    if last_syll:
                        ms *= final_stretch
                    ms *= 2 ** r(-0.12, 0.12, 0.0)
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
                    ms *= 2 ** r(-0.12, 0.12, 0.0)
                    units.append(Unit(ph, ms / speed, stress=stressed))
                levels.append(level)
    if cat is not None and natural > 0:
        _natural_timing(units, cat, natural)
    end = r(-1.0, 1.2, 0.0) if (seed is None or rng.uniform() < 0.5) else 0.0
    kw = dict(onset=r(0.3, 1.0, 1.0), end_st=end, seed=seed if seed is not None else 7,
              step_ms=r(70.0, 110.0, 75.0))
    return units, levels, kw


def _natural_timing(units, cat, natural):
    """Choose each steady sound's recording by context; blend in its real length."""
    for i, u in enumerate(units):
        if u.ph == "_" or cat.dynamic.get(u.ph, False) or not cat.inst.get(u.ph):
            continue
        left = units[i - 1].ph if i > 0 else "#"
        right = "_" if u.fade_ms else (units[i + 1].ph if i + 1 < len(units) else "#")
        c = cat.pick_half(u.ph, "L", left, float("nan"), u.stress, i == 0)
        cr = cat.pick_half(u.ph, "R", right, float("nan"), u.stress, i == len(units) - 1, same_as=c, w_join=1.0)
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
