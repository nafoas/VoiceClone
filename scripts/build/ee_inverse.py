"""Step 2b: his folds' puff and his mouth, recovered from his tones.

Glottal inverse filtering with his bun mouth: his tones / the mouth = the airflow
puff his folds make. The right mouth is the one that leaves a real puff (one
smooth hump, a closed pause, nothing negative). Per "ee" the mouth may differ a
little from the shared "ee" shape (coming out of n / p / t), with a cost for
every bit of difference.

Then the puff is described by a flexible physical pulse (open share, rise share,
how rounded the closing is), shared by all four "ee"s, and the recipe (pulse x
mouth) is checked tone by tone against his.

    python scripts/build/ee_inverse.py -> analysis/physics/ee_inverse.png, models/ee_inverse.json
"""
import json, sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/build"))
import ee_recipe as R  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose, NAMES  # noqa: E402

NH = R.NH
FREE = ["jaw", "body", "front", "root", "lips", "larynx"]


def pulse_flex(n, Oq, am, p):
    """One cycle: rise over am*Oq (raised cosine), fall over the rest of the open
    phase with closing roundness p (1 = cosine; >1 = gentler start, sharper end;
    <1 = rounder end), then closed."""
    x = np.arange(n, dtype=float) / n; To = Oq; Tp = am * To
    rise = 0.5 * (1 - np.cos(np.pi * x / Tp))
    fall = np.clip(np.cos(0.5 * np.pi * (x - Tp) / max(To - Tp, 1e-3)), 0, None) ** p
    return np.where(x < Tp, rise, np.where(x < To, fall, 0.0))


def puff_from(t, m, pose):
    k = np.arange(1, NH + 1) * t["f0"]
    H = m.response(pose, k, radiate=True)
    Zh = 10 ** (t["level"] / 20) * np.exp(1j * t["phase"])
    U = Zh / (H / np.abs(H[0]))
    U = U / U[0] * np.abs(U[0])                            # H1 at phase 0
    steady = t["coh"] >= 0.6
    n = 512; tt = np.arange(n) / n
    pu = np.real(np.sum((U * steady)[None, :] * np.exp(2j * np.pi * np.outer(tt, np.arange(1, NH + 1))), 1))
    return pu, U


def glottalness(pu):
    """0 = a perfect puff: one hump, a flat closed pause at the bottom."""
    pu = (pu - pu.min()) / (pu.max() - pu.min() + 1e-12)
    n = len(pu); w = n // 5
    i0 = np.argmin(np.convolve(np.r_[pu, pu[:w]], np.ones(w) / w, "valid")[:n])   # the quietest fifth: closed pause
    closed = np.r_[pu, pu][i0: i0 + w]
    d = np.diff(np.r_[pu, pu[:1]]); s = np.sign(d)
    peaks = np.sum((s[:-1] > 0) & (s[1:] <= 0) & (pu[1:-0 or None][:len(s) - 1] > 0.15))
    return float(np.std(closed) * 4 + closed.mean() * 3 + max(0, peaks - 1) * 0.5)


def main():
    T = R.his_tones()
    rec = json.loads((ROOT / "models/ee_recipe.json").read_text())
    neck = rec["neck"]; m = BunMouth(0.75, neck_mm=neck, larcav=tuple(rec["larcav"]))
    base = np.array(rec["pose"]); idx = [NAMES.index(n) for n in FREE]
    poses, puffs, Us = [], [], []
    for t in T:
        def cost(dz):
            v = base.copy(); v[idx] = v[idx] + dz; v[:9] = np.clip(v[:9], R.E.EE_LO, R.E.EE_HI)
            pu, _ = puff_from(t, m, Pose.from_vec(v))
            return glottalness(pu) + 0.6 * np.sqrt(np.mean(dz ** 2))
        best = min((minimize(cost, d0, method="Powell", options=dict(maxfev=1500)) for d0 in
                    (np.zeros(len(idx)), np.full(len(idx), 0.1), np.full(len(idx), -0.1))), key=lambda r: r.fun)
        v = base.copy(); v[idx] += best.x; v[:9] = np.clip(v[:9], R.E.EE_LO, R.E.EE_HI); p = Pose.from_vec(v)
        pu, U = puff_from(t, m, p); poses.append(p); puffs.append(pu); Us.append(U)
        F = [round(x) for x in m.formants(p, fmax=8000)[:3] if x == x]
        print(f"{t['f0']:.0f} Hz: mouth nudged {dict((n, round(float(d), 2)) for n, d in zip(FREE, best.x) if abs(d) > 0.02)}; "
              f"resonances {F}; puff quality {glottalness(pu):.2f} (0 = perfect)")
    # one shared flexible pulse for all four, fitted to the recovered puffs' tones
    def pcost(q):
        Oq, am, p = np.clip(q, [0.3, 0.3, 0.3], [0.98, 0.95, 4.0]); e = 0.0
        for t, U in zip(T, Us):
            P = np.fft.rfft(pulse_flex(4096, Oq, am, p))[1: NH + 1]; P = P / P[0] * np.abs(P[0])
            a = 20 * np.log10(np.abs(P) / np.abs(P[0])); b = 20 * np.log10(np.abs(U) / np.abs(U[0]))
            ok = t["level"] > R.FLOOR
            w = np.clip((t["coh"] - 0.5) / 0.5, 0, 1)
            e += np.sqrt(np.mean((a - b)[ok][1:] ** 2)) + 5 * np.sqrt(np.sum(w * np.angle(P * np.conj(U)) ** 2) / (w.sum() + 1e-9))
        return e
    q = min((minimize(pcost, q0, method="Powell") for q0 in ((0.75, 0.6, 1.0), (0.85, 0.7, 1.5), (0.6, 0.5, 0.8))), key=lambda r: r.fun)
    Oq, am, p = np.clip(q.x, [0.3, 0.3, 0.3], [0.98, 0.95, 4.0])
    print(f"\nhis folds' puff: open {Oq:.2f} of each cycle; rising for {am:.2f} of that; closing roundness {p:.2f}")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 4, figsize=(22, 9)); rows = []
    for j, (t, pz, pu) in enumerate(zip(T, poses, puffs)):
        k = np.arange(1, NH + 1) * t["f0"]
        P = np.fft.rfft(pulse_flex(4096, Oq, am, p))[1: NH + 1]
        Z = P * m.response(pz, k, radiate=True); L = 20 * np.log10(np.abs(Z)); L -= L[0]
        ph = np.angle(np.exp(1j * (np.angle(Z) - np.arange(1, NH + 1) * np.angle(Z[0]))))
        print(f"{t['f0']:.0f} Hz his    " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print(f"{t['f0']:.0f} Hz recipe " + " ".join(f"{v:4.0f}" for v in L))
        print(f"{'':6} timing diff " + " ".join(f"{np.angle(np.exp(1j * (a - b))):4.1f}" if c >= 0.6 else "   ."
                                            for a, b, c in zip(ph, t["phase"], t["coh"])))
        tt = np.arange(len(pu)) / len(pu); pn = (pu - pu.min()) / (pu.max() - pu.min())
        pm_ = pulse_flex(len(pu), Oq, am, p); sh = np.argmax(np.correlate(np.r_[pn, pn], pm_, "valid")[:len(pn)])
        ax[0, j].plot(tt, pn, color="#c0392b", label="his folds (recovered)")
        ax[0, j].plot(tt, np.roll(pm_, sh), "--", color="#2c3e50", label="recipe puff")
        ax[0, j].set_title(f"vocal-fold puff, {t['f0']:.0f} Hz"); ax[0, j].legend(fontsize=7)
        ax[1, j].plot(range(1, NH + 1), t["level"], "-o", color="#c0392b", label="his tones")
        ax[1, j].plot(range(1, NH + 1), L, "-s", color="#2c3e50", label="recipe tones")
        ax[1, j].set_ylim(-80, 5); ax[1, j].legend(fontsize=7); ax[1, j].set_xlabel("harmonic")
        rows.append(dict(f0=t["f0"], pose=pz.vec().tolist(), his=t["level"].tolist(), recipe=L.tolist()))
    plt.tight_layout(); plt.savefig(ROOT / "analysis/physics/ee_inverse.png", dpi=65)
    (ROOT / "models/ee_inverse.json").write_text(json.dumps(dict(neck=neck, larcav=rec["larcav"], pulse=dict(Oq=Oq, am=am, p=p),
                                                                   rows=rows), indent=1, default=float))


if __name__ == "__main__":
    main()
