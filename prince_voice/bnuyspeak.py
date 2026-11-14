"""Speak an utterance: several phrases as one continuous act of speaking.

Each phrase after the first continues from where his voice was: it starts near
the previous phrase's last pitch, with a gentler restart, and a little softer
than the previous phrase (the same breath running on), instead of resetting.
"""

from __future__ import annotations

import numpy as np

from .bnuyprosody import phrase_pitch
from .bnuysynth import SR, Catalogue, synth

# how he'd speak new phrases: one breath, one steady hum, joins that melt like
# his real ones, little manipulation of his recordings
NEW_PHRASE = dict(pitch_life=0.75, pitch_loud=0.6, w_pitch=4.0, edge_ms=10, hum_boost_db=4,
                  hum_steady=0.4, breath_support=0.7, attack_ms=40, release_ms=50)


def speak(phrases, seed: int | None = None, cat: Catalogue | None = None, pause_s: float = 0.3,
          follow_down_db: float = 1.5, **synth_kw):
    """phrases: list of (phrase, mood). Returns float32 audio at SR."""
    cat = cat or Catalogue(level_match=0.5)
    kw = {**NEW_PHRASE, **synth_kw}
    out, prev_end, prev_rms = [], None, None
    for k, (phrase, mood) in enumerate(phrases):
        s = None if seed is None else seed * 31 + k
        units, f = phrase_pitch(phrase, mood, seed=s, cat=cat, follow_from=prev_end)
        y = synth(units, f, cat, **kw)
        v = y[np.abs(y) > 0.05 * np.abs(y).max()]
        rms = float(np.sqrt(np.mean(v ** 2))) if len(v) else 1.0
        if prev_rms is not None and mood != "excited":
            y = y * (prev_rms * 10 ** (-follow_down_db / 20) / rms)   # the same breath running on
            rms = prev_rms * 10 ** (-follow_down_db / 20)
        prev_rms = rms
        lv = getattr(phrase_pitch, "last_levels", None)
        prev_end = float(lv[-1]) if lv else None
        out.append(y)
        if k + 1 < len(phrases):
            out.append(np.zeros(int(pause_s * SR), np.float32))
    y = np.concatenate(out)
    return (y / (np.abs(y).max() + 1e-9) * 0.8).astype(np.float32)
