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
OPTIONS = {}    # engine options set with set_options (our build), re-applied after every speaker load
OPT_DEFAULTS = dict(noise=True, turbulence=True, walls=True, skin=True, fossa=True, inner=False, transvelar=False)
if hasattr(_LIB, "vtlTdsSetOptions"):
    _LIB.vtlTdsSetOptions.argtypes = [ctypes.c_bool] * 7; _LIB.vtlTdsSetOptions.restype = ctypes.c_int


def set_options(**kw):
    """VocalTractLab's acoustic options (our build): noise sources, turbulence losses, soft walls, radiation
    from the skin, piriform fossa, inner length corrections, transvelar coupling. Persist until changed."""
    OPTIONS.update(kw); o = dict(OPT_DEFAULTS, **OPTIONS)
    _LIB.vtlTdsSetOptions(o["noise"], o["turbulence"], o["walls"], o["skin"], o["fossa"], o["inner"], o["transvelar"])


SIDE = [None]   # his side anatomy (windpipe, nose, sinuses, fossa), re-applied after every speaker load
if hasattr(_LIB, "vtlSetSideAnatomy"):
    _LIB.vtlSetSideAnatomy.argtypes = [ctypes.c_double, ctypes.c_double, _D, _D, ctypes.c_double, ctypes.c_double, ctypes.c_double]
    _LIB.vtlSetSideAnatomy.restype = ctypes.c_int


def set_side_anatomy(trachea_len, trachea_area, nose_len, nose_area, sinus_scale, fossa_len, fossa_vol):
    """His side parts (our engine build only). Without it VocalTractLab's tube carries HUMAN ones whatever
    the speaker file says: a 23 cm windpipe of 2.5-4 cm2, a human nose (0.8-4.2 cm2) with 57 cm3 of sinuses,
    a 3 cm piriform fossa. nose_len/nose_area: 19 sections from the velum to the nostrils."""
    if not hasattr(_LIB, "vtlSetSideAnatomy"):
        raise RuntimeError("vtlSetSideAnatomy needs our engine build (VTL_LIB=ours)")
    nl = np.ascontiguousarray(nose_len, np.float64); na = np.ascontiguousarray(nose_area, np.float64)
    assert len(nl) == 19 and len(na) == 19
    SIDE[0] = (float(trachea_len), float(trachea_area), nl, na, float(sinus_scale), float(fossa_len), float(fossa_vol))
    r = _LIB.vtlSetSideAnatomy(SIDE[0][0], SIDE[0][1], nl.ctypes.data_as(_D), na.ctypes.data_as(_D), *SIDE[0][4:])
    if r != 0:
        raise RuntimeError(f"vtlSetSideAnatomy returned {r}")


def use_speaker(path):
    """Load a speaker file (anatomy outside the tube: nose, larynx pockets, windpipe, vocal folds).
    Note: reloading leaks memory in the library; load once per process where possible."""
    if SPEAKER[0] is not None:
        _LIB.vtlClose()
    r = _LIB.vtlInitialize(str(path).encode())
    if r != 0:
        raise RuntimeError(f"vtlInitialize({path}) returned {r}")
    SPEAKER[0] = str(path)
    if SIDE[0] is not None:
        set_side_anatomy(*SIDE[0])
    if OPTIONS:
        set_options()
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
