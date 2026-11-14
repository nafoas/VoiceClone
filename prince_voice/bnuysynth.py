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
    avoid: tuple | None = None  # (start, end) in the reference: don't use an instance
                                # from there (fair evaluation: no copying)


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
        self.wav = {k: z[f"wav_{i}"] for i, k in enumerate(self.meta["labels"]) if f"wav_{i}" in z}
        self.inst = {}
        for i, k in enumerate(self.meta["labels"]):
            for j, info in enumerate(self.meta.get("instances", {}).get(k, [])):
                self.inst.setdefault(k, []).append(dict(
                    sp=z[f"isp_{i}_{j}"], ap=z[f"iap_{i}_{j}"], res=z[f"ires_{i}_{j}"], **info))
        # level-match instances of a sound: borrowing one shouldn't bring its loudness
        for k, insts in self.inst.items():
            lv = [np.log(np.exp(c["sp"]).sum()) for c in insts]
            ref = float(np.median(lv))
            for c, l in zip(insts, lv):
                c["sp"] = c["sp"] + (ref - l)

    def pick(self, ph: str, f0_target: float, avoid=None):
        """Instance closest in pitch (unit selection); None if no instances."""
        cands = self.inst.get(ph, [])
        if avoid is not None and len(cands) > 1:
            free = [c for c in cands if c["span"][1] <= avoid[0] or c["span"][0] >= avoid[1]]
            cands = free or cands
        if not cands:
            return None
        if not np.isfinite(f0_target) or f0_target <= 0:
            return cands[0]
        return min(cands, key=lambda c: abs(np.log(max(c["f0"], 1.0) / f0_target)))

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
          hold: float = 0.35, burst_wave: bool = True, fade_breath: float = 0.6,
          life: float = 1.0, burst_onset_ms: float = 15.0, hold_cons: float = 0.35,
          fade_drop_db: float = 20.0, fade_drop_ms: float = 20.0, fade_tail_db: float = 12.0,
          hum_fix: float = 0.5,
          trans_ms: float | None = None) -> np.ndarray:
    """units: sequence of catalogue sounds; f0_fn(t_seconds) -> Hz (or nan).

    hold        fraction of each steady sound spent exactly on its target; the
                rest glides (smoothstep, log-envelope) toward the neighbours,
                so the voice keeps gently moving like his real mouth
    burst_wave  p/t bursts are spliced in as his recorded audio (the vocoder
                renders bursts badly)
    fade_breath fades ("pee(t)") get breathier as they die away
    life        how much of his natural micro-movement inside each sound to keep
    hold_cons   hold fraction for steady consonants (n, m, ɹ, ɕ): closures hold
    fade_*      his fades are two-stage: a quick drop (fade_drop_db within
                fade_drop_ms), then a quiet humming tail dying by fade_tail_db
    "_" units   silence (e.g. the closure before a t); bursts and silences are
                hard edges: neighbours don't glide into them
    burst_onset_ms  a vowel right after a spliced burst comes in this fast
    """
    cat = cat or Catalogue()
    sp_rows, ap_rows, f0s, gains, breath = [], [], [], [], []
    anchors = []          # (frame index, log sp, ap)
    bursts = []           # (sample offset, waveform, gain)
    lifes = []            # (start frame, residual trajectory)
    owner_f0 = []
    prev_burst = False
    pos = 0
    t = 0.0
    CONS = {"n", "m", "ɹ", "ɕ"}

    def hard(k):  # is unit k a hard edge (silence or spliced burst)?
        if k < 0 or k >= len(units):
            return False
        ph = units[k].ph
        return ph == "_" or (burst_wave and cat.dynamic.get(ph, False) and ph in cat.wav)

    for ui, u in enumerate(units):
        n = max(1, int(round(u.ms / FRAME_MS)))
        if u.ph == "_":
            some = next(iter(cat.sp.values()))
            quiet = np.log(some + 1e-20) - 12.0
            for j in range(n):
                anchors.append((pos + j, quiet, np.ones_like(some)))
                f0s.append(0.0); gains.append(u.gain_db); breath.append(0.0)
            owner_f0 += [0.0] * n
            prev_burst = True
            pos += n; t += n * FRAME_MS / 1000
            continue
        sp, ap = cat.sp[u.ph], cat.ap[u.ph]
        vm = np.ones(n, bool) if cat.voiced[u.ph] else np.zeros(n, bool)
        if cat.dynamic[u.ph]:
            idx = np.linspace(0, len(sp) - 1, n).round().astype(int)
            if u.ph in cat.vmask:
                vm = cat.vmask[u.ph][idx].astype(bool)
            if burst_wave and u.ph in cat.wav:
                w = cat.wav[u.ph][: int(n * FRAME_MS / 1000 * SR)]
                bursts.append((int(round(t * SR)), w, u.gain_db))
                vm[:] = False
                quiet = np.log(sp[idx] + 1e-20) - 9.0   # vocoder stays near-silent here
                for j in range(n):
                    anchors.append((pos + j, quiet[j], ap[idx][j]))
            else:
                for j in range(n):
                    anchors.append((pos + j, np.log(sp[idx][j] + 1e-20), ap[idx][j]))
        else:
            tf = np.array([f0_fn(t + j * FRAME_MS / 1000) for j in range(n)], dtype=float)
            tf = tf[np.isfinite(tf)]
            inst = cat.pick(u.ph, float(np.median(tf)) if len(tf) else np.nan, u.avoid)
            target = np.log(sp + 1e-20) if inst is None else inst["sp"]
            ap_t = ap if inst is None else inst["ap"]
            h = max(1, int(round((hold_cons if u.ph in CONS else hold) * n)))
            a0 = pos + (n - h) // 2
            if prev_burst:   # voice comes straight in after a burst / silence
                a0 = pos + min(n - h, max(0, int(burst_onset_ms / FRAME_MS)))
            pts = {a0, a0 + h - 1}
            if hard(ui + 1):  # hold right up to a following burst / silence
                pts.add(pos + n - 1)
            for j in sorted(pts):
                anchors.append((j, target, ap_t))
            if inst is not None and life > 0 and len(inst["res"]) > 1:
                ridx = np.linspace(0, len(inst["res"]) - 1, n).round().astype(int)
                lifes.append((pos, inst["res"][ridx]))
        prev_burst = cat.dynamic[u.ph] and burst_wave and u.ph in cat.wav
        if cat.dynamic[u.ph] or not cat.inst.get(u.ph):
            owner_f0 += [cat.f0_ref[u.ph]] * n
        else:
            owner_f0 += [inst["f0"] if inst is not None else cat.f0_ref[u.ph]] * n
        for j in range(n):
            tt = t + j * FRAME_MS / 1000
            f = f0_fn(tt) if vm[j] else np.nan
            f0s.append(f if np.isfinite(f) else 0.0)
            g, b = u.gain_db, 0.0
            if u.fade_ms and (n - j) * FRAME_MS <= u.fade_ms:
                el = u.fade_ms - (n - j) * FRAME_MS          # ms into the fade
                x = el / u.fade_ms
                g -= fade_drop_db * min(1.0, el / fade_drop_ms)
                g -= fade_tail_db * max(0.0, (el - fade_drop_ms) / max(1.0, u.fade_ms - fade_drop_ms))
                b = fade_breath * x
            gains.append(g); breath.append(b)
        pos += n
        t += n * FRAME_MS / 1000

    # glide between anchors
    T = pos
    nb = anchors[0][1].shape[-1]
    sp = np.zeros((T, nb)); ap = np.zeros((T, nb))
    anchors.sort(key=lambda a: a[0])
    idxs = [a[0] for a in anchors]
    for (i0, s0, p0), (i1, s1, p1) in zip(anchors, anchors[1:]):
        sp[i0], ap[i0] = s0, p0
        for k in range(i0 + 1, i1):
            x = (k - i0) / (i1 - i0)
            x = x * x * (3 - 2 * x)
            sp[k] = (1 - x) * s0 + x * s1
            ap[k] = (1 - x) * p0 + x * p1
    i_last, s_last, p_last = anchors[-1]
    sp[i_last:], ap[i_last:] = s_last, p_last
    sp[: idxs[0]], ap[: idxs[0]] = anchors[0][1], anchors[0][2]

    for p0, res in lifes:   # natural micro-movement, tapered at the edges
        taper = np.sin(np.linspace(0, np.pi, len(res)))[:, None] ** 0.5
        sp[p0:p0 + len(res)] += life * res * taper

    f0 = np.array(f0s)
    sp = np.exp(sp) * (10 ** (np.array(gains) / 10))[:, None]
    b = np.array(breath)[:, None]
    ap = np.clip(ap + (1 - ap) * b, 0, 1)

    # keep his hum when the pitch differs from where the sound was recorded
    owner_f0 = np.array(owner_f0, dtype=float)
    for f_from in (np.unique(owner_f0[owner_f0 > 0]) if hum_fix > 0 else []):
        sel = (owner_f0 == f_from) & (f0 > 0)
        if sel.any():   # partial: full correction over-deepens the cliff
            fixed = _hum_correct(sp[sel], f_from, f0[sel])
            sp[sel] = np.exp((1 - hum_fix) * np.log(sp[sel] + 1e-20) + hum_fix * np.log(fixed + 1e-20))

    y = pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(ap), SR, FRAME_MS)
    for off, w, g in bursts:   # splice his real bursts
        w = w * 10 ** (g / 20)
        fade = np.ones(len(w))
        fi, fo = min(len(w), int(0.002 * SR)), min(len(w), int(0.010 * SR))
        fade[:fi] = np.linspace(0, 1, fi); fade[len(w) - fo:] *= np.linspace(1, 0, fo)
        end = min(len(y), off + len(w))
        y[off:end] += (w * fade)[: end - off]
    return y.astype(np.float32)
