"""His four recorded vowels as poses of his (one-change) bun mouth.
    python analysis/physics/fit_vowels.py -> models/bun_vowels.json"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from prince_voice.bunmouth import BunMouth, Pose, LO, HI  # noqa: E402
from fit_mouth import HIS, bark  # noqa: E402

SIZE, NECK = 0.75, 50.0
W = np.array([1, 1, 0.7])
STARTS = [Pose(), Pose(jaw=0.2, body=0.6, front=0.7, lips=0.7, root=1), Pose(jaw=1, body=0.9, front=0, lips=1, root=-1),
          Pose(jaw=0.15, body=1, front=1, lips=0.6), Pose(jaw=0.2, body=0.8, front=0.0, lips=0.25, round=1, root=-0.5)]


def main():
    m = BunMouth(SIZE, neck_mm=NECK); out = dict(size=SIZE, neck=NECK, vowels={})
    for v, d in HIS.items():
        T = np.array(d["F"], float)

        def P(z):
            z = np.clip(z, LO, HI); z[7] = 0; z[9] = 0; return Pose.from_vec(z)

        def cost(z):
            F = np.array(m.formants(P(z), fmax=7000, df=10)[:3]); F = np.where(np.isfinite(F), F, 9000)
            return np.sqrt(np.sum(W * (bark(F) - bark(T[:3])) ** 2))
        r = min((minimize(cost, s.vec(), method="Powell", options=dict(maxfev=1500, xtol=1e-4)) for s in STARTS),
                key=lambda r: r.fun)
        p = P(r.x); F = m.formants(p)
        print(v, d["F"][:3], [int(x) for x in F[:3]], round(r.fun, 2))
        out["vowels"][v] = dict(pose=[float(x) for x in p.vec()], formants=F, err=float(r.fun))
    (ROOT / "models/bun_vowels.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
