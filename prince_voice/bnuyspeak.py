"""Speak an utterance: several phrases as one continuous act of speaking.

Each phrase after the first continues from where his voice was (it starts near
the previous phrase's last pitch, with a gentler restart), only the last phrase
gets his humming fade, and every phrase sits at one consistent loudness, moved
only for a reason (its intent: excited a bit louder, sleepy softer).
"""

from __future__ import annotations

import numpy as np

from .bnuyprosody import MOODS, phrase_pitch
from .bnuysynth import SR, Catalogue, synth

# how he'd speak new phrases: one breath, one steady hum, joins that melt like
# his real ones, little manipulation of his recordings
NEW_PHRASE = dict(pitch_life=0.75, pitch_loud=0.4, w_pitch=4.0, edge_ms=10, hum_boost_db=4,
                  hum_steady=0.4, breath_support=0.7, attack_ms=40, release_ms=50)


def _voiced_rms(y):
    v = y[np.abs(y) > 0.05 * (np.abs(y).max() + 1e-9)]
    return float(np.sqrt(np.mean(v ** 2))) if len(v) else 1.0


def speak(phrases, cat: Catalogue | None = None, pause_s: float = 0.3, **synth_kw):
    """phrases: list of dicts {"phrase": ..., "mood": "calm", "focus": None}
    (or (phrase, mood) tuples). Returns float32 audio at SR."""
    cat = cat or Catalogue(level_match=0.5)
    kw = {**NEW_PHRASE, **synth_kw}
    out, prev_end, ref_rms = [], None, None
    for k, p in enumerate(phrases):
        if isinstance(p, tuple):
            p = {"phrase": p[0], "mood": p[1]}
        mood = p.get("mood", "calm")
        units, f = phrase_pitch(p["phrase"], mood, cat=cat, focus=p.get("focus"),
                                final=(k == len(phrases) - 1), follow_from=prev_end)
        y = synth(units, f, cat, **kw)
        rms = _voiced_rms(y)
        if ref_rms is None:
            ref_rms = rms * 10 ** (-MOODS.get(mood, MOODS["calm"])["gain_db"] / 20)
        target = ref_rms * 10 ** (MOODS.get(mood, MOODS["calm"])["gain_db"] / 20)
        y = y * (target / rms)          # one consistent loudness, moved only by intent
        lv = getattr(phrase_pitch, "last_levels", None)
        prev_end = float(lv[-1]) if lv else None
        out.append(y)
        if k + 1 < len(phrases):
            out.append(np.zeros(int(pause_s * SR), np.float32))
    y = np.concatenate(out)
    return (y / (np.abs(y).max() + 1e-9) * 0.8).astype(np.float32)
