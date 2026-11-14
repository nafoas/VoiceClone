"""Frame transplant: rebuild speech out of Prince's *real* sound.

For every 5 ms frame of the planned speech, pick a frame from the reference
clip whose spectral shape is closest, preferring to keep reading consecutive
reference frames (so his real transitions, the "joiner", come through). The
chosen frames' spectral envelope and aperiodicity replace the TTS ones; timing
and pitch stay as planned.

Selection is a Viterbi search (unit selection at frame level):
    cost = spectral distance to the planned frame
         + jump_cost when not continuing to the next reference frame
         + hold_cost when repeating the same reference frame
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.fft import dct
from scipy.signal import resample_poly

DEFAULT_REF = Path(__file__).resolve().parents[1] / "reference" / "source" / "prince_reference.wav"
N_CEP = 24


def _cep(sp: np.ndarray) -> np.ndarray:
    c = dct(np.log(sp + 1e-12), type=2, norm="ortho", axis=1)[:, 1:N_CEP + 1]
    return c * np.linspace(1.0, 0.6, N_CEP)[None, :]   # light liftering


@lru_cache(maxsize=4)
def load_reference(path: str, fs: int, frame_ms: float):
    a, sr = sf.read(path, dtype="float64")
    if a.ndim > 1:
        a = a.mean(1)
    if sr != fs:
        from math import gcd
        g = gcd(sr, fs)
        a = resample_poly(a, fs // g, sr // g)
    f0, t = pw.harvest(a, fs, frame_period=frame_ms, f0_floor=60, f0_ceil=900)
    sp = pw.cheaptrick(a, f0, t, fs)
    ap = pw.d4c(a, f0, t, fs)
    energy = sp.sum(1)
    keep = 10 * np.log10(energy + 1e-20) > 10 * np.log10(energy.max()) - 35
    idx = np.where(keep)[0]
    return dict(sp=sp[idx], ap=ap[idx], voiced=(f0[idx] > 0), energy=energy[idx],
                cep=_cep(sp[idx]), nxt=np.r_[(np.diff(idx) == 1), False])


def select(q_cep: np.ndarray, q_voiced: np.ndarray, ref: dict,
           jump_cost: float, hold_cost: float) -> np.ndarray:
    """Viterbi over reference frames. Returns ref index per query frame."""
    R = ref["cep"]
    T, N = len(q_cep), len(R)
    D = np.sqrt(((q_cep[:, None, :] - R[None, :, :]) ** 2).sum(-1))
    D /= np.median(D) + 1e-9
    D = D + np.where(q_voiced[:, None] != ref["voiced"][None, :], 3.0, 0.0)
    cont = ref["nxt"]                       # frame j-1 -> j is a real continuation
    cost = D[0].copy()
    back = np.zeros((T, N), dtype=np.int32)
    ar = np.arange(N)
    for t in range(1, T):
        best_i = int(np.argmin(cost))
        c_jump = cost[best_i] + jump_cost
        c_hold = cost + hold_cost
        c_next = np.full(N, np.inf)
        c_next[1:] = np.where(cont[:-1], cost[:-1], np.inf)
        stack = np.stack([np.full(N, c_jump), c_hold, c_next])
        choice = np.argmin(stack, axis=0)
        prev = np.where(choice == 0, best_i, np.where(choice == 1, ar, ar - 1))
        cost = stack[choice, ar] + D[t]
        back[t] = prev
    path = np.zeros(T, dtype=np.int32)
    path[-1] = int(np.argmin(cost))
    for t in range(T - 1, 0, -1):
        path[t - 1] = back[t, path[t]]
    return path


def transplant(sp: np.ndarray, ap: np.ndarray, f0: np.ndarray, fs: int, frame_ms: float,
               amount: float = 1.0, ref_path: str | None = None,
               jump_cost: float = 0.6, hold_cost: float = 0.15,
               keep_unvoiced: bool = True, smooth: int = 3):
    """Replace envelope/aperiodicity with Prince's real frames (amount 0..1)."""
    if amount <= 0:
        return sp, ap
    ref = load_reference(str(ref_path or DEFAULT_REF), fs, frame_ms)
    voiced = f0 > 0
    energy = sp.sum(1)
    active = 10 * np.log10(energy + 1e-20) > 10 * np.log10(energy.max() + 1e-20) - 45
    path = select(_cep(sp), voiced, ref, jump_cost, hold_cost)

    new_sp = ref["sp"][path] * (energy / ref["energy"][path])[:, None]
    new_ap = ref["ap"][path]
    if smooth > 1:
        k = np.ones(smooth) / smooth
        lg = np.log(new_sp + 1e-20)
        lg = np.apply_along_axis(lambda c: np.convolve(np.pad(c, smooth // 2, mode="edge"), k, "valid"), 0, lg)
        new_sp = np.exp(lg)
    use = active & (voiced | ~keep_unvoiced)
    m = amount * use[:, None]
    out_sp = np.exp((1 - m) * np.log(sp + 1e-20) + m * np.log(new_sp + 1e-20))
    out_ap = (1 - m) * ap + m * new_ap
    return out_sp, out_ap
