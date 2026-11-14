"""Text -> phonemes, with Prince's lexicon and sound rules.

The text is the phonology: we pronounce exactly what is written, plus a few
rules measured from the reference clip (analysis/REFERENCE_ANALYSIS.md):

  soft S        s/z -> alveolo-palatal [ɕ]; stressed vowel before a final s/z
                carries extra weight ("Boss" ~ "Bohsh")
  full vowels   unstressed -er is not reduced ("nanner" -> "nannar")
  round uh      stressed [ʌ] -> rounded [u] ("moneys" -> "munis")
  final t       a word-final t before another consonant fades out, and before
                a p it moves onto the next word ("peet peet" -> "pee teet")
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .params import Params

LEXICON_PATH = Path(__file__).with_name("lexicon.json")
VOWELS = set("aeiouæɑɒɔəɛɜɪʊʌɐɚᵻ")
VOWEL_RE = "aeiouæɑɒɔəɛɜɪʊʌɐɚᵻAIOWYQ"
CONSONANT_START = re.compile(r"^[ˈˌ]?[bcdfghjklmnpqrstvwxzðŋɕɡɹʃʒθʤʧT]")


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


def word_rules(ps: str, p: Params) -> str:
    """Rules that only look inside one word."""
    if p.full_vowels:
        ps = ps.replace("ɚ", "ɑɹ")
        ps = re.sub(rf"əɹ(?![{VOWEL_RE}])", "ɑɹ", ps)
    if p.round_uh and p.round_uh != "off":
        ps = ps.replace("ˈʌ", "ˈ" + p.round_uh)
    return ps


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

    def tokens(self, text: str, p: Params):
        """misaki tokens with Prince's phonemes filled in (keeps word identity,
        so the TTS can report per-word timing)."""
        text = normalize_case(text)
        _, toks = self.g2p(text)
        words = []
        for t in toks:
            ph = self.lookup(t.text)
            if ph is None:
                ph = t.phonemes or ""
            if re.search(r"[A-Za-z]", t.text):
                ph = word_rules(ph, p)
                words.append(t)
            t.phonemes = ph
        # cross-word rule: final t
        if p.final_t:
            for a, b in zip(words, words[1:]):
                if a.phonemes.endswith("t") and not a.whitespace == "" and CONSONANT_START.match(b.phonemes):
                    a.phonemes = a.phonemes[:-1]
                    b.phonemes = re.sub(r"^([ˈˌ]?)p", r"\1t", b.phonemes)
        for t in toks:
            t.phonemes = soften_s(t.phonemes, p)
        return [t for t in toks if t.phonemes or t.text.strip()]

    def __call__(self, text: str, p: Params) -> str:
        return "".join(t.phonemes + (" " if t.whitespace else "") for t in self.tokens(text, p)).strip()
