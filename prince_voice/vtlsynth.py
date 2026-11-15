"""Voice his bun mouth with VocalTractLab's time-domain physical simulation.

VocalTractLab's synthesizer (Birkholz) simulates the air in the tube over time:
a glottis model (geometric glottis: two moving folds, real airflow, natural
pitch flutter, aspiration), the tract as a branched tube with losses, noise
generated wherever the air is squeezed, and the voice and mouth interacting.
We feed it OUR tube: the bun mouth's area function (resampled to its 40
sections), so the anatomy stays his and the physics is a validated engine.

    from prince_voice.vtlsynth import synth_tubes
"""
from __future__ import annotations

import ctypes
from pathlib import Path

import numpy as np

import vocaltractlab_cython as cy   # initializes the API (default speaker)

_LIB = ctypes.CDLL(str(Path(cy.__file__).parent / "libVocalTractLabApi.so"))
_C = cy.get_constants()
SR = int(_C["sr_audio"]); NSEC = int(_C["n_tube_sections"]); NGP = int(_C["n_glottis_params"])
FRAME = 220                                      # samples per 5 ms state (at 44.1 kHz)
D = ctypes.POINTER(ctypes.c_double); I = ctypes.POINTER(ctypes.c_int)
_LIB.vtlSynthesisAddTube.argtypes = [ctypes.c_int, D, D, D, I, ctypes.c_double, ctypes.c_double, ctypes.c_double, D]
GLOTTIS_NAMES = [p["name"] for p in cy.get_param_info("glottis")]


def glottis(**kw):
    g = np.array(cy.get_shape("modal", "glottis"), float)
    for k, v in kw.items():
        g[GLOTTIS_NAMES.index(k)] = v
    return g


def to40(area, length, incisor_frac=0.93, lip_frac=0.97):
    """Our area function (any number of sections) -> 40 equal sections."""
    edges = np.r_[0, np.cumsum(length)]; L = edges[-1]
    e40 = np.linspace(0, L, NSEC + 1)
    a40 = np.empty(NSEC)
    for i in range(NSEC):   # length-weighted mean area over each new section
        lo, hi = e40[i], e40[i + 1]
        ov = np.clip(np.minimum(edges[1:], hi) - np.maximum(edges[:-1], lo), 0, None)
        a40[i] = float(np.sum(ov * area) / max(ov.sum(), 1e-9))
    l40 = np.full(NSEC, L / NSEC)
    art = np.full(NSEC, 1, np.int32)              # tongue along the floor
    pos = (np.arange(NSEC) + 0.5) / NSEC
    art[pos < 0.35] = 4                           # throat: other
    art[(pos >= incisor_frac) & (pos < lip_frac)] = 2
    art[pos >= lip_frac] = 3                      # lips
    return a40, l40, art, incisor_frac * L


def synth_tubes(tubes, glottis_frames):
    """tubes: list of (area40, length40, articulators, incisor_cm, velum_cm2) per 5 ms;
    glottis_frames: list of glottis parameter vectors. Returns audio at 44.1 kHz."""
    _LIB.vtlSynthesisReset()
    out = []
    for k, ((a, l, art, inc, vel), g) in enumerate(zip(tubes, glottis_frames)):
        a = np.ascontiguousarray(np.maximum(a, 1e-4), float); l = np.ascontiguousarray(l, float)
        art = np.ascontiguousarray(art, np.int32); g = np.ascontiguousarray(g, float)
        n = 0 if k == 0 else FRAME
        buf = np.zeros(max(n, 1), float)
        r = _LIB.vtlSynthesisAddTube(n, buf.ctypes.data_as(D), l.ctypes.data_as(D), a.ctypes.data_as(D),
                                     art.ctypes.data_as(I), float(inc), float(vel), 0.0, g.ctypes.data_as(D))
        if r != 0:
            raise RuntimeError(f"vtlSynthesisAddTube returned {r}")
        if n:
            out.append(buf[:n].copy())
    return np.concatenate(out) if out else np.zeros(0)


def bun_tube(m, pose):
    """The bun mouth's tube for a pose, as VTL wants it."""
    area, length, port, br = m.tube(pose)
    a40, l40, art, inc = to40(area, length)
    return a40, l40, art, inc, float(port)
