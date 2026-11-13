"""Text -> phonemes, with Prince's lexicon and the soft-S rule.

The text is the phonology: we pronounce exactly what is written. The only rule
the voice adds on top is the soft S (VOICE_SPEC.md): s/z become the
alveolo-palatal [ɕ] (tongue tip down, body raised forward), and the vowel before
a word-final s/z carries a little extra weight.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .params import Params

LEXICON_PATH = Path(__file__).with_name("lexicon.json")
VOWELS = set("aeiouæɑɒɔəɛɜɪʊʌɐɚᵻ")
STRESS = set("ˈˌ")


def load_lexicon(path: Path = LEXICON_PATH) -> dict[str, str]:
    data = json.loads(path.read_text())
    return {k.lower(): v for k, v in data.items() if not k.startswith("_")}


def _collapse(word: str) -> str:
    return re.sub(r"([a-z])\1{2,}", r"\1", word.lower())


def normalize_case(text: str) -> str:
    """ALL CAPS lines would otherwise be read as acronyms."""
    letters = [c for c in text if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        text = text.lower()
        text = re.sub(r"\bi\b", "I", text)
        text = re.sub(r"\bi's\b", "I's", text)
        text = re.sub(r"\bda boss\b", "Da Boss", text)
        text = re.sub(r"\bprince\b", "Prince", text)
    return text


def _stressed(chars: list[str], i: int) -> bool:
    """Is the vowel at chars[i] in a primary-stressed syllable?"""
    j = i - 1
    while j >= 0 and chars[j] in VOWELS:
        j -= 1
    while j >= 0:
        c = chars[j]
        if c == "ˈ":
            return True
        if c in VOWELS or c.isupper() or c in " ˌ.,!?":
            return False
        j -= 1
    return False


def soften_s(ps: str, p: Params) -> str:
    if not p.soft_s:
        return ps
    z_to = {"sh": "ɕ", "zh": "ʒ", "keep": "z"}.get(p.z_mode, "ɕ")
    out: list[str] = []
    for i, ch in enumerate(ps):
        if ch in "sz":
            word_final = i + 1 >= len(ps) or not ps[i + 1].isalpha() and ps[i + 1] not in "ːˈˌ"
            if p.lengthen_before_s and word_final and out and out[-1] in VOWELS \
                    and _stressed(out, len(out) - 1):
                out.append("ː")
            out.append("ɕ" if ch == "s" else z_to)
        else:
            out.append(ch)
    return "".join(out)


class Phonemizer:
    def __init__(self, g2p, lexicon: dict[str, str] | None = None):
        self.g2p = g2p
        self.lexicon = lexicon if lexicon is not None else load_lexicon()

    def lookup(self, word: str) -> str | None:
        w = word.lower()
        for key in (w, _collapse(w)):
            if key in self.lexicon:
                return self.lexicon[key]
        return None

    def __call__(self, text: str, p: Params) -> str:
        text = normalize_case(text)
        whole = self.lookup(text.strip(" .,!?"))
        if whole is not None:
            trail = re.search(r"[.,!?]*$", text.strip()).group(0)
            return soften_s(whole + trail, p).strip()
        _, tokens = self.g2p(text)
        parts = []
        for t in tokens:
            ph = self.lookup(t.text)
            if ph is None:
                ph = t.phonemes or ""
            parts.append(ph + (" " if t.whitespace else ""))
        return soften_s("".join(parts), p).strip()
