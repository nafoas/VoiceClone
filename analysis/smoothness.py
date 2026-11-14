"""How smooth (hummy) vs. choppy a recording is, frame to frame.

    python analysis/smoothness.py file.wav [...]

spec_flux   median change of the 0-5 kHz log spectrum between 5 ms frames (dB)
flux_p95    the biggest jumps (95th percentile): join clicks / sudden changes
loud_jump   median frame-to-frame loudness change (dB)
loud_p95    the biggest loudness jumps
"""
import sys

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import resample_poly


def frames(path, sr_out=24000):
    a, sr = sf.read(path)
    if a.ndim > 1:
        a = a.mean(1)
    if sr != sr_out:
        a = resample_poly(a, sr_out, sr)
    a = a.astype(np.float64)
    f0, t = pw.harvest(a, sr_out, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(a, f0, t, sr_out)
    fq = np.linspace(0, sr_out / 2, sp.shape[1])
    L = 10 * np.log10(sp[:, fq < 5000] + 1e-20)
    e = 10 * np.log10(sp.sum(1) + 1e-20)
    active = e > e.max() - 30
    return L, e, active


def smoothness(path):
    L, e, act = frames(path)
    both = act[1:] & act[:-1]
    flux = np.sqrt(np.mean(np.diff(L, axis=0) ** 2, axis=1))[both]
    loud = np.abs(np.diff(e))[both]
    return dict(spec_flux=np.median(flux), flux_p95=np.percentile(flux, 95),
                loud_jump=np.median(loud), loud_p95=np.percentile(loud, 95))


if __name__ == "__main__":
    print(f"{'':34} spec_flux  flux_p95  loud_jump  loud_p95")
    for p in sys.argv[1:]:
        s = smoothness(p)
        print(f"{p[-34:]:34} {s['spec_flux']:8.2f} {s['flux_p95']:9.2f} {s['loud_jump']:10.2f} {s['loud_p95']:9.2f}")
