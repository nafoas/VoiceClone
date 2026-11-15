"""New vowels from his mouth: start at the shape fitted to one of his real
vowels and move the tongue to reach a target, staying close to where he was.

    python scripts/mouth_vowels.py   -> models/mouth_fit.json ("derived")
"""
import json, sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from fit_mouth import bark  # noqa: E402
from prince_voice.mouth import Mouth  # noqa: E402

# new vowel: (his base vowel, articulators allowed to move, target F1..F3, why)
DERIVED = {
    "ɑ": ("ã", ["TCX", "TCY", "TRX", "TRY", "TBX", "TBY"], (1178, 1700, 3600),
          "mama's ah: tongue back from his nannar a (F2 1700 = Da Boss's pick, version F)"),
}
# new vowel by the HUMAN articulatory move between two VocalTractLab shapes,
# applied to his fitted shape (works for small moves; see docs/MOUTH_TOOLS.md)
MOVES = {
    "ɪ": ("iː", "i", "I", 1.0, "the i of ninny/minny: his ee + the human i->I move (tongue lower and back, jaw opens)"),
}


def main():
    fit = json.loads((ROOT / "models/mouth_fit.json").read_text())
    m = Mouth(scale=fit["scale"])
    fit.setdefault("derived", {})
    for new, (base, free, tgt, why) in DERIVED.items():
        p0 = np.array(fit["vowels"][base]["params"]); idx = [m.names.index(n) for n in free]
        span = (m.hi - m.lo)[idx]

        def P(z):
            p = p0.copy(); p[idx] = np.clip(p0[idx] + z * span, m.lo[idx], m.hi[idx]); return p

        def cost(z):
            F = np.array(m.formants(P(z), fmax=5800, df=10)[:3]); F = np.where(np.isfinite(F), F, 9000)
            return np.sqrt(np.sum((bark(F) - bark(tgt)) ** 2)) + 0.3 * np.sqrt(np.mean(z ** 2))

        r = minimize(cost, np.zeros(len(idx)), method="Powell", options=dict(maxfev=800, xtol=1e-3))
        p = P(r.x); F = m.formants(p)
        moved = {n: round(float(p[i] - p0[i]), 2) for n, i in zip(free, idx) if abs(p[i] - p0[i]) > 0.05}
        print(f"/{new}/ from his /{base}/: {[int(x) for x in F[:3]]} (target {tgt}); moved {moved}")
        fit["derived"][new] = dict(base=base, params=[float(x) for x in p], formants=F, why=why, moved=moved)
    for new, (base, h_from, h_to, k, why) in MOVES.items():
        p = np.array(fit["vowels"][base]["params"]) + k * (m.shape(h_to) - m.shape(h_from))
        p = np.clip(p, m.lo, m.hi); F = m.formants(p)
        print(f"/{new}/ from his /{base}/ + human {h_from}->{h_to}: {[int(x) for x in F[:3]]}")
        fit["derived"][new] = dict(base=base, params=[float(x) for x in p], formants=F, why=why)
    (ROOT / "models/mouth_fit.json").write_text(json.dumps(fit, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
