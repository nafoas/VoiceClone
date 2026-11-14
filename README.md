# Prince Voice

The voice of Little Prince, for the Little Self project.
What he should sound like is defined in [`VOICE_SPEC.md`](VOICE_SPEC.md).

## How it works

```
Prince's text ──► markup ──► phonemes ──► Kokoro-82M ──► body transform ──► audio
                 (caps, !!,   (lexicon,     (base TTS,     (WORLD vocoder:
                  ??, ...,     soft S)       CPU-friendly)   size, pitch, breath,
                  awwww)                                     nose, softness)
```

- **markup** (`prince_voice/markup.py`): his writing is the prosody.
  `!!` excited, ALL CAPS very excited, `??` eager question, `...` pause,
  `awwww`/`hmmmm` held sounds, `*narration*` not spoken.
- **phonemes** (`prince_voice/phonemes.py`, `prince_voice/lexicon.json`):
  pronounce exactly what is written; hand-tuned signature sounds (Bnuy, OH,
  mhm…); the one added rule is the soft S, s/z → [ɕ].
- **base TTS**: [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
  (Apache-2.0). Any Kokoro voice or weighted blend of voices.
- **body** (`prince_voice/body.py`): WORLD vocoder moves pitch, body size
  (formants) and breathiness independently, so he sounds small without
  sounding like a child or a chipmunk.
- **params** (`prince_voice/params.py`): every knob, in one place.

## Setup

Python 3.10–3.12 (3.13 can't build a dependency yet). No GPU needed.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

First run downloads the Kokoro model (~330 MB) and an English language model.

## Use

```bash
python -m prince_voice "OH!! what dis??" -o out/oh.wav
python -m prince_voice -f reference/test_lines.txt -o out/test/
python -m prince_voice "is round." --set formant_high=1.5 --set pitch_st=2
python -m prince_voice "Da Boss!!" --phonemes      # inspect, no audio
python scripts/audition.py                          # compare base voices
```

Save a tuned set of knobs as a preset with `Params.save()` and load it with
`--preset presets/whatever.json`.
