"""The physics of Prince: which physical property makes which property of his voice.

Each experiment turns ONE physical knob in a physical model (his one-change bun
mouth + a standard glottal-flow source) and measures the result with exactly
the tools we measured him with (analysis/fingerprint.py: Praat + harmonics).

    python analysis/physics/lab.py  -> analysis/physics/results.json, *.png

Experiments
  E1  closure smoothness (how gently the folds close)  -> H1-H2, H1-A3
  E2  open quotient (how long the folds stay open)      -> H1-H2, H1-A3
  E3  F1 vs pitch (mouth openness, resonance tuning)    -> H1-A1, H3, H1-A3
  E4  velum (nose) coupling                             -> H1-A3, H1-H2, A1-P0, H3
  E5  glottal leak (folds not fully closing)            -> B1, HNR, H1-H2
  E6  breath noise (aspiration)                         -> HNR bands, CPPS
  E7  cycle-to-cycle variation                          -> jitter, shimmer
  E8  where the noise is made (frication place)         -> fricative centroid/peak
  E9  lip seal vs lip leak (aerodynamics)               -> voicing through p, burst strength
  E10 pitch by tension vs by breath pressure            -> loudness per semitone
  E11 fold tension (stress)                             -> pitch level
  E12 how quickly the mouth moves (time constant)       -> spectral movement (flux)
"""
import json, sys, warnings
from pathlib import Path

import numpy as np
import parselmouth as pm
from scipy.signal import fftconvolve, lfilter

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "analysis"))
from prince_voice.bunmouth import BunMouth, Pose, NAMES  # noqa: E402
from fingerprint import source_measures  # noqa: E402

SR = 48000
OUT = ROOT / "analysis/physics"
VOW = json.loads((ROOT / "models/bun_vowels.json").read_text())
M = BunMouth(VOW["size"], neck_mm=VOW["neck"])
POSE = {v: Pose.from_vec(d["pose"]) for v, d in VOW["vowels"].items()}
RNG = np.random.default_rng(1)

# a plain, ordinary "modal" voice to start every experiment from
BASE = dict(f0=264.0, Oq=0.6, am=0.66, Ta=0.15, asp=0.0, jit=0.003, shim=0.03, zg=None, velum=0.0)


# ---- source: glottal flow (KLGLOTT88-style pulse + Klatt's tilt + aspiration) ---------
def flow(f0, dur, Oq, am, Ta, asp, jit, shim, f0_track=None, amp_track=None):
    """Glottal volume flow. Oq: fraction of each cycle the folds are open.
    am: fraction of the open phase spent opening. Ta (ms): closure smoothness
    (how gradually the folds come together: a first-order low-pass on the flow,
    Klatt's spectral tilt). asp: breath noise, modulated by the flow."""
    n = int(dur * SR); u = np.zeros(n); t = 0.0; k = 0
    while True:
        F = f0 if f0_track is None else f0_track(t)
        T = 1.0 / F * (1 + jit * RNG.standard_normal())
        A = (1 + shim * RNG.standard_normal()) * (1 if amp_track is None else amp_track(t))
        s0 = int(round(t * SR)); L = int(round(T * SR))
        if s0 + L >= n:
            break
        To = Oq * L; Tp = am * To
        x = np.arange(L, dtype=float)
        p = np.where(x < Tp, 0.5 * (1 - np.cos(np.pi * x / Tp)),
                     np.where(x < To, np.cos(0.5 * np.pi * (x - Tp) / max(To - Tp, 1)), 0.0))
        u[s0:s0 + L] = A * np.clip(p, 0, None)
        t += T; k += 1
    if Ta > 0:
        a = np.exp(-1.0 / (Ta * 1e-3 * SR))
        u = lfilter([1 - a], [1, -a], u)
    if asp > 0:
        nz = RNG.standard_normal(n)
        nz = lfilter([1, -0.9], [1], nz)                     # breath noise is brighter than flow
        u = u + asp * nz * (0.2 + u / (u.max() + 1e-12))
    return u


def tract_ir(pose, zg=None, velum=None, n=8192):
    if velum is not None:
        v = pose.vec(); v[NAMES.index("velum")] = velum; pose = Pose.from_vec(v)
    f = np.fft.rfftfreq(n, 1 / SR)
    H = M.response(pose, np.maximum(f, 1.0), radiate=True, zg=zg)
    H[0] = 0
    ir = np.fft.irfft(H, n)
    return ir * np.hanning(2 * n)[n:]                         # gentle fade (causal decay)


def render(vowel, dur=0.7, **kw):
    q = dict(BASE); q.update(kw)
    u = flow(q["f0"], dur, q["Oq"], q["am"], q["Ta"], q["asp"], q["jit"], q["shim"])
    y = fftconvolve(u, tract_ir(POSE[vowel], q["zg"], q["velum"]))[: len(u)]
    return y / (np.abs(y).max() + 1e-12) * 0.8


# ---- measures (the ones we used on him) ---------------------------------------------
def harmonics(y, f0, nh=4):
    seg = y[int(0.2 * SR): int(0.6 * SR)]
    S = 20 * np.log10(np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 17)) + 1e-12)
    fq = np.fft.rfftfreq(1 << 17, 1 / SR)
    h = [S[(fq > f0 * (m - .3)) & (fq < f0 * (m + .3))].max() for m in range(1, nh + 1)]
    return [float(x - h[0]) for x in h]


def measure(y, f0=264.0):
    snd = pm.Sound(y, SR)
    F = snd.to_formant_burg(time_step=0.005, max_number_of_formants=5, maximum_formant=8000)
    P = snd.to_pitch_ac(time_step=0.005, pitch_floor=120, pitch_ceiling=900)
    r = source_measures(snd, 0.15, 0.6, F, P)
    ts = np.arange(0.25, 0.5, 0.01)
    r["B1"] = float(np.nanmedian([F.get_bandwidth_at_time(1, t) for t in ts]))
    r["F1"] = float(np.nanmedian([F.get_value_at_time(1, t) for t in ts]))
    h = harmonics(y, f0); r["H2"], r["H3"], r["H4"] = h[1], h[2], h[3]
    return {k: float(v) for k, v in r.items()}


def sweep(name, vowels, knob, values, **fixed):
    rows = []
    for v in vowels:
        for x in values:
            kw = dict(fixed); kw[knob] = x
            r = measure(render(v, **kw), kw.get("f0", BASE["f0"]))
            r.update(vowel=v, knob=knob, value=(x if x is not None else -1)); rows.append(r)
            print(f"  {name} {v:3} {knob}={x}: " + " ".join(f"{k}={r[k]:.1f}" for k in
                  ("H1H2", "H1A1", "H1A3", "H3", "B1", "HNR_0_500", "HNR_1500_2500", "jitter_pct", "shimmer_dB", "CPPS")), flush=True)
    return rows


# ---- E8: where the noise is made -------------------------------------------------------
def frication():
    """Noise made at a constriction excites only the cavity in front of it. A
    longer front cavity (constriction further back, tongue down) = lower peak."""
    f = np.linspace(500, 11500, 2000)
    rows = []
    base = Pose(jaw=0.2, body=0.7, front=0.9, tip=0.0, lips=0.6, velum=0.0)
    area, length, _, _ = M.tube(base)
    cum = np.cumsum(length[::-1])[::-1]                        # front-cavity length from section i
    for i in range(len(area) - 22, len(area) - 1):
        H = M.response(base, f, radiate=True, source_at=i)
        P = np.abs(H) ** 2 * (f / 1000.0) ** -1.0             # turbulence noise falls ~-3 dB/oct
        c = float(np.sum(f * P) / np.sum(P)); pk = float(f[np.argmax(P)])
        rows.append(dict(section=i, front_cm=float(cum[i]), centroid=c, peak=pk))
        print(f"  E8 noise at {cum[i]:.2f} cm behind the lips: centroid {c:.0f} Hz, peak {pk:.0f} Hz", flush=True)
    return rows


# ---- E9: lip seal vs leak (steady aerodynamics, orifice equation) -----------------------
def lips_aero(Ps=9.0, Ag=0.04, ptp=3.0):
    """Lungs -> glottis (area Ag) -> mouth -> lips (area Al). Mouth pressure
    Po = Ps * Ag^2 / (Ag^2 + Al^2). Voicing needs Ps - Po above the phonation
    threshold (~3 cmH2O); the burst at release scales with sqrt(Po)."""
    rows = []
    for Al in [0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08, 0.12]:
        Po = Ps * Ag ** 2 / (Ag ** 2 + Al ** 2)
        rows.append(dict(leak_cm2=Al, mouth_p=Po, across_folds=Ps - Po, voiced=bool(Ps - Po >= ptp),
                         burst_rel_db=float(10 * np.log10(max(Po, 1e-3) / Ps))))
        print(f"  E9 lip leak {Al:.3f} cm2: mouth {Po:.1f} cmH2O, across folds {Ps - Po:.1f} -> "
              f"{'voiced' if Ps - Po >= ptp else 'voicing stops'}; burst {rows[-1]['burst_rel_db']:+.1f} dB", flush=True)
    return rows


# ---- E10: pitch by tension vs pitch by breath pressure ---------------------------------
def loud_per_semitone(f0=264.0, Ps=9.0, hz_per_cm=3.0, db_per_doubling=9.0):
    """Raising pitch with more breath pressure also makes it louder (SPL rises
    ~8-9 dB per doubling of pressure; f0 rises ~2-4 Hz per cmH2O). Raising it
    with fold tension alone keeps loudness constant."""
    dHz = f0 * (2 ** (1 / 12) - 1)
    out = {}
    for share in (0.0, 0.25, 0.5, 1.0):                         # share of pitch made by pressure
        dP = share * dHz / hz_per_cm
        out[share] = float(db_per_doubling * np.log2((Ps + dP) / Ps))
        print(f"  E10 pitch made {int(share * 100)}% by breath pressure: {out[share]:+.2f} dB per semitone", flush=True)
    return out


# ---- E11: fold tension -> pitch (ideal string) -----------------------------------------
def pitch_from_stress(L_cm=0.45, rho=1.04):
    """f0 = 1/(2L) sqrt(stress/rho). Rabbit vocal folds are a few mm long."""
    out = {}
    for f0 in (215, 265, 390, 590):
        s = rho * (2 * L_cm * f0) ** 2 / 1e4                    # dyn/cm^2 -> kPa
        out[f0] = float(s)
        print(f"  E11 {f0} Hz needs fold stress ~{s:.1f} kPa (L={L_cm * 10:.1f} mm)", flush=True)
    return out


# ---- E12: how quickly his mouth moves -> spectral movement -----------------------------
def mouth_speed():
    seq = [("n", 105), ("ã", 145), ("n", 75), ("ɐ˞", 95), ("m", 90), ("ũ", 120), ("n", 60), ("iː", 210)]
    tgt = dict(POSE)
    vn = Pose.from_vec(POSE["iː"].vec()); v = vn.vec(); v[NAMES.index("tip")] = 1; v[NAMES.index("velum")] = 0.5
    tgt["n"] = Pose.from_vec(v)
    v = POSE["ũ"].vec(); v[NAMES.index("lips")] = 0; v[NAMES.index("velum")] = 0.5; tgt["m"] = Pose.from_vec(v)
    f = np.geomspace(90, 5000, 120)
    rows = []
    for tau in (3, 8, 15, 25, 40, 60):
        z = tgt["n"].vec().copy(); frames = []
        for ph, ms in seq:
            for _ in range(ms // 5):
                z = z + (tgt[ph].vec() - z) * (1 - np.exp(-5.0 / tau))
                frames.append(20 * np.log10(np.abs(M.response(Pose.from_vec(z), f)) + 1e-12))
        L = np.array(frames); fl = np.sqrt(np.mean(np.diff(L, axis=0) ** 2, 1))
        rows.append(dict(tau_ms=tau, flux=float(np.median(fl)), flux_p95=float(np.percentile(fl, 95))))
        print(f"  E12 mouth time constant {tau} ms: spectral movement median {rows[-1]['flux']:.2f}, "
              f"p95 {rows[-1]['flux_p95']:.2f} dB/frame", flush=True)
    return rows


def main():
    res = {}
    print("E1 closure smoothness"); res["E1"] = sweep("E1", ["iː", "ã"], "Ta", [0.0, 0.15, 0.4, 0.8, 1.5, 2.5])
    print("E2 open quotient"); res["E2"] = sweep("E2", ["iː", "ã"], "Oq", [0.4, 0.55, 0.7, 0.85, 0.95])
    print("E3 F1 vs pitch"); res["E3"] = sweep("E3", ["iː", "ũ", "ã"], "f0", [180, 215, 264, 330, 390, 440])
    print("E4 nose coupling"); res["E4"] = sweep("E4", ["iː", "ã"], "velum", [0.0, 0.1, 0.25, 0.5, 1.0])
    print("E5 glottal leak"); res["E5"] = sweep("E5", ["iː", "ã"], "zg", [None, 1000.0, 300.0, 100.0, 40.0])
    print("E6 breath noise"); res["E6"] = sweep("E6", ["iː"], "asp", [0.0, 0.003, 0.01, 0.03, 0.1])
    print("E7 cycle variation"); res["E7"] = sweep("E7", ["iː"], "jit", [0.0, 0.002, 0.005, 0.01, 0.02, 0.04])
    res["E7b"] = sweep("E7b", ["iː"], "shim", [0.0, 0.02, 0.05, 0.1, 0.2])
    print("E8 frication place"); res["E8"] = frication()
    print("E9 lips"); res["E9"] = lips_aero()
    print("E10 loudness vs pitch"); res["E10"] = loud_per_semitone()
    print("E11 pitch level"); res["E11"] = pitch_from_stress()
    print("E12 mouth speed"); res["E12"] = mouth_speed()
    (OUT / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
