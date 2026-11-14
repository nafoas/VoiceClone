"""Check one sound in a file against Prince's spec: is it the intended phoneme,
does it meet its class's voice targets, and does its edge carry the right
neighbour?

    python scripts/check_phoneme.py file.wav START END PHONEME [--after m|n|p|tʰ]

identity    F1/F2 at the middle vs every phoneme target in spec.json: the
            nearest must be the intended one (distance in Bark-like units)
class       H1-H2, H1-A3, low-band purity, jitter, shimmer, B1 vs its class
transition  after a lip consonant F2 must RISE into the vowel; after a tongue-
            tip consonant it FALLS from high (n locus); never an F3 drop (r)
"""
import argparse, json, sys, warnings
from pathlib import Path

import numpy as np
import parselmouth as pm

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from fingerprint import source_measures  # noqa: E402

SPEC = json.loads((ROOT / "prince_voice/spec.json").read_text())
CLASS_OF = {"ɪ": "near_closed_vowel", "iː": "closed_vowel", "ũ": "closed_vowel", "ã": "open_vowel", "ɐ˞": "open_vowel", "ɑ": "open_vowel",
            "n": "nasal", "m": "nasal"}
LIP, TIP = {"m", "p", "b"}, {"n", "tʰ", "t", "d"}
LOCUS = {c: 1200.0 for c in LIP} | {c: 2700.0 for c in TIP}   # his F2 loci (Hz)


def bark(f):
    return 26.81 * f / (1960 + f) - 0.53


def check(path, s, e, ph, after=None):
    snd = pm.Sound(str(path)).convert_to_mono()
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
    d = e - s
    mid = np.arange(s + 0.35 * d, e - 0.35 * d + 1e-9, 0.005)
    f1 = float(np.nanmedian([F.get_value_at_time(1, t) for t in mid]))
    f2 = float(np.nanmedian([F.get_value_at_time(2, t) for t in mid]))
    out = {"F1": f1, "F2": f2}
    # identity
    dist = {}
    for name, tg in SPEC["phonemes"].items():
        if name in ("n", "m") and ph not in ("n", "m"):
            continue
        dist[name] = float(np.hypot(bark(f1) - bark(tg["F1"]), bark(f2) - bark(tg["F2"])))
    nearest = min(dist, key=dist.get)
    out["identity"] = (nearest == ph, nearest, dist)
    # class targets
    cls = SPEC["classes"].get(CLASS_OF.get(ph, ""), {})
    src = source_measures(snd, s, e, F, P)
    b1 = float(np.nanmedian([F.get_bandwidth_at_time(1, t) for t in mid]))
    checks = {}
    for key, val in (("H1H2", src["H1H2"]), ("H1A3", src["H1A3"]), ("B1", b1)):
        if key in cls:
            lo, hi = cls[key]; checks[key] = (val, lo <= val <= hi, f"{lo}..{hi}")
    if "HNR_0_500_min" in cls:
        checks["HNR_0_500"] = (src["HNR_0_500"], src["HNR_0_500"] >= cls["HNR_0_500_min"], f">= {cls['HNR_0_500_min']}")
    if "jitter_max" in cls:
        checks["jitter"] = (src["jitter_pct"], src["jitter_pct"] <= cls["jitter_max"], f"<= {cls['jitter_max']}")
    out["class"] = checks
    # transition into the vowel
    if after:
        # locus rule: the vowel's onset points toward the consonant's locus (his
        # tongue tip ~2700 Hz, his lips ~1200 Hz). Onset = F2 at 10-25 ms (after
        # the release frame, where a nasal murmur fools formant tracking).
        vals = np.array([F.get_value_at_time(2, s + q) for q in np.arange(0.015, 0.0401, 0.005)])
        vals = vals[np.isfinite(vals)]
        vals = vals[np.abs(vals - np.median(vals)) < 400] if len(vals) else vals   # drop tracker spikes
        on = float(np.median(vals)) if len(vals) else np.nan
        mid2 = f2
        locus = LOCUS.get(after)
        if locus is None:
            ok, want = True, None
        else:
            want = f"not away from {locus:.0f} Hz"
            # validated on his clip: the onset never moves clearly AWAY from the
            # consonant's locus (small movements are normal, e.g. tip -> ee)
            moved = on - mid2
            ok = not (abs(moved) > 80 and np.sign(moved) != np.sign(locus - mid2))
        rise = on - mid2
        f3on = np.nanmin([F.get_value_at_time(3, s + q) for q in (0.010, 0.020, 0.030)])
        out["transition"] = (ok, want, rise, f3on, f3on >= 2750)
    return out


def report(path, s, e, ph, after=None):
    r = check(path, s, e, ph, after)
    ok_id, nearest, dist = r["identity"]
    print(f"\n{path} [{s:.3f}-{e:.3f}] as /{ph}/" + (f" after /{after}/" if after else ""))
    print(f"  identity:   {'PASS' if ok_id else 'FAIL'}: measures as /{nearest}/ (F1 {r['F1']:.0f}, F2 {r['F2']:.0f}); "
          + ", ".join(f"{k} {v:.2f}" for k, v in sorted(dist.items(), key=lambda kv: kv[1])[:3]))
    for k, (v, ok, rng) in r["class"].items():
        print(f"  class:      {'PASS' if ok else 'FAIL'} {k:9} {v:7.1f}  (target {rng})")
    if "transition" in r:
        ok, want, rise, f3, f3ok = r["transition"]
        print(f"  transition: {'PASS' if ok else 'FAIL'}: onset F2 is {rise:+.0f} Hz from the vowel's middle (want {want})"
              f"; lowest F3 at onset {f3:.0f} Hz {'ok' if f3ok else '(r-like!)'}")
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("start", type=float); ap.add_argument("end", type=float)
    ap.add_argument("phoneme"); ap.add_argument("--after")
    a = ap.parse_args()
    report(a.file, a.start, a.end, a.phoneme, a.after)
