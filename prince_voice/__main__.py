"""Command line:

    python -m prince_voice "OH!! what dis??" -o oh.wav
    python -m prince_voice -f lines.txt -o out/          # one wav per line
    python -m prince_voice "is round." --preset presets/default.json --set formant_high=1.5
    python -m prince_voice "Da Boss!!" --phonemes        # show phonemes only
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import soundfile as sf

from .params import Params


def main() -> None:
    ap = argparse.ArgumentParser(prog="prince_voice")
    ap.add_argument("text", nargs="?", help="line(s) to speak")
    ap.add_argument("-f", "--file", help="text file, one line per output")
    ap.add_argument("-o", "--out", default="out/prince.wav", help="wav file, or directory with -f")
    ap.add_argument("--preset", help="params json")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a param, e.g. --set pitch_st=4 --set caps.gain_db=5")
    ap.add_argument("--raw", action="store_true", help="base TTS only, no body transform")
    ap.add_argument("--phonemes", action="store_true", help="print phonemes and segments, no audio")
    a = ap.parse_args()

    p = Params.load(a.preset) if a.preset else Params()
    for kv in a.set:
        k, _, v = kv.partition("=")
        p.set(k.strip(), v.strip())

    from .engine import PrinceVoice, SR
    from . import markup

    pv = PrinceVoice(p)
    lines = Path(a.file).read_text().splitlines() if a.file else [a.text or ""]
    lines = [l for l in lines if l.strip() and not l.lstrip().startswith("#")]

    if a.phonemes:
        for line in lines:
            print(line)
            for s in markup.parse(line):
                if s.is_pause:
                    print("    [pause]")
                else:
                    tags = [n for n in ("excited", "caps", "soft") if getattr(s, n)]
                    if s.question: tags.append("?" * s.question)
                    if s.stretch: tags.append(f"stretch+{s.stretch}")
                    print(f"    {pv.phonemize(s.text, p):32} {' '.join(tags)}")
        return

    out = Path(a.out)
    if a.file:
        out.mkdir(parents=True, exist_ok=True)
        for i, line in enumerate(lines, 1):
            slug = re.sub(r"[^a-z0-9]+", "_", line.lower()).strip("_")[:40]
            path = out / f"{i:02d}_{slug}.wav"
            sf.write(path, pv.render(line, raw=a.raw), SR)
            print(path)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(out, pv.render(lines[0], raw=a.raw), SR)
        print(out)


if __name__ == "__main__":
    main()
