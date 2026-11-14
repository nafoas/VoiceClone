"""Every tunable knob of Prince's voice, in one place.

Each field is meant to be adjusted by ear. Defaults are a starting point,
not a verdict. See VOICE_SPEC.md for what each one is trying to achieve.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class StyleMod:
    """How one delivery style (from the text markup) bends the base voice."""

    pitch_st: float = 0.0        # extra pitch, semitones
    range_mul: float = 1.0       # multiplies pitch range (expressiveness)
    gain_db: float = 0.0         # loudness change
    breath_mul: float = 1.0      # multiplies breathiness (lower = firmer)
    speed_mul: float = 1.0       # multiplies speaking rate


@dataclass
class Params:
    # --- base model -------------------------------------------------------
    # Kokoro voice, or a weighted blend: "af_heart:0.7,af_nicole:0.3"
    voice: str = "af_heart"
    speed: float = 0.85          # overall rate; reference is unhurried (~270 ms/syllable)

    # --- instrument (body transform, WORLD vocoder) ------------------------
    pitch_st: float = 3.0        # pitch shift, semitones
    pitch_range: float = 0.8     # <1 flattens leftover melody, >1 exaggerates it
    # forward resonances: low region (F1) scaled by formant_low, upper region
    # (F2, F3...) by formant_high, blended between the two frequencies
    formant_low: float = 0.95
    formant_high: float = 1.40
    formant_low_hz: float = 700.0
    formant_high_hz: float = 2200.0
    hum_db: float = 20.0         # THE hum: drop everything above the 2nd harmonic by this much
    hum_start: float = 1.6       #   cliff starts at this multiple of pitch
    hum_end: float = 3.0         #   and is fully down here
    roundness: float = 0.0       # extra spectral tilt (superseded by hum), dB/octave above roundness_hz
    roundness_hz: float = 480.0  #   (the humming, fundamental-heavy tone)
    breathiness: float = 0.4     # 0..1; tuned so noise level matches the reference (still cleaner than normal speech)
    nasality: float = 0.2        # 0..1, nasal resonance
    nasal_pole_hz: float = 380.0
    nasal_zero_hz: float = 1100.0
    softness: float = 0.5        # 0..1, gentle roll-off above 5 kHz
    legato: float = 0.4          # 0..1, evens out loudness inside a phrase

    # --- frame transplant (rebuild voiced sound from the reference clip) ----
    transplant: float = 0.0      # 0 = off, 1 = every voiced frame is his real sound
    transplant_jump: float = 0.6 # higher = longer runs of his real transitions
    transplant_hold: float = 0.15
    transplant_ref: str = ""     # reference wav ("" = reference/source/prince_reference.wav)

    # --- terraced pitch ----------------------------------------------------
    terrace: float = 0.9         # 0 = TTS melody, 1 = dead-flat plateau per word
    step_st: float = 3.0         # stressed words step up by this much
    repeat_step_st: float = -1.2 # repeated word steps down (peet peet peet)
    onset_fall_st: float = 5.0   # quick fall into the first word of a phrase
    chirp_st: float = 6.0        # little pitch chirp on p/t/k/b/d/g word onsets
    end_flick_st: float = 2.0    # small upward flick at the very end of a phrase

    # --- sound rules (VOICE_SPEC.md / REFERENCE_ANALYSIS.md) ---------------
    soft_s: bool = True          # s -> alveolo-palatal [ɕ]
    z_mode: str = "sh"           # z -> "sh" ([ɕ], devoiced) | "zh" ([ʒ]) | "keep"
    lengthen_before_s: bool = True  # stressed vowel before word-final s/z gets weight
    de_ess_db: float = 6.0       # extra attenuation on remaining hiss
    full_vowels: bool = True     # unstressed -er stays full: nanner -> nannar
    round_uh: str = "off"        # global ʌ -> "u"|"ʊ"|"off". Prefer per-word entries in lexicon.json (moneys -> munis)
    final_t: bool = True         # final t fades before consonants; peet peet -> pee teet

    # --- timing ------------------------------------------------------------
    gap_s: float = 0.06          # between phrases in one sentence
    sentence_gap_s: float = 0.22
    ellipsis_pause_s: float = 0.6
    stretch_speed: float = 0.55  # rate for stretched sounds (awwww, hmmmm)

    # --- styles (driven by punctuation / caps in the text) -----------------
    excited: StyleMod = field(default_factory=lambda: StyleMod(
        pitch_st=2.5, range_mul=1.2, gain_db=2.5, breath_mul=0.5, speed_mul=1.06))
    caps: StyleMod = field(default_factory=lambda: StyleMod(
        pitch_st=4.5, range_mul=1.3, gain_db=4.5, breath_mul=0.25, speed_mul=1.10))
    soft: StyleMod = field(default_factory=lambda: StyleMod(
        pitch_st=-0.5, range_mul=0.8, gain_db=-3.0, breath_mul=1.3, speed_mul=0.94))
    eager_question_rise_st: float = 3.0   # extra end-rise for "??"

    # ------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Params":
        p = cls()
        for f in fields(cls):
            if f.name not in d:
                continue
            v = d[f.name]
            if isinstance(getattr(p, f.name), StyleMod):
                v = StyleMod(**v)
            setattr(p, f.name, v)
        return p

    @classmethod
    def load(cls, path: str | Path) -> "Params":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n")

    def set(self, key: str, value: str) -> None:
        """Set a field from a string, e.g. set('caps.gain_db', '5')."""
        obj, name = self, key
        if "." in key:
            head, name = key.split(".", 1)
            obj = getattr(self, head)
        cur = getattr(obj, name)
        if isinstance(cur, bool):
            val = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(cur, (int, float)):
            val = type(cur)(float(value))
        else:
            val = value
        setattr(obj, name, val)
