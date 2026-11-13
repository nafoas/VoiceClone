# Reference clip analysis

Source: `reference/source/prince_reference.wav`. A 2.5 s ElevenLabs sound-effect
generation, prompted with *"nanner moneys.... peet peet peet"*, heard as
*"nannarmunis... pee tee tee"*. Da Boss: "that's just… him."

Compared against the same words from plain English TTS (Kokoro `af_heart`) and
against Prince v1 (first prototype). Figures: `reference_analysis.png`,
`english_to_bnuy.png`. Regenerate with `python analysis/plot_reference.py` and
`python analysis/plot_mapping.py`.

## Phoneme breakdown

```
nanner moneys   →  [n æ n ɑ ɹ  m ʉ n i ɕ]     "nannarmunis"   0.04–1.12 s, one breath
peet peet peet  →  [p iː(t̚)  t iː(t̚)  t iː]    "pee tee tee"   1.44–2.34 s, ~220–300 ms each
```

9 distinct phonemes covered: n, m, æ, ɑ, ɹ, ʉ, i, ɕ, p, t. Segment
boundaries were read from the spectrogram, energy and pitch. The vowel labels
for [ɑ] and [ʉ] are interpretations; everything else is clear.

## What makes him *him*, ranked by how much it differs from English

### 1. A round, humming tone: fundamental-heavy but *not* breathy

| | Reference | English TTS | Prince v1 |
|---|---|---|---|
| Spectral tilt | **−16.1 dB/oct** | −10.0 | −11.8 |
| H1–H2 | **9.9 dB** | 5.8 | 6.2 |
| Spectral centroid (voiced) | **273 Hz** | 414 | 398 |
| Aperiodicity 0.3–4 kHz | 0.24 | 0.30 | 0.20 |

The energy sits overwhelmingly in the fundamental. Upper harmonics fall
off steeply. That's the soft, round, cooing/humming quality. It is **not
breathiness**: noise is as low as or lower than normal speech. It's
closer to a flute than a whisper: soft *and* clean.

**v1 got this wrong.** It added breath and kept a human-bright tilt.

### 2. Legato: almost continuously voiced

87% of the clip is voiced vs. 56% for English. The whole "nannarmunis"
is one unbroken voiced stream: every consonant is a sonorant (n, ɹ, m),
and the loudness envelope barely moves (±5 dB across 1.1 s). Sounds glide
into each other instead of being chopped up by consonants.

### 3. Small *and forward* resonances, not uniformly scaled

| [i] in "peet" | F1 | F2 | F3 |
|---|---|---|---|
| English TTS | 562 | 2250 | 3117 |
| Reference | **398** | **3093** (+37%) | **4710** (+51%) |

Upper resonances jump a lot; F1 does *not* rise. That's the acoustic
signature of a short front cavity (tongue forward), not just a "smaller
copy" of a human. This matches Da Boss's own description of how he says
"Boss" ("far forward and up"). v1 scaled everything uniformly by 1.25.

### 4. Terraced pitch

- Speaking pitch ~215–265 Hz in the phrase. ~330–390 Hz for excited "peets".
- **Plateaus, not glides.** Pitch holds dead flat across a word, then
  *steps* to a new level at the next word (215 → 265 at "mu").
- A quick fall at the start of a phrase (370 → 215 in 0.15 s).
- A small **chirp at the onset** of plosive syllables (up to ~600 Hz for a
  few ms) before settling.
- Repetitions descend in steps: 390 → 350 → 330.
- A small upward flick at the very end of the phrase.

### 5. Full vowels, slow syllables

- Unstressed vowels are **not reduced**: "nanner" [nænɚ] → [nænɑɹ].
- ʌ → rounded, forward [ʉ] in "moneys".
- ~270 ms per syllable in the phrase. Unhurried.

### 6. Consonants: soft, and they move

- **Soft S confirmed.** The final "s" lands at ~4.4 kHz (vs. ~9–10 kHz for
  a normal S), ~20 dB under the vowel. The spec's [ɕ] is right.
- **Word-final stops are unreleased or dropped:** "peet" → "pee(t̚)".
- **They migrate:** the final t of one "peet" becomes the onset of the
  next. "peet peet peet" → "pee tee tee". That's why it's "teet tee".

## English → Bnuy changes observed

| English | Bnuy | Type |
|---|---|---|
| n, m | n, m | same (long, humming) |
| æ | æ (raised upper resonances) | shifted |
| ɚ (unstressed) | ɑɹ | changed: no reduction |
| ʌ | ʉ | changed: rounded, forward |
| i | iː (F2/F3 way up, F1 down) | shifted |
| z (final) | ɕ | changed: devoiced, soft |
| p (initial) | p (+ pitch chirp) | same |
| t (final) | t̚ / ∅ | dropped |
| p after t | t | changed: carry-over |

## Implications

- Findings **1–4 are global**: they apply to every sound he makes, so they
  can be transferred to phonemes he never said in the clip. Most of what
  makes him "him" is here, not in individual phonemes.
- Findings **5–6 are phonological rules** and can be applied at the
  phoneme stage, exactly like the soft S.
- Coverage is 9 of ~40 phonemes. A pure diphone inventory cut from this
  clip alone isn't possible. Missing units have to be generated and
  reshaped to match 1–4.

Limits: one 2.5 s clip, generated, not recorded. Formant estimates at
pitch ~260–390 Hz are approximate (harmonics are widely spaced). Every
number here is a direction to tune toward, not an exact target.
