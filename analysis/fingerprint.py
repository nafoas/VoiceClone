"""Voice fingerprint: standard objective voice measures for Prince, per sound and
overall, against an ordinary adult voice (English TTS, same words) and published
child/woman vowel averages.

    python analysis/fingerprint.py   -> analysis/fingerprint_*.csv / *.png

Measures (per voiced sound unless noted):
  source   H1-H2, H1-A1, H1-A3 (fundamental vs 2nd harmonic / vs harmonics at
           F1 and F3: voice quality and "hum"), CPPS (clarity), jitter (local,
           %), shimmer (local, dB), HNR overall and in bands (0-500, 0.5-1.5k,
           1.5-2.5k, 2.5-3.5k)
  mouth    F1-F4 and bandwidths B1-B4, formant dispersion dF and the vocal tract
           length it implies (VTL = c / 2dF), nasality A1-P0 (vowels)
  noise    spectral centroid, peak, spread, skewness (fricatives, bursts)
  overall  f0 distribution, loudness-pitch coupling (dB per semitone), voiced
           fraction, syllable rate, formant transition speed by consonant
"""

import csv
import sys
from pathlib import Path

import numpy as np
import parselmouth as pm
from parselmouth.praat import call

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_catalogue import PHRASES  # noqa: E402

C = 35000.0  # speed of sound, cm/s

# Hillenbrand et al. (1995) vowel averages (F1, F2, F3), approximate
REF = {
    "women":    {"i": (437, 2761, 3372), "æ": (669, 2349, 2972), "ɑ": (936, 1551, 2815), "u": (459, 1105, 2735)},
    "children": {"i": (452, 3081, 3702), "æ": (1012, 2434, 3343), "ɑ": (1002, 1688, 2950), "u": (494, 1345, 2988)},
}


def vtl(formants):
    """Formant dispersion (Reby & McComb): Fi = (2i-1)/2 * dF -> dF by regression
    through the origin; VTL = c / (2 dF)."""
    f = np.array([x for x in formants if np.isfinite(x)])
    k = (2 * np.arange(1, len(f) + 1) - 1) / 2.0
    dF = float((k @ f) / (k @ k))
    return dF, C / (2 * dF)


def harm_amp(spec_db, fq, f):
    band = (fq > f * 0.9) & (fq < f * 1.1)
    return spec_db[band].max() if band.any() else np.nan


def source_measures(snd, s, e, F, P):
    part = snd.extract_part(s, e, preserve_times=True)
    rows = []
    for t in np.arange(s + 0.015, e - 0.015, 0.005):
        f0 = P.get_value_at_time(t)
        if not np.isfinite(f0):
            continue
        seg = snd.extract_part(t - 0.02, t + 0.02, preserve_times=True)
        x = seg.values[0] * np.hanning(len(seg.values[0]))
        S = 20 * np.log10(np.abs(np.fft.rfft(x, 16384)) + 1e-12); fq = np.fft.rfftfreq(16384, 1 / snd.sampling_frequency)
        h1, h2 = harm_amp(S, fq, f0), harm_amp(S, fq, 2 * f0)
        f1, f3 = F.get_value_at_time(1, t), F.get_value_at_time(3, t)
        a1 = harm_amp(S, fq, round(f1 / f0) * f0) if np.isfinite(f1) else np.nan
        a3 = harm_amp(S, fq, round(f3 / f0) * f0) if np.isfinite(f3) else np.nan
        # nasality: P0 = strongest harmonic near 250 Hz (below F1) vs A1
        p0 = harm_amp(S, fq, max(f0, round(250 / f0) * f0))
        rows.append((h1 - h2, h1 - a1, h1 - a3, a1 - p0))
    m = np.nanmedian(np.array(rows), 0) if rows else np.full(4, np.nan)
    out = dict(H1H2=m[0], H1A1=m[1], H1A3=m[2], A1P0=m[3])
    try:
        pp = call(part, "To PointProcess (periodic, cc)", 120, 900)
        out["jitter_pct"] = 100 * call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        out["shimmer_dB"] = call([part, pp], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    except Exception:
        out["jitter_pct"] = out["shimmer_dB"] = np.nan
    try:
        cep = call(part, "To PowerCepstrogram", 120, 0.002, 5000, 50)
        out["CPPS"] = call(cep, "Get CPPS", "yes", 0.02, 0.0005, 120, 900, 0.05, "parabolic", 0.001, 0.05,
                           "Exponential decay", "Robust")
    except Exception:
        out["CPPS"] = np.nan
    for lo, hi in ((0, 500), (500, 1500), (1500, 2500), (2500, 3500)):
        try:
            b = call(part, "Filter (pass Hann band)", lo, hi, 100)
            h = b.to_harmonicity_cc(time_step=0.005, minimum_pitch=120)
            v = h.values[h.values > -100]
            out[f"HNR_{lo}_{hi}"] = float(np.median(v)) if len(v) else np.nan
        except Exception:
            out[f"HNR_{lo}_{hi}"] = np.nan
    return out


def noise_measures(snd, s, e):
    part = snd.extract_part(s, e, preserve_times=True)
    sp = part.to_spectrum()
    peak_fq = None
    v = np.abs(sp.values[0] + 1j * sp.values[1]) ** 2; fq = np.linspace(0, sp.xmax, len(v))
    m = fq > 500
    peak_fq = float(fq[m][np.argmax(v[m])])
    return dict(centroid=sp.get_centre_of_gravity(2), spread=sp.get_standard_deviation(2),
                skew=sp.get_skewness(2), peak=peak_fq)


def measure_clip():
    snd = pm.Sound(str(ROOT / "reference/source/prince_reference.wav")).convert_to_mono()
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
    rows = []
    for ph in PHRASES:
        for lab, s, e, st in ph:
            if lab == "_":
                continue
            d = e - s
            r = dict(sound=lab, start=s, ms=round(1000 * d), stressed=st)
            mid = np.arange(s + 0.3 * d, e - 0.3 * d + 1e-9, 0.005)
            for i in (1, 2, 3, 4):
                r[f"F{i}"] = float(np.nanmedian([F.get_value_at_time(i, t) for t in mid]))
                r[f"B{i}"] = float(np.nanmedian([F.get_bandwidth_at_time(i, t) for t in mid]))
            r["f0"] = float(np.nanmedian([P.get_value_at_time(t) for t in mid]))
            if lab in ("ɕ", "p", "tʰ"):
                r.update(noise_measures(snd, s, e))
            else:
                r.update(source_measures(snd, s, e, F, P))
                if lab in ("ã", "ɐ˞", "ũ", "iː"):
                    r["dF"], r["VTL_cm"] = vtl([r["F1"], r["F2"], r["F3"], r["F4"]])
            rows.append(r)
    return snd, F, P, rows


def transitions(F, P):
    """Formant speed into/out of vowels at each consonant boundary (Hz/ms over
    the first/last 30 ms of the vowel)."""
    out = []
    for ph in PHRASES:
        for k in range(len(ph) - 1):
            a, b = ph[k], ph[k + 1]
            vowels = ("ã", "ɐ˞", "ũ", "iː")
            if a[0] in vowels and b[0] not in vowels and b[0] != "_":
                t0, t1, kind = a[2] - 0.03, a[2], f"{a[0]}→{b[0]}"
            elif b[0] in vowels and a[0] not in vowels and a[0] != "_":
                t0, t1, kind = b[1], b[1] + 0.03, f"{a[0]}→{b[0]}"
            else:
                continue
            f2a, f2b = F.get_value_at_time(2, t0), F.get_value_at_time(2, t1)
            f1a, f1b = F.get_value_at_time(1, t0), F.get_value_at_time(1, t1)
            out.append(dict(transition=kind, F2_from=f2a, F2_to=f2b, F2_speed=(f2b - f2a) / 30.0,
                            F1_speed=(f1b - f1a) / 30.0))
    return out


def overall(snd, P):
    it = snd.to_intensity(minimum_pitch=120, time_step=0.005)
    t = P.xs(); f = P.selected_array["frequency"]; v = f > 0
    dB = np.array([it.get_value(x) for x in t])
    ok = v & np.isfinite(dB)
    st = 12 * np.log2(f[ok] / np.median(f[ok]))
    slope = float(np.polyfit(st, dB[ok], 1)[0])
    return dict(f0_median=float(np.median(f[v])), f0_p10=float(np.percentile(f[v], 10)),
                f0_p90=float(np.percentile(f[v], 90)), loud_per_semitone=slope,
                voiced_pct=float(100 * v.mean()), pitch_st=st, dB=dB[ok])


def main():
    snd, F, P, rows = measure_clip()
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(ROOT / "analysis/fingerprint_sounds.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    tr = transitions(F, P)
    with open(ROOT / "analysis/fingerprint_transitions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tr[0])); w.writeheader(); w.writerows(tr)
    ov = overall(snd, P)
    # ordinary adult voice: same words, English TTS
    eng = pm.Sound(str(ROOT / "out/english_ref.wav"))
    Pe = eng.to_pitch_ac(time_step=0.005, pitch_floor=80, pitch_ceiling=600)
    ove = overall(eng, Pe)
    np.save(ROOT / "analysis/fingerprint_overall.npy", dict(prince=ov, english=ove), allow_pickle=True)
    for r in rows:
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()})
    print("transitions:", [(t["transition"], round(t["F2_speed"], 1)) for t in tr])
    print({k: round(v, 2) for k, v in ov.items() if not isinstance(v, np.ndarray)},
          {k: round(v, 2) for k, v in ove.items() if not isinstance(v, np.ndarray)})


if __name__ == "__main__":
    main()
