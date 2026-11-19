"""Fit his one mouth on the WHOLE phrase: positions, anatomy and the movement between sounds
together, judged on every 5 ms of his voiced sound (transitions included), plus the
steady-tone checks and physics guards of mouth_inverse. Same model; better judge.

    python scripts/build/phrase_fit.py  (ZWARM=models/mouth_inverse_H3.json TWARM=models/transitions_H3.json TAG=_P1)
"""
import json, os, sys
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from scipy.fft import idct
from scipy.optimize import least_squares

os.environ.setdefault("SRC", "his"); os.environ.setdefault("NH", "40"); os.environ.setdefault("HUMW", "3")
os.environ.setdefault("CHMIN", "0.005"); os.environ.setdefault("F1GUARD", "1")
os.environ.setdefault("ZFILE", os.environ.get("ZWARM", "models/mouth_inverse_H3.json"))
ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "scripts", ROOT / "scripts/build", ROOT / "analysis/physics"):
    sys.path.insert(0, str(p))
sys.argv = sys.argv[:1]
import mouth_inverse as M  # noqa: E402
import transitions as TR  # noqa: E402
from build_catalogue import PHRASES  # noqa: E402

SR = 48000; TAG = os.environ.get("TAG", "_F1")
FW = float(os.environ.get("FW", "1.0"))      # weight of the whole-phrase frames vs the steady tones
z0 = np.array(json.loads((ROOT / os.environ.get("ZWARM", "models/mouth_inverse_H3.json")).read_text())["z"])
z0 = M.pad(z0)
tw = json.loads((ROOT / os.environ.get("TWARM", "models/transitions_H3.json")).read_text())


def mag(z, pose9, f):
    a0, L, frac, port = M.tube(pose9, z[0], z[M.SH["lar"]])
    a = a0 * np.exp(idct(np.r_[z[M.SH["shape"]], np.zeros(M.NS - M.NF)], norm="ortho"))
    if pose9[TR.LIPS] < 0.04:
        a = M.seal(a, "m")
    M.body(z)
    fc = 1.84 * 35000 / (np.pi * 2 * np.sqrt(a.max() / np.pi))
    return np.abs(M.B.tube_H_nose(a, L, f, frac, port, z[6], z[7]) * M.B.head_baffle(f, z[1]) / (1 + (f / fc) ** 8))


def bands(z, pose9, f0):
    k = np.arange(1, min(60, int(12800 // f0)) + 1); f = k * f0
    E = (np.abs(TR.his_at(f0)[: len(k)]) * mag(z, pose9, f)) ** 2
    S = np.zeros(len(TR.FB))
    for fk, ek in zip(f, E):
        S += ek * np.interp(TR.FB - fk, TR.KER_F, TR.KER, left=0, right=0)
    b = np.array([10 * np.log10(S[(TR.FB >= lo) & (TR.FB < hi)].mean() + 1e-30) for lo, hi in zip(TR.EDGES[:-1], TR.EDGES[1:])])
    return b - b.max()


def setup():
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    Pt = pm.Sound(x, SR).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    tt = Pt.xs(); ff0 = Pt.selected_array["frequency"]
    F = []; layout = []; nb = 0
    for pi, ph in enumerate(PHRASES):
        vs = [dict(lab=l, s=s, e=e) for l, s, e, _ in ph if l in M.SOUNDS]
        bnd = [(i, vs[i + 1]["s"]) for i in range(len(vs) - 1) if abs(vs[i + 1]["s"] - vs[i]["e"]) < 0.003]
        layout.append((vs, bnd, nb)); nb += len(bnd)
        for v in vs:
            for t in np.arange(v["s"] + 0.005, v["e"] - 0.005, 0.005):
                F.append(dict(pi=pi, t=t, f0=float(np.interp(t, tt[ff0 > 0], ff0[ff0 > 0])), clip=TR.clip_bands(x, t), floor=TR.clip_floor(x, t)))
    return F, layout, nb


F, LAYOUT, NB = setup()
TP = np.concatenate([np.array(tw[str(pi)]["par"]).ravel() if bnd else np.zeros(0) for pi, (vs, bnd, _) in enumerate(LAYOUT)])
LO = np.r_[M.LO[: M.NP], np.tile(TR.LO, NB)]; HI = np.r_[M.HI[: M.NP], np.tile(TR.HI, NB)]


def unpack(q):
    return q[: M.NP], q[M.NP:].reshape(-1, 4)


def frame_resid(q):
    z, tp = unpack(q); r = []
    for fr in F:
        vs, bnd, b0 = LAYOUT[fr["pi"]]
        TR.Z = z
        pose = TR.pose_at(fr["t"], vs, bnd, tp[b0: b0 + len(bnd)]) if bnd else z[M.PO[vs[0]["lab"]]]
        if not bnd:   # sounds separated by consonants: each holds its own position
            pose = z[M.PO[[v for v in vs if v["s"] <= fr["t"] <= v["e"]][0]["lab"]]]
        ch, fl = fr["clip"], fr["floor"]
        if os.environ.get("JUDGE", "hiss") == "old":
            fl = np.full_like(ch, -50.0)
        ok = ch > fl          # judged where his sound stands above the recording's hiss
        w = np.clip((ch - fl) / 40.0, 0.05, 1.0) if os.environ.get("JUDGE", "hiss") != "old" else np.ones_like(ch)
        w = w[ok]             # each band counts as much as it is audible: by how far it stands above the hiss
        r.append((np.maximum(bands(z, pose, fr["f0"]), fl) - ch)[ok] * np.sqrt(w / w.sum()))
    return np.concatenate(r)


def resid(q):
    z, _ = unpack(q)
    return np.r_[M.resid(z), FW * 6.0 * frame_resid(q)]


_last = {}


def resid_c(q):
    """resid, remembering the last point (the parallel Jacobian reuses it)."""
    k = q.tobytes()
    if k not in _last:
        _last.clear(); _last[k] = resid(q)
    return _last[k]


def _col(args):
    q, i, h = args
    qq = q.copy(); qq[i] += h
    return (resid(qq) - resid_c(q)) / h


def jac(q):
    """Forward differences, one column per unknown, spread over the machine's processors."""
    h = 1e-3 * np.maximum(1.0, np.abs(q))
    h = np.where(q + h > HI, -h, h)          # step inward at an upper bound
    f0 = resid_c(q)
    with _POOL() as pool:
        cols = pool.map(_col, [(q, i, h[i]) for i in range(len(q))], chunksize=4)
    _N[0] += 1
    print(f"  step {_N[0]}: whole-phrase {np.sqrt(np.sum(frame_resid(q) ** 2) / len(F)):.3f} dB", flush=True)
    return np.array(cols).T


_N = [0]


def _POOL():
    import multiprocessing as mp
    return mp.get_context("fork").Pool(int(os.environ.get("NPROC", str(os.cpu_count()))))


def score(q):
    fr = frame_resid(q); n = len(F)
    return float(np.sqrt(np.sum(fr ** 2) / n))


def main():
    q0 = np.clip(np.r_[z0, TP], LO + 1e-6, HI - 1e-6)
    print(f"{len(F)} frames, {len(q0)} unknowns; whole-phrase likeness at start {score(q0):.2f} dB", flush=True)
    r = least_squares(resid_c, q0, jac=jac, bounds=(LO, HI), method="trf", max_nfev=int(os.environ.get("NFEV", "120")),
                      x_scale="jac", xtol=1e-12, ftol=1e-10, verbose=0)
    q = r.x; z, tp = unpack(q)
    print(f"whole-phrase likeness after {score(q):.2f} dB (nfev {r.nfev})", flush=True)
    M.report(z, "(whole-phrase fit)")
    (ROOT / f"models/mouth_inverse{TAG}.json").write_text(json.dumps(dict(z=z.tolist()), indent=1))
    out = {}
    for pi, (vs, bnd, b0) in enumerate(LAYOUT):
        if bnd:
            out[str(pi)] = dict(bounds=[[int(i), float(tb)] for i, tb in bnd], par=tp[b0: b0 + len(bnd)].tolist())
    (ROOT / f"models/transitions{TAG}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
