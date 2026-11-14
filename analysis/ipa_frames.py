"""Frame-level measurements of the reference clip for IPA transcription.
Writes analysis/ipa_frames.csv and zoomed spectrograms with Praat formant tracks."""
import numpy as np, parselmouth as pm, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

snd = pm.Sound("reference/source/prince_reference.wav").convert_to_mono()
# small vocal tract -> allow a high formant ceiling
form = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000, window_length=0.02)
pitch = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
inten = snd.to_intensity(minimum_pitch=120, time_step=0.005)
harm = snd.to_harmonicity_cc(time_step=0.005, minimum_pitch=120)
spec_t = np.arange(0.0, snd.duration, 0.01)

rows = []
for t in spec_t:
    f = [form.get_value_at_time(i, t) for i in (1, 2, 3)]
    b = [form.get_bandwidth_at_time(i, t) for i in (1, 2)]
    seg = snd.extract_part(max(0, t - 0.015), min(snd.duration, t + 0.015))
    sp = seg.to_spectrum()
    lo = sp.get_band_energy(0, 600); hi = sp.get_band_energy(600, 5000); fr = sp.get_band_energy(3500, 12000)
    tot = sp.get_band_energy(0, 12000) + 1e-20
    rows.append([t, pitch.get_value_at_time(t), inten.get_value(t), harm.get_value(t), *f, *b,
                 10 * np.log10(lo / (hi + 1e-20) + 1e-20), fr / tot])
R = np.array(rows, dtype=float)
hdr = "t,f0,dB,HNR,F1,F2,F3,B1,B2,low_vs_mid_dB,fric_ratio"
np.savetxt("analysis/ipa_frames.csv", R, delimiter=",", header=hdr, fmt="%.3f", comments="")

S = snd.to_spectrogram(window_length=0.012, maximum_frequency=6000)
X, Y = S.x_grid(), S.y_grid(); Z = 10 * np.log10(S.values + 1e-20)
for name, (a, b) in {"nannar": (0.0, 0.64), "munis": (0.56, 1.2), "peets": (1.4, 2.42)}.items():
    fig, ax = plt.subplots(2, 1, figsize=(16, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax[0].pcolormesh(X, Y, Z, vmin=Z.max() - 70, cmap="Greys", shading="auto")
    m = (R[:, 0] >= a) & (R[:, 0] <= b)
    for i, c in zip((4, 5, 6), ("red", "blue", "green")):
        ax[0].plot(R[m, 0], R[m, i], ".", color=c, ms=5, label=f"F{i-3}")
    ax[0].set_xlim(a, b); ax[0].set_ylim(0, 6000); ax[0].legend(loc="upper right")
    ax[0].set_xticks(np.arange(a, b, 0.02), minor=True); ax[0].set_xticks(np.round(np.arange(a, b, 0.05), 2))
    ax[0].grid(which="both", axis="x", alpha=0.25); ax[0].set_title(name)
    ax[1].plot(R[m, 0], R[m, 2], label="intensity dB"); ax[1].plot(R[m, 0], R[m, 9] + 40, label="low/mid ratio +40 (nasal murmur high)")
    ax[1].plot(R[m, 0], R[m, 10] * 100, label="fricative % (>3.5k)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(f"analysis/ipa_{name}.png", dpi=60); plt.close()
print("ok")
