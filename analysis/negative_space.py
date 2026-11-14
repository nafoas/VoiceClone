"""What he is NOT: measure every approved version (positives) and every rejected
or standard-failure version (negatives) the same way, and find which measures
separate them.

    python analysis/negative_space.py  -> analysis/negative_space.csv / .png
"""
import csv, sys, warnings
from pathlib import Path

import numpy as np, parselmouth as pm, pyworld as pw, soundfile as sf
from scipy.signal import resample_poly
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from fingerprint import source_measures, vtl  # noqa: E402
SR = 24000
O = ROOT / "out"

POS = {  # approved by Da Boss
    "clip (the real him)": ROOT / "reference/source/prince_reference.wav",
    "gold rebuild": ROOT / "reference/gold/rebuild_gold_v9.wav",
    "fresh munis... nannar ('perfect')": O / "fresh/munis_nannar.wav",
    "fresh nanni ('good')": O / "fresh/nanni.wav",
    "mama F ('best')": O / "fresh/mama_F_ah_deep.wav",
}
NEG = {  # rejected, with his words, or standard failures
    "ordinary adult (English TTS)": O / "english_ref.wav",
    "first audition: af_heart ('synthetic')": O / "audition/af_heart.wav",
    "first audition: am_puck ('synthetic')": O / "audition/am_puck.wav",
    "first audition: af_nicole ('synthetic')": O / "audition/af_nicole.wav",
    "candidate A ('a child')": O / "candidate_A_test_lines.wav",
    "candidate A2 hum ('a child')": O / "candidate_A2_hum_lines.wav",
    "candidate C transplant ('a child')": O / "candidate_C_transplant_hum_lines.wav",
    "Seed-VC ('not close')": O / "candidate_B_seedvc_lines.wav",
    "v16 intents ('worse, robotic')": O / "bnuy/new_sayings_v16_intents.wav",
    "mama, untouched ('nana')": O / "fresh/mama_A_none.wav",
    "std: child-like": O / "negatives/child_like.wav",
    "std: chipmunk": O / "negatives/chipmunk.wav",
    "std: breathy": O / "negatives/breathy.wav",
    "std: robotic": O / "negatives/robotic.wav",
    "std: choppy": O / "negatives/choppy.wav",
}

FEATS = ["pitch_Hz", "pitch_change_st", "jitter_pct", "shimmer_dB", "CPPS", "H1H2", "H1A3", "HNR_0_500",
         "HNR_1500_2500", "voiced_pct", "VTL_cm", "flux", "flux_p95", "loud_flutter", "F3_low", "loud_per_st"]
NICE = {"pitch_Hz": "pitch Hz", "pitch_change_st": "pitch wobble st/frame", "jitter_pct": "jitter %",
        "shimmer_dB": "shimmer dB", "CPPS": "CPPS", "H1H2": "H1–H2", "H1A3": "H1–A3 (hum cliff)",
        "HNR_0_500": "purity <500", "HNR_1500_2500": "purity 1.5–2.5k", "voiced_pct": "voiced %",
        "VTL_cm": "tract length cm", "flux": "spectral movement", "flux_p95": "biggest jumps",
        "loud_flutter": "loudness flutter", "F3_low": "lowest F3 (r-ness)", "loud_per_st": "loudness/pitch"}


def load(p):
    a, sr = sf.read(p)
    if a.ndim > 1: a = a.mean(1)
    if sr != SR: a = resample_poly(a, SR, sr)
    return a.astype(np.float64)


def features(path):
    x = load(path)
    snd = pm.Sound(x, SR)
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=80, pitch_ceiling=900)
    it = snd.to_intensity(minimum_pitch=120, time_step=0.005)
    t = P.xs(); f = P.selected_array["frequency"]; v = f > 0
    dB = np.array([it.get_value(q) for q in t]); act = np.isfinite(dB) & (dB > np.nanmax(dB) - 35)
    out = source_measures(snd, 0.0, snd.duration, F, P)
    st = 12 * np.log2(np.where(v, f, np.nan)); d = np.abs(np.diff(st)); d = d[np.isfinite(d) & (d < 3)]
    out["pitch_Hz"] = float(np.median(f[v])); out["pitch_change_st"] = float(np.median(d))
    out["voiced_pct"] = float(100 * (v & act).sum() / max(1, act.sum()))
    ok = v & act
    ss = st[ok] - np.nanmedian(st[ok])
    out["loud_per_st"] = float(np.polyfit(ss, dB[ok], 1)[0]) if ok.sum() > 10 else np.nan
    loud = ok & (dB > np.nanmax(dB) - 15)
    fm = [np.nanmedian([F.get_value_at_time(i, q) for q in t[loud][::2]]) for i in (1, 2, 3, 4)]
    out["VTL_cm"] = vtl(fm)[1]
    f3 = np.array([F.get_value_at_time(3, q) for q in t[loud][::2]])
    out["F3_low"] = float(np.nanpercentile(f3, 5))
    f0w, tw = pw.harvest(x, SR, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(x, f0w, tw, SR); fq = np.linspace(0, SR / 2, sp.shape[1])
    L = 10 * np.log10(sp[:, fq < 5000] + 1e-20); e = 10 * np.log10(sp.sum(1) + 1e-20)
    a = e > e.max() - 30; both = a[1:] & a[:-1]
    fl = np.sqrt(np.mean(np.diff(L, axis=0) ** 2, 1))[both]
    out["flux"] = float(np.median(fl)); out["flux_p95"] = float(np.percentile(fl, 95))
    vv = (f0w > 0) & (e > e.max() - 20)
    k = 12; tr = np.convolve(np.pad(e, k // 2, mode="edge"), np.ones(k) / k, "valid")[: len(e)]
    out["loud_flutter"] = float(np.std((e - tr)[vv])) if vv.sum() > 10 else np.nan
    return out


def main():
    rows = []
    for grp, d in (("positive", POS), ("negative", NEG)):
        for name, p in d.items():
            if not Path(p).exists():
                print("missing", p); continue
            r = features(p); r.update(name=name, group=grp); rows.append(r)
            print(f"{grp[:3]} {name:40} " + " ".join(f"{NICE[k][:8]}={r[k]:.2f}" for k in FEATS[:6]))
    with open(ROOT / "analysis/negative_space.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["group", "name"] + FEATS); w.writeheader()
        w.writerows([{k: r.get(k) for k in ["group", "name"] + FEATS} for r in rows])

    pos = np.array([[r[k] for k in FEATS] for r in rows if r["group"] == "positive"])
    lo, hi = np.nanmin(pos, 0), np.nanmax(pos, 0)
    mu, sd = np.nanmean(pos, 0), np.nanstd(pos, 0) + 1e-9
    span = np.maximum(hi - lo, 1e-9)
    # distance outside his range, in units of his range width (0 = inside)
    def outside(v):
        return np.where(v < lo, (lo - v) / span, np.where(v > hi, (v - hi) / span, 0.0))
    names = [r["name"] for r in rows]
    M = np.array([[r[k] for k in FEATS] for r in rows])
    Out = np.array([outside(m) for m in M])
    signed = np.where(M < lo, -Out, Out)

    fig, ax = plt.subplots(figsize=(18, 10))
    ax.imshow(np.clip(signed, -2, 2), cmap="coolwarm", aspect="auto", vmin=-2, vmax=2)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]; s = f"{v:.0f}" if abs(v) >= 100 else (f"{v:.1f}" if abs(v) >= 1 else f"{v:.2f}")
            ax.text(j, i, s, ha="center", va="center", fontsize=7, fontweight="bold" if Out[i, j] > 0 else "normal")
    npos = int((np.array([r["group"] for r in rows]) == "positive").sum())
    ax.axhline(npos - 0.5, color="k", lw=2)
    ax.set_xticks(range(len(FEATS))); ax.set_xticklabels([NICE[k] for k in FEATS], rotation=35, ha="right")
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names)
    ax.set_title("What he is NOT. Above the line: approved (they define his range). Below: rejected / failures.\n"
                 "White = inside his range; red = above it; blue = below it (bold = outside).")
    plt.tight_layout(); plt.savefig(ROOT / "analysis/negative_space.png", dpi=70); plt.close()

    # which measures catch which failures
    neg_idx = [i for i, r in enumerate(rows) if r["group"] == "negative"]
    print("\nMeasures that separate him from each failure:")
    for i in neg_idx:
        caught = [(NICE[FEATS[j]], signed[i, j]) for j in np.argsort(-Out[i]) if Out[i, j] > 0][:5]
        print(f"  {names[i]:40} " + ", ".join(f"{n} {'high' if s > 0 else 'low'} ({abs(s):.1f})" for n, s in caught))
    print("\nHow many failures each measure catches:")
    for j in np.argsort(-(Out[neg_idx] > 0).sum(0)):
        print(f"  {NICE[FEATS[j]]:22} {(Out[neg_idx, j] > 0).sum():2}/{len(neg_idx)}   his range {lo[j]:.2f} .. {hi[j]:.2f}")
    np.save(ROOT / "analysis/negative_space_ranges.npy", dict(feats=FEATS, lo=lo, hi=hi, mu=mu, sd=sd), allow_pickle=True)


if __name__ == "__main__":
    main()
