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


def irs(M, Z):
    """The mouth's response for each noise source, from the fitted mouth."""
    B = M.B; f = np.maximum(fH, 1.0); M.body(Z)
    bf = B.head_baffle(f, Z[1]); out = {}
    cap = lambda a: 1 / (1 + (f / (1.84 * 35000 / (np.pi * 2 * np.sqrt(a.max() / np.pi)))) ** 8)   # plane-wave limit
    a, L, frac, port = M.area_of(Z, M.pose_full(Z, "iː"))
    k = int(np.argmin(a[len(a) // 2:])) + len(a) // 2                 # tongue front against the palate
    out["fric"] = _ir(B.tube_H_from(a, L, f, k + 1) * bf * cap(a) * turb(f, a[k]))
    out["asp"] = _ir(B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * bf * cap(a) * turb(f, 0.02))   # breath at the cords
    pn = M.pose_full(Z, "n").copy(); pn[7] = 0.0
    a2, L2, _, _ = M.area_of(Z, pn)
    k2 = int(np.argmin(a2[len(a2) // 2:])) + len(a2) // 2
    a2o = a2.copy(); a2o[k2] = max(a2o[k2], 0.01)                    # the tip just letting go: a narrow gap at the ridge
    out["burst_t"] = _ir(B.tube_H_from(a2o, L2, f, k2 + 1) * bf * cap(a2o) * turb(f, 0.01))   # hiss through it
    out["burst_p"] = _ir(B.tube_H_from(a, L, f, len(a) - 1) * bf * cap(a) * turb(f, 0.05))   # at the lips
    out["asp_p"] = _ir(B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * bf * cap(a) * turb(f, 0.3))   # weak p: breath, lips opening wide
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
            parts = [(s - 0.003, s + 0.03, "fric"), (s + 0.03, b, "asp")]   # before "ee" the blade lets go at the front palate: hiss (~30 ms), then breath
        else:
            parts = [(s + 0.01, b, "asp_p")]   # his p is weak: breath through the opening lips, barely a burst
        for pa, pb, kind in parts:   # each part's airflow set on its own, over its own stretch of time
            i0, i1 = max(0, int((pa - s0) * SR)), min(n, int((pb - s0) * SR))
            if i1 <= i0:
                continue
            src = rng.standard_normal(i1 - i0)
            L_ = i1 - i0; fade = np.minimum(1, np.minimum(np.arange(L_), np.arange(L_)[::-1]) / (0.003 * SR))

            def through_mouth(gain):
                """The noise source (scaled by how hard the air blows: at the SOURCE) through his mouth."""
                out = np.zeros(n + NFT); o = np.convolve(src * gain, R[kind]); out[i0: i0 + len(o)] += o[: len(out) - i0]
                return out
            seg = through_mouth(fade)
            # how hard the air blows: set (provisionally) so the result matches his loudness over this part
            hb = _band(x[int(s0 * SR) + i0: int(s0 * SR) + i1]) * kk; mb = _band(seg[i0:i1])
            sm = lambda q: np.convolve(q ** 2, np.hanning(4 * hop) / np.hanning(4 * hop).sum(), mode="same")   # ~20 ms
            eh, em = sm(hb), sm(mb)
            g = np.sqrt(eh / np.maximum(em, 1e-2 * em.max()))               # never divide by a near-silent edge
            y += through_mouth(fade * g)
    return y[:n]
