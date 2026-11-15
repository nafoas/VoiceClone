"""Everything about his "ee", over time and cycle by cycle, vs the model.

Not just the average spectrum: how it CHANGES, which is what separates a
living voice from a "computery" one.

  per cycle   period, peak, RMS; shape stability (correlation of each cycle
              with the next); open/closed look of the waveform
  over time   pitch, loudness, F1/F2/F3, H1-H2, bright-band level (3-5 kHz),
              spectral movement (flux) frame to frame
  noise       noise between harmonics per band, and how steady it is in time
  envelope    onset (how it starts) and offset (how it ends)

    python analysis/physics/ee_props.py MODEL_PREFIX  (e.g. out/build/ee_tone_)
      -> analysis/physics/ee_props.json, ee_props_*.png
"""
import json, sys, warnings
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
from parselmouth.praat import call
from scipy.signal import resample_poly

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SR = 24000
HIS = [(0.79, 0.99, "after n, phrase-final (+ɕ)"), (1.52, 1.60, "after p"), (1.77, 1.90, "after tʰ"),
       (2.09, 2.30, "after tʰ, phrase-final")]


def load_his(s, e, pad=0.03):
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    return resample_poly(x[int((s - pad) * sr): int((e + pad) * sr)], SR, sr), pad


def cycles(snd, f0min=150, f0max=700):
    pp = call(snd, "To PointProcess (periodic, cc)", f0min, f0max)
    n = call(pp, "Get number of points")
    return np.array([call(pp, "Get time from index", i + 1) for i in range(n)])


def props(x, t0=0.0, t1=None):
    snd = pm.Sound(x, SR); dur = snd.duration; t1 = t1 or dur
    out = {}
    # per cycle
    tc = cycles(snd); tc = tc[(tc > t0) & (tc < t1)]
    if len(tc) > 6:
        per = np.diff(tc); out["n_cycles"] = len(per)
        out["period_cv_pct"] = float(np.std(np.diff(per)) / np.mean(per) * 100 / np.sqrt(2))   # cycle-to-cycle
        segs = [x[int(a * SR): int(b * SR)] for a, b in zip(tc[:-1], tc[1:])]
        L = int(np.median([len(s) for s in segs]))
        cyc = np.array([np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(s)), s) for s in segs if len(s) > 4])
        rms = np.sqrt(np.mean(cyc ** 2, 1)); out["rms_cv_pct"] = float(np.std(np.diff(rms)) / np.mean(rms) * 100 / np.sqrt(2))
        cc = [np.corrcoef(a, b)[0, 1] for a, b in zip(cyc[:-1], cyc[1:])]
        out["shape_corr"] = float(np.median(cc)); out["shape_corr_p10"] = float(np.percentile(cc, 10))
        out["mean_cycle"] = (cyc.mean(0) / (np.abs(cyc.mean(0)).max() + 1e-9)).tolist()
    # over time (5 ms)
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
    I = snd.to_intensity(minimum_pitch=150, time_step=0.005)
    ts = np.arange(t0 + 0.01, t1 - 0.01, 0.005)
    tr = {"t": ts.tolist(), "f0": [P.get_value_at_time(t) for t in ts], "dB": [I.get_value(t) for t in ts]}
    for i in (1, 2, 3):
        tr[f"F{i}"] = [F.get_value_at_time(i, t) for t in ts]
    # spectral frames: H1-H2, bright band, flux
    n = int(0.03 * SR); win = np.hanning(n); fq = np.fft.rfftfreq(4096, 1 / SR)
    H12, BR, SPEC = [], [], []
    for t, f0 in zip(ts, tr["f0"]):
        c = int(t * SR); seg = x[max(0, c - n // 2): c + n // 2]
        if len(seg) < n or not np.isfinite(f0):
            H12.append(np.nan); BR.append(np.nan); continue
        S = 20 * np.log10(np.abs(np.fft.rfft(seg * win, 4096)) + 1e-9); SPEC.append(S[fq < 6000])
        h1 = S[(fq > .8 * f0) & (fq < 1.2 * f0)].max(); h2 = S[(fq > 1.8 * f0) & (fq < 2.2 * f0)].max()
        H12.append(h1 - h2); BR.append(10 * np.log10(np.mean(10 ** (S[(fq > 3000) & (fq < 5000)] / 10))) - h1)
    tr["H1H2"] = H12; tr["bright"] = BR
    SPEC = np.array(SPEC)
    if len(SPEC) > 3:
        fl = np.sqrt(np.mean(np.diff(SPEC, axis=0) ** 2, 1)); out["flux_med"] = float(np.median(fl))
    for k in ("f0", "dB", "F1", "F2", "F3", "H1H2", "bright"):
        v = np.array(tr[k], float); v = v[np.isfinite(v)]
        if len(v) > 4:
            mid = v[len(v) // 5: -len(v) // 5] if len(v) > 10 else v
            out[f"{k}_mean"] = float(np.mean(mid)); out[f"{k}_sd"] = float(np.std(mid))
            out[f"{k}_trend"] = float(mid[-1] - mid[0]) if len(mid) > 1 else 0.0
    out["track"] = tr
    # envelope: onset (10->90% of peak level) and offset
    env = np.array(tr["dB"], float); env = env[np.isfinite(env)]
    if len(env) > 5:
        pk = env.max(); out["onset_ms"] = float(5 * np.argmax(env > pk - 3)); out["offset_ms"] = float(5 * (len(env) - 1 - np.where(env > pk - 3)[0][-1]))
    return out


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "out/build/ee_tone_")
    model_files = sorted(Path(prefix).parent.glob(Path(prefix).name + "*.wav"))
    model_files = [p for p in model_files if p.stem.split("_")[-1].isdigit()]
    rows = []
    for (s, e, ctx) in HIS:
        x, pad = load_his(s, e)
        r = props(x, pad, pad + (e - s)); r["who"] = "him"; r["ctx"] = ctx; r["f0"] = r.get("f0_mean"); rows.append(r)
    for p in model_files:
        y, sr = sf.read(p); y = resample_poly(y, SR, sr) if sr != SR else y
        r = props(y); r["who"] = "model"; r["ctx"] = p.stem; rows.append(r)
    keys = ["f0_mean", "period_cv_pct", "rms_cv_pct", "shape_corr", "shape_corr_p10", "flux_med", "f0_sd", "dB_sd",
            "F1_sd", "F2_sd", "F3_sd", "H1H2_sd", "bright_sd", "F1_trend", "F2_trend", "f0_trend", "dB_trend", "onset_ms", "offset_ms"]
    print(f"{'':28}" + "".join(f"{k[:11]:>12}" for k in keys))
    for r in rows:
        print(f"{r['who'] + ' ' + r['ctx'][:22]:28}" + "".join(f"{r.get(k, np.nan):12.2f}" for k in keys))
    (ROOT / "analysis/physics/ee_props.json").write_text(json.dumps(rows, default=float))
    # figure: waveform cycles + tracks
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    hs = [r for r in rows if r["who"] == "him"]; ms = [r for r in rows if r["who"] == "model"]
    fig, ax = plt.subplots(3, 4, figsize=(20, 11))
    for j in range(4):
        for r, c, lab in ((hs[j], "#c0392b", "him"), (ms[j] if j < len(ms) else None, "#2c3e50", "model")):
            if r is None or "mean_cycle" not in r:
                continue
            ax[0, j].plot(np.linspace(0, 1, len(r["mean_cycle"])), r["mean_cycle"], color=c, label=lab)
            tr = r["track"]; t = np.array(tr["t"]) - tr["t"][0]
            ax[1, j].plot(t, np.array(tr["F1"]), color=c, alpha=.8); ax[1, j].plot(t, np.array(tr["F2"]) / 8, "--", color=c, alpha=.8)
            ax[2, j].plot(t, tr["dB"], color=c); ax2 = ax[2, j]
        ax[0, j].set_title(f"one cycle (average): {hs[j]['ctx']}"); ax[0, j].legend(fontsize=8)
        ax[1, j].set_title("F1 (solid), F2/8 (dashed) over time"); ax[2, j].set_title("loudness over time (dB)")
    plt.tight_layout(); plt.savefig(ROOT / "analysis/physics/ee_props.png", dpi=65)


if __name__ == "__main__":
    main()
