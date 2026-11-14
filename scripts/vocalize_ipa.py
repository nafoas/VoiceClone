"""Vocalize the reference clip's narrow IPA transcription, with the clip's own
timing and pitch, to test whether the transcription is right.

Kokoro normally predicts each phoneme's duration and a pitch curve. Here both
are replaced: durations come from analysis/IPA_TRANSCRIPTION.md and pitch is
the clip's measured pitch at the same moments. Only the voice differs.

    python scripts/vocalize_ipa.py            -> out/ipa_test/*.wav
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import numpy as np
import parselmouth as pm
import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SR = 24000
UNIT = 0.025  # Kokoro duration unit (s): 600 samples
REF = ROOT / "reference" / "source" / "prince_reference.wav"

# (kokoro symbols, ms, ref start time, fade_ms) from IPA_TRANSCRIPTION.md
# diacritics: ̃ nasal, ʰ aspirated, ː long. ɐ˞ is rendered as ɐ + ɹ.
PHRASES = [
    (0.05, [("n", 105), ("ã", 145), ("n", 75), ("ɐ", 95), ("ɹ", 50), ("m", 90),
            ("ũ", 120), ("n", 60), ("iː", 200), ("ɕ", 90)]),
    (1.465, [("p", 55), ("iː", 180, 100), ("tʰ", 45), ("iː", 230, 100),
             ("tʰ", 40), ("iː", 310, 100)]),
]
PAUSE_S = 0.34


def ref_pitch():
    snd = pm.Sound(str(REF)).convert_to_mono()
    p = snd.to_pitch_ac(time_step=UNIT / 2, pitch_floor=120, pitch_ceiling=900)
    return lambda t: p.get_value_at_time(t)


def ref_intensity():
    snd = pm.Sound(str(REF)).convert_to_mono()
    it = snd.to_intensity(minimum_pitch=120, time_step=UNIT / 2)
    return lambda t: it.get_value(t)


# Kokoro's energy track N vs. the clip's intensity: loud vowel (~74 dB) ~ N 8
def db_to_n(db: float) -> float:
    return 8.0 + (db - 74.0) / 3.5


def synth_phrase(model, voice, segs, t0, f0_at):
    vocab = model.vocab
    LEAD, TAIL = 18, 8  # natural boundary silences (Kokoro needs them; trimmed after)
    ids, durs, fades = [0], [LEAD], []
    t_units = LEAD
    for seg in segs:
        sym, ms = seg[0], seg[1]
        fade = seg[2] if len(seg) > 2 else 0
        chars = list(unicodedata.normalize("NFD", sym))  # ã -> a + ̃
        units = max(len(chars), round(ms / 1000 / UNIT))
        for k, c in enumerate(chars):
            if c not in vocab:
                raise KeyError(f"{c!r} not in Kokoro vocab")
            ids.append(vocab[c])
            durs.append(units - (len(chars) - 1) if k == 0 else 1)
        if fade:
            fades.append(((t_units + units) * UNIT - fade / 1000, (t_units + units) * UNIT))
        t_units += units
    ids.append(0); durs.append(TAIL)

    input_ids = torch.LongTensor([ids])
    ref_s = voice[len(ids) - 3]  # Kokoro picks style by phoneme count
    m = model
    with torch.no_grad():
        L = torch.tensor([input_ids.shape[-1]])
        mask = torch.zeros_like(input_ids).bool()
        bert = m.bert(input_ids, attention_mask=(~mask).int())
        d_en = m.bert_encoder(bert).transpose(-1, -2)
        s = ref_s[:, 128:]
        d = m.predictor.text_encoder(d_en, s, L, mask)
        dur = torch.tensor(durs)
        idx = torch.repeat_interleave(torch.arange(len(ids)), dur)
        aln = torch.zeros((len(ids), len(idx))); aln[idx, torch.arange(len(idx))] = 1
        en = d.transpose(-1, -2) @ aln.unsqueeze(0)
        F0, N = m.predictor.F0Ntrain(en, s)
        # replace pitch with the clip's: F0 frames are UNIT/2 long, phrase starts at
        # 2 boundary units before t0
        # inside the phrase, voicing/pitch and energy follow the clip exactly
        db_at = ref_intensity()
        lo, hi = LEAD * 2, t_units * 2
        for j in range(lo, min(hi, F0.shape[-1])):
            t_ref = t0 + (j - lo) * UNIT / 2
            f = f0_at(t_ref)
            F0[0, j] = float(f) if np.isfinite(f) else 0.0
            db = db_at(t_ref)
            if np.isfinite(db):
                N[0, j] = db_to_n(db)
        t_en = m.text_encoder(input_ids, L, mask)
        audio = m.decoder(t_en @ aln.unsqueeze(0), F0, N, ref_s[:, :128]).squeeze().numpy()
    env = np.ones_like(audio)
    tt = np.arange(len(audio)) / SR
    for a, b in fades:  # final t never closes: the vowel fades ~20 dB instead
        sel = (tt >= a) & (tt < b)
        env[sel] = 10 ** (-20 * (tt[sel] - a) / (b - a) / 20)
    after = tt >= t_units * UNIT
    env[after] = 0.0
    y = audio * env
    return y[int(LEAD * UNIT * SR):int(t_units * UNIT * SR)]


def main():
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    model = pipe.model
    f0_at = ref_pitch()
    out = ROOT / "out" / "ipa_test"
    out.mkdir(parents=True, exist_ok=True)
    for vname in ("af_heart", "af_nicole", "bf_emma"):
        voice = pipe.load_voice(vname)
        parts = []
        for i, (t0, segs) in enumerate(PHRASES):
            parts.append(synth_phrase(model, voice, segs, t0, f0_at))
            if i == 0:
                parts.append(np.zeros(int(PAUSE_S * SR), np.float32))
        y = np.concatenate(parts)
        y = y / np.abs(y).max() * 0.8
        sf.write(out / f"ipa_{vname}.wav", y, SR)
        print(out / f"ipa_{vname}.wav", f"{len(y)/SR:.2f}s")


if __name__ == "__main__":
    main()
