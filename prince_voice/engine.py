"""PrinceVoice: text in Prince's idiolect -> audio in Prince's voice.

Pipeline:  markup -> phonemes (lexicon + soft S) -> Kokoro base TTS
           -> body transform (WORLD) -> per-style loudness -> assembled line
"""

from __future__ import annotations

import warnings

import numpy as np
import torch

from . import markup
from .body import BodySettings, WordPitch, transform
from .params import Params, StyleMod
from .phonemes import Phonemizer

SR = 24000
warnings.filterwarnings("ignore")


def _trim(a: np.ndarray, db: float = -42.0, pad_s: float = 0.015) -> tuple[np.ndarray, int]:
    """Trim silence; returns (audio, samples removed from the start)."""
    if len(a) == 0:
        return a, 0
    env = np.abs(a)
    thr = env.max() * 10 ** (db / 20)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return a[:0], 0
    pad = int(pad_s * SR)
    start = max(0, idx[0] - pad)
    return a[start: idx[-1] + pad], start


def _legato(y: np.ndarray, amount: float) -> np.ndarray:
    """Even out loudness inside a phrase (the reference barely moves: +-5 dB)."""
    if amount <= 0 or len(y) < SR * 0.05:
        return y
    n = int(0.03 * SR)
    env = np.sqrt(np.convolve(y**2, np.ones(n) / n, mode="same")) + 1e-9
    active = env > env.max() * 10 ** (-30 / 20)
    if not active.any():
        return y
    ref = np.median(env[active])
    gain = np.where(active, (env / ref) ** (-0.6 * amount), 1.0)
    gain = np.clip(gain, 0.5, 2.0)
    gain = np.convolve(gain, np.ones(n) / n, mode="same")
    return (y * gain).astype(np.float32)


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

    def base_tts(self, phonemes, speed: float, voice: str):
        """phonemes: str, or misaki tokens. Returns audio, or with tokens
        (audio, [(word, phonemes, start_s, end_s), ...])."""
        chunks, words, offset = [], [], 0.0
        for r in self.pipe.generate_from_tokens(phonemes, voice=self.voice_tensor(voice), speed=speed):
            if r.audio is None:
                continue
            a = r.audio.numpy()
            for t in (r.tokens or []) if not isinstance(phonemes, str) else []:
                if t.start_ts is not None and any(c.isalpha() for c in t.text):
                    words.append((t.text, t.phonemes, offset + t.start_ts, offset + t.end_ts))
            chunks.append(a)
            offset += len(a) / SR
        audio = np.concatenate(chunks) if chunks else np.zeros(0, np.float32)
        return audio if isinstance(phonemes, str) else (audio, words)

    def word_pitch(self, words, p: Params) -> list[WordPitch]:
        """Terraced plateaus: unstressed words sit a little low, the last
        stressed word steps up, repeated words step down."""
        stressed = [i for i, w in enumerate(words) if "ˈ" in w[1]]
        last = stressed[-1] if stressed else -1
        out, prev = [], None
        for i, (text, ph, a, b) in enumerate(words):
            if i not in stressed:
                level = -1.0
            elif i == last and len(words) > 1:
                level = p.step_st
            else:
                level = 0.0
            if prev is not None and text.lower() == prev[0].lower():
                level = prev[1] + p.repeat_step_st
            chirp = bool(ph) and ph.lstrip("ˈˌ")[:1] in "ptkbdɡT"
            out.append(WordPitch(a, b, level, chirp))
            prev = (text, level)
        return out

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
        toks = self.phonemize.tokens(seg.text, p)
        if not "".join(t.phonemes for t in toks).strip(" .,!?"):
            return np.zeros(0, np.float32)
        st = self._style(seg, p)
        speed = p.speed * st.speed_mul
        if seg.stretch:
            speed = min(speed, max(0.35, p.stretch_speed - 0.03 * (seg.stretch - 1)))
        audio, words = self.base_tts(toks, speed, p.voice)
        audio, cut = _trim(audio)
        if raw or len(audio) == 0:
            return audio
        words = [(w, ph, a - cut / SR, b - cut / SR) for w, ph, a, b in words]
        body = BodySettings(
            pitch_st=p.pitch_st + st.pitch_st,
            pitch_range=p.pitch_range * st.range_mul,
            formant_low=p.formant_low, formant_high=p.formant_high,
            formant_low_hz=p.formant_low_hz, formant_high_hz=p.formant_high_hz,
            roundness=p.roundness, roundness_hz=p.roundness_hz,
            breathiness=float(np.clip(p.breathiness * st.breath_mul, 0, 1)),
            nasality=p.nasality, nasal_pole_hz=p.nasal_pole_hz, nasal_zero_hz=p.nasal_zero_hz,
            softness=p.softness, de_ess_db=p.de_ess_db,
            terrace=p.terrace, onset_fall_st=p.onset_fall_st, chirp_st=p.chirp_st,
            end_flick_st=p.end_flick_st if seg.question == 0 else 0.0,
            end_rise_st=p.eager_question_rise_st if seg.question == 2 else 0.0,
            words=self.word_pitch(words, p),
        )
        y = transform(audio, SR, body)
        y = _legato(y, p.legato)
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
