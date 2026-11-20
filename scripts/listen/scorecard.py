"""Perceptual scorecard: measures that track what a listener hears, not just spectra.

Run with the SPARC environment's python (torch, transformers). For each model render (aligned to the
clip's timeline) and the clip itself:
  diction    : a phoneme recogniser (wav2vec2 lv-60 espeak) every 20 ms; Jensen-Shannon distance
               between the clip's and the model's phoneme probabilities over his speech, and what
               phonemes it hears per sound (n heard as l? t heard as k?)
  gesture    : SPARC articulator trajectories from the model's audio vs from the clip (z-scored)
  speaker    : WavLM speaker-verification similarity to the clip (same speaker?)
  age/child  : audeering age/gender model: apparent age and probability of a child voice
  hum/warmth : first tone over second, energy below 600 Hz vs 600-3000 Hz, in voiced sounds
  smoothness : loudness flutter (dB) vs a 30 ms smooth track, inside sounds

    python scorecard.py clip.wav name1=model1.wav name2=model2.wav ...   (16 kHz mono, same timeline)
"""
import json
import sys

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn
from transformers import (AutoFeatureExtractor, Wav2Vec2ForCTC, Wav2Vec2Model, Wav2Vec2PreTrainedModel,
                          Wav2Vec2Processor, WavLMForXVector)

SR = 16000
torch.set_num_threads(4)
SEGS = json.loads(open(sys.argv[1].replace(".wav", "_segs.json")).read())   # [[lab, s, e], ...]


class _Head(nn.Module):
    def __init__(self, config, n):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, n)

    def forward(self, x):
        return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(x)))))


class AgeGender(Wav2Vec2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.wav2vec2 = Wav2Vec2Model(config)
        self.age = _Head(config, 1)
        self.gender = _Head(config, 3)
        self.post_init()

    def forward(self, x):
        h = self.wav2vec2(x)[0].mean(1)
        return self.age(h), torch.softmax(self.gender(h), 1)


PH_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"
ph_proc = Wav2Vec2Processor.from_pretrained(PH_ID); ph_model = Wav2Vec2ForCTC.from_pretrained(PH_ID).eval()
VOCAB = {v: k for k, v in ph_proc.tokenizer.get_vocab().items()}
sv_fe = AutoFeatureExtractor.from_pretrained("microsoft/wavlm-base-plus-sv")
sv_model = WavLMForXVector.from_pretrained("microsoft/wavlm-base-plus-sv").eval()
AG_ID = "audeering/wav2vec2-large-robust-24-ft-age-gender"
ag_proc = Wav2Vec2Processor.from_pretrained(AG_ID); ag_model = AgeGender.from_pretrained(AG_ID).eval()


def phon_probs(w):
    with torch.no_grad():
        x = ph_proc(w, sampling_rate=SR, return_tensors="pt").input_values
        return torch.softmax(ph_model(x).logits[0], -1).numpy()   # (frames, vocab), 20 ms


def decode(P, lo, hi):
    ids = P[lo:hi].argmax(1); out = []; prev = -1
    for i in ids:
        if i != prev and VOCAB[int(i)] not in ("<pad>", "<s>", "</s>", "<unk>"):
            out.append(VOCAB[int(i)])
        prev = i
    return "".join(out)


def heard(P, s, e):
    """Most probable phonemes (blank excluded) over a sound, with probabilities."""
    k = slice(int(s / 0.02), max(int(s / 0.02) + 1, int(e / 0.02)))
    p = P[k].mean(0).copy(); p[ph_proc.tokenizer.pad_token_id] = 0; p /= p.sum()
    top = np.argsort(-p)[:3]
    return " ".join(f"{VOCAB[int(i)]}:{p[i]:.2f}" for i in top)


def js(p, q):
    m = 0.5 * (p + q)
    kl = lambda a, b: np.sum(a * (np.log(a + 1e-9) - np.log(b + 1e-9)), -1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def speaker_vec(w):
    with torch.no_grad():
        x = sv_fe(w, sampling_rate=SR, return_tensors="pt")
        e = sv_model(**x).embeddings[0]
        return (e / e.norm()).numpy()


def age(w):
    with torch.no_grad():
        x = ag_proc(w, sampling_rate=SR, return_tensors="pt").input_values
        a, g = ag_model(x)
        return float(a[0, 0]) * 100, g[0].numpy()   # years; female, male, child


def warmth(w):
    out = []
    for lab, s, e in SEGS:
        if lab in ("ɕ", "tʰ", "p", "_"):
            continue
        seg = w[int(s * SR): int(e * SR)]
        if len(seg) < 400:
            continue
        S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; f = np.fft.rfftfreq(len(seg), 1 / SR)
        out.append(10 * np.log10(S[f < 600].sum() / (S[(f >= 600) & (f < 3000)].sum() + 1e-20)))
    return float(np.mean(out))


def flutter(w):
    from scipy.ndimage import uniform_filter1d
    n = int(0.008 * SR); res = []
    for lab, s, e in SEGS:
        ts = np.arange(s + 0.012, e - 0.012, 0.002)
        if len(ts) < 20:
            continue
        en = np.array([10 * np.log10(np.mean(w[int(t * SR) - n // 2: int(t * SR) + n // 2] ** 2) + 1e-12) for t in ts])
        res += list(np.abs(en - uniform_filter1d(en, 15)))
    return float(np.percentile(res, 95))


clip, _ = sf.read(sys.argv[1])
items = [("clip", clip)] + [(a.split("=")[0], sf.read(a.split("=")[1])[0]) for a in sys.argv[2:]]
speech = np.zeros(int(len(clip) / SR / 0.02) + 2, bool)
for lab, s, e in SEGS:
    speech[int(s / 0.02): int(e / 0.02)] = True
Pc = phon_probs(clip)
phr = [(0.03, 1.14), (1.435, 2.33)]
ec = speaker_vec(np.concatenate([clip[int(a * SR): int(b * SR)] for a, b in phr]))
res = {}
for name, w in items:
    w = w[: len(clip)] if len(w) >= len(clip) else np.pad(w, (0, len(clip) - len(w)))
    P = phon_probs(w); n = min(len(P), len(Pc)); sp = speech[:n]
    d = float(np.mean(js(Pc[:n][sp], P[:n][sp])))
    sv = float(np.dot(ec, speaker_vec(np.concatenate([w[int(a * SR): int(b * SR)] for a, b in phr]))))
    ag, g = age(np.concatenate([w[int(a * SR): int(b * SR)] for a, b in phr]))
    res[name] = dict(diction_js=round(d, 3), speaker_sim=round(sv, 3), age=round(ag, 1), child=round(float(g[2]), 2),
                     female=round(float(g[0]), 2), warmth=round(warmth(w), 1), flutter95=round(flutter(w), 2),
                     heard=" | ".join(decode(P, int(a / 0.02), int(b / 0.02)) for a, b in phr),
                     per_sound={f"{lab}@{s:.2f}": heard(P, s, e) for lab, s, e in SEGS})
    print(f"{name:14} diction {d:.3f}  speaker {sv:.3f}  age {ag:5.1f}  child {g[2]:.2f}  female {g[0]:.2f}  "
          f"warmth {res[name]['warmth']:5.1f}  flutter95 {res[name]['flutter95']:.2f}  heard: {res[name]['heard']}", flush=True)
json.dump(res, open(sys.argv[1].replace(".wav", "_scores.json"), "w"), ensure_ascii=False, indent=1)
