"""Bnuy synthesizer: speech built only from Prince's own sounds.

The catalogue (models/catalogue.npz, built by scripts/build_catalogue.py) holds,
for each phoneme found in the reference clip, his spectral envelope and
aperiodicity (WORLD vocoder representation), cut from the labelled segments in
analysis/IPA_TRANSCRIPTION.md:

  steady sounds (vowels, nasals, r, ɕ): one representative frame (median)
  dynamic sounds (p, t bursts):         the whole frame sequence

synth() strings catalogue sounds together at any duration and pitch, gliding
between neighbours (log-envelope interpolation) so joins are smooth, then lets
WORLD render it. No human TTS voice is involved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyworld as pw

SR = 24000
FRAME_MS = 5.0
CAT_PATH = Path(__file__).resolve().parents[1] / "models" / "catalogue.npz"


@dataclass
class Unit:
    ph: str                # catalogue label
    ms: float              # duration
    fade_ms: float = 0.0   # fade out over the last fade_ms (final t that never closes)
    gain_db: float = 0.0


class Catalogue:
    def __init__(self, path: Path = CAT_PATH):
        z = np.load(path, allow_pickle=False)
        self.meta = json.loads(str(z["meta"]))
        self.sp = {k: z[f"sp_{i}"] for i, k in enumerate(self.meta["labels"])}
        self.ap = {k: z[f"ap_{i}"] for i, k in enumerate(self.meta["labels"])}
        self.voiced = dict(zip(self.meta["labels"], self.meta["voiced"]))
        self.dynamic = dict(zip(self.meta["labels"], self.meta["dynamic"]))
        self.f0_ref = dict(zip(self.meta["labels"], self.meta["f0"]))
        self.vmask = {k: z[f"vm_{i}"] for i, k in enumerate(self.meta["labels"]) if f"vm_{i}" in z}

    def __contains__(self, ph: str) -> bool:
        return ph in self.sp


def _hum_correct(sp: np.ndarray, f0_from: float, f0_to: np.ndarray) -> np.ndarray:
    """Envelopes measured at one pitch carry his harmonic cliff at that pitch.
    When rendering at another pitch, warp the low region so H1/H2 keep their
    strength relative to the new harmonics."""
    if f0_from <= 0:
        return sp
    freqs = np.linspace(0, SR / 2, sp.shape[1])
    out = sp.copy()
    for k in np.where(f0_to > 0)[0]:
        r = f0_to[k] / f0_from
        if abs(r - 1) < 0.03:
            continue
        lim = 4.0 * f0_to[k]  # only the hum region; formants above stay put
        src = np.where(freqs < lim, freqs / r, freqs)
        blend = np.clip((freqs - 3.0 * f0_to[k]) / f0_to[k], 0, 1)
        src = (1 - blend) * src + blend * freqs
        out[k] = np.exp(np.interp(src, freqs, np.log(sp[k] + 1e-20)))
    return out


def synth(units: list[Unit], f0_fn, cat: Catalogue | None = None,
          trans_ms: float = 35.0) -> np.ndarray:
    """units: sequence of catalogue sounds; f0_fn(t_seconds) -> Hz (or nan)."""
    cat = cat or Catalogue()
    nb = next(iter(cat.sp.values())).shape[-1]
    frames_sp, frames_ap, frames_f0, owner, gains = [], [], [], [], []
    t = 0.0
    for ui, u in enumerate(units):
        n = max(1, int(round(u.ms / FRAME_MS)))
        sp, ap = cat.sp[u.ph], cat.ap[u.ph]
        vm = np.ones(n, bool) if cat.voiced[u.ph] else np.zeros(n, bool)
        if cat.dynamic[u.ph]:   # resample the recorded frame sequence to n frames
            idx = np.linspace(0, len(sp) - 1, n).round().astype(int)
            sp_seq, ap_seq = sp[idx], ap[idx]
            if u.ph in cat.vmask:
                vm = cat.vmask[u.ph][idx].astype(bool)
        else:
            sp_seq, ap_seq = np.repeat(sp[None], n, 0), np.repeat(ap[None], n, 0)
        for j in range(n):
            tt = t + j * FRAME_MS / 1000
            f = f0_fn(tt) if vm[j] else np.nan
            frames_f0.append(f if np.isfinite(f) else 0.0)
            g = u.gain_db
            if u.fade_ms and (n - j) * FRAME_MS <= u.fade_ms:
                g -= 20.0 * (1 - (n - j) * FRAME_MS / u.fade_ms)
            gains.append(g)
            owner.append(ui)
        frames_sp.append(sp_seq); frames_ap.append(ap_seq)
        t += n * FRAME_MS / 1000
    sp = np.log(np.vstack(frames_sp) + 1e-20)
    ap = np.vstack(frames_ap)
    f0 = np.array(frames_f0)
    owner = np.array(owner)

    # smooth joins: crossfade log-envelopes around every boundary between
    # steady sounds (dynamic bursts keep their own recorded transitions)
    w = max(1, int(trans_ms / FRAME_MS / 2))
    bounds = np.where(np.diff(owner) != 0)[0] + 1
    sp_s, ap_s = sp.copy(), ap.copy()
    for b in bounds:
        a_u, b_u = units[owner[b - 1]], units[owner[b]]
        if cat.dynamic[a_u.ph] or cat.dynamic[b_u.ph]:
            continue
        lo, hi = max(0, b - w), min(len(sp), b + w)
        L, R = sp[max(0, lo - 1)], sp[min(len(sp) - 1, hi)]
        La, Ra = ap[max(0, lo - 1)], ap[min(len(sp) - 1, hi)]
        for k in range(lo, hi):
            x = (k - lo + 0.5) / (hi - lo)
            x = x * x * (3 - 2 * x)
            sp_s[k] = (1 - x) * L + x * R
            ap_s[k] = (1 - x) * La + x * Ra
    sp = np.exp(sp_s) * (10 ** (np.array(gains) / 10))[:, None]

    # keep his hum when the pitch differs from where the sound was recorded
    ref_f0 = np.array([cat.f0_ref[units[o].ph] for o in owner])
    for f_from in np.unique(ref_f0[ref_f0 > 0]):
        sel = (ref_f0 == f_from) & (f0 > 0)
        if sel.any():
            sp[sel] = _hum_correct(sp[sel], f_from, f0[sel])

    y = pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(np.clip(ap_s, 0, 1)),
                      SR, FRAME_MS)
    return y.astype(np.float32)
