"""How his resonances form, and which rabbit side spaces could make his upper
"ee" cluster (F2 3323, F3 4119, F4 4963 Hz).

A  sensitivity map (Fant): widen each point of the tube by 10%; how much does
   each resonance move? Shows which part of the mouth "owns" each resonance.
B  side spaces every rabbit has, swept over plausible sizes; the "ee" pose is
   refitted each time (F1..F4). Which reach his cluster?

    python analysis/physics/resonances.py [A|B]  -> analysis/physics/resonances_*.png / .json
"""
import itertools, json, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402
from fit_mouth import bark  # noqa: E402

OUT = ROOT / "analysis/physics"
NECK = 30.0
EE = np.array([362, 3323, 4119, 4963.0])
WT = np.array([1, 1, .8, .6])
LO = np.array([0.0, 0.3, 0.4, 0.0, -1.0, 0.3, 0.0, 0.0, 0.0]); HI = np.array([0.45, 1, 1, 0.35, 1, 1, 0.5, 0.3, 1])
EE_POSE = Pose(jaw=0.1, body=0.8, front=0.4, tip=0.19, root=1.0, lips=0.3, round=0.5, larynx=1.0)
A_POSE = Pose(jaw=1, body=0.89, front=0, lips=1, root=-1)


def formants_tube(m, area, length, port, br, f):
    """Formants straight from an (edited) area function, same acoustics."""
    from prince_voice import bunmouth as bm
    sh = getattr(m, "_shunts", [])
    w = 2 * np.pi * f
    Kp = bm._chain_sh(area[:br], length[:br], w, [(j, L, a) for j, L, a in sh if j < br])
    Ko = bm._chain_sh(area[br:], length[br:], w, [(j - br, L, a) for j, L, a in sh if j >= br])
    Zl = bm._radiation(area[-1], w)
    Ul = 1.0 / (Ko[0, 0] * Zl + Ko[0, 1]); Ub = (Ko[1, 0] * Zl + Ko[1, 1]) * Ul
    H = np.abs(Ul / (Kp[1, 0] + Kp[1, 1] * Ub))
    k = np.where((H[1:-1] > H[:-2]) & (H[1:-1] >= H[2:]))[0] + 1
    return np.array([f[i] for i in k][:5] + [np.nan] * (5 - len(k[:5])))


def part_a():
    f = np.arange(80.0, 8000, 5)
    res = {}
    for name, pose in (("ee", EE_POSE), ("a", A_POSE)):
        m = BunMouth(0.75, neck_mm=NECK)
        area, length, port, br = m.tube(pose)
        F0 = formants_tube(m, area, length, port, br, f)
        pos = np.cumsum(length) - length / 2
        S = np.zeros((len(area), 5))
        for i in range(len(area)):
            a2 = area.copy(); a2[i] *= 1.10
            S[i] = (formants_tube(m, a2, length, port, br, f) - F0) / F0 * 100   # % shift per +10% width
        res[name] = dict(F=F0.tolist(), pos_cm=pos.tolist(), area=area.tolist(), S=S.tolist())
        print(name, "resonances", np.round(F0).tolist())
    (OUT / "resonances_A.json").write_text(json.dumps(res))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(15, 8), gridspec_kw=dict(height_ratios=[1, 2]))
    for c, name in enumerate(("ee", "a")):
        r = res[name]; pos = np.array(r["pos_cm"]); S = np.array(r["S"])
        ax[0, c].fill_between(pos, 0, np.sqrt(np.array(r["area"]) / np.pi), step="mid", color="#e58c9a")
        ax[0, c].fill_between(pos, 0, -np.sqrt(np.array(r["area"]) / np.pi), step="mid", color="#e58c9a")
        ax[0, c].set_title(f"his '{name}' as a tube (glottis left, lips right): radius vs distance (cm)")
        for j in range(4):
            if np.isfinite(r["F"][j]):
                ax[1, c].plot(pos, S[:, j], "-o", ms=3, label=f"F{j + 1} {r['F'][j]:.0f} Hz")
        ax[1, c].axhline(0, color="k", lw=0.5)
        ax[1, c].set_xlabel("distance from the vocal folds (cm)"); ax[1, c].set_ylabel("% shift when this spot is 10% wider")
        ax[1, c].legend(fontsize=8); ax[1, c].set_title("which part of the mouth owns each resonance (big = owns it)")
    plt.tight_layout(); plt.savefig(OUT / "resonances_A.png", dpi=75)


def fit_ee(m):
    def P(z):
        v = Pose().vec(); v[:9] = np.clip(z, LO, HI); return Pose.from_vec(v)

    def c(z):
        F = np.array(m.formants(P(z), fmax=8000, df=10)[:4]); F = np.where(np.isfinite(F), F, 9500)
        return np.sqrt(np.sum(WT * (bark(F) - bark(EE)) ** 2))
    st = [EE_POSE.vec()[:9]] + [Pose(jaw=.1, body=b, front=fr, lips=.6, root=1, larynx=.5).vec()[:9]
                                for fr in (0.4, 0.6, 0.8) for b in (0.6, 1.0)]
    r = min((minimize(c, s, method="Powell", options=dict(maxfev=900)) for s in st), key=lambda r: r.fun)
    return [round(x) for x in m.formants(P(r.x), fmax=8000, df=10)[:4] if x == x], float(r.fun)


def one(cfg):
    kind, kw = cfg
    m = BunMouth(0.75, neck_mm=NECK, **kw)
    F, e = fit_ee(m)
    return dict(kind=kind, cfg={k: list(v) for k, v in kw.items()}, F=F, err=e)


def part_b():
    cfgs = [("none", {})]
    for Lc, rc, Li, ri in itertools.product((4, 7, 10), (0.6, 1.0), (2, 4), (0.15, 0.3)):   # laryngeal cavity
        cfgs.append(("larynx cavity", dict(larcav=(Lc, rc, Li, ri))))
    for Lp, rp in itertools.product((8, 12, 16, 20), (0.08, 0.15, 0.25)):                    # + piriform pair
        cfgs.append(("+ piriform", dict(larcav=(7, 1.0, 3, 0.25), piriform=(Lp, rp))))
    for Lb, rb, sb in itertools.product((8, 12, 16, 20), (0.15, 0.3, 0.5), (44, 52, 60)):    # cheek spaces
        cfgs.append(("cheek spaces", dict(buccal=(Lb, rb, sb))))
    with Pool(4) as pool:
        rows = pool.map(one, cfgs)
    rows.sort(key=lambda r: r["err"])
    (OUT / "resonances_B.json").write_text(json.dumps(rows, indent=1))
    print("his ee:", EE.tolist())
    for kind in ("none", "larynx cavity", "+ piriform", "cheek spaces"):
        best = [r for r in rows if r["kind"] == kind][:3]
        for r in best:
            print(f"  {kind:14} {r['F']}  err {r['err']:.2f}  {r['cfg']}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "AB"
    if "A" in which:
        part_a()
    if "B" in which:
        part_b()
