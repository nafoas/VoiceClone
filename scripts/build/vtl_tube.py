"""VocalTractLab's time-domain engine, driven by OUR bun mouth's tube.

VocalTractLab (Birkholz) synthesizes speech from a tube (40 sections) that changes over time:
vtlSynthesisAddTube(n_samples, audio, lengths, areas, articulators, incisor_pos, velum_area,
tongue_tip_side_elevation, glottis_params). Its physics: time-domain acoustics with losses and yielding
walls, vocal folds interacting with the tract, aerodynamics, turbulence noise placed by articulator, the
nose with sinuses, radiation. We hand it HIS tube instead of its human one.

Which engine (roadmap Step 1): VTL_LIB=ours (default when built: engine/build/libVocalTractLabApi_bun.so,
our own build from engine/VocalTractLabBackend, where we change the physics) or VTL_LIB=installed (the
vocaltractlab_cython package's library, unmodified). Everything goes through the C API directly.
"""
import ctypes
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
_OURS = ROOT / "engine/build/libVocalTractLabApi_bun.so"


def _installed_path():
    import importlib.util
    spec = importlib.util.find_spec("vocaltractlab_cython")
    return Path(spec.origin).parent / "libVocalTractLabApi.so"


_which = os.environ.get("VTL_LIB", "ours" if _OURS.exists() else "installed")
LIB_PATH = _OURS if _which == "ours" else _installed_path()
_LIB = ctypes.CDLL(str(LIB_PATH))
_D = ctypes.POINTER(ctypes.c_double); _I = ctypes.POINTER(ctypes.c_int)
_LIB.vtlInitialize.argtypes = [ctypes.c_char_p]; _LIB.vtlInitialize.restype = ctypes.c_int
_LIB.vtlClose.restype = ctypes.c_int
_LIB.vtlGetConstants.argtypes = [_I, _I, _I, _I, _I, _D]; _LIB.vtlGetConstants.restype = ctypes.c_int
_LIB.vtlGetGlottisParams.argtypes = [ctypes.c_char_p, _D]; _LIB.vtlGetGlottisParams.restype = ctypes.c_int
_LIB.vtlSynthesisReset.restype = ctypes.c_int
_LIB.vtlSynthesisAddTube.argtypes = [ctypes.c_int, _D, _D, _D, _I, ctypes.c_double, ctypes.c_double, ctypes.c_double, _D]
_LIB.vtlSynthesisAddTube.restype = ctypes.c_int
TONGUE, INCISORS, LOWER_LIP, OTHER = 1, 2, 3, 4
SPEAKER = [None]


def use_speaker(path):
    """Load a speaker file (anatomy outside the tube: nose, larynx pockets, windpipe, vocal folds).
    Note: reloading leaks memory in the library; load once per process where possible."""
    if SPEAKER[0] is not None:
        _LIB.vtlClose()
    r = _LIB.vtlInitialize(str(path).encode())
    if r != 0:
        raise RuntimeError(f"vtlInitialize({path}) returned {r}")
    SPEAKER[0] = str(path)
    c = [ctypes.c_int() for _ in range(5)]; d = ctypes.c_double()
    _LIB.vtlGetConstants(*[ctypes.byref(q) for q in c], ctypes.byref(d))
    global SR, NT, NTRACT, NGLOT, STEP
    SR, NT, NTRACT, NGLOT, STEP = (q.value for q in c)


use_speaker(os.environ.get("VTL_SPEAKER", str(ROOT / "models/bun.speaker")))


def glottis_shape(name="modal"):
    """A named vocal-fold setting from the loaded speaker file."""
    g = np.zeros(NGLOT)
    if _LIB.vtlGetGlottisParams(name.encode(), g.ctypes.data_as(_D)) != 0:
        raise KeyError(name)
    return g


def synth(frames, glottis):
    """frames: list of dicts (lengths[40], areas[40], artic[40], incisor, velum, ts3), one per 2.5 ms;
    glottis: (F, n) glottis parameters per frame. Returns audio at SR (44.1 kHz)."""
    _LIB.vtlSynthesisReset()
    out = []; buf = np.zeros(STEP)
    for k, (fr, g) in enumerate(zip(frames, glottis)):
        n = 0 if k == 0 else STEP
        L = np.ascontiguousarray(fr["lengths"], np.float64)
        A = np.ascontiguousarray(np.maximum(fr["areas"], 1e-4 if k == 0 else 0.0), np.float64)
        art = np.ascontiguousarray(fr["artic"], np.int32); gp = np.ascontiguousarray(g, np.float64)
        r = _LIB.vtlSynthesisAddTube(n, buf.ctypes.data_as(_D), L.ctypes.data_as(_D), A.ctypes.data_as(_D),
                                     art.ctypes.data_as(_I), float(fr["incisor"]), float(fr["velum"]), float(fr.get("ts3", 0.0)),
                                     gp.ctypes.data_as(_D))
        if r != 0:
            raise RuntimeError(f"vtlSynthesisAddTube returned {r}")
        if n:
            out.append(buf.copy())
    return np.concatenate(out) if out else np.zeros(0)
