"""Perceptual objective: render his phrase from a mouth, and judge it the way a listener would.

render(z, tp, opts) -> 48 kHz audio on the clip's timeline (his voice through his mouth, consonants
                       included; nothing applied after the mouth)
judge(y)            -> dict: diction (per-sound phoneme agreement with the clip), age, child,
                       speaker similarity, spectral likeness (the existing whole-phrase judge)

Runs in the SPARC environment (torch + transformers + the renderer).
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "scripts", ROOT / "scripts/build", ROOT / "analysis/physics"):
    sys.path.insert(0, str(p))
os.environ.setdefault("MOUTH_V1", "1"); os.environ.setdefault("FAST", "0.015"); os.environ.setdefault("NH", "40")
os.environ.setdefault("TRANS", "models/transitions_F14.json"); os.environ.setdefault("ZFILE", "models/mouth_inverse_F14.json")
sys.argv = sys.argv[:1]
import render_his as R  # noqa: E402
import consonants as CN  # noqa: E402
from transformers import (AutoFeatureExtractor, Wav2Vec2ForCTC, Wav2Vec2Model, Wav2Vec2PreTrainedModel,  # noqa: E402
                          Wav2Vec2Processor, WavLMForXVector)

torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "3")))
SR = 48000; SR16 = 16000
M = R.M
X, _ = sf.read(ROOT / "reference/source/prince_reference.wav"); X = X.mean(1)
import parselmouth as pm  # noqa: E402
_P = pm.Sound(X, SR).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=700)
TT, FF0 = _P.xs(), _P.selected_array["frequency"]
SEGS = [(l, s, e) for ph in R.PHRASES for l, s, e, _ in ph]


class _Head(nn.Module):
    def __init__(self, c, n):
        super().__init__()
        self.dense = nn.Linear(c.hidden_size, c.hidden_size); self.dropout = nn.Dropout(c.final_dropout)
        self.out_proj = nn.Linear(c.hidden_size, n)

    def forward(self, x):
        return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(x)))))


class AgeGender(Wav2Vec2PreTrainedModel):
    def __init__(self, c):
        super().__init__(c)
        self.config = c; self.wav2vec2 = Wav2Vec2Model(c); self.age = _Head(c, 1); self.gender = _Head(c, 3); self.post_init()

    def forward(self, x):
        h = self.wav2vec2(x)[0].mean(1)
        return self.age(h), torch.softmax(self.gender(h), 1)


_PH = "facebook/wav2vec2-lv-60-espeak-cv-ft"
ph_proc = Wav2Vec2Processor.from_pretrained(_PH); ph_model = Wav2Vec2ForCTC.from_pretrained(_PH).eval()
VOCAB = {v: k for k, v in ph_proc.tokenizer.get_vocab().items()}; BLANK = ph_proc.tokenizer.pad_token_id
sv_fe = AutoFeatureExtractor.from_pretrained("microsoft/wavlm-base-plus-sv")
sv_model = WavLMForXVector.from_pretrained("microsoft/wavlm-base-plus-sv").eval()
_AG = "audeering/wav2vec2-large-robust-24-ft-age-gender"
ag_proc = Wav2Vec2Processor.from_pretrained(_AG); ag_model = AgeGender.from_pretrained(_AG).eval()
PHR = [(R.PHRASES[0][0][1] - 0.02, R.PHRASES[0][-1][2] + 0.03), (R.PHRASES[1][0][1] - 0.02, R.PHRASES[1][-1][2] + 0.03)]


def to16(y):
    return resample_poly(y, 1, 3)


def phon_probs(w16):
    with torch.no_grad():
        x = ph_proc(w16, sampling_rate=SR16, return_tensors="pt").input_values
        return torch.softmax(ph_model(x).logits[0], -1).numpy()


def seg_dist(P, s, e):
    k = slice(int(s / 0.02), max(int(s / 0.02) + 1, int(round(e / 0.02))))
    p = P[k].mean(0).copy(); p[BLANK] = 0
    return p / max(p.sum(), 1e-9)


def speaker_vec(w16):
    with torch.no_grad():
        e = sv_model(**sv_fe(w16, sampling_rate=SR16, return_tensors="pt")).embeddings[0]
        return (e / e.norm()).numpy()


def age_child(w16):
    with torch.no_grad():
        a, g = ag_model(ag_proc(w16, sampling_rate=SR16, return_tensors="pt").input_values)
        return float(a[0, 0]) * 100, float(g[0, 2])


def phrases16(w):
    return np.concatenate([w[int(a * SR): int(b * SR)] for a, b in PHR])


X16 = to16(X / np.sqrt(np.mean(phrases16(X) ** 2)) * 0.05)
PC = phon_probs(X16)
CLIP_DIST = {(l, s): seg_dist(PC, s, e) for l, s, e in SEGS}
EC = speaker_vec(to16(phrases16(X)))
AGE_CLIP, CHILD_CLIP = age_child(to16(phrases16(X)))


def render(z=None, tp=None, cons=True):
    """His phrase from mouth z (and transitions tp, list per phrase of [[c,w,lips,velum], ...])."""
    if z is not None:
        R.Z[:] = z; R._ir.clear(); M.body(R.Z)
    tr = json.loads((ROOT / os.environ["TRANS"]).read_text())
    if tp is not None:
        for k_, p_ in tp.items():
            tr[k_]["par"] = p_
    R._TR_OVERRIDE = tr
    y = np.zeros(len(X)); spec = []
    for ph in R.PHRASES:
        y1, s0, e0, vs = R.render_phrase(ph, X, TT, FF0, R.bank())
        bt = np.arange(vs[0]["s"], vs[-1]["e"] + 0.005, 0.005)
        ins = np.array([any(v["s"] <= q <= v["e"] for v in vs) for q in bt])
        from scipy.ndimage import uniform_filter1d as uf
        bd = R.envelope_db(X, 0.0, bt) - R.envelope_db(y1, s0, bt)
        if os.environ.get("EFFORT", "copy") == "sound":
            # breath pressure changes slowly: one level per sound (its middle), gliding between sounds (60 ms);
            # the mouth makes the loudness changes at the joins by itself
            lev = []
            for v in vs:
                k = (bt >= v["s"] + 0.3 * (v["e"] - v["s"])) & (bt <= v["e"] - 0.3 * (v["e"] - v["s"]))
                lev.append((0.5 * (v["s"] + v["e"]), float(np.median(bd[k])) if k.any() else float(np.median(bd[ins]))))
            tk = np.array([q[0] for q in lev]); lk = np.array([q[1] for q in lev])
            sm_ = np.interp(bt, tk, lk); bd = uf(sm_, 13)                 # ~60 ms glide between levels
        bd = bd[ins] if os.environ.get("EFFORT", "copy") != "sound" else bd[ins]
        if os.environ.get("EFFORT", "copy") != "sound":
            bd = uf(bd, 5)
        bd -= bd.max(); bt = bt[ins]
        yy, s0, e0, vs = R.render_phrase(ph, X, TT, FF0, R.bank(), (bt, bd))
        if cons:
            yy = yy + CN.layer(ph, s0, len(yy), X, M, R.Z, yy)
        spec += R.frame_score(X, yy, s0, vs, None)
        # equal loudness to the clip over his voiced sounds (one fixed playback gain per phrase)
        rx = np.sqrt(np.mean(np.concatenate([X[int(v["s"] * SR): int(v["e"] * SR)] for v in vs]) ** 2))
        ry = np.sqrt(np.mean(np.concatenate([yy[int((v["s"] - s0) * SR): int((v["e"] - s0) * SR)] for v in vs]) ** 2))
        i0 = int(s0 * SR); y[i0: i0 + len(yy)] += yy[: len(y) - i0] * rx / ry
    return y, float(np.sqrt(np.mean(np.square([q[2] for q in spec]))))


def judge(y, spec=None, detail=False):
    w16 = to16(y / np.sqrt(np.mean(phrases16(y) ** 2) + 1e-20) * 0.05)
    P = phon_probs(w16)
    dd = {}
    for l, s, e in SEGS:
        p, q = CLIP_DIST[(l, s)], seg_dist(P, s, e)
        m = 0.5 * (p + q); kl = lambda a, b: float(np.sum(a * (np.log(a + 1e-9) - np.log(b + 1e-9))))
        dd[f"{l}@{s:.2f}"] = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    ph16 = to16(phrases16(y))
    ag, ch = age_child(ph16); sv = float(np.dot(EC, speaker_vec(ph16)))
    _v = np.sort(np.array(list(dd.values())))[::-1]
    out = dict(diction=float(np.mean(_v)), diction_worst=float(np.mean(_v[:4])), age=ag, child=ch, speaker=sv, spec=spec,
               envelope=env_dist(y), warmth=warmth(y) - WARM_CLIP)
    if detail:
        out["per_sound"] = dd
        out["heard"] = {k: " ".join(f"{VOCAB[int(i)]}:{seg_dist(P, s, e)[i]:.2f}" for i in np.argsort(-seg_dist(P, s, e))[:3])
                        for (k, (l, s, e)) in zip(dd, SEGS)}
    return out


def _env(y):
    n = int(0.01 * SR); out = []
    for a, b in PHR:
        for t in np.arange(a + 0.01, b - 0.01, 0.01):
            c = int(t * SR); out.append(10 * np.log10(np.mean(y[c - n: c + n] ** 2) + 1e-12))
    out = np.array(out); return np.maximum(out - out.max(), -45.0)


_ENV_CLIP = None


def env_dist(y):
    """Loudness every 10 ms across both phrases (consonants and gaps included) vs his, rms dB."""
    global _ENV_CLIP
    if _ENV_CLIP is None:
        _ENV_CLIP = _env(X)
    return float(np.sqrt(np.mean((_env(y) - _ENV_CLIP) ** 2)))


def warmth(y):
    out = []
    for l, s, e in SEGS:
        if l in ("ɕ", "tʰ", "p", "_"):
            continue
        seg = y[int(s * SR): int(e * SR)]
        S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; f = np.fft.rfftfreq(len(seg), 1 / SR)
        out.append(10 * np.log10(S[f < 600].sum() / (S[(f >= 600) & (f < 3000)].sum() + 1e-20)))
    return float(np.mean(out))


WARM_CLIP = None


def objective(o, w=dict(diction=14.0, worst=6.0, age=0.3, speaker=2.0, spec=0.2, envelope=0.15, warmth=0.3)):
    """Lower is better. Diction (JS, 0..0.69 per sound) dominates; apparent age toward his; same speaker;
    the spectral judge as a guard."""
    return (w["diction"] * o["diction"] + w["worst"] * o.get("diction_worst", 0) + w["age"] * abs(o["age"] - AGE_CLIP) + w["speaker"] * (1 - o["speaker"])
            + w["spec"] * (o["spec"] or 0) + w["envelope"] * o.get("envelope", 0) + w["warmth"] * abs(o.get("warmth", 0)))


WARM_CLIP = warmth(X)


if __name__ == "__main__":
    t = time.time(); y, sp = render(); t1 = time.time() - t
    o = judge(y, sp, detail=True); t2 = time.time() - t - t1
    print(f"render {t1:.1f}s judge {t2:.1f}s | clip age {AGE_CLIP:.1f} child {CHILD_CLIP:.2f}")
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items() if k not in ("per_sound", "heard")}, "objective", round(objective(o), 3))
    for k in o["heard"]:
        print(f"  {k:10} JS {o['per_sound'][k]:.2f}  heard {o['heard'][k]}")
    sf.write(ROOT / "out/listen/perc_test.wav", y / np.abs(y).max() * 0.7, SR)
