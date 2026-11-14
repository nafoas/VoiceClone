"""Check audio against Prince's voice spec (prince_voice/spec.json).

    python scripts/check_voice.py file.wav [more.wav ...]

For each file: every voice-quality measure as PASS / LOW / HIGH against his
accepted range, an overall score, and which approved version and which failure
type (from the negative space) it is closest to.
"""
import csv, json, sys, warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from negative_space import features  # noqa: E402

SPEC = json.loads((ROOT / "prince_voice/spec.json").read_text())
VQ = SPEC["voice_quality"]
KEYS = [k for k in VQ if k != "pitch_Hz"]


def reference_points():
    rows = list(csv.DictReader(open(ROOT / "analysis/negative_space.csv")))
    pts = []
    for r in rows:
        v = np.array([float(r[k]) if r[k] not in ("", "nan") else np.nan for k in KEYS])
        pts.append((r["group"], r["name"], v))
    return pts


def check(path, pts=None):
    f = features(path)
    res = {}
    for k in VQ:
        lo, hi = VQ[k]["accept"]; v = f.get(k, np.nan)
        res[k] = (v, "PASS" if lo <= v <= hi else ("LOW" if v < lo else "HIGH") if np.isfinite(v) else "n/a")
    score = np.mean([s == "PASS" for _, s in res.values() if s != "n/a"])
    near = None
    if pts:
        x = np.array([f.get(k, np.nan) for k in KEYS])
        span = np.array([VQ[k]["accept"][1] - VQ[k]["accept"][0] for k in KEYS])
        def d(v):
            z = (x - v) / span
            return float(np.sqrt(np.nanmean(z ** 2)))
        best_pos = min((p for p in pts if p[0] == "positive" and Path(path).name not in p[1]), key=lambda p: d(p[2]))
        best_neg = min((p for p in pts if p[0] == "negative"), key=lambda p: d(p[2]))
        near = (best_pos[1], d(best_pos[2]), best_neg[1], d(best_neg[2]))
    return res, score, near


def main():
    pts = reference_points()
    for p in sys.argv[1:]:
        res, score, near = check(p, pts)
        print(f"\n{p}\n  in his voice: {100 * score:.0f}% of measures pass")
        for k, (v, s) in res.items():
            if s != "PASS":
                lo, hi = VQ[k]["accept"]
                print(f"   {s:4} {k:16} {v:8.2f}  (his range {lo}..{hi}): {VQ[k]['why']}")
        if near:
            print(f"  closest approved: {near[0]} (distance {near[1]:.2f})")
            print(f"  closest failure:  {near[2]} (distance {near[3]:.2f})")


if __name__ == "__main__":
    main()
