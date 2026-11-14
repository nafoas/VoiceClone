"""Frame-level detail around joins: what happens in the 60 ms either side.
Used to diagnose 'choking' (catches, roughness, loudness collapse, F1 collapse)."""
import numpy as np, parselmouth as pm

def detail(path, t_join, span=0.06, step=0.005):
    s = pm.Sound(str(path)).convert_to_mono()
    P = s.to_pitch_ac(time_step=step, pitch_floor=100, pitch_ceiling=900)
    I = s.to_intensity(minimum_pitch=150, time_step=step)
    H = s.to_harmonicity_cc(time_step=step, minimum_pitch=150)
    F = s.to_formant_burg(time_step=step, max_number_of_formants=5, maximum_formant=8000)
    ts = np.arange(t_join - span, t_join + span + 1e-9, 0.01)
    rows = [(t - t_join, P.get_value_at_time(t), I.get_value(t), H.get_value(t), F.get_value_at_time(1, t)) for t in ts]
    return rows

def summary(path, t_join, span=0.06):
    r = np.array([x[1:] for x in detail(path, t_join, span, 0.005)], float)
    f0, dB, hnr, f1 = r.T
    st = 12 * np.log2(f0)
    return dict(voice_breaks=int(np.sum(~np.isfinite(f0))), pitch_jump=float(np.nanmax(np.abs(np.diff(st)))) if np.isfinite(st).sum() > 2 else np.nan,
                loud_dip=float(np.nanmax(dB) - np.nanmin(dB)), hnr_min=float(np.nanmin(hnr)), f1_min=float(np.nanmin(f1)))
