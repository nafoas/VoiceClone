"""PrinceVoice: text in Prince's idiolect -> audio in Prince's voice.

Pipeline:  markup -> phonemes (lexicon + soft S) -> Kokoro base TTS
           -> body transform (WORLD) -> per-style loudness -> assembled line
"""

from __future__ import annotations

import warnings

import numpy as np
import torch

from . import markup
from .body import BodySettings, transform
from .params import Params, StyleMod
from .phonemes import Phonemizer

SR = 24000
warnings.filterwarnings("ignore")


def _trim(a: np.ndarray, db: float = -42.0, pad_s: float = 0.015) -> np.ndarray:
    if len(a) == 0:
        return a
    env = np.abs(a)
    thr = env.max() * 10 ** (db / 20)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return a[:0]
    pad = int(pad_s * SR)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


def _rms_db(a: np.ndarray) -> float:
    return 20 * np.log10(np.sqrt(np.mean(a**2)) + 1e-9)


def _fade(a: np.ndarray, ms: float = 8) -> np.ndarray:
    n = min(len(a) // 2, int(SR * ms / 1000))
    if n > 0:
        r = np.linspace(0, 1, n, dtype=a.dtype)
        a = a.copy()
        a[:n] *= r
        a[-n:] *= r[::-1]
    return a


class PrinceVoice:
    def __init__(self, params: Params | None = None):
        from kokoro import KPipeline

        self.params = params or Params()
        self.pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        self.phonemize = Phonemizer(self.pipe.g2p)
        self._voices: dict[str, torch.Tensor] = {}

    # -- base voice ---------------------------------------------------------
    def voice_tensor(self, spec: str) -> torch.Tensor:
        """'af_heart' or a weighted blend 'af_heart:0.7,af_nicole:0.3'."""
        if spec in self._voices:
            return self._voices[spec]
        parts = []
        for item in spec.split(","):
            name, _, w = item.strip().partition(":")
            parts.append((self.pipe.load_single_voice(name), float(w or 1)))
        total = sum(w for _, w in parts)
        v = sum(t * (w / total) for t, w in parts)
        self._voices[spec] = v
        return v

    def base_tts(self, phonemes: str, speed: float, voice: str) -> np.ndarray:
        chunks = [r.audio.numpy() for r in
                  self.pipe.generate_from_tokens(phonemes, voice=self.voice_tensor(voice), speed=speed)
                  if r.audio is not None]
        return np.concatenate(chunks) if chunks else np.zeros(0, np.float32)

    # -- style --------------------------------------------------------------
    def _style(self, seg: markup.Segment, p: Params) -> StyleMod:
        m = StyleMod()
        for on, mod in ((seg.excited, p.excited), (seg.caps, p.caps), (seg.soft, p.soft)):
            if on:
                if mod is p.excited and seg.caps:
                    continue  # caps supersedes excited
                m.pitch_st += mod.pitch_st
                m.range_mul *= mod.range_mul
                m.gain_db += mod.gain_db
                m.breath_mul *= mod.breath_mul
                m.speed_mul *= mod.speed_mul
        return m

    # -- render -------------------------------------------------------------
    def render_segment(self, seg: markup.Segment, p: Params, raw: bool = False) -> np.ndarray:
        ps = self.phonemize(seg.text, p)
        if not ps.strip(" .,!?"):
            return np.zeros(0, np.float32)
        st = self._style(seg, p)
        speed = p.speed * st.speed_mul
        if seg.stretch:
            speed = min(speed, max(0.35, p.stretch_speed - 0.03 * (seg.stretch - 1)))
        audio = _trim(self.base_tts(ps, speed, p.voice))
        if raw or len(audio) == 0:
            return audio
        body = BodySettings(
            pitch_st=p.pitch_st + st.pitch_st,
            pitch_range=p.pitch_range * st.range_mul,
            formant_shift=p.formant_shift,
            breathiness=float(np.clip(p.breathiness * st.breath_mul, 0, 1)),
            nasality=p.nasality,
            nasal_pole_hz=p.nasal_pole_hz,
            nasal_zero_hz=p.nasal_zero_hz,
            softness=p.softness,
            de_ess_db=p.de_ess_db,
            end_rise_st=p.eager_question_rise_st if seg.question == 2 else 0.0,
        )
        y = transform(audio, SR, body)
        y = y * 10 ** ((-20.0 - _rms_db(y) + st.gain_db) / 20)  # level per style
        return _fade(y)

    def render(self, text: str, params: Params | None = None, raw: bool = False) -> np.ndarray:
        p = params or self.params
        out: list[np.ndarray] = []
        segs = markup.parse(text)
        for i, seg in enumerate(segs):
            if seg.is_pause:
                out.append(np.zeros(int(p.ellipsis_pause_s * SR), np.float32))
                continue
            out.append(self.render_segment(seg, p, raw=raw))
            nxt = segs[i + 1] if i + 1 < len(segs) else None
            if nxt is not None and not nxt.is_pause:
                gap = p.sentence_gap_s if seg.sentence_end else p.gap_s
                out.append(np.zeros(int(gap * SR), np.float32))
        if not out:
            return np.zeros(0, np.float32)
        y = np.concatenate(out)
        peak = np.abs(y).max()
        if peak > 0.89:
            y = y * (0.89 / peak)
        return y.astype(np.float32)
