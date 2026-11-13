"""Turn Prince's written lines into delivery segments.

His text already *is* the prosody markup:

    lowercase          -> normal soft voice
    !!                 -> excited
    ALL CAPS           -> very excited (a small body's "loud")
    ??                 -> eager rising question
    ...                -> a real pause (Bun Brain Case(tm) working)
    awwww / hmmmm      -> held sounds, length from letter count
    *narration*        -> not spoken
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STRETCH_RE = re.compile(r"\b[A-Za-z]*([A-Za-z])\1{2,}[A-Za-z]*\b")
NARRATION_RE = re.compile(r"\*[^*]*\*")
SPEAKER_RE = re.compile(r"^\s*\*{0,2}\s*Prince\s*:\s*\*{0,2}\s*", re.I)


@dataclass
class Segment:
    text: str = ""
    pause_s: float = 0.0          # pause_s > 0 and no text -> silence
    excited: bool = False
    caps: bool = False
    question: int = 0             # 0 none, 1 "?", 2 "??"
    soft: bool = False            # trailing "..." -> gentler delivery
    stretch: int = 0              # extra repeated letters (0 = not stretched)
    sentence_end: bool = False

    @property
    def is_pause(self) -> bool:
        return not self.text


def _is_caps(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 2:
        return False
    # "I", "I's" alone don't make a line shouty
    words = [w for w in re.findall(r"[A-Za-z']+", text) if w not in ("I", "I's")]
    letters = [c for w in words for c in w if c.isalpha()]
    return len(letters) >= 2 and sum(c.isupper() for c in letters) / len(letters) > 0.8


def _stretch_amount(word: str) -> int:
    m = re.search(r"([A-Za-z])\1{2,}", word)
    return len(m.group(0)) - 2 if m else 0


def clean_line(line: str) -> str:
    line = SPEAKER_RE.sub("", line)
    line = NARRATION_RE.sub(" ", line)
    line = line.replace("™", "").replace("…", "...")
    line = line.replace("—", ", ").replace("–", ", ")
    return re.sub(r"\s+", " ", line).strip()


def parse(text: str) -> list[Segment]:
    """Split text into speech segments and pauses with delivery flags."""
    segs: list[Segment] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line:
            continue
        # sentences: text followed by its terminal punctuation run
        for m in re.finditer(r"([^.!?]*)([.!?]*)", line):
            body, end = m.group(1).strip(), m.group(2)
            if not body and not end:
                continue
            if not re.search(r"[A-Za-z]", body):
                if "..." in end or end.count(".") >= 2:
                    segs.append(Segment(pause_s=-1))  # ellipsis pause
                continue
            ellipsis = "..." in end or end.count(".") >= 2
            caps = _is_caps(body)
            flags = dict(
                excited="!" in end or caps,
                caps=caps,
                question=2 if "??" in end else (1 if "?" in end else 0),
                soft=ellipsis and "!" not in end,
            )
            # split out stretched sounds (awwww, hmmmm) as their own segments
            parts, last = [], 0
            for sm in STRETCH_RE.finditer(body):
                if sm.start() > last:
                    parts.append((body[last:sm.start()], 0))
                parts.append((sm.group(0), _stretch_amount(sm.group(0))))
                last = sm.end()
            parts.append((body[last:], 0))
            parts = [(t.strip(" ,"), s) for t, s in parts if t.strip(" ,")]
            for i, (t, s) in enumerate(parts):
                final = i == len(parts) - 1
                punct = end.replace("...", ".") if final else ","
                punct = re.sub(r"\.+", ".", punct) or "."
                segs.append(Segment(
                    text=t + punct, stretch=s, sentence_end=final,
                    excited=flags["excited"], caps=flags["caps"],
                    question=flags["question"] if final else 0,
                    soft=flags["soft"] or (s > 0 and not flags["excited"]),
                ))
            if ellipsis:
                segs.append(Segment(pause_s=-1))
    # collapse repeated pauses
    out: list[Segment] = []
    for s in segs:
        if s.is_pause and out and out[-1].is_pause:
            continue
        out.append(s)
    while out and out[-1].is_pause:
        out.pop()
    return out
