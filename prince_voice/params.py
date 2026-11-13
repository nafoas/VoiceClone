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
    speed: float = 0.92          # overall speaking rate (1.0 = model default)

    # --- instrument (body transform, WORLD vocoder) ------------------------
    pitch_st: float = 3.0        # pitch shift, semitones
    pitch_range: float = 0.8     # <1 flattens melody, >1 exaggerates it
    formant_shift: float = 1.25  # >1 = smaller vocal tract (main "small" cue)
    breathiness: float = 0.30    # 0..1, air in the voice
    nasality: float = 0.35       # 0..1, nasal resonance
    nasal_pole_hz: float = 380.0
    nasal_zero_hz: float = 1100.0
    softness: float = 0.5        # 0..1, gentle high-frequency roll-off

    # --- soft S ------------------------------------------------------------
    soft_s: bool = True          # s -> alveolo-palatal [ɕ]
    z_mode: str = "sh"           # z -> "sh" ([ɕ], devoiced) | "zh" ([ʒ]) | "keep"
    lengthen_before_s: bool = True  # vowel before word-final s/z gets weight
    de_ess_db: float = 6.0       # extra attenuation on remaining hiss

    # --- timing ------------------------------------------------------------
    gap_s: float = 0.10          # between phrases in one sentence
    sentence_gap_s: float = 0.28
    ellipsis_pause_s: float = 0.65
    stretch_speed: float = 0.55  # rate for stretched sounds (awwww, hmmmm)

    # --- styles (driven by punctuation / caps in the text) -----------------
    excited: StyleMod = field(default_factory=lambda: StyleMod(
        pitch_st=2.0, range_mul=1.35, gain_db=2.5, breath_mul=0.5, speed_mul=1.06))
    caps: StyleMod = field(default_factory=lambda: StyleMod(
        pitch_st=3.5, range_mul=1.5, gain_db=4.5, breath_mul=0.25, speed_mul=1.10))
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
