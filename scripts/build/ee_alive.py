"""Step 1d: his "ee" alive (Da Boss on 1c: "very, very, very computery").

Research (analysis/physics/ee_props.py): cycle-level steadiness already matched;
what was missing is that his mouth and breath are never frozen:
  - timbre flickers fast (hum depth +-0.5-1.1 dB, bright band +-0.7-3.4 dB):
    the folds close slightly differently every cycle
  - the mouth moves: out of the consonant before (after p: F2 rises ~310 Hz),
    toward what follows, and small slow drift (a living tongue and jaw)
  - breath pressure swells gently (+-0.2-0.7 dB)
  - a small noise floor ~20 dB under the bright band (glottal turbulence)
  - phrase-final: a long tail (~150 ms)

All physical, all ordinary bun physiology. Shared: ONE "ee" target, ONE voice.

    python scripts/build/ee_alive.py -> out/build/ee_alive_*.wav, models/build_ee_alive.json
"""
import itertools, json, sys, warnings
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "analysis/physics"))
from prince_voice.bunmouth import BunMouth, Pose, NAMES  # noqa: E402
from prince_voice import voicebox as VB  # noqa: E402
import ee_props as EP  # noqa: E402
import tone as T  # noqa: E402

FIT = json.loads((ROOT / "models/build_ee_tone.json").read_text())
M = BunMouth(0.75, neck_mm=FIT["neck"], larcav=tuple(FIT["larcav"]))
EE = Pose.from_vec(FIT["pose"])
OUT = ROOT / "out/build"


def with_(p, **kw):
    v = p.vec().copy()
    for k, x in kw.items():
        v[NAMES.index(k)] = x
    return Pose.from_vec(v)


# each of his "ee"s: where the mouth comes from, where it goes, pitch, length (ms)
CASES = [
    dict(f0=264, ms=200, start=with_(EE, tip=1.0, velum=0.5), end="tail", ctx="after n, phrase-final"),
    dict(f0=391, ms=80, start=with_(EE, lips=0.02), end=with_(EE, tip=1.0), ctx="after p", rise=True),
    dict(f0=350, ms=130, start=with_(EE, tip=1.0), end=with_(EE, tip=1.0), ctx="after tʰ"),
    dict(f0=331, ms=210, start=with_(EE, tip=1.0), end="tail", ctx="after tʰ, phrase-final"),
]
TAIL = with_(EE, lips=0.25, velum=0.35, jaw=0.05)          # mouth closing, hum carries on through the nose
DRIFT = dict(body=0.03, front=0.03, jaw=0.02, lips=0.03, root=0.05)


def render_case(c, voice, drift_scale, seed):
    tail_ms = 150 if c["end"] == "tail" else 0
    n_ms = 30 + c["ms"] + tail_ms + 30
    f0 = np.full(n_ms, float(c["f0"]))
    if c.get("rise"):                                        # out of a burst the pitch rises in from below
        f0[:60] = c["f0"] * 2 ** (np.linspace(-1.0, 0, 60) / 12)
    if tail_ms:
        f0[-(tail_ms + 30):] *= 2 ** (np.linspace(0, -0.8, tail_ms + 30) / 12)
    t = np.arange(n_ms)
    amp = np.clip((t - 5) / 25, 0, 1)                        # breath swells in
    if tail_ms:
        a0 = 30 + c["ms"]; amp = np.where(t > a0, 10 ** (-np.clip(t - a0, 0, None) / tail_ms * 30 / 20), amp)
    amp = amp * np.clip((n_ms - 5 - t) / 20, 0, 1)
    nf = n_ms // 5
    end = TAIL if c["end"] == "tail" else c["end"]
    end_frames = (tail_ms // 5) if tail_ms else 4
    rng = np.random.default_rng(seed)
    drift = {k: v * drift_scale for k, v in DRIFT.items()} if drift_scale > 0 else None
    poses = VB.pose_track(nf, EE, rng, drift=drift, start=c["start"], tau_ms=20.0, end=end, end_frames=end_frames)
    y = VB.render(M, poses, f0, amp, voice, seed=seed)
    return y / (np.abs(y).max() + 1e-12) * 0.7


def measure(y, c):
    y24 = resample_poly(y, 1, 2)
    a = 0.03 + 0.2 * c["ms"] / 1000; b = 0.03 + c["ms"] / 1000
    p = EP.props(y24, a, b)
    tn = T.analyse(y24[int(a * 24000): int(b * 24000)], 24000, "m")
    return p, tn


def main():
    hisP = [EP.props(*EP.load_his(s, e)[:1], EP.load_his(s, e)[1], EP.load_his(s, e)[1] + (e - s)) for s, e, _ in EP.HIS]
    hisT = T.his_rows()
    def score(ps, tns, idx):
        e = 0.0
        for p, tn, j in zip(ps, tns, idx):
            h, ht = hisP[j], hisT[j]
            e += abs(p.get("bright_sd", 0) - h["bright_sd"]) / 1.0 + abs(p.get("H1H2_sd", 0) - h["H1H2_sd"]) / 0.4
            e += abs(p.get("dB_sd", 0) - h["dB_sd"]) / 0.3 + abs(p.get("F1_sd", 0) - h["F1_sd"]) / 5
            e += abs(tn["N3000"] - ht["N3000"]) / 5 + abs(tn["N1500"] - ht["N1500"]) / 5
        return e / len(idx)
    base = FIT["source"]
    grid = []
    for sv, tb, ds, sw in itertools.product((0.0, 0.04, 0.08, 0.12), (0.0, 0.01, 0.02, 0.04), (0.0, 0.6, 1.2), (0.0, 0.3)):
        v = VB.Voice(Oq=base["Oq"], am=base["am"], Ta_ms=base["Ta_ms"], shape_var=sv, turbulence=tb, swell_db=sw)
        ps, tns = [], []
        for j in (0, 2):
            y = render_case(CASES[j], v, ds, seed=j); p, tn = measure(y, CASES[j]); ps.append(p); tns.append(tn)
        grid.append((score(ps, tns, (0, 2)), sv, tb, ds, sw))
    grid.sort()
    for g in grid[:5]:
        print(f"  score {g[0]:.2f}: shape variation {g[1]}, turbulence {g[2]}, mouth drift x{g[3]}, breath swell {g[4]} dB")
    _, sv, tb, ds, sw = grid[0]
    v = VB.Voice(Oq=base["Oq"], am=base["am"], Ta_ms=base["Ta_ms"], shape_var=sv, turbulence=tb, swell_db=sw)
    x, sr = sf.read(ROOT / "reference/source/prince_reference.wav"); x = x.mean(1)
    gap = np.zeros(int(0.35 * 24000)); pieces = []; files = []
    for j, c in enumerate(CASES):
        y = render_case(c, v, ds, seed=10 + j)
        f = OUT / f"ee_alive_{c['f0']}.wav"; sf.write(f, resample_poly(y, 1, 2), 24000); files.append(f)
        s, e, _ = EP.HIS[j]
        real = resample_poly(x[int((s - 0.02) * sr): int((e + (0.15 if c["end"] == "tail" else 0.03)) * sr)], 1, 2)
        pieces += [real / np.abs(real).max() * 0.7, gap, resample_poly(y, 1, 2), gap, gap]
    sf.write(OUT / "ee_alive_him_vs_model.wav", np.concatenate(pieces), 24000)
    print("\n                      bright_sd H1H2_sd  dB_sd  F1_sd  F2_sd | noise 1.5-3k  3-5k")
    for j, c in enumerate(CASES):
        y, _ = sf.read(files[j]); p, tn = measure(resample_poly(y, 2, 1), c)
        h, ht = hisP[j], hisT[j]
        for who, a, b in (("him", h, ht), ("model", p, tn)):
            print(f"  {who:5} {c['f0']} {c['ctx'][:12]:12} {a.get('bright_sd', np.nan):6.2f} {a.get('H1H2_sd', np.nan):7.2f} "
                  f"{a.get('dB_sd', np.nan):6.2f} {a.get('F1_sd', np.nan):6.1f} {a.get('F2_sd', np.nan):6.1f} | "
                  f"{b['N1500']:8.0f} {b['N3000']:6.0f}")
    (ROOT / "models/build_ee_alive.json").write_text(json.dumps(dict(
        base=FIT, voice=v.__dict__, drift={k: x_ * ds for k, x_ in DRIFT.items()}, grid_best=grid[:5]), indent=1, default=float))


if __name__ == "__main__":
    main()
