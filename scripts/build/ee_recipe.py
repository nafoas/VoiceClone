"""Step 2: exactly where every tone of his "ee" comes from, and the recipe that
reproduces them in a bun.

Every tone = (vocal-fold puff's tone) x (mouth's effect at that frequency),
in strength AND timing. From his measured tones (strength + place in the cycle,
analysis/physics/ee_decompose.py):
  1. fit the mouth (his bun mouth: "ee" pose + larynx depth) and the folds'
     puff (open quotient, opening share, closing smoothness) to every tone's
     strength and, where his tones are steady, their timing
  2. inverse-filter: divide his tones by the fitted mouth -> the puff his folds
     must make. A real puff = smooth rise, sharper fall, a closed pause.
  3. account for every tone: how much of it is the folds and how much each
     resonance of the mouth
  4. rebuild his tones-only "ee" from the recipe

    python scripts/build/ee_recipe.py -> analysis/physics/ee_recipe.png, models/ee_recipe.json, out/build/ee_recipe_*.wav
"""
import json, sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "analysis/physics")); sys.path.insert(0, str(ROOT / "scripts/build"))
sys.argv = sys.argv[:1] + ["30"]
import ee_decompose as DC  # noqa: E402
import ee as E  # noqa: E402
from prince_voice.bunmouth import BunMouth, Pose  # noqa: E402
from prince_voice import voicebox as VB  # noqa: E402

NH = 20; FLOOR = -58.0
SPANS = [(0.79, 0.99), (1.52, 1.60), (1.77, 1.90), (2.09, 2.30)]
LARCAV = (7, 1.0, 4, 0.15)


def his_tones():
    """Per "ee": each tone's strength (dB re H1), its average place in the cycle
    (relative phase) and how steady that place is."""
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    out = []
    for s, e in SPANS:
        d = DC.decompose(x[int((s - 0.02) * sr): int((e + 0.02) * sr)], sr, f"r{int(s * 100)}")
        A = d["A"]; ok = ~np.isnan(A[:, 0]); mid = slice(ok.sum() // 5, -(ok.sum() // 5) or None)
        dB = 20 * np.log10(A[ok][mid] + 1e-12); dB -= dB[:, :1]
        z = np.nanmean(np.exp(1j * d["rel"][ok][mid]), 0)
        out.append(dict(f0=float(np.median(d["F0"])), level=np.nanmedian(dB, 0)[:NH], phase=np.angle(z)[:NH], coh=np.abs(z)[:NH]))
    return out


def src_complex(f0, Oq, am, Ta):
    n = 4096; U = np.fft.rfft(VB.pulse(n, Oq, am))[1: NH + 1]
    k = np.arange(1, NH + 1) * f0
    return U / (1 + 1j * 2 * np.pi * k * Ta * 1e-3)


def model_tones(m, pose, f0, src):
    k = np.arange(1, NH + 1) * f0
    Z = src_complex(f0, *src) * m.response(pose, k, radiate=True)
    L = 20 * np.log10(np.abs(Z) + 1e-15); L -= L[0]
    ph = np.angle(Z) - np.arange(1, NH + 1) * np.angle(Z[0])
    return L, np.angle(np.exp(1j * ph)), Z


def unpack(z):
    v = Pose().vec(); v[:9] = np.clip(z[:9], E.EE_LO, E.EE_HI)
    return Pose.from_vec(v), float(np.clip(z[9], 15.0, 45.0)), (float(np.clip(z[10], 0.3, 0.92)),
                                                                 float(np.clip(z[11], 0.4, 0.95)), float(np.clip(z[12], 0.0, 2.0)))


def fit(T):
    cache = {}

    def cost(z):
        pose, neck, src = unpack(z); key = round(neck, 1)
        m = cache.setdefault(key, BunMouth(0.75, neck_mm=key, larcav=LARCAV))
        e = 0.0
        for t in T:
            L, ph, _ = model_tones(m, pose, t["f0"], src)
            el = np.maximum(L[1:], FLOOR) - np.maximum(t["level"][1:], FLOOR)
            w = np.clip((t["coh"][1:] - 0.5) / 0.5, 0, 1)                    # only where his timing is steady
            ep = np.angle(np.exp(1j * (ph[1:] - t["phase"][1:])))
            e += np.sqrt(np.mean(el ** 2)) + 6.0 * np.sqrt(np.sum(w * ep ** 2) / (w.sum() + 1e-9))
        return e / len(T)
    prev = json.loads((ROOT / "models/build_ee_tones.json").read_text())
    starts = [np.r_[np.array(prev["pose"])[:9], prev["neck"], prev["source"]["Oq"], prev["source"]["am"], 0.0]]
    for neck in (20.0, 26.0, 32.0):
        for src in ((0.5, 0.6, 0.2), (0.7, 0.75, 0.5), (0.6, 0.85, 0.1)):
            starts.append(np.r_[np.array(prev["pose"])[:9], neck, src])
    rs = [minimize(cost, z, method="Powell", options=dict(maxfev=3000, xtol=1e-4, ftol=1e-5)) for z in starts]
    r = min(rs, key=lambda r: r.fun)
    return unpack(r.x), float(r.fun)


def main():
    T = his_tones()
    (pose, neck, src), err = fit(T)
    m = BunMouth(0.75, neck_mm=neck, larcav=LARCAV)
    F = [round(x) for x in m.formants(pose, fmax=8000, n=5) if x == x]
    print(f"recipe: larynx {neck * 0.075:.2f} cm lower; folds open {src[0]:.2f} of each cycle, opening share {src[1]:.2f}, "
          f"closing smoothness {src[2]:.2f} ms; mouth resonances {F}; error {err:.2f}")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 4, figsize=(22, 9))
    rows = []
    for j, t in enumerate(T):
        k = np.arange(1, NH + 1) * t["f0"]
        L, ph, Z = model_tones(m, pose, t["f0"], src)
        Hm = 20 * np.log10(np.abs(m.response(pose, k, radiate=True))); Hm -= Hm[0]
        S = 20 * np.log10(np.abs(src_complex(t["f0"], *src))); S -= S[0]
        print(f"\n{t['f0']:.0f} Hz   harmonic: " + " ".join(f"{i:4d}" for i in range(1, NH + 1)))
        print("  his strength      " + " ".join(f"{v:4.0f}" for v in t["level"]))
        print("  recipe strength   " + " ".join(f"{v:4.0f}" for v in L))
        print("    = folds         " + " ".join(f"{v:4.0f}" for v in S))
        print("    + mouth         " + " ".join(f"{v:4.0f}" for v in Hm))
        print("  his timing steady " + " ".join(f"{v:4.1f}" for v in t["coh"]))
        print("  timing diff (rad) " + " ".join(f"{np.angle(np.exp(1j * (a - b))):4.1f}" for a, b in zip(ph, t["phase"])))
        # inverse filtering: his tones / the mouth -> the folds' puff (steady tones only for timing)
        H = m.response(pose, k, radiate=False)
        Zh = 10 ** (t["level"] / 20) * np.exp(1j * t["phase"])
        U = Zh / (H / np.abs(H[0])) / (1j * k / k[0])                 # remove mouth and radiation
        U = np.where(t["coh"] >= 0.5, U, np.abs(U) * np.exp(1j * np.angle(src_complex(t["f0"], *src))))
        tt = np.linspace(0, 1, 400)
        puff = np.real(np.sum(U[None, :] * np.exp(2j * np.pi * np.outer(tt, np.arange(1, NH + 1))), 1))
        puff = puff - puff.min(); puff /= puff.max() + 1e-12
        model_puff = VB.pulse(400, src[0], src[1])
        ax[0, j].plot(tt, puff, color="#c0392b", label="his folds (his tones / his mouth)")
        ax[0, j].plot(tt, model_puff / model_puff.max(), color="#2c3e50", ls="--", label="recipe puff")
        ax[0, j].set_title(f"one vocal-fold puff, {t['f0']:.0f} Hz"); ax[0, j].legend(fontsize=7)
        ax[1, j].plot(range(1, NH + 1), t["level"], "-o", color="#c0392b", label="his tones")
        ax[1, j].plot(range(1, NH + 1), L, "-s", color="#2c3e50", label="recipe")
        ax[1, j].plot(range(1, NH + 1), S, ":", color="#7f8c8d", label="folds' share")
        ax[1, j].plot(range(1, NH + 1), Hm, ":", color="#16a085", label="mouth's share")
        ax[1, j].set_ylim(-80, 30); ax[1, j].set_xlabel("harmonic"); ax[1, j].legend(fontsize=7)
        rows.append(dict(f0=t["f0"], his=t["level"].tolist(), recipe=L.tolist(), folds=S.tolist(), mouth=Hm.tolist()))
    plt.tight_layout(); plt.savefig(ROOT / "analysis/physics/ee_recipe.png", dpi=65)
    (ROOT / "models/ee_recipe.json").write_text(json.dumps(dict(
        pose=pose.vec().tolist(), neck=neck, larcav=LARCAV, source=dict(Oq=src[0], am=src[1], Ta_ms=src[2]),
        resonances=F, err=err, rows=rows), indent=1))


if __name__ == "__main__":
    main()
