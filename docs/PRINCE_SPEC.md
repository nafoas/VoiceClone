# Prince: the definitive voice spec

Everything we know about what makes Prince sound like **him**, and what he is
**not**, in a form we can use to make new phonemes and check them objectively.

- Machine-readable: `prince_voice/spec.json`
- Check a whole recording: `python scripts/check_voice.py file.wav`
- Check one sound: `python scripts/check_phoneme.py file.wav START END PHONEME --after CONSONANT`
- Background: `docs/PRINCE_IDENTITY.md` (the identity table), `analysis/` (all measurements)

A sound is in his voice when it passes **all four layers**. Each layer catches
failures the others can't see.

## Layer 1: voice quality (whole recording)
`check_voice.py`. Accepted ranges come from Da Boss-approved versions (clip,
gold rebuild, fresh "munis... nannar", "nanni", "mama" F), widened slightly.

| Measure | His range | Too low means | Too high means |
|---|---|---|---|
| Pitch steadiness (st/frame) | 0.02–0.04 | robotic (frozen) | synthetic, child, chipmunk |
| Jitter | 0.5–0.9 % | — | synthetic, child-like, breathy |
| Shimmer | 0.37–0.60 dB | robotic, choppy | synthetic, child |
| **Hum cliff (H1–A3)** | **33–37 dB** | ordinary, synthetic, chipmunk | **overdone hum: heard as a child** |
| Purity <500 Hz | 29–36 dB | breathy, ordinary | robotic |
| Purity 1.5–2.5 kHz | 13–19 dB | — | robotic |
| Spectral movement | 3.2–3.85 dB/frame | frozen, robotic, choppy | breathy |
| Biggest jumps | 6.2–7.3 dB | slurred | choppy, chipmunk |
| Voiced | 84–98 % of speech | ordinary, synthetic | — |
| Vocal tract length | 11.8–12.8 cm | chipmunk | adult |
| Lowest F3 | ≥ ~2840 Hz | r-colour / rounding where there shouldn't be | — |
| Loudness vs pitch | −0.5…+0.8 dB/st | — | loudness tied to pitch (robotic) |

**Validated against every version heard so far:** all 5 approved versions pass
100%. All voice-quality failures fail (31–75%): ordinary adult, all three
"synthetic" auditions, all three "a child" candidates, Seed-VC, and standard
child-like, chipmunk, breathy, robotic and choppy. (The ranges were set from
the same approved files: it is a consistency check until new material is
tested.)

## Layer 2: what he is NOT (failure signatures)

| Not | Its signature |
|---|---|
| an ordinary adult | pitch wobble x5–8, jitter x3, shallow hum cliff, less voicing |
| synthetic (TTS) | pitch wobble x3–5, shallow cliff, rough |
| **a child** | **overdone hum cliff (H1–A3 42–46 dB)**, pitch wobble x2, short tract or low F3. Being small is shared with children; this isn't |
| a chipmunk | pitch and resonances up together: wobble x10, tract < 11 cm |
| breathy | jitter up, low-band purity down |
| robotic / frozen | pitch frozen, purity too high, no spectral movement, loudness tied to pitch |
| choppy | sounds held frozen, then jumping |
| slurred | joins melting more than his (~2.6 dB spectral change per join) |
| "nana", "rarra" | wrong consonant on the vowel's edge (layer 3) |
| formulaic | variation without a reason, pitch sliding inside vowels, fades mid-utterance (layer 4) |

## Layer 3: phoneme identity (one sound)
`check_phoneme.py`. Voice-quality measures can't tell "nana" from "mama"; this can.

- **Identity:** F1/F2 at the middle must be closest to the intended phoneme's
  target in his space:

  | Phoneme | F1 | F2 | Source |
  |---|---|---|---|
  | iː | 375 | 3240 | recorded |
  | ũ (hummy u) | 388 | 1325 | recorded |
  | ã (a of nannar) | 1178 | 2138 | recorded |
  | ɐ˞ | 813 | 1954 | recorded |
  | ɑ (ah of mama) | 1178 | 1700 | derived, approved (version F) |
- **Class targets:** closed vowels, open vowels, nasals, r, sibilant, bursts
  (spec.json `classes`). Example: closed vowels need H1–H2 10–32 dB, low-band
  purity ≥ 35 dB, jitter ≤ 0.4 %, and F1 within ~1–1.6× his pitch (hum tuning).
- **Transitions:** a vowel's onset must never move clearly **away** from its
  consonant's F2 locus (his lips ~1200 Hz, his tongue tip ~2700 Hz). Onset =
  F2 over 15–40 ms after the release (tracker spikes on the nasal release frame
  rejected), compared with the vowel's middle. F3 must not dip toward ~2.7 kHz
  ("r"). Small movements are normal (tip -> "ee" barely moves).

**Validated:** all 7 real transitions in his clip pass. "nana" fails (onset
moves away from the lips). "mama" F passes identity but its onset still leans
toward n (+90 Hz): the measured reason it doesn't sound like a word-starting
M. With the lip edge rebuilt over its first ~45 ms (G, H) it passes.

## Layer 4: prosody
- Pitch is steady on vowels (0.02–0.04 st/frame) and **moves only in consonants**.
- Levels: calm ~215 Hz, raised ~265, excited 330–390.
- Main stress: a step up of ~3.6 st on the stressed word, held after.
- A nasal start gets his hummed fall (~8 st over ~150 ms).
- **Loudness does not follow pitch.**
- His fade only at the end of what he's saying: −20 dB in 20 ms, then a
  humming tail of 80–150 ms.
- Variation only with a reason, never random.

## How to make a new phoneme with this
1. Pick its **nearest recorded relative** (identity doc: b ← p voiced, d ← tʰ
   voiced and softer, s/z ← ɕ, l ← n without the nose, w ← ũ, ɪ ← iː opened a
   little, ɛ ← ã closed a little, ...).
2. Change **only** the traits that differ (resonance targets for vowels; voicing,
   burst or noise shape for consonants), keeping his source, purity and movement.
3. Run **layer 3** on it in context (identity, class, transitions from its
   real neighbours), then **layer 1** on a phrase using it.
4. Listen. Your verdict goes back into the spec as a new positive or negative,
   and the ranges get sharper with every sound.

## Phoneme log

| Phoneme | Built from | How | Identity | Class | Transition | Voice | Da Boss |
|---|---|---|---|---|---|---|---|
| ɑ ("ah", mama) | ã | F2 2160 -> 1700 | pass | pass (B1 wide) | pass (lip + jaw rise) | 94 % | F best; G/H "choking" -> fixed (see below), to hear |
| **ɪ ("ih")** | iː | `[(375,520),(3240,2300),(3900,3700)]`, calibrated in context to F1 ~435, F2 ~2700 | **pass** (ninny, minny) | pass | pass | 94–100 % | **to hear** |

Calibration note: a derivation only moves the measured formants ~40% of the
requested shift in a short vowel between consonants (neighbours pull it back),
so derivations are calibrated by measuring the result in a real word.

### Release lessons (from "mama" sounding like choking)
- An instant F1 jump at a lip release (405 -> 964 Hz in 10 ms) plus a purity
  collapse (HNR 3–6) sounds like choking. His real releases stay clean
  (HNR ~9–13). Fix: the jaw opens over the lip edge (`jaw_open=0.35`), a 50 ms
  release blend, a 65 ms lip rise: release HNR 12.
- Into an open vowel his F1 does climb fast (his n->ã: 395 Hz per 10 ms), so a
  fast F1 rise is fine; the roughness spike was the problem.
- The m's murmur dip depends on the next vowel: before an open vowel ~-4 dB,
  before a closed one ~0 dB (his m->ũ loudness change: 3.7 dB).
- His joins briefly roughen (HNR 7–16) while mine stay clean (22–26); adding
  noise did not reproduce it (and lowered the voice score), so it is left open.
