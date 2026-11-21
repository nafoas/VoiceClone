"""VocalTractLab's time-domain engine, driven by OUR bun mouth's tube (feasibility, 2026-11-21).

VocalTractLab (Birkholz) synthesizes speech from a tube (40 sections) that changes over time:
vtlSynthesisAddTube(n_samples, audio, lengths, areas, articulators, incisor_pos, velum_area,
tongue_tip_side_elevation, glottis_params). Its physics: time-domain acoustics with losses and yielding
walls, a vocal-fold model interacting with the tract, aerodynamics, turbulence noise sources placed by
articulator, the nose with sinuses, radiation. We hand it HIS tube instead of its human one.
"""
import ctypes
import os

import numpy as np
import vocaltractlab_cython as cy

_LIB = ctypes.CDLL(os.path.join(os.path.dirname(cy.__file__), "libVocalTractLabApi.so"))
_D = ctypes.POINTER(ctypes.c_double); _I = ctypes.POINTER(ctypes.c_int)
_LIB.vtlSynthesisReset.restype = ctypes.c_int
_LIB.vtlSynthesisAddTube.argtypes = [ctypes.c_int, _D, _D, _D, _I, ctypes.c_double, ctypes.c_double, ctypes.c_double, _D]
_LIB.vtlSynthesisAddTube.restype = ctypes.c_int
def use_speaker(path):
    """Load a speaker file (anatomy outside the tube: nose, larynx pockets, windpipe, vocal folds)."""
    from vocaltractlab_cython import VocalTractLabApi as _api
    _api._close(); _api._initialize(str(path))


C = cy.get_constants()
SR = C["sr_audio"]; NT = C["n_tube_sections"]; STEP = C["n_samples_per_state"]   # 44100 Hz, 40, 110 (2.5 ms)
TONGUE, INCISORS, LOWER_LIP, OTHER = 1, 2, 3, 4


def _p(a, t=ctypes.c_double):
    return np.ascontiguousarray(a, dtype=np.float64 if t is ctypes.c_double else np.int32).ctypes.data_as(ctypes.POINTER(t))


def synth(frames, glottis):
    """frames: list of dicts (lengths[40], areas[40], artic[40], incisor, velum, ts3), one per 2.5 ms;
    glottis: (F, 11) VocalTractLab glottis parameters per frame. Returns audio at 44.1 kHz."""
    _LIB.vtlSynthesisReset()
    out = []; buf = np.zeros(STEP)
    for k, (fr, g) in enumerate(zip(frames, glottis)):
        n = 0 if k == 0 else STEP
        L = np.ascontiguousarray(fr["lengths"], np.float64); A = np.ascontiguousarray(np.maximum(fr["areas"], 1e-4 if k == 0 else 0.0), np.float64)
        art = np.ascontiguousarray(fr["artic"], np.int32); gp = np.ascontiguousarray(g, np.float64)
        r = _LIB.vtlSynthesisAddTube(n, buf.ctypes.data_as(_D), L.ctypes.data_as(_D), A.ctypes.data_as(_D),
                                     art.ctypes.data_as(_I), float(fr["incisor"]), float(fr["velum"]), float(fr.get("ts3", 0.0)),
                                     gp.ctypes.data_as(_D))
        if r != 0:
            raise RuntimeError(f"vtlSynthesisAddTube returned {r}")
        if n:
            out.append(buf.copy())
    return np.concatenate(out) if out else np.zeros(0)
