"""Prince's pitch, modelled on the reference clip (measured with Praat):

  levels       calm ~215 Hz, raised ~265 Hz (+3.6 st), excited ~330-390 Hz
  plateaus     extremely steady: wobble ~0.1 st, almost no slope
  steps        S-shaped, ~75 ms, starting before the new syllable's vowel
               (216 -> 265 begins during the m of "munis")
  onset fall   a phrase starts ~8 st above its first plateau and falls into
               it over ~150 ms (during the opening hum "nnn")
  after bursts the vowel comes in ~2.5 st low and rises in ~30 ms (p: 347 -> 388)

pitch_plan(units, levels_hz) returns f0_fn(t) for bnuysynth.synth.
"""

from __future__ import annotations

import numpy as np

CALM, RAISED = 215.0, 265.0
EXCITED = (390.0, 350.0, 330.0)

# onset fall measured from the clip: (seconds from phrase start, st above plateau)
_ONSET = np.array([[0.000, 8.6], [0.013, 8.3], [0.023, 7.3], [0.033, 6.4], [0.043, 5.5],
                   [0.053, 5.0], [0.063, 4.1], [0.073, 3.2], [0.093, 3.1], [0.113, 2.3],
                   [0.133, 1.6], [0.153, 0.5], [0.175, 0.0]])
BURSTS = {"p", "tʰ"}


def pitch_plan(units, levels_hz, onset: float = 1.0, step_ms: float = 75.0,
               step_lead: float = 0.65, wobble_st: float = 0.1, burst_dip_st: float = 2.5,
               burst_rise_ms: float = 30.0, seed: int = 7):
    """units: bnuysynth Units; levels_hz: target plateau per unit (Hz).

    onset      scale of the measured phrase-onset fall (0 = none)
    step_ms    duration of the S-shaped step between different levels
    step_lead  fraction of the step that happens before the unit boundary
    """
    edges = np.cumsum([0.0] + [u.ms / 1000 for u in units])
    lv = np.array([12 * np.log2(max(h, 1.0)) for h in levels_hz])
    total = edges[-1]
    rng = np.random.default_rng(seed)
    # smooth, slow wobble (~6 Hz), matched to his ~0.1 st
    tt = np.arange(0, total + 0.05, 0.005)
    w = rng.standard_normal(len(tt))
    k = np.hanning(31); w = np.convolve(w, k / k.sum(), "same")
    w = w / (w.std() + 1e-9) * wobble_st
    burst_ends = [edges[i + 1] for i, u in enumerate(units) if u.ph in BURSTS]
    first_voiced = next((edges[i] for i, u in enumerate(units) if u.ph not in BURSTS and u.ph != "_"), 0.0)

    def f(t: float) -> float:
        i = int(np.clip(np.searchsorted(edges, t, side="right") - 1, 0, len(units) - 1))
        st = lv[i]
        # S-shaped steps around each boundary where the level changes
        for b in (i, i + 1):
            if 0 < b < len(units) and lv[b] != lv[b - 1]:
                start = edges[b] - step_lead * step_ms / 1000
                x = np.clip((t - start) / (step_ms / 1000), 0, 1)
                x = 0.5 - 0.5 * np.cos(np.pi * x)
                st = lv[b - 1] + (lv[b] - lv[b - 1]) * x if t >= start else st
        st += onset * np.interp(t - first_voiced, _ONSET[:, 0], _ONSET[:, 1], left=_ONSET[0, 1], right=0.0)
        for be in burst_ends:
            if 0 <= t - be < burst_rise_ms / 1000:
                st -= burst_dip_st * (1 - (t - be) / (burst_rise_ms / 1000))
        st += float(np.interp(t, tt, w))
        return float(2 ** (st / 12))
    return f
