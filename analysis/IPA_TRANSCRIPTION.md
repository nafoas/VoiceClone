# Reference clip: narrow IPA transcription

Clip: `reference/source/prince_reference.wav`. Prompted *"nanner moneys....
peet peet peet"*, heard as *"nannarmunis... pee tee tee"*.

Measured with Praat (`analysis/ipa_frames.py` → `ipa_frames.csv`, zoomed
spectrograms `ipa_nannar.png`, `ipa_munis.png`, `ipa_peets.png`). Vowel map:
`vowel_map.png`. Each sound is read in terms of **his** mouth: small, split
upper lip, big incisors, nose-breather. He is a bun trying his best, so these
are descriptions of what he did, not rules he obeys.

## Whole clip

```
English (prompt):   nænɚ mʌniz      pit  pit  pit
Prince:            ˈnːã.nɐ˞ɹ̞ ˈmũ.niːɕ  ‖  ˈp˭iː   ˈtʰiː   ˈtʰiː
                   └─ one unbroken hum ─┘     each ends in a soft fade, no t
```

## Sound by sound

| # | Time (s) | ms | IPA | English target | Pitch Hz | Measurements | Reading (his mouth) |
|---|---|---|---|---|---|---|---|
| 1 | 0.05–0.16 | 105 | **nː** | n | 344→249 | F1 330, HNR 21 | A long hummed "nnn" to start: the phrase begins as a hum, pitch sliding down into it. |
| 2 | 0.16–0.30 | 145 | **ã** | æ | 216 flat | F1 1115, F2 2164 | Jaw drops wide open, much more than a human æ (F1 669). Between two n's, so nasal-tinged. |
| 3 | 0.30–0.38 | 75 | **n** | n | 215 | F1 385, HNR 25 | Light tongue touch; the vowel's resonance carries straight through it (smooth join). |
| 4 | 0.38–0.47 | 95 | **ɐ˞** | ɚ | 216 | F1 793, F2 1969, F3 3114 (lowered) | Unstressed -er **not reduced**: an open, central, r-coloured vowel ("nannAR"). |
| 5 | 0.47–0.52 | 50 | **ɹ̞** | (ɹ) | 214 | F2 1740, F3 3327 | A faint, loose r, more a colour than a consonant. |
| 6 | 0.52–0.61 | 90 | **m** | m | 220 | HNR 27.5 | Lips closed, humming. |
| 7 | 0.61–0.73 | 120 | **ũ** | ʌ | **steps up** 237→266 | F1 360, F2 1303, HNR 28 | **The hummy "u".** Mouth nearly closed (F1 halved vs. ʌ's 753), lips rounded, very clean tone. Coming straight off the closed-lip m, he only opens a crack. |
| 8 | 0.73–0.79 | 60 | **n** | n | 265 | F2 jumps to 2712 | Quick tongue tap. |
| 9 | 0.79–0.99 | 200 | **iː** | i (unstressed) | 264 flat | F1 359, F2 3275 | Acoustically a full "ee", long. It *reads* short ("is") because it melts straight into the soft ending. |
| 10 | 1.02–1.11 | 90 | **ɕ** (partly voiced) | z | 255 under the noise | noise 80%, ~16 dB under vowel, HNR 5 | Soft "sh"-leaning s, with some voice humming underneath. Then a faint voiced puff. |
| — | 1.12–1.46 | 340 | ‖ | | | silence | Pause. |
| 11 | 1.47–1.52 | 55 | **p˭** | pʰ | 352→366 | weak burst, no aspiration (noise 1%) | Lip sound is **weak**: the split lip barely seals, so no puff of air. Pitch chirps up. |
| 12 | 1.52–1.60 | 80 | **iː** | i | 390 | F1 392, F2 3118 | "ee", excited pitch. |
| 13 | 1.60–1.70 | 100 | (fade) | t | 394 | −20 dB, voiced, no closure | **No t at all.** The vowel just fades out. |
| 14 | 1.72–1.76 | 45 | **tʰ** | p (!) | | strong burst, noise 82% | Tongue-tip sound is **strong**: a crisp, airy t. The p became a t. |
| 15 | 1.77–1.90 | 130 | **iː** | i | 350 | F1 378, F2 3159 | Same "ee", a step lower. |
| 16 | 1.90–2.00 | 100 | (fade) | t | 362 | −30 dB | Fade, no t. |
| 17 | 2.04–2.08 | 40 | **tʰ** | p | | noise 80% | Crisp t again. |
| 18 | 2.09–2.30 | 210 | **iː** | i | 331, rises at end | F1 410, F2 3233 | Longest and lowest of the three. |
| 19 | 2.30–2.40 | 100 | (fade) | t | 327 | F1 rises 420→900 | Fades as the jaw relaxes open. |

## What his mouth is doing

1. **Hum first.** He starts the phrase on a long "nnn", keeps voicing through
   every consonant (n, ɹ, m, n), and the tone is very clean (HNR 25–34 dB on
   nasals and vowels, vs. ~15–20 typical for speech). One breath, one hum.
2. **Lips are weak, tongue tip is strong.** The only lip consonant he releases
   (p) is soft and airless. Tongue-tip t's are crisp and airy. After the
   first "peet" he swaps the hard-for-him lip sound for the easy tongue one:
   "pee tee tee". This fits a split upper lip.
3. **Vowels follow the mouth's position.** Right after a closed-lip m, "uh"
   comes out as a nearly closed, rounded, humming [ũ], because he barely opens.
   That's the hummy u, and it's why "moneys" → "munis" but nothing pushes
   "wasn't" the same way. When nothing holds the mouth shut, it opens wide:
   "nAnner" is far more open than English. Tendency, not rule.
4. **Final stops dissolve.** Word-final t's never close. The vowel fades over
   ~100 ms instead.
5. **Unstressed vowels keep their shape.** "-er" → open [ɐ˞], "-eys" → full
   [iː]. Nothing collapses to a lazy schwa.
6. **Pitch is held, then stepped.** Flat plateaus per syllable group
   (≈216 → step → ≈265), excited "ee"s at 390 → 350 → 330.

## Confidence

High: segment timing, pitch, n/m/t/p/fade, ɕ, all [iː], the open [ã].
Medium: [ɐ˞] and [ɹ̞] (one short stretch), nasalisation of [ã].
Medium-high: [ũ]. The closed, rounded, back quality is clear in the numbers.
"Nasal" is inferred from the following m and the hum, not measured directly.
One clip only: every pattern here is a tendency seen once or a few times.
