"""His consonants (provisional, Da Boss: "reconstruct the whole thing with consonants" to test
whether their absence is what sounds babyish and choppy). Made by the same mouth:

  soft s (ɕ): turbulent noise where the tongue front is squeezed against the palate, shaped by the
              small part of the mouth in front of it (the "ee" tongue position)
  t (tʰ):     a short burst where the tongue tip lets go at the ridge, then breath noise from the
              vocal cords through the mouth as it opens toward the vowel
  p:          a short burst at the lips, then breath through the opening mouth (his p is weak)

PROVISIONAL: how hard the air blows through each gap over time is set so the result matches the
clip's loudness (as the voice's breath still is until the effort step). It scales the noise SOURCE,
before the mouth; nothing is done to the sound after it. The noise is a fixed seeded source.
"""
import numpy as np

SR = 48000; NFT = 4096
fH = np.fft.rfftfreq(NFT, 1 / SR)


def _ir(H):
    H = np.asarray(H, complex).copy(); H[0] = 0
    h = np.fft.irfft(H, NFT); h *= np.r_[np.ones(NFT // 2), np.hanning(NFT)[NFT // 2:]]
    return h


def turb(f, area_cm2):
    """Turbulence noise spectrum: strong up to the Strouhal frequency St*v/d of the jet through a
    gap of width d at the speed v the lung pressure gives, falling above it."""
    v = np.sqrt(2 * 8000.0 / 1.14e-3)                 # cm/s, soft-voice lung pressure (as the cord gap)
    d = 2 * np.sqrt(max(area_cm2, 1e-4) / np.pi)
    fs = 0.2 * v / d
    return 1 / (1 + 1j * f / fs) ** 2          # falls ~12 dB per octave above it


# Each consonant, physically: where the air is squeezed (place: fraction of the tube from the vocal folds,
# ~0.95 = teeth/ridge, 1.0 = lips), how narrow the gap is (area, cm^2: sets the hiss's pitch), how open the
# lips are then (factor on the last sections), and how long the burst lasts before breath takes over.
CP = dict(s_place=0.80, s_area=0.013, s_lips=1.0,
          t_place=0.80, t_area=0.013, t_lips=1.0, t_burst=0.033,
          p_area=0.3, p_lips=1.0, p_burst=0.0)


def _squeezed(a, place, area, lips):
    """The base tube with a gap of `area` at `place` and the lips scaled; returns (areas, source index)."""
    a = a.copy(); n = len(a); k = int(np.clip(round(place * n), 1, n - 1))
    a[k - 1: k + 1] = np.minimum(a[k - 1: k + 1], area)
    a[-2:] = a[-2:] * lips
    return a, k


def irs(M, Z):
    """The mouth's response for each noise source, from the fitted mouth and the consonant settings CP."""
    B = M.B; f = np.maximum(fH, 1.0); M.body(Z)
    bf = B.head_baffle(f, Z[1]); out = {}
    cap = lambda a: 1 / (1 + (f / (1.84 * 35000 / (np.pi * 2 * np.sqrt(a.max() / np.pi)))) ** 8)   # plane-wave limit
    a, L, frac, port = M.area_of(Z, M.pose_full(Z, "iː"))
    as_, ks = _squeezed(a, CP["s_place"], CP["s_area"], CP["s_lips"])
    out["fric"] = _ir(B.tube_H_from(as_, L, f, ks + 1) * bf * cap(as_) * turb(f, CP["s_area"]))
    at_, kt = _squeezed(a, CP["t_place"], CP["t_area"], CP["t_lips"])
    out["burst_t"] = _ir(B.tube_H_from(at_, L, f, kt + 1) * bf * cap(at_) * turb(f, CP["t_area"]))
    out["asp"] = _ir(B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * bf * cap(a) * turb(f, 0.02))   # breath at the cords
    ap = a.copy(); ap[-2:] *= CP["p_lips"]
    out["burst_p"] = _ir(B.tube_H_from(ap, L, f, len(a) - 1) * bf * cap(ap) * turb(f, 0.05))   # at the lips
    out["asp_p"] = _ir(B.tube_H_nose(ap, L, f, frac, port, Z[6], Z[7]) * bf * cap(ap) * turb(f, CP["p_area"]))
    return out


# GEST (2026-11-20): the noises go through the mouth AS IT MOVES (the stop gestures in render_his), every
# 2 ms: the burst is made at the opening gap itself (the tip at the ridge, or the lips), so it starts as the
# tiny cavity in front of the gap and grows into the whole mouth as the gap widens; the breath after it is
# made at the vocal cords. Before, every noise went through one fixed "ee" mouth.
# Tested and dropped: cords spread wide for the breath (0.05-0.1 cm^2) - his release spectra, the "t" and
# naturalness all fit better with the cords as in his voice (t-ee 7.0/7.8 dB vs 7.7/8.0).
POSES = None       # (positions every hop, start time, hop) from render_his.render_phrase
ONSETS = None      # where the voice starts in this phrase (render_his): the cords close to buzz, the breath hiss stops
_TV = {}


def _tv_ir(M, Z, kind, pose, f, bf):
    key = (kind, tuple(np.round(pose, 3)))
    if key in _TV:
        return _TV[key]
    B = M.B; a, L, frac, port = M.area_of(Z, pose)
    if pose[5] < 0.04:
        a = M.seal(a, "m")
    cap = 1 / (1 + (f / (1.84 * 35000 / (np.pi * 2 * np.sqrt(a.max() / np.pi)))) ** 8)
    n = len(a); kf = int(0.8 * n)
    if kind in ("burst_t",):            # at the tongue tip's gap
        k = kf + int(np.argmin(a[kf:-2])); H = B.tube_H_from(a, L, f, k + 1) * turb(f, max(a[k], 0.002))
    elif kind == "burst_p":             # at the lips (his weak p: the source as fitted before, 0.05)
        H = B.tube_H_from(a, L, f, n - 1) * turb(f, 0.05)
    elif kind == "asp_p":               # his weak, voiced p: the cords are NOT spread (the split lip leaks, little
        H = B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * turb(f, CP["p_area"])   # pressure); the wide lip jet's hiss
    elif kind == "fric":                # the tongue front squeezed toward the palate
        as_, ks = _squeezed(a, CP["s_place"], CP["s_area"], CP["s_lips"]); a = as_
        H = B.tube_H_from(as_, L, f, ks + 1) * turb(f, CP["s_area"])
    else:                               # breath at the cords (the t's "asp"), through the mouth as it opens
        H = B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * turb(f, 0.02)
    if len(_TV) > 4000:
        _TV.clear()
    _TV[key] = _ir(H * bf * cap)
    return _TV[key]


def _through_moving_mouth(src, i0, kind, M, Z, n):
    """src (starting at phrase sample i0) through the mouth's position at each moment (2 ms frames)."""
    P, ps0, phop = POSES; f = np.maximum(fH, 1.0); bf = M.B.head_baffle(f, Z[1])
    hp = 96; win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(2 * hp) / (2 * hp))   # sums to 1 at 50% overlap
    out = np.zeros(n + NFT)
    for c in range(-hp, len(src), hp):
        a_, b_ = max(c, 0), min(c + 2 * hp, len(src))
        if b_ <= a_:
            continue
        seg = src[a_:b_] * win[a_ - c: b_ - c]
        kpos = min(len(P) - 1, max(0, int(round((i0 + c + hp) / phop))))
        o = np.convolve(seg, _tv_ir(M, Z, kind, P[kpos], f, bf)); st = i0 + a_
        out[st: st + len(o)] += o[: len(out) - st]
    return out


def _band(sig, lo=1000.0):
    S = np.fft.rfft(sig); f = np.fft.rfftfreq(len(sig), 1 / SR); S[f < lo] = 0
    return np.fft.irfft(S, len(sig))


def layer(ph, s0, n, x, M, Z, ref, seed=7):
    """The consonant noises of one phrase, as sound at the lips (length n). ref: the phrase's
    voiced sound, so each consonant keeps his loudness relative to his vowels."""
    R = irs(M, Z); y = np.zeros(n + NFT); rng = np.random.default_rng(seed)
    vo = [(s, e) for l, s, e, _ in ph if l in M.SOUNDS]
    kk = np.sqrt(np.mean(np.concatenate([ref[int((s - s0) * SR): int((e - s0) * SR)] for s, e in vo]) ** 2) /
                 np.mean(np.concatenate([x[int(s * SR): int(e * SR)] for s, e in vo]) ** 2))
    hop = 240; win = np.hanning(2 * hop)
    for lab, s, e, _ in ph:
        if lab not in ("ɕ", "tʰ", "p"):
            continue
        a, b = s - 0.005, e + 0.01
        if lab == "ɕ":
            parts = [(a, b, "fric")]
        elif lab == "tʰ":
            parts = [(s - 0.003, s + CP["t_burst"], "burst_t"), (s + CP["t_burst"], b, "asp")]   # release hiss, then breath
        else:
            parts = ([(s + 0.01, s + 0.01 + CP["p_burst"], "burst_p")] if CP["p_burst"] > 0.002 else []) + [(s + 0.01 + CP["p_burst"], b, "asp_p")]   # his weak p
        if ONSETS is not None and getattr(M, "GEST", False):   # breath ends where the voice begins
            von = [q for q in ONSETS if q > s + 0.003]
            if von:
                parts = [(pa, min(pb, von[0] + 0.003) if k_ in ("asp", "asp_p") else pb, k_) for pa, pb, k_ in parts]
        for pa, pb, kind in parts:   # each part's airflow set on its own, over its own stretch of time
            i0, i1 = max(0, int((pa - s0) * SR)), min(n, int((pb - s0) * SR))
            if i1 <= i0:
                continue
            src = rng.standard_normal(i1 - i0)
            L_ = i1 - i0; fade = np.minimum(1, np.minimum(np.arange(L_), np.arange(L_)[::-1]) / (0.003 * SR))

            def through_mouth(gain):
                """The noise source (scaled by how hard the air blows: at the SOURCE) through his mouth."""
                if POSES is not None and getattr(M, "GEST", False):
                    return _through_moving_mouth(src * gain, i0, kind, M, Z, n)
                out = np.zeros(n + NFT); o = np.convolve(src * gain, R[kind]); out[i0: i0 + len(o)] += o[: len(out) - i0]
                return out
            seg = through_mouth(fade)
            # how hard the air blows: set (provisionally) so the result matches his loudness over this part
            hb = _band(x[int(s0 * SR) + i0: int(s0 * SR) + i1]) * kk; mb = _band(seg[i0:i1])
            _k = np.hanning(max(3, min(4 * hop, L_ - 1))); _k /= _k.sum()
            sm = lambda q: np.convolve(q ** 2, _k, mode="same")   # ~20 ms (shorter for short parts)
            eh, em = sm(hb), sm(mb)
            g = np.sqrt(eh / np.maximum(em, 1e-2 * em.max()))               # never divide by a near-silent edge
            y += through_mouth(fade * g)
    return y[:n]
