"""How his mouth moves between sounds (PLAN step 5, pulled into the foundation).

Each articulator glides from one sound's position to the next with a smooth (raised-
cosine) step. Per boundary between two voiced sounds, fitted to the clip:
  centre  when the glide happens (relative to the label boundary)
  width   how long it takes
  lips    how far the lips lead or lag the rest
  velum   how far the soft palate (nose opening) leads or lags the rest
Judged frame by frame (every 5 ms within 60 ms of the boundary): his spectrum shape
(third-octave bands) vs the model's, predicted from his voice's tones and the mouth's
shape at that instant. Mouth movement only; nothing is done to the sound.

    ZFILE=models/mouth_inverse_H3.json python scripts/build/transitions.py -> models/transitions{TAG}.json
"""
import json, os, sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.fft import idct
from scipy.optimize import least_squares

os.environ.setdefault("SRC", "his"); os.environ.setdefault("NH", "40")
ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "scripts", ROOT / "scripts/build", ROOT / "analysis/physics"):
    sys.path.insert(0, str(p))
sys.argv = sys.argv[:1]
import mouth_inverse as M  # noqa: E402
from build_catalogue import PHRASES  # noqa: E402

SR = 48000
Z = np.array(json.loads((ROOT / os.environ.get("ZFILE", "models/mouth_inverse_H3.json")).read_text())["z"])
TAG = os.environ.get("TAG", "")
EDGES = 200 * 2 ** (np.arange(0, 19) / 3); EDGES = EDGES[EDGES <= 12800]
LIPS, VELUM = 5, 7
LO = np.array([-0.03, 0.008, -0.03, -0.04]); HI = np.array([0.03, 0.08, 0.03, 0.04]); X0 = np.array([0.0, 0.03, 0.0, 0.0])
HIS = M.his_voice_tones(nh=60)
_H = {}


def mouth_mag(pose9, f):
    key = (tuple(np.round(pose9, 2)), round(float(f[0]), 1), len(f))
    if key not in _H:
        a0, L, frac, port = M.tube(pose9, Z[0], Z[M.SH["lar"]])
        a = a0 * np.exp(idct(np.r_[Z[M.SH["shape"]], np.zeros(M.NS - M.NF)], norm="ortho"))
        if pose9[LIPS] < 0.04:
            a = M.seal(a, "m")
        M.B.NOSE_SURF = float(Z[M.NV]) if len(Z) > M.NV else 1.0
        fc = 1.84 * 35000 / (np.pi * 2 * np.sqrt(a.max() / np.pi))
        H = M.B.tube_H_nose(a, L, f, frac, port, Z[6], Z[7]) * M.B.head_baffle(f, Z[1]) / (1 + (f / fc) ** 8)
        _H[key] = np.abs(H)
    return _H[key]


def step(u):
    u = np.clip(u + 0.5, 0, 1); return 0.5 - 0.5 * np.cos(np.pi * u)


def pose_at(t, vs, bnd, par):
    """Articulator positions at time t: first sound's position + each boundary's smooth step."""
    P = Z[M.PO[vs[0]["lab"]]].copy()
    for b, (i, tb) in enumerate(bnd):
        c, w, dl, dv = par[b]; d = Z[M.PO[vs[i + 1]["lab"]]] - Z[M.PO[vs[i]["lab"]]]
        lead = np.zeros(9); lead[LIPS] = dl; lead[VELUM] = dv
        P = P + d * step((t - tb - c - lead) / w)
    return P


NW = 2048; FB = np.fft.rfftfreq(NW, 1 / SR)
_win = np.abs(np.fft.fft(np.hanning(NW), 16 * NW)) ** 2; _wf = np.fft.fftfreq(16 * NW, 1 / SR)
_o = np.argsort(_wf); KER_F, KER = _wf[_o], _win[_o]


def model_bands(pose, f0):
    """Each tone spread exactly as the clip's analysis window spreads it, then the same bands."""
    k = np.arange(1, min(60, int(12800 // f0)) + 1); f = k * f0
    E = (np.abs(HIS[: len(k)]) * mouth_mag(pose, f)) ** 2
    S = np.zeros(len(FB))
    for fk, ek in zip(f, E):
        S += ek * np.interp(FB - fk, KER_F, KER, left=0, right=0)
    b = np.array([10 * np.log10(S[(FB >= lo) & (FB < hi)].mean() + 1e-30) for lo, hi in zip(EDGES[:-1], EDGES[1:])])
    return b - b.max()


def clip_bands(x, t):
    N = 2048; seg = x[int(t * SR) - N // 2: int(t * SR) + N // 2]; f = np.fft.rfftfreq(N, 1 / SR)
    S = np.abs(np.fft.rfft(seg * np.hanning(N))) ** 2
    b = np.array([10 * np.log10(S[(f >= lo) & (f < hi)].mean() + 1e-14) for lo, hi in zip(EDGES[:-1], EDGES[1:])])
    return b - b.max()


def main():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    Pt = pm.Sound(x, SR).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff0 = Pt.selected_array["frequency"]
    f0_at = lambda t: float(np.interp(t, tt[ff0 > 0], ff0[ff0 > 0]))
    out = {}
    for pi, ph in enumerate(PHRASES):
        vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
        bnd = [(i, vs[i + 1]["s"]) for i in range(len(vs) - 1) if abs(vs[i + 1]["s"] - vs[i]["e"]) < 0.003]
        if not bnd:
            continue
        frames = [t for v in vs for t in np.arange(v["s"] + 0.005, v["e"] - 0.005, 0.005)]
        near = [t for t in frames if min(abs(t - tb) for _, tb in bnd) < 0.06]
        CB = {t: clip_bands(x, t) for t in near}

        def resid(z):
            par = z.reshape(-1, 4); r = []
            for t in near:
                ch = CB[t]; ok = ch > -50
                r.append((np.maximum(model_bands(pose_at(t, vs, bnd, par), f0_at(t)), -50) - ch)[ok] / np.sqrt(ok.sum()))
            return np.concatenate(r)

        z0 = np.tile(X0, len(bnd)); lo = np.tile(LO, len(bnd)); hi = np.tile(HI, len(bnd))
        e0 = np.sqrt(np.mean(resid(z0) ** 2) * len(resid(z0)) / len(near))
        best = None
        for start in (z0, np.tile([0.0, 0.05, -0.01, -0.02], len(bnd)), np.tile([0.0, 0.02, 0.01, -0.01], len(bnd))):
            r = least_squares(resid, np.clip(start, lo + 1e-6, hi - 1e-6), bounds=(lo, hi), diff_step=0.05, x_scale="jac", max_nfev=200)
            if best is None or r.cost < best.cost:
                best = r
        e1 = np.sqrt(np.mean(best.fun ** 2) * len(best.fun) / len(near))
        par = best.x.reshape(-1, 4)
        print(f"phrase {pi + 1}: transition frames {len(near)}; likeness {e0:.2f} -> {e1:.2f} dB")
        for (i, tb), p in zip(bnd, par):
            print(f"  {vs[i]['lab']:3}->{vs[i + 1]['lab']:3} at {tb:.3f}s: glide centre {p[0] * 1000:+4.0f} ms, takes {p[1] * 1000:3.0f} ms, "
                  f"lips {p[2] * 1000:+4.0f} ms, soft palate {p[3] * 1000:+4.0f} ms")
        out[str(pi)] = dict(bounds=[[int(i), float(tb)] for i, tb in bnd], par=par.tolist())
    (ROOT / f"models/transitions{TAG}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
