"""Probe VocalTractLab's mouth on its own (no vocal folds): a pressure pulse just above the folds, the sound
leaving lips, nostrils and skin recorded step by step (vtlTdsSetTubeAndRun, our engine build). Used to
see what the engine's walls and losses do to his tube's resonances (roadmap Step 2/3)."""
import ctypes

import numpy as np

import vtl_tube as V

NS = 93; NB = NS + 4; FIRST_PHARYNX = 25
_D = ctypes.POINTER(ctypes.c_double); _I = ctypes.POINTER(ctypes.c_int)
L = V._LIB
L.vtlTdsResetMotion.restype = ctypes.c_int
L.vtlTdsSetTubeAndRun.argtypes = [_D, _D, _I, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_bool,
                                  ctypes.c_int, ctypes.c_double] + [_D] * 14
L.vtlTdsSetTubeAndRun.restype = ctypes.c_int


def set_options(**kw):   # for this probe only: on top of the session's options, undone afterwards
    o = dict(V.OPT_DEFAULTS, **V.OPTIONS); o.update(kw)
    L.vtlTdsSetOptions(o["noise"], o["turbulence"], o["walls"], o["skin"], o["fossa"], o["inner"], o["transvelar"])


def impulse_response(frame, n=8192, amp=1000.0, **opts):
    set_options(noise=False, **opts)
    L.vtlTdsResetMotion()
    lengths = np.ascontiguousarray(frame["lengths"], np.float64); areas = np.ascontiguousarray(np.maximum(frame["areas"], 1e-4), np.float64)
    art = np.ascontiguousarray(frame["artic"], np.int32)
    bufs = [np.zeros(NS) for _ in range(11)] + [np.zeros(NB)]
    m, nz, sk = ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
    flow = np.zeros(n)
    for k in range(n):
        L.vtlTdsSetTubeAndRun(lengths.ctypes.data_as(_D), areas.ctypes.data_as(_D), art.ctypes.data_as(_I),
                              float(frame["incisor"]), float(frame["velum"]), float(frame.get("ts3", 0.0)), False,
                              FIRST_PHARYNX, amp if k == 0 else 0.0, *[b.ctypes.data_as(_D) for b in bufs],
                              ctypes.byref(m), ctypes.byref(nz), ctypes.byref(sk))
        flow[k] = m.value + nz.value + sk.value
    V.set_options()   # back to the session's options
    return np.diff(flow, prepend=0.0)   # radiated sound ~ d/dt of the flow leaving him
