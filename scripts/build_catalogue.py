"""Build Prince's phoneme catalogue from the labelled reference clip.

Segment times come from analysis/IPA_TRANSCRIPTION.md, as one ordered sequence
per phrase, so every instance knows its sub-phoneme context: left and right
neighbour, pitch, stress, and position in the phrase. Steady sounds are stored
per instance as two halves (the first half is coloured by the left neighbour,
the second by the right) plus their natural micro-movement. Dynamic sounds
(bursts) keep their full frame sequence and real audio.

    python scripts/build_catalogue.py   -> models/catalogue.npz
"""

import json
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
SR, FRAME_MS = 24000, 5.0

# The clip as ordered sounds: (label, start, end, stressed syllable?)
# "_" = closure silence. Phrase edges count as "#".
PHRASES = [
    [("n", 0.05, 0.155, True), ("ã", 0.155, 0.30, True), ("n", 0.30, 0.375, False),
     ("ɐ˞", 0.375, 0.47, False), ("ɹ", 0.47, 0.52, False), ("m", 0.52, 0.61, True),
     ("ũ", 0.61, 0.73, True), ("n", 0.73, 0.79, False), ("iː", 0.79, 0.99, False),
     ("ɕ", 1.02, 1.11, False)],
    [("p", 1.455, 1.525, True), ("iː", 1.52, 1.60, True), ("_", 1.70, 1.715, False),
     ("tʰ", 1.712, 1.772, True), ("iː", 1.77, 1.90, True), ("_", 2.00, 2.04, False),
     ("tʰ", 2.04, 2.08, True), ("iː", 2.09, 2.30, True)],
]
SEGMENTS = {}
CONTEXT = {}   # (label, start) -> context
for ph in PHRASES:
    for k, (lab, s0, e0, st) in enumerate(ph):
        if lab == "_":
            continue
        SEGMENTS.setdefault(lab, []).append((s0, e0))
        CONTEXT[(lab, s0)] = dict(
            left=ph[k - 1][0] if k > 0 else "#", right=ph[k + 1][0] if k + 1 < len(ph) else "#",
            stress=st, initial=k == 0, final=k == len(ph) - 1)
# bursts: recorded examples kept whole (audio + frames)
SEGMENTS["p"] = [(1.455, 1.525)]                    # weak lip release + rising transition
SEGMENTS["tʰ"] = [(1.712, 1.772), (2.035, 2.09)]    # crisp burst + aspiration (both t's)
# his hummy S: partly voiced (the hum continues under the hiss) and ending in a
# tiny voiced puff; kept as real audio, from the vowel's fade into it to the puff
SEGMENTS["ɕ"] = [(1.00, 1.15)]
# fade tails: the quiet humming decay after a vowel whose final t never closes,
# keyed by the vowel instance it follows
TAILS = {1.52: (1.60, 1.70), 1.77: (1.90, 2.00), 2.09: (2.30, 2.47)}   # last one decays to ~2.46
DYNAMIC = {"p", "tʰ", "ɕ"}
VOICED = {"n", "ã", "ɐ˞", "ɹ", "m", "ũ", "iː", "p", "tʰ"}


def main():
    a, sr = sf.read(ROOT / "reference/source/prince_reference.wav")
    x = resample_poly(a.mean(1), SR, sr)
    f0, t = pw.harvest(x, SR, frame_period=FRAME_MS, f0_floor=60, f0_ceil=900)
    sp, ap = pw.cheaptrick(x, f0, t, SR), pw.d4c(x, f0, t, SR)
    labels, store, voiced, dyn, f0s = [], {}, [], [], []
    instances = {}
    for i, (lab, spans) in enumerate(SEGMENTS.items()):
        if lab in DYNAMIC:
            fr = np.linspace(0, SR / 2, ap.shape[1]); band = (fr > 300) & (fr < 4000)
            dyn_inst = []
            for k, (s, e) in enumerate(spans):
                m = (t >= s) & (t < e)
                store[f"dsp_{i}_{k}"], store[f"dap_{i}_{k}"] = sp[m], ap[m]
                store[f"dwav_{i}_{k}"] = x[int(s * SR): int(e * SR)].astype(np.float32)
                store[f"dvm_{i}_{k}"] = ((f0[m] > 0) & (ap[m][:, band].mean(1) < 0.5)).astype(np.int8)
                store[f"dvf_{i}_{k}"] = (f0[m] > 0).astype(np.int8)   # any voicing (hum under a hiss)
                fv_ = f0[m][f0[m] > 0]
                rec_f0 = float(np.median(fv_)) if len(fv_) else 0.0
                after = (t >= e) & (t < e + 0.05) & (f0 > 0)
                # does this burst lead into the phrase's last syllable?
                nxt_final = any(ph[-1][1] >= e - 0.03 and any(abs(sg[1] - s) < 0.02 for sg in ph) for ph in PHRASES
                                if ph[-1][0] != "_" and ph[-1][1] - e < 0.05)
                dyn_inst.append(dict(span=[s, e], f0=float(np.median(f0[after])) if after.any() else 0.0,
                                     next_final=bool(nxt_final), rec_f0=rec_f0))
            instances[lab] = dyn_inst
            s, e = spans[0]
            m = (t >= s) & (t < e)
            S, A = sp[m], ap[m]
            store[f"wav_{i}"] = x[int(s * SR): int(e * SR)].astype(np.float32)  # real burst audio
            store[f"vm_{i}"] = ((f0[m] > 0) & (A[:, band].mean(1) < 0.5)).astype(np.int8)  # tone, not noise
            f = float(np.median(f0[m][f0[m] > 0])) if (f0[m] > 0).any() else 0.0
        else:
            S_all, A_all, F = [], [], []
            inst = []
            for k, (s, e) in enumerate(spans):
                d = e - s
                m = (t >= s + d * 0.25) & (t < e - d * 0.25)
                S_all.append(np.log(sp[m] + 1e-20)); A_all.append(ap[m]); F.append(f0[m])
                # per-instance: snapshot + natural micro-movement (residual trajectory)
                mm = (t >= s + d * 0.1) & (t < e - d * 0.1)
                Lm = np.log(sp[mm] + 1e-20)
                snap = np.median(np.log(sp[m] + 1e-20), 0)
                fv = f0[m][f0[m] > 0]
                store[f"isp_{i}_{k}"] = snap
                store[f"iap_{i}_{k}"] = np.median(ap[m], 0)
                store[f"ires_{i}_{k}"] = (Lm - Lm.mean(0)).astype(np.float32)
                # halves: first coloured by the left neighbour, second by the right
                halves = {}
                for side, (a0, a1) in (("L", (s + d * 0.1, s + d * 0.5)), ("R", (s + d * 0.5, e - d * 0.1))):
                    mh = (t >= a0) & (t < a1)
                    store[f"i{side}_{i}_{k}"] = np.median(np.log(sp[mh] + 1e-20), 0)
                    store[f"ia{side}_{i}_{k}"] = np.median(ap[mh], 0)
                    fh = f0[mh][f0[mh] > 0]
                    halves[f"f0{side}"] = float(np.median(fh)) if len(fh) else 0.0
                # full recorded trajectory of each half (real movement, for trajectory mode)
                mid = s + d / 2
                for side, (a0, a1) in (("L", (s, mid)), ("R", (mid, e))):
                    mh = (t >= a0) & (t < a1)
                    store[f"iT{side}_{i}_{k}"] = np.log(sp[mh] + 1e-20).astype(np.float32)
                    # his real pitch micro-movement in this half (semitones, mean 0)
                    fh = f0[mh].astype(float); vh = fh > 0
                    if vh.sum() >= 2:
                        stt = 12 * np.log2(np.where(vh, fh, 1.0))
                        idx_ = np.arange(len(fh))
                        stt = np.interp(idx_, idx_[vh], stt[vh])
                        stt -= stt.mean()
                    else:
                        stt = np.zeros(len(fh))
                    store[f"iP{side}_{i}_{k}"] = stt.astype(np.float32)
                    store[f"iTa{side}_{i}_{k}"] = ap[mh].astype(np.float32)
                # this instance's own hum: how far its 3rd harmonic sits below the
                # 1st, compared with ordinary speech (~-11 dB) -> cliff depth
                fqs = np.linspace(0, SR / 2, sp.shape[1]); hd = []
                for q in np.where(m & (f0 > 0))[0]:
                    a1 = np.interp(f0[q], fqs, sp[q]); a3 = np.interp(3 * f0[q], fqs, sp[q])
                    hd.append(-(10 * np.log10(a3 / a1 + 1e-20) + 11.0))
                hum_db = float(np.clip(np.median(hd), 0, 40)) if hd else 0.0
                tail = TAILS.get(round(s, 3)) if lab == "iː" else None
                if tail:
                    mt = (t >= tail[0]) & (t < tail[1])
                    store[f"itail_{i}_{k}"] = np.log(sp[mt] + 1e-20).astype(np.float32)
                    store[f"itaila_{i}_{k}"] = ap[mt].astype(np.float32)
                    fr_ = np.linspace(0, SR / 2, ap.shape[1]); bd = (fr_ > 300) & (fr_ < 4000)
                    # voiced only where still tonal: his tail turns to breath before it ends
                    store[f"itailvm_{i}_{k}"] = ((f0[mt] > 0) & (ap[mt][:, bd].mean(1) < 0.6)).astype(np.int8)
                inst.append(dict(span=[s, e], f0=float(np.median(fv)) if len(fv) else 0.0,
                                 has_tail=bool(tail), hum_db=hum_db, **halves, **CONTEXT[(lab, s)]))
            instances[lab] = inst
            S = np.exp(np.median(np.vstack(S_all), 0))
            A = np.median(np.vstack(A_all), 0)
            Fv = np.concatenate(F); Fv = Fv[Fv > 0]
            f = float(np.median(Fv)) if len(Fv) else 0.0
        store[f"sp_{i}"], store[f"ap_{i}"] = S, A
        labels.append(lab); voiced.append(lab in VOICED); dyn.append(lab in DYNAMIC); f0s.append(f)
        print(f"{lab:3} {'dynamic ' + str(len(S)) + ' frames' if lab in DYNAMIC else 'steady':18} f0 {f:5.0f}")
    meta = dict(labels=labels, voiced=voiced, dynamic=dyn, f0=f0s, instances=instances,
                source="reference/source/prince_reference.wav", frame_ms=FRAME_MS)
    out = ROOT / "models"; out.mkdir(exist_ok=True)
    np.savez(out / "catalogue.npz", meta=json.dumps(meta, ensure_ascii=False), **store)
    print("saved models/catalogue.npz")


if __name__ == "__main__":
    main()
