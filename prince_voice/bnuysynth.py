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
HUMMY_WAVE = {"ɕ"}   # recorded-audio units that carry his hum (pitch-sensitive)
CAT_PATH = Path(__file__).resolve().parents[1] / "models" / "catalogue.npz"


# Phonetic features, used to judge how similar two contexts are:
#        lab cor pal nas stp fri apx vow frn bck hig low rnd rho sil
_F = {
    "n":  [0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "m":  [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "ɹ":  [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
    "ɕ":  [0, .5, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "p":  [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "tʰ": [0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "ã":  [0, 0, 0, .5, 0, 0, 0, 1, .6, 0, 0, 1, 0, 0, 0],
    "ɐ˞": [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, .5, 0, 1, 0],
    "ũ":  [0, 0, 0, .5, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0],
    "iː": [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0],
    "_":  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    "#":  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
}


def ctx_dist(a: str, b: str) -> float:
    if a == b:
        return 0.0
    fa, fb = _F.get(a), _F.get(b)
    if fa is None or fb is None:
        return 2.0
    return float(np.sqrt(np.sum((np.array(fa) - np.array(fb)) ** 2)))


@dataclass
class Unit:
    ph: str                # catalogue label
    ms: float              # duration
    fade_ms: float = 0.0   # fade out over the last fade_ms (final t that never closes)
    gain_db: float = 0.0
    avoid: tuple | None = None  # (start, end) in the reference: don't use an instance
                                # from there (fair evaluation: no copying)
    stress: bool | None = None  # stressed syllable? (None = don't care)
    prefer: tuple | None = None  # (start, end): use this recording if possible (set by the planner)


class Catalogue:
    def __init__(self, path: Path = CAT_PATH, level_match: float = 0.0):
        z = np.load(path, allow_pickle=False)
        self.meta = json.loads(str(z["meta"]))
        self.sp = {k: z[f"sp_{i}"] for i, k in enumerate(self.meta["labels"])}
        self.ap = {k: z[f"ap_{i}"] for i, k in enumerate(self.meta["labels"])}
        self.voiced = dict(zip(self.meta["labels"], self.meta["voiced"]))
        self.dynamic = dict(zip(self.meta["labels"], self.meta["dynamic"]))
        self.f0_ref = dict(zip(self.meta["labels"], self.meta["f0"]))
        self.vmask = {k: z[f"vm_{i}"] for i, k in enumerate(self.meta["labels"]) if f"vm_{i}" in z}
        self.wav = {k: z[f"wav_{i}"] for i, k in enumerate(self.meta["labels"]) if f"wav_{i}" in z}
        self.inst, self.dyn = {}, {}
        for i, k in enumerate(self.meta["labels"]):
            for j, info in enumerate(self.meta.get("instances", {}).get(k, [])):
                if f"dsp_{i}_{j}" in z:
                    self.dyn.setdefault(k, []).append(dict(
                        sp=z[f"dsp_{i}_{j}"], ap=z[f"dap_{i}_{j}"], wav=z[f"dwav_{i}_{j}"],
                        vm=z[f"dvm_{i}_{j}"].astype(bool),
                        vf=z[f"dvf_{i}_{j}"].astype(bool) if f"dvf_{i}_{j}" in z else None, **info))
                    continue
                d = dict(sp=z[f"isp_{i}_{j}"], ap=z[f"iap_{i}_{j}"], res=z[f"ires_{i}_{j}"], **info)
                if f"iL_{i}_{j}" in z:
                    d.update(L=z[f"iL_{i}_{j}"], R=z[f"iR_{i}_{j}"], aL=z[f"iaL_{i}_{j}"], aR=z[f"iaR_{i}_{j}"])
                if f"itail_{i}_{j}" in z:
                    d.update(tail=z[f"itail_{i}_{j}"].astype(float), taila=z[f"itaila_{i}_{j}"].astype(float),
                             tailvm=z[f"itailvm_{i}_{j}"].astype(bool))
                if f"dsp_{i}_{j}" in z:
                    d = dict(sp=z[f"dsp_{i}_{j}"], ap=z[f"dap_{i}_{j}"], wav=z[f"dwav_{i}_{j}"],
                             vm=z[f"dvm_{i}_{j}"].astype(bool), **info)
                    self.dyn.setdefault(k, []).append(d)
                    continue
                if f"iPL_{i}_{j}" in z:
                    d.update(PL=z[f"iPL_{i}_{j}"].astype(float), PR=z[f"iPR_{i}_{j}"].astype(float))
                if f"iTL_{i}_{j}" in z:
                    d.update(TL=z[f"iTL_{i}_{j}"].astype(float), TR=z[f"iTR_{i}_{j}"].astype(float),
                             TaL=z[f"iTaL_{i}_{j}"].astype(float), TaR=z[f"iTaR_{i}_{j}"].astype(float))
                self.inst.setdefault(k, []).append(d)
        # level-match instances of a sound (level_match 0..1): 0 keeps each
        # recording's own loudness (his natural stress); 1 makes all instances
        # of a sound equally loud (both halves shift together)
        for k, insts in self.inst.items():
            lv = [np.log(np.exp(c["sp"]).sum()) for c in insts]
            ref = float(np.median(lv))
            for c, l in zip(insts, lv):
                for key in ("sp", "L", "R", "TL", "TR", "tail"):
                    if key in c:
                        c[key] = c[key] + level_match * (ref - l)

    def pick_dyn(self, ph: str, f0_next: float, next_final: bool | None = None):
        """Recorded burst best matching where it sits (does it lead into the
        phrase's last syllable?) and the pitch of the vowel after it."""
        c = self.dyn.get(ph, [])
        if not c:
            return None

        def cost(d):
            k = 0.0
            if np.isfinite(f0_next) and f0_next > 0:
                k += 2.0 * abs(np.log2(max(d["f0"], 1.0) / f0_next))
            if next_final is not None and d.get("next_final") is not None and d["next_final"] != next_final:
                k += 0.5
            return k
        return min(c, key=cost)

    def pick_tail(self, f0_target: float, prefer=None):
        """A recorded fade tail: the chosen vowel's own if it has one, else
        the one recorded closest in pitch."""
        if prefer is not None and "tail" in prefer:
            return prefer
        c = [d for d in self.inst.get("iː", []) if "tail" in d]
        if not c:
            return None
        if not np.isfinite(f0_target):
            return c[0]
        return min(c, key=lambda d: abs(np.log(max(d["f0"], 1.0) / f0_target)))

    def pick_half(self, ph: str, side: str, ctx: str, f0_target: float, stress=None,
                  edge: bool = False, avoid=None, w_ctx=1.0, w_pitch=2.0, w_stress=0.3, w_edge=0.2,
                  avoid_penalty: float = 0.0, same_as=None, w_join: float = 0.0, prefer=None,
                  noise=None):
        """Sub-phoneme selection: the instance whose `side` half ("L" or "R")
        best matches the wanted neighbour, pitch, stress and phrase position."""
        cands = [c for c in self.inst.get(ph, []) if "L" in c]
        if not cands:
            return None

        def overlaps(c):
            return avoid is not None and not (c["span"][1] <= avoid[0] or c["span"][0] >= avoid[1])
        if np.isinf(avoid_penalty) and len(cands) > 1:   # strict: never the same moment
            cands = [c for c in cands if not overlaps(c)] or cands

        def cost(c):
            nb = c["left"] if side == "L" else c["right"]
            k = w_ctx * ctx_dist(ctx, nb)
            fc = c["f0" + side]
            if np.isfinite(f0_target) and f0_target > 0 and fc > 0:
                k += w_pitch * abs(np.log2(f0_target / fc))
            if stress is not None and c["stress"] != stress:
                k += w_stress
            if (c["initial"] if side == "L" else c["final"]) != edge:
                k += w_edge
            if np.isfinite(avoid_penalty) and overlaps(c):
                k += avoid_penalty
            if same_as is not None and c is not same_as:
                k += w_join   # switching instance mid-sound changes the hum audibly
            if prefer is not None and tuple(c["span"]) != tuple(prefer):
                k += 3.0      # the planner already chose this recording (and its timing)
            if noise is not None:
                k += noise(c)  # natural variety: not always the same mouth shape
            return k
        return min(cands, key=cost)

    def pick(self, ph: str, f0_target: float, avoid=None, strict: bool = False):
        """Instance closest in pitch (unit selection); None if no instances."""
        cands = self.inst.get(ph, [])
        if strict and avoid is not None and len(cands) > 1:
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


def _cliff_db(freqs: np.ndarray, f0: np.ndarray, depth: float, start: float, end: float) -> np.ndarray:
    """His humming source: harmonics 1-2 strong, everything above start*f0
    falling by `depth` dB by end*f0 (frames x bins)."""
    x = np.clip((freqs[None, :] / f0[:, None] - start) / (end - start), 0, 1)
    return -depth * x * x * (3 - 2 * x)


def _source_refit(sp: np.ndarray, f_from: np.ndarray, f_to: np.ndarray, depth,
                  start: float, end: float) -> np.ndarray:
    """Re-pitch his hum while keeping his mouth shape: remove the cliff where
    it sat at the recorded pitch, put it back at the new pitch. Formants stay put.
    depth: per frame (each recorded sound's own measured hum), or a constant."""
    freqs = np.linspace(0, SR / 2, sp.shape[1])
    d = np.broadcast_to(np.asarray(depth, dtype=float), f_to.shape)[:, None]
    gain = d * (_cliff_db(freqs, f_to, 1.0, start, end) - _cliff_db(freqs, f_from, 1.0, start, end))
    return sp * 10 ** (gain / 10)


def synth(units: list[Unit], f0_fn, cat: Catalogue | None = None,
          hold: float = 0.35, burst_wave: bool = True, fade_breath: float = 0.6,
          life: float = 1.0, burst_onset_ms: float = 15.0, hold_cons: float = 0.35,
          fade_drop_db: float = 20.0, fade_drop_ms: float = 20.0, fade_tail_db: float = 12.0,
          hum_fix: float = 0.5, sub_phonemes: bool = True, w_ctx: float = 1.0,
          avoid_penalty: float = 0.0, trajectories: bool = True, join_ms: float = 20.0,
          real_tails: bool = True, hum_mode: str = "source", hum_depth: float = 25.0,
          hum_start: float = 1.5, hum_end: float = 3.2, per_sound_hum: bool = True,
          w_join: float = 1.0, smooth_warp: bool = True, fill_pitch: bool = True,
          wave_max_shift_st: float = 1.0, pitch_life: float = 0.0, pitch_life_hp_ms: float = 25.0,
          pitch_loud: float = 0.0, edge_ms: float = 40.0, hum_smooth_ms: float = 40.0,
          w_pitch: float = 2.0, hum_boost_db: float = 0.0, hum_steady: float = 0.0,
          breath_support: float = 0.0, breath_ms: float = 200.0,
          attack_ms: float = 0.0, release_ms: float = 0.0,
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
    edge_ms     at joins between pieces, spread their mismatch over this much of
                each side so they meet halfway instead of stepping
    attack_ms   a phrase swells in over this long (his: ~40 ms from silence),
                instead of starting at full volume
    release_ms  a phrase that doesn't end on one of his natural fades eases out
    breath_support  0..1: one breath carries the phrase. Voiced frames' loudness
                is pulled toward a slow breath curve (breath_ms smoothing), so
                borrowed sounds don't bring their own loudness jumps; fades and
                unvoiced sounds keep their natural levels
    hum_steady  0..1: steady his hum's loudness within continuous voiced
                stretches (keeps slow rises/falls, evens out fast wobble)
    hum_boost_db  extra pitch-locked hum cliff (dB) for new phrases, whose hum
                otherwise comes out softer than in his real speech
    pitch_loud  dB of extra loudness per semitone above the phrase's middle pitch
                (0 for the rebuild, whose loudness is already his; ~0.8 for new)
    pitch_life  add each recording's own pitch micro-movement (0 for the rebuild,
                whose pitch already is his; ~1 for new phrases)
    w_join      cost of taking a sound's two halves from different recordings
    smooth_warp stretch recorded movement by interpolating frames (no repeats)
    fill_pitch  inside a voiced sound, bridge brief gaps in f0_fn (tracker dropouts)
    hum_mode    "source": treat his sound as humming source x mouth shape and move
                only the source cliff with pitch (formants stay put); "warp": old
                partial frequency warp
    real_tails  fades use his recorded humming decay (vowel isn't stretched over it)
    trajectories  use each chosen half's real recorded movement (time-stretched),
                joined smoothly over join_ms, instead of targets + glides
    avoid_penalty how strongly to avoid a unit's own moment in the clip (u.avoid):
                0 = free choice, inf = never (strict fairness test)
    sub_phonemes  pick each half of a sound by its context (neighbour, pitch,
                stress, phrase position) instead of one snapshot per sound
    "_" units   silence (e.g. the closure before a t); bursts and silences are
                hard edges: neighbours don't glide into them
    burst_onset_ms  a vowel right after a spliced burst comes in this fast
    """
    cat = cat or Catalogue()
    if fill_pitch:
        raw_fn = f0_fn

        def f0_fn(t, _r=raw_fn):   # bridge brief tracker dropouts (<= 40 ms)
            v = _r(t)
            if np.isfinite(v) and v > 0:
                return v
            for d in (0.005, 0.01, 0.02, 0.03, 0.04):
                a, b = _r(t - d), _r(t + d)
                ok = [x for x in (a, b) if np.isfinite(x) and x > 0]
                if ok:
                    return float(np.mean(ok))
            return v
    sp_rows, ap_rows, f0s, gains, breath = [], [], [], [], []
    anchors = []          # (frame index, log sp, ap)
    bursts = []           # (sample offset, waveform, gain)
    lifes = []            # (start frame, residual trajectory)
    trajs = []            # (start frame, log-sp trajectory, ap trajectory)
    traj_src = {}         # start frame -> (left-half recording, right-half recording, has tail)
    plife = []            # (start frame, recorded pitch micro-movement, semitones)
    picks = []            # (sound, left-half recording, right-half recording) for diagnostics
    owner_f0 = []
    owner_hum = []        # each frame's recorded hum depth (dB), for re-pitching
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
            owner_hum += [0.0] * n
            prev_burst = True
            pos += n; t += n * FRAME_MS / 1000
            continue
        sp, ap = cat.sp[u.ph], cat.ap[u.ph]
        vm = np.ones(n, bool) if cat.voiced[u.ph] else np.zeros(n, bool)
        if cat.dynamic[u.ph]:
            dinst = cat.pick_dyn(u.ph, f0_fn(t + (n + 4) * FRAME_MS / 1000),
                                 next_final=(ui + 2 == len(units)))
            dwav = cat.wav.get(u.ph)
            if dinst is not None:
                sp, ap, dwav = dinst["sp"], dinst["ap"], dinst["wav"]
            idx = np.linspace(0, len(sp) - 1, n).round().astype(int)
            if dinst is not None:
                vm = dinst["vm"][idx].astype(bool)
            elif u.ph in cat.vmask:
                vm = cat.vmask[u.ph][idx].astype(bool)
            # a voiced recording (his hummy S) is spliced as real audio only if the
            # phrase pitch is close to where it was recorded; otherwise it is
            # rebuilt from its frames at the phrase's pitch (hum under the hiss)
            use_wave = burst_wave and dwav is not None
            if use_wave and dinst is not None and dinst.get("vf") is not None and dinst.get("rec_f0", 0) > 0 \
                    and u.ph in HUMMY_WAVE:
                tgt = np.array([f0_fn(t + j * FRAME_MS / 1000) for j in range(n)], dtype=float)
                tgt = tgt[np.isfinite(tgt) & (tgt > 0)]
                if len(tgt) and abs(12 * np.log2(np.median(tgt) / dinst["rec_f0"])) > wave_max_shift_st:
                    use_wave = False
                    vm = dinst["vf"][idx].astype(bool)
            partial = None
            if use_wave and u.ph not in HUMMY_WAVE and dinst is not None and dinst.get("f0", 0) > 0:
                # the recording also holds the start of the next vowel at ITS pitch; if the
                # phrase wants another pitch, splice only the unvoiced pop/puff and let the
                # hum come out of it at the phrase's own pitch
                tgt = f0_fn(t + (n + 2) * FRAME_MS / 1000)
                if np.isfinite(tgt) and tgt > 0 and abs(12 * np.log2(tgt / dinst["f0"])) > wave_max_shift_st:
                    rv = ~dinst["vm"][idx].astype(bool)
                    if rv.any():
                        a0 = int(np.argmax(rv)); a1 = a0
                        while a1 < n and rv[a1]:
                            a1 += 1
                        partial = (a0, a1)
            if use_wave:
                w = dwav[: int(n * FRAME_MS / 1000 * SR)]
                if partial is not None:
                    a0, a1 = partial
                    w = w.copy()
                    w[: int(a0 * FRAME_MS / 1000 * SR)] = 0.0
                    w[int((a1 + 1) * FRAME_MS / 1000 * SR):] = 0.0
                bursts.append((int(round(t * SR)), w, u.gain_db))
                if partial is not None:
                    vm[:] = True
                    vm[partial[0]:partial[1]] = False
                else:
                    vm[:] = False
                quiet = np.log(sp[idx] + 1e-20) - 9.0   # vocoder stays near-silent here
                for j in range(n):
                    in_splice = partial is None or (partial[0] <= j < partial[1])
                    anchors.append((pos + j, quiet[j] if in_splice else np.log(sp[idx][j] + 1e-20), ap[idx][j]))
            else:
                for j in range(n):
                    anchors.append((pos + j, np.log(sp[idx][j] + 1e-20), ap[idx][j]))
        else:
            fr = np.array([f0_fn(t + j * FRAME_MS / 1000) for j in range(n)], dtype=float)

            def med(a):
                a = a[np.isfinite(a)]
                return float(np.median(a)) if len(a) else np.nan
            lctx = units[ui - 1].ph if ui > 0 else "#"
            # a phrase-final sound looks for a phrase-final recording ("#"), even
            # when it fades; a mid-phrase fade leads into silence ("_")
            rctx = "#" if ui + 1 >= len(units) else ("_" if u.fade_ms else units[ui + 1].ph)
            iL = cat.pick_half(u.ph, "L", lctx, med(fr[: n // 2 + 1]), u.stress, ui == 0, u.avoid,
                               w_ctx=w_ctx, avoid_penalty=avoid_penalty, prefer=u.prefer,
                               w_pitch=w_pitch) if sub_phonemes else None
            iR = cat.pick_half(u.ph, "R", rctx, med(fr[n // 2:]), u.stress, ui == len(units) - 1, u.avoid,
                               w_ctx=w_ctx, avoid_penalty=avoid_penalty,
                               same_as=iL, w_join=w_join, prefer=u.prefer, w_pitch=w_pitch) if sub_phonemes else None
            picks.append((u.ph, iL["span"] if iL else None, iR["span"] if iR else None))
            if iL is not None and iR is not None:
                tL, tR, aL, aR = iL["L"], iR["R"], iL["aL"], iR["aR"]
                inst = iL
                fL, fR = iL["f0L"], iR["f0R"]
            else:
                inst = cat.pick(u.ph, med(fr), u.avoid, strict=np.isinf(avoid_penalty))
                tL = tR = np.log(sp + 1e-20) if inst is None else inst["sp"]
                aL = aR = ap if inst is None else inst["ap"]
                fL = fR = inst["f0"] if inst is not None else cat.f0_ref[u.ph]
            hh = (hold_cons if u.ph in CONS else hold)
            if trajectories and iL is not None and iR is not None and "TL" in iL and "TR" in iR:
                def warp(seq, m):
                    pos_ = np.linspace(0, len(seq) - 1, max(1, m))
                    if not smooth_warp or len(seq) < 2:
                        return seq[pos_.round().astype(int)]
                    i0 = np.floor(pos_).astype(int); i1 = np.minimum(i0 + 1, len(seq) - 1)
                    fr_ = (pos_ - i0)[:, None] if seq.ndim > 1 else (pos_ - i0)
                    out_ = seq[i0] * (1 - fr_) + seq[i1] * fr_
                    return out_.astype(seq.dtype) if seq.dtype == bool else out_
                tinst = cat.pick_tail(fR, iR) if (u.fade_ms and real_tails) else None
                nf = min(n - 2, int(round(u.fade_ms / FRAME_MS))) if tinst is not None else 0
                nv = n - nf
                nl = nv // 2; nr = nv - nl
                tr = [warp(iL["TL"], nl), warp(iR["TR"], nr)]
                ta = [warp(iL["TaL"], nl), warp(iR["TaR"], nr)]
                if nf:   # his real humming decay instead of a stretched vowel + fade
                    tr.append(warp(tinst["tail"], nf)); ta.append(warp(tinst["taila"], nf))
                    tv = tinst["tailvm"].astype(float)
                    vm = np.concatenate([vm[:nv], warp(tv, nf).reshape(-1) > 0.5])
                trajs.append((pos, np.vstack(tr), np.vstack(ta)))
                traj_src[pos] = (tuple(iL["span"]), tuple(iR["span"]), bool(nf))
                if pitch_life > 0 and "PL" in iL and "PR" in iR:
                    pl = np.concatenate([warp(iL["PL"], nl), warp(iR["PR"], nr), np.zeros(nf)]).reshape(-1)
                    if pitch_life_hp_ms > 0 and len(pl) > 3:   # keep fine detail only, not
                        kk = max(3, int(pitch_life_hp_ms / FRAME_MS) | 1)   # the recording's big shapes
                        trend = np.convolve(np.pad(pl, kk // 2, mode="edge"), np.ones(kk) / kk, "valid")
                        pl = pl - trend
                    plife.append((pos, pitch_life * pl))
                pts = [(pos, None, None), (pos + n - 1, None, None)]  # placeholders, filled below
                for j, tt_, aa in pts:
                    anchors.append((j, trajs[-1][1][0 if j == pos else -1], trajs[-1][2][0 if j == pos else -1]))
                half_f0 = [fL] * nl + [fR] * (n - nl)
                prev_burst = cat.dynamic[u.ph] and burst_wave and u.ph in cat.wav and u.ph not in HUMMY_WAVE
                owner_f0 += half_f0
                owner_hum += [iL.get("hum_db", hum_depth)] * nl + [iR.get("hum_db", hum_depth)] * (n - nl)
                for j in range(n):
                    tt = t + j * FRAME_MS / 1000
                    f = f0_fn(tt) if vm[j] else np.nan
                    f0s.append(f if np.isfinite(f) else 0.0)
                    g, b = u.gain_db, 0.0
                    if u.fade_ms and not nf and (n - j) * FRAME_MS <= u.fade_ms:
                        el = u.fade_ms - (n - j) * FRAME_MS
                        g -= fade_drop_db * min(1.0, el / fade_drop_ms)
                        g -= fade_tail_db * max(0.0, (el - fade_drop_ms) / max(1.0, u.fade_ms - fade_drop_ms))
                        b = fade_breath * el / u.fade_ms
                    gains.append(g); breath.append(b)
                pos += n
                t += n * FRAME_MS / 1000
                continue
            if n < 6:   # too short for two targets: one blended target
                h = max(1, int(round(hh * n)))
                a0 = pos + (n - h) // 2
                mid_t, mid_a = (tL + tR) / 2, (aL + aR) / 2
                pts = [(a0, mid_t, mid_a), (a0 + h - 1, mid_t, mid_a)]
            else:       # first half aims at the left-coloured target, second at the right
                h = max(1, int(round(hh * n / 2)))
                cL, cR = pos + int(0.3 * n), pos + int(0.7 * n)
                if prev_burst:   # voice comes straight in after a burst / silence
                    cL = pos + min(n // 2 - h, max(0, int(burst_onset_ms / FRAME_MS))) + h // 2
                pts = [(cL - h // 2, tL, aL), (cL - h // 2 + h - 1, tL, aL),
                       (cR - h // 2, tR, aR), (cR - h // 2 + h - 1, tR, aR)]
            if hard(ui + 1):  # hold right up to a following burst / silence
                pts.append((pos + n - 1, tR, aR))
            for j, tt_, aa in pts:
                anchors.append((j, tt_, aa))
            if inst is not None and life > 0 and len(inst["res"]) > 1:
                ridx = np.linspace(0, len(inst["res"]) - 1, n).round().astype(int)
                lifes.append((pos, inst["res"][ridx]))
            half_f0 = [fL] * (n // 2) + [fR] * (n - n // 2)
        prev_burst = cat.dynamic[u.ph] and burst_wave and u.ph in cat.wav and u.ph not in HUMMY_WAVE
        if cat.dynamic[u.ph] or not cat.inst.get(u.ph):
            owner_f0 += [cat.f0_ref[u.ph]] * n
            owner_hum += [0.0 if cat.dynamic[u.ph] else hum_depth] * n
        else:
            owner_f0 += half_f0
            owner_hum += [(inst or {}).get("hum_db", hum_depth)] * n
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

    # real recorded movement: paste trajectories, then blend each join over join_ms
    if trajs:
        glide_sp, glide_ap = sp.copy(), ap.copy()
        wj = max(1, int(join_ms / FRAME_MS / 2))
        for p0, tr, ta in trajs:
            sp[p0:p0 + len(tr)] = tr
            ap[p0:p0 + len(ta)] = ta
        # edge matching: where two pieces meet, spread their mismatch over the
        # last/first edge_ms of each so they meet halfway (his sounds melt into
        # each other; glued pieces otherwise step). Each keeps its own movement.
        if edge_ms > 0:
            ke = max(1, int(edge_ms / FRAME_MS))
            starts = {p0: len(tr) for p0, tr, _ in trajs}
            for p0, tr, _ in trajs:
                b = p0 + len(tr)
                if b not in starts or b < 2 or b + 2 > len(sp):
                    continue
                # a join that was real in his recording (pieces were neighbours)
                # is already his: leave it exactly as it was
                a_src, b_src = traj_src.get(p0), traj_src.get(b)
                if a_src and b_src and not a_src[2] and abs(a_src[1][1] - b_src[0][0]) < 0.012:
                    continue
                dL = sp[b:b + 2].mean(0) - sp[b - 2:b].mean(0)
                dA = ap[b:b + 2].mean(0) - ap[b - 2:b].mean(0)
                ka = min(ke, len(tr)); kb = min(ke, starts[b])
                ra = np.linspace(0, 1, ka + 1)[1:][:, None]          # 0 -> 1 toward the join
                rb = np.linspace(1, 0, kb + 1)[:-1][:, None]         # 1 -> 0 away from it
                sp[b - ka:b] += 0.5 * dL[None, :] * ra
                sp[b:b + kb] -= 0.5 * dL[None, :] * rb
                ap[b - ka:b] += 0.5 * dA[None, :] * ra
                ap[b:b + kb] -= 0.5 * dA[None, :] * rb
            ap = np.clip(ap, 0, 1)
        for p0, tr, ta in trajs:
            for b in (p0, p0 + len(tr)):
                lo, hi = max(0, b - wj), min(len(sp), b + wj)
                if hi - lo < 2 or b <= 0 or b >= len(sp):
                    continue
                L, R = sp[lo].copy(), sp[hi - 1].copy()
                La, Ra = ap[lo].copy(), ap[hi - 1].copy()
                for k in range(lo, hi):
                    x = (k - lo) / (hi - 1 - lo)
                    x = x * x * (3 - 2 * x)
                    sp[k] = (1 - x) * L + x * R
                    ap[k] = (1 - x) * La + x * Ra

    for p0, res in lifes:   # natural micro-movement, tapered at the edges
        taper = np.sin(np.linspace(0, np.pi, len(res)))[:, None] ** 0.5
        sp[p0:p0 + len(res)] += life * res * taper

    f0 = np.array(f0s)
    if pitch_loud:   # effort: a higher syllable is a little louder (his ~1 dB per semitone)
        v = f0 > 0
        if v.any():
            stv = 12 * np.log2(np.where(v, f0, 1.0))
            ref_st = np.median(stv[v])
            g = np.array(gains, dtype=float)
            g[v] += pitch_loud * np.clip(stv[v] - ref_st, -6, 6)
            gains = list(g)
    for p0, pl in plife:   # his real pitch micro-movement on top of the plan
        seg = f0[p0:p0 + len(pl)]
        f0[p0:p0 + len(pl)] = np.where(seg > 0, seg * 2 ** (pl[: len(seg)] / 12), 0.0)
    sp = np.exp(sp) * (10 ** (np.array(gains) / 10))[:, None]
    b = np.array(breath)[:, None]
    ap = np.clip(ap + (1 - ap) * b, 0, 1)

    # keep his hum when the pitch differs from where the sound was recorded
    owner_f0 = np.array(owner_f0, dtype=float)
    if breath_support > 0:
        fade_mask = np.array(breath) > 0
        m = (f0 > 0) & ~fade_mask
        if m.sum() > 5:
            le = np.log(sp.sum(1) + 1e-30)
            ii = np.arange(len(le))
            fill = np.interp(ii, ii[m], le[m])            # bridge consonants
            kb = max(3, int(breath_ms / FRAME_MS) | 1)
            curve = np.convolve(np.pad(fill, kb // 2, mode="edge"), np.ones(kb) / kb, "valid")
            corr = np.where(m, breath_support * (curve - le), 0.0)
            ks = max(3, int(30 / FRAME_MS) | 1)               # no step at the edges of the mask
            corr = np.convolve(np.pad(corr, ks // 2, mode="edge"), np.ones(ks) / ks, "valid")
            sp *= np.exp(corr)[:, None]
    if attack_ms > 0 or release_ms > 0:
        T_ = len(f0)
        g_ = np.zeros(T_)
        if attack_ms > 0:
            # the swell starts where his voice starts (after any opening burst,
            # which keeps its own natural level)
            vf = np.where(f0 > 0)[0]
            a0 = int(vf[0]) if len(vf) else 0
            ka = min(T_ - a0, max(1, int(attack_ms / FRAME_MS)))
            x_ = np.linspace(0, 1, ka)
            g_[a0:a0 + ka] += -40.0 * (1 - x_ * x_ * (3 - 2 * x_))   # from -40 dB, S-shaped swell
            if a0 > 0:
                g_[:a0] += 0.0
        if release_ms > 0 and not units[-1].fade_ms and not cat.dynamic.get(units[-1].ph, False):
            kr = min(T_, max(1, int(release_ms / FRAME_MS)))
            x_ = np.linspace(0, 1, kr)
            g_[T_ - kr:] += -30.0 * x_ * x_
        sp *= (10 ** (g_ / 10))[:, None]
    if hum_steady > 0:   # breath support: even out fast loudness wobble inside a hum
        v = f0 > 0
        le = np.log(sp.sum(1) + 1e-30)
        kk = max(3, int(60 / FRAME_MS) | 1)
        i = 0
        while i < len(v):
            if not v[i]:
                i += 1; continue
            j = i
            while j < len(v) and v[j]:
                j += 1
            if j - i >= kk:
                seg = le[i:j]
                sm = np.convolve(np.pad(seg, kk // 2, mode="edge"), np.ones(kk) / kk, "valid")
                sp[i:j] *= np.exp(hum_steady * (sm - seg))[:, None]
            i = j
    if hum_boost_db > 0:   # firm up his hum: harmonics above the 2nd pulled down a bit more
        vb = f0 > 0
        if vb.any():
            fqb = np.linspace(0, SR / 2, sp.shape[1])
            sp[vb] = sp[vb] * 10 ** (_cliff_db(fqb, f0[vb], hum_boost_db, hum_start, hum_end) / 10)
    if hum_mode == "source":   # source x mouth: move only the hum cliff with pitch
        sel = (owner_f0 > 0) & (f0 > 0)
        oh = np.array(owner_hum, dtype=float)
        if hum_smooth_ms > 0 and len(owner_f0) > 3:   # no abrupt hum switch at joins
            kk = max(3, int(hum_smooth_ms / FRAME_MS) | 1)
            pos_ = owner_f0 > 0
            lg = np.where(pos_, np.log(np.maximum(owner_f0, 1.0)), np.nan)
            ii = np.arange(len(lg))
            if pos_.any():
                lg = np.interp(ii, ii[pos_], lg[pos_])
                lg = np.convolve(np.pad(lg, kk // 2, mode="edge"), np.ones(kk) / kk, "valid")
                owner_f0 = np.where(pos_, np.exp(lg), owner_f0)
                oh = np.convolve(np.pad(oh, kk // 2, mode="edge"), np.ones(kk) / kk, "valid")
        if sel.any():
            depth = oh[sel] if per_sound_hum else hum_depth
            sp[sel] = _source_refit(sp[sel], owner_f0[sel], f0[sel], depth, hum_start, hum_end)
    for f_from in (np.unique(owner_f0[owner_f0 > 0]) if hum_fix > 0 and hum_mode == "warp" else []):
        sel = (owner_f0 == f_from) & (f0 > 0)
        if sel.any():   # partial: full correction over-deepens the cliff
            fixed = _hum_correct(sp[sel], f_from, f0[sel])
            sp[sel] = np.exp((1 - hum_fix) * np.log(sp[sel] + 1e-20) + hum_fix * np.log(fixed + 1e-20))

    edges_ = np.cumsum([0] + [max(1, int(round(u.ms / FRAME_MS))) for u in units])
    synth.last = dict(f0=f0.copy(), owner_f0=owner_f0.copy(), picks=picks,
                      bounds=[(int(b), units[k].ph, units[k + 1].ph) for k, b in enumerate(edges_[1:-1])])
    end_fade_ms = 15.0
    y = pw.synthesize(f0, np.ascontiguousarray(sp), np.ascontiguousarray(ap), SR, FRAME_MS)
    for off, w, g in bursts:   # splice his real bursts
        w = w * 10 ** (g / 20)
        fade = np.ones(len(w))
        fi, fo = min(len(w), int(0.002 * SR)), min(len(w), int(0.010 * SR))
        fade[:fi] = np.linspace(0, 1, fi); fade[len(w) - fo:] *= np.linspace(1, 0, fo)
        end = min(len(y), off + len(w))
        y[off:end] += (w * fade)[: end - off]
    k = min(len(y), int(end_fade_ms / 1000 * SR))   # never stop dead: tiny natural release
    if k > 1:
        y[-k:] *= np.linspace(1, 0, k) ** 2
    return y.astype(np.float32)
