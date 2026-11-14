"""Prosody planner: how a small creature would naturally say a phrase, and why.

Every difference in how he says something has a reason. Nothing varies at
random: the shape follows from the phrase's structure and from his intent.

Structure (always):
  per syllable  pitch is set per syllable and only changes in the consonants
                between syllables, never sliding inside a vowel
  breath        a small body runs out of breath: each syllable sits a little
                lower than the last
  main stress   the focused word's stressed syllable gets the main lift (by
                default the last content word: his "nannar MUnis"); syllables
                after it stay near it, words after a focus are de-emphasised
  start         a nasal start gets his hummed fall ("nnn"); vowels/bursts don't
  ending        only the end of the whole utterance gets his humming fade; a
                phrase with more to follow holds and pauses instead

Intent (the reasons):
  calm      his ordinary way of saying something
  excited   more energy: higher, a bit louder and quicker, each new word a step
            lower as the burst of energy runs on ("pee tee tee")
  curious   asking: the last syllable lifts
  sleepy    low on energy: lower, softer, slower, a smaller lift, longer fade
  unsure    still thinking: slower, a smaller lift, the end lengthens and sinks
  focus=k   emphasis on word k (e.g. answering "which one?"): it gets the main
            lift, the words after it are flattened

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
CLOSURE_MS = 25

# where a phrase may sit (Hz of its first syllable) for each intent
REGISTER = {"calm": (200.0, 285.0), "curious": (205.0, 290.0), "excited": (320.0, 410.0),
            "sleepy": (185.0, 245.0), "unsure": (195.0, 270.0)}

MOODS = {
    # L0: start Hz; decl: per syllable (st); decl_word: per new word (st);
    # acc / nuc: lift of stressed / main-stress syllable (st); final: last
    # syllable (st); tempo: pace; gain_db: loudness; tail_ms: end fade;
    # final_len: extra stretch of the last syllable
    "calm":    dict(L0=CALM, decl=0.35, decl_word=0.0, acc=0.3, nuc=4.2, final=0.0,
                    tempo=1.0, gain_db=0.0, tail_ms=100, final_len=1.0),
    "excited": dict(L0=EXCITED[0], decl=0.3, decl_word=1.5, acc=0.0, nuc=0.0, final=0.0,
                    tempo=1.1, gain_db=1.5, tail_ms=90, final_len=0.9),
    "curious": dict(L0=CALM, decl=0.25, decl_word=0.0, acc=0.6, nuc=2.0, final=2.5,
                    tempo=1.0, gain_db=0.0, tail_ms=80, final_len=1.0),
    "sleepy":  dict(L0=CALM * 2 ** (-1.5 / 12), decl=0.45, decl_word=0.0, acc=0.2, nuc=2.0, final=-0.5,
                    tempo=0.8, gain_db=-3.0, tail_ms=170, final_len=1.25),
    "unsure":  dict(L0=CALM, decl=0.3, decl_word=0.0, acc=0.3, nuc=2.5, final=-1.0,
                    tempo=0.88, gain_db=-1.0, tail_ms=150, final_len=1.35),
}


def plan(phrase, mood: str = "calm", speed: float = 1.0, cat=None, natural: float = 0.7,
         focus: int | None = None, final: bool = True, follow_from: float | None = None,
         register_follow: float = 1.0, **_ignored):
    """Returns (units, levels_hz, pitch_kwargs). See module docstring.

    focus        index of the emphasised word (None = the last word)
    final        does this phrase end the utterance? (only then the full fade)
    follow_from  pitch (Hz) where the previous phrase ended, for continuity
    """
    m = MOODS.get(mood, MOODS["calm"])
    sylls = [(wi, si, phs.split(), st) for wi, word in enumerate(phrase) for si, (phs, st) in enumerate(word)]
    stressed = [i for i, (_, _, _, st) in enumerate(sylls) if st]
    if focus is not None:
        in_focus = [i for i in stressed if sylls[i][0] == focus]
        nuclear = in_focus[0] if in_focus else (stressed[-1] if stressed else -1)
    else:
        nuclear = stressed[-1] if stressed else -1
    focus_word = sylls[nuclear][0] if nuclear >= 0 else -1

    def level_of(i):
        wi, _, _, st = sylls[i]
        x = -m["decl"] * i - m["decl_word"] * wi
        # deliberate emphasis (focus given) lifts more than his neutral main stress
        lift = m["nuc"] + (1.5 if focus is not None else 0.0)
        if i == nuclear:
            x += lift
        elif nuclear >= 0 and i > nuclear:
            # after the main lift: the rest of the focused word stays near it;
            # words after a focus step down moderately (not collapse)
            x += (lift - 0.2) if wi == focus_word else (lift - 2.5)
        elif st:
            x += m["acc"]
        if i == len(sylls) - 1:
            x += m["final"]
        return m["L0"] * 2 ** (x / 12)

    units, levels = [], []
    tempo = m["tempo"] * speed
    for i, (wi, si, phs, st) in enumerate(sylls):
        lv = level_of(i)
        last_syll = i == len(sylls) - 1
        for k, ph in enumerate(phs):
            if ph in VOWELS:
                ms = (STRESSED_V if st else UNSTRESSED_V).get(ph, 110)
                if last_syll:
                    ms *= FINAL_STRETCH * m["final_len"]
                # his humming fade only where the whole utterance ends
                fade = m["tail_ms"] if (last_syll and final and k == len(phs) - 1) else 0
                units.append(Unit(ph, ms / tempo + fade, fade_ms=fade, stress=st))
            else:
                if ph in ("p", "tʰ") and units and units[-1].ph != "_":
                    units.append(Unit("_", CLOSURE_MS)); levels.append(lv)
                ms = CONS.get(ph, 70)
                if not units and ph in ("n", "m"):
                    ms = INITIAL_SONORANT
                units.append(Unit(ph, ms / tempo, stress=st))
            levels.append(lv)

    if cat is not None and natural > 0:
        # place the phrase where his chosen recordings naturally sit: keep the
        # shape (relative levels), move only the register, so recordings are
        # shifted as little as possible (the gold standard shifts ~0.1 st)
        lo, hi = REGISTER.get(mood, REGISTER["calm"])
        timing = [u.ms for u in units]
        for _ in range(2):
            for u, ms in zip(units, timing):
                u.ms = ms
            _natural_timing(units, cat, natural, levels)
            d = [12 * np.log2(u.rec_f0 / lv) for u, lv in zip(units, levels)
                 if getattr(u, "rec_f0", 0) > 0 and u.ph in VOWELS]
            if not d:
                break
            off = float(np.median(d)) * register_follow
            first = levels[0] * 2 ** (off / 12)
            off += 12 * np.log2(np.clip(first, lo, hi) / first)
            levels = [lv * 2 ** (off / 12) for lv in levels]
        for u in units:   # the intent's pace survives the recordings' natural lengths
            u.ms = u.fade_ms + (u.ms - u.fade_ms) / m["tempo"] ** 0.5
    if follow_from is not None and levels:
        # a follow-on phrase starts near where his voice was, not from a reset
        lo_c, hi_c = follow_from * 2 ** (-1.5 / 12), follow_from * 2 ** (1.0 / 12)
        if mood in ("excited", "curious"):
            hi_c = max(hi_c, follow_from * 2 ** (3.0 / 12))
        sh = 12 * np.log2(np.clip(levels[0], lo_c, hi_c) / levels[0])
        levels = [lv * 2 ** (sh / 12) for lv in levels]

    first_ph = units[0].ph if units else ""
    onset = 1.0 if first_ph in ("n", "m", "ɹ") else 0.0   # his hummed fall into a nasal start
    if follow_from is not None:
        onset *= 0.4                                       # a follow-on phrase: a gentler restart
    if mood == "sleepy":
        onset *= 0.5
    if levels and onset > 0:   # his hummed start peaks ~344 Hz: never start above ~360
        onset = float(np.clip(12 * np.log2(360.0 / levels[0]) / 8.6, 0.0, onset))
    kw = dict(onset=onset, step_ms=55.0)
    return units, levels, kw


def _natural_timing(units, cat, natural, levels=None, w_pitch=4.0):
    """Choose each steady sound's recording by context and planned pitch; blend
    in its real recorded length."""
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
        u.ms = u.fade_ms + (1 - natural) * body + natural * rec
        if c is cr:
            u.prefer = tuple(c["span"])
        u.rec_f0 = float(c.get("f0", 0.0))


def phrase_pitch(phrase, mood="calm", cat=None, natural=0.7, focus=None, final=True,
                 follow_from=None, **_ignored):
    """Convenience: (units, f0_fn) for a phrase."""
    units, levels, kw = plan(phrase, mood, cat=cat, natural=natural, focus=focus, final=final,
                             follow_from=follow_from)
    phrase_pitch.last_levels = levels
    return units, pitch_plan(units, levels, **kw)
