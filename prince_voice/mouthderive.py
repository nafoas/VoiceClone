"""Use his mouth on his own sounds.

A new sound = one of his real sounds x |H(new shape)|^2 / |H(the shape fitted to
that real sound)|^2. The tube model only supplies the CHANGE between two nearby
mouth shapes; his recording supplies everything else (hum, purity, texture,
movement), and the model's own absolute error cancels in the ratio.

    derive_by_mouth(cat, "ɑ", "ã", shape)    a vowel he never said
    mouth_edge(steady, k, "ɑ", "lab", ...)   lips opening into a vowel
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .mouth import Mouth

ROOT = Path(__file__).resolve().parents[1]
FIT_PATH = ROOT / "models" / "mouth_fit.json"
SR = 24000
MAX_DB = 24.0          # the model is trusted for moderate changes only
TOP_HZ = (5000.0, 7000.0)   # above this, his recording is kept unchanged

SHAPES: dict[str, np.ndarray] = {}


@lru_cache(maxsize=1)
def mouth() -> Mouth:
    fit = json.loads(FIT_PATH.read_text())
    m = Mouth(scale=fit["scale"])
    for ph, d in fit["vowels"].items():
        SHAPES.setdefault(ph, np.array(d["params"], float))
    return m


def shape(ph: str) -> np.ndarray | None:
    mouth()
    s = SHAPES.get(ph)
    return None if s is None else s.copy()


def gain_ln(new: np.ndarray, base: np.ndarray, nb: int) -> np.ndarray:
    """Natural-log POWER gain on WORLD's nb bins (0..SR/2)."""
    m = mouth()
    hz = np.linspace(0, SR / 2, nb)
    hn = np.abs(m.response(new, hz, radiate=False)) ** 2
    hb = np.abs(m.response(base, hz, radiate=False)) ** 2
    g = 10 * np.log10((hn + 1e-20) / (hb + 1e-20))
    g = np.clip(g, -MAX_DB, MAX_DB)
    fade = np.clip((TOP_HZ[1] - hz) / (TOP_HZ[1] - TOP_HZ[0]), 0, 1)
    return g * fade * np.log(10) / 10


def derive_by_mouth(cat, new: str, base: str, new_shape: np.ndarray) -> None:
    """Like derive_vowel, but the change is a physical mouth movement."""
    if base not in cat.inst or new in cat.inst:
        return
    b = shape(base)
    insts = []
    for c in cat.inst[base]:
        d = dict(c)
        for key in ("sp", "L", "R", "TL", "TR", "tail"):
            if key in d:
                g = gain_ln(new_shape, b, d[key].shape[-1])
                d[key] = d[key] + g
        insts.append(d)
    cat.inst[new] = insts
    g = gain_ln(new_shape, b, cat.sp[base].shape[-1])
    cat.sp[new] = cat.sp[base] * np.exp(g) if cat.sp[base].min() >= 0 else cat.sp[base] + g
    for table in (cat.ap, cat.voiced, cat.dynamic, cat.f0_ref):
        if base in table:
            table[new] = table[base]
    from . import bnuysynth
    bnuysynth._F.setdefault(new, bnuysynth._F.get(base, [0] * 15))
    SHAPES[new] = np.array(new_shape, float)


def closed_shape(ph: str, place: str, opening: float) -> np.ndarray:
    """The vowel's shape with the consonant's articulator `opening` (0 = closed
    at the consonant, 1 = the vowel). Lips: lip distance (and some jaw); tongue
    tip: tip raised toward the ridge."""
    m = mouth(); v = shape(ph)
    p = v.copy()
    if place == "lab":
        cl = m.shape("ll-labial-closure(a)")
        for n in ("LD", "LP"):
            i = m.names.index(n); p[i] = cl[i] + opening * (v[i] - cl[i])
        i = m.names.index("JA"); p[i] = v[i] + (1 - opening) * 0.5 * (cl[i] - v[i])
    elif place == "cor":
        cl = m.shape("tt-alveolar-closure(a)")
        for n in ("TTX", "TTY", "TBX", "TBY"):
            i = m.names.index(n); p[i] = cl[i] + opening * (v[i] - cl[i])
    return p


def mouth_edge(steady_ln: np.ndarray, k: int, ph: str, place: str, toward_start: bool,
               start_open: float = 0.15) -> np.ndarray:
    """k frames of a vowel edge next to a consonant: his steady vowel frame,
    reshaped by the mouth moving from (nearly) closed at the consonant to the
    vowel. Loudness follows the mouth, softened (the murmur/burst already
    carries the closure)."""
    v = shape(ph)
    out = np.empty((k, steady_ln.shape[-1]))
    for j in range(k):
        x = (j + 1) / (k + 1) if toward_start else (k - j) / (k + 1)
        x = x * x * (3 - 2 * x)
        op = start_open + (1 - start_open) * x
        g = gain_ln(closed_shape(ph, place, op), v, steady_ln.shape[-1])
        # keep the spectral SHAPE change, but only half of the overall level drop
        lvl = np.log(np.exp(steady_ln + g).sum() / np.exp(steady_ln).sum())
        out[j] = steady_ln + g - 0.5 * lvl
    return out
