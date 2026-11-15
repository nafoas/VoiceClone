# The physics of Prince: what makes each property of his voice

Every measured property of "him" (docs/PRINCE_IDENTITY.md, the fingerprint, the
negative space) is linked here to the physical mechanism that makes it. For
each one: the most parsimonious explanation in **bun biology**, the knob in a
physical model, and what a small change to that knob does.

**Method.** Each experiment turns ONE physical knob in a physical model and
measures the result with the same tools we used on him (Praat and harmonic
amplitudes; `analysis/fingerprint.py`). The model is his one-change bun mouth
(a small bun with a lower larynx; `prince_voice/bunmouth.py`) plus a standard
glottal-flow source (KLGLOTT88 pulse, Klatt tilt, aspiration).
Code: `analysis/physics/lab.py`. Numbers: `analysis/physics/results.json`.
Graph: `analysis/physics/physics_overview.png` (his real values overlaid as stars).

**Confidence.** STRONG: the model reproduces his own measurements. GOOD: the
physics is clear and his values fall where it predicts. OPEN: competing
explanations, or not yet tested.

---

> **Correction (build step 1c):** building his "ee" showed his voice box closes
> **cleanly** (an ordinary closure, not an especially gentle one), with **no
> breath**. His hum is made by the mouth (F1 on his pitch). His bright 3–5 kHz
> band is harmonic, and his pitch drifts slowly with almost no fast wobble.
> "Gentle closure" below was an over-reading of E1/E2.

## The short version

He is a small bun with one difference, a slightly lower larynx, speaking
**gently**. Nearly everything follows from that:

| His property | What makes it | Bun biology | Confidence |
|---|---|---|---|
| **The hum** (H1 towering; cliff after H2) | His small, nearly closed mouth puts its first resonance (F1) right on his pitch, so the 1st harmonic is amplified and the rest fall away. Gentle fold closure adds to it. | a small mouth + gentle phonation | **STRONG** |
| Hum lighter on open sounds ("a") | Open mouth: F1 far above pitch (×4–5), so no harmonic is singled out | same rule | **STRONG** |
| Size / resonances (tract 12 cm) | Tube length | the lower larynx (his one adaptation) | **STRONG** |
| Pure low band (HNR <500 Hz ≈ 32) | Very steady fold vibration: tiny pitch *and* loudness variation | relaxed, small folds, steady breath | GOOD |
| Slightly breathy up high (HNR 1.5–2.5 kHz ≈ 13) | A little breath noise through the glottis | normal | GOOD |
| Loudness doesn't follow pitch | Pitch made by fold tension at steady breath pressure | small lungs, steady breath | GOOD |
| Calm pitch 215–265 Hz (excited 390) | Relaxed fold tension (~4–13 kPa) | a relaxed rabbit larynx (a rabbit's in-vivo phonation was 590 Hz) | GOOD (fold length assumed) |
| Soft S at ~4 kHz | Noise made ~2 cm behind the lips (tongue blade at the palate, tip down) | a rabbit's long, narrow front mouth | **STRONG** (physics) |
| Weak, mostly voiced p | The lips don't seal fully, so air leaks, mouth pressure stays low and the folds keep vibrating | **the rabbit's split upper lip** | GOOD |
| Crisp, airy t | The tongue tip seals fully, so full pressure builds and releases | a mobile rabbit tongue tip | GOOD |
| Voiced 65–87% of the time | Follows from the two above (leaky lips) + humming through n, m | — | GOOD |
| Broad F1 in his nasal vowels (ã, ũ) | Nasal coupling *or* a slightly open glottis | — | **OPEN** |
| Slow, gliding transitions | How fast the mouth moves (time constant) | behaviour, not anatomy | **OPEN** (needs the rebuild) |
| Final stops never close; humming tails | Mouth closes while the folds keep humming through the nose | a nose-breather's habit | OPEN (untested) |

---

## 1. The hum (H1–H2, H1–A3, H1–A1 = 0, the H2/H3/H4 cliff)

**His values.** H1–H2 12.6 dB overall (ordinary 6.1). The cliff is H2 −12,
H3 −32, H4 −46 (ordinary −7, −11, −16). H1–A1 = 0 on closed sounds, which means
the harmonic nearest F1 *is* H1. It is deepest when F1/pitch ≈ 1–1.4; his open
"a" (F1/pitch 5.4) has a light hum.

**Not him.** Too little hum = ordinary, synthetic or chipmunk. Too much
(H1–A3 > 38.5) is heard as "a child" (candidate A, A2, C).

**Mechanism: resonance tuning.** A harmonic near a resonance is radiated
strongly. Sopranos deliberately tune F1 onto their pitch to do exactly this
(Joliveau, Smith & Wolfe). In Prince it happens without trying: his mouth is
small and his closed sounds (ee, the hummy u, n, m) have F1 ≈ 320–410 Hz,
which *is* his pitch range (215–390 Hz).

**Test (E3).** Keep the source ordinary and fixed; move only pitch, so F1/pitch
changes:

| | F1/pitch | H1–H2 (him) | H1–H2 (model) |
|---|---|---|---|
| ee @ 389 Hz | 1.01 | 31.8 | 27.1 |
| ee @ 331 Hz | 1.25 | 12.2 | 14.5 |
| ee @ 264 Hz | 1.37 | 9.6 | 2.8 (model F1 a bit high: ratio 1.55) |
| a @ 216 Hz | 5.4 | 5.6 | ~3 |

His stars fall on the model's curve (graph panel 1), and the same holds for the
H3 cliff (panel 2). Even his oddly narrow B1 when F1 sits on H1 (13.7 Hz at
389 Hz) appears in the model (15.7 Hz). **No special source is needed for the
hum.** Its depth is set by where F1 sits relative to pitch.

**What a gentle voice adds (E1, E2).** With the mouth fixed:
- **Closure smoothness** (folds coming together gradually rather than
  slapping shut), Ta 0 → 2.5 ms: H1–H2 +6 dB, and H3 falls a further 7–9 dB.
- **Open quotient** (folds open longer each cycle), 0.4 → 0.95: H1–H2 up to
  +13 dB.

Both describe a relaxed, gentle phonation. Small changes: Ta 0.15 → 0.4 ms is
about +2 dB of H1–H2. Too much of both, on top of the tuning, overshoots into
the "child" zone (H1–A3 > 38.5).

**Sensitivity rule of thumb.** For his closed sounds, moving F1 from 1.0× to
1.4× his pitch costs about 20 dB of H1–H2. **His hum is mostly where he holds
his pitch relative to his closed-mouth F1.** The bun reading: a small mouth,
humming gently near its own resonance.

## 2. Size (formant spacing; tract 12.2 cm)

Formant spacing is set by the length of the tube. A small bun has about 5.6 cm
and cannot make his vowels (error 15.1). **A larynx about 3.8 cm lower** (the
one adaptation) gives about 9.3 cm and his vowels (error 5.2–6.2). See
docs/BUN_MOUTH.md. Small changes: each +1 cm of throat lowers all resonances
about 10%. "ee" prefers a shorter throat (about 1.5 cm lower), "oo" a longer
one (5 cm), which is still open.

## 3. Purity and steadiness (HNR, jitter, shimmer, CPPS)

**His values.** HNR <500 Hz 32.4 (ordinary 21.9); HNR 1.5–2.5 kHz 12.7
(ordinary 11.2); jitter 0.7% (ordinary 2.9%); shimmer 0.6 dB; CPPS 7.4.
**Not him.** Breathy (HNR <500 = 21.9), synthetic/child (jitter 1.3–2.9%),
robotic (HNR <500 = 50, shimmer 0.26: too perfect).

**Tests (E6, E7).**
- Breath noise hits the **high band** first: HNR 1.5–2.5 kHz goes 27 → 12 as
  breath noise rises. His 12.7 = a little breath, normal.
- The **low band** is spoiled by unsteady folds. Pitch variation (jitter) 2%
  takes it from 24 to 15, and loudness variation (shimmer) 5% takes it to 22.
  Only with very steady loudness (shimmer ≈ 0) does the model reach about 30,
  close to his 29–36.

**Bun reading.** Small, relaxed folds driven by a steady little breath. The
"robotic" negative shows the other edge: perfectly steady (HNR 50) is not him
either. He sits at steady-but-alive (jitter about 0.5%, shimmer about 0.4 dB).

## 4. Loudness independent of pitch (−0.2 dB per semitone)

Raising pitch by pushing more breath also makes the voice louder (sound level
rises about 8–9 dB per doubling of pressure; pitch rises a few Hz per cmH2O).
**E10:** pitch made 0% by pressure gives 0 dB/semitone; 25% gives +1.8; 100%
gives +6.0. Ordinary voices (+0.6) mix a little pressure in. **He makes pitch
with fold tension alone, at a steady breath.** Bun reading: small lungs, steady
pressure.

## 5. Pitch level (calm 215, raised 265, excited 330–390 Hz)

A vibrating fold behaves like a string: f0 = (1/2L)·√(stress/density).
**E11** (fold length assumed 4.5 mm): 215 Hz needs about 3.9 kPa of fold
stress, 265 Hz about 5.9, 390 Hz about 12.8. A rabbit's larynx made to phonate
in vivo ran at **590 Hz** (Novaleski et al. 2016; about 29 kPa by the same
formula). **His pitch is a relaxed rabbit larynx: no adaptation needed.**
Relaxed folds also fit section 1's gentle closure. Caveat: the rabbit fold
length is an assumption. Pitch scales with 1/length, so ±1 mm is about ±20%.

## 6. The soft S (ɕ: centroid 3.9 kHz, peak 4.1 kHz; an ordinary s is 7–9 kHz)

Hiss is made where the air is squeezed and is shaped only by the cavity in
front of that point. A longer front cavity gives a lower peak (quarter-wave:
c / 4L). **E8**, noise source moved along his mouth:

| noise made this far behind the lips | peak | centroid |
|---|---|---|
| 1.5 cm | 9.0 kHz | 9.1 kHz (an ordinary s) |
| 1.8 cm | 5.4 | 6.2 |
| **1.95 cm** | **3.9** | **4.8** |
| **2.1 cm** | **3.0** | **3.8** |

**His S is made about 2 cm back: the tongue blade against the middle of the
palate, tip down.** That is exactly Da Boss's description ("tongue down, sound
forward") and the transcription (ɕ, alveolo-palatal). It is also why it is
gentle: no sharp jet onto the teeth. Small changes: 1.5 mm further forward or
back moves the peak by about 1 kHz. That is what separates his S from a sharp
one.

## 7. The lips: weak, mostly voiced p (noise 1%, centroid 0.7 kHz)

To keep vibrating, the folds need a pressure drop across them (about 3 cmH2O).
With the lips sealed, mouth pressure rises to lung pressure, voicing stops and
the release is a strong puff. **E9** (lungs 9 cmH2O, glottis 0.04 cm²):

| lip leak | mouth pressure | across folds | voicing | burst |
|---|---|---|---|---|
| 0 (sealed) | 9.0 | 0.0 | stops | full |
| 0.02 cm² | 7.2 | 1.8 | stops | −1 dB |
| **0.03–0.04 cm²** | 5.8–4.5 | 3.2–4.5 | **continues** | −2…−3 dB |
| 0.08 cm² | 1.8 | 7.2 | continues | −7 dB |

**A lip leak about the size of his glottis keeps p voiced and the puff weak.**
Bun reading: **a rabbit's upper lip is split.** It cannot seal perfectly, so his
lip sounds leak. This is existing rabbit anatomy, not new biology. The tongue
tip, by contrast, seals fully against the ridge, so **t is crisp and airy**
(tʰ: 80% noise). One fact explains both the weak lips and the strong tip.
Small changes: the leak area decides everything between a sharp "p" and an "m"
without the nose.

## 8. How much he voices (65–87%; hums through n, m, r)

Follows from section 7 (leaky lips keep the folds going through p) and from
nasals (the nose is open, so air flows and the folds keep going). OPEN: confirm
in the full rebuild that voicing stays on through p with the measured leak.

## 9. Broad F1 in his nasal vowels (ã 369 Hz, ũ 256 Hz; oral ee 69 Hz) — OPEN

Two candidates. (a) **Nasal coupling** damps F1. The transcription marks ã
and ũ as nasal, but in our model nose coupling barely broadens F1 (about
100 Hz). Our nose model is crude (a damped tube; a real rabbit nose is full of
scrolls and side cavities), so this is not ruled out. (b) **A slightly open
glottis** (a leaky, breathier phonation) broadens F1 strongly (250–800 Hz), but
he is not breathy in the low band. Caveat: with f0 216 Hz and F1 1178 Hz,
Praat's B1 for the "a" is not reliable. Next: model the rabbit nose more
faithfully, and measure B1 another way.

## 10. Timing and movement (slow glides 1–6 Hz/ms; joins melt ~2.6 dB) — OPEN

How quickly the mouth moves between targets (a time constant) sets how smooth
the sound is. E12 measured spectral movement of the mouth alone (without a
voice), which is not comparable to his measured flux. This must be fitted in
the rebuild, with sound. It is "how he says things", not anatomy.

## 11. Phrase ends (vowel drops ~20 dB in 20 ms, then a humming tail) — OPEN

Hypothesis: the mouth closes while the folds keep humming through the open
nose, then the folds part and the hum turns to breath. That is a natural
nose-breather habit. Test in the rebuild.

---

## What this means for the rebuild (parameters, from the physics)

| Model part | Setting the physics suggests |
|---|---|
| Larynx | ~3.8 cm lower (his one adaptation) |
| Fold vibration | relaxed and gentle: smooth closure (Ta ~0.4–1 ms), open quotient ~0.6–0.7; pitch by tension; very steady (jitter ~0.3–0.5%, shimmer small) |
| Breath | steady pressure; a little breath noise (shows only above 1.5 kHz) |
| Hum | NOT stamped on: it comes from F1 sitting on his pitch in closed sounds |
| Lips | leak ~0.03–0.04 cm² when "closed" (the split lip) |
| Tongue tip | seals fully |
| Soft S | blade constriction ~2 cm behind the lips |
| Velum | open for m, n and his nasal vowels |
| Open questions | nasal-vowel bandwidth (nose model); movement speed; phrase-end tails; ee vs oo throat length |

## Sources

- Resonance tuning: Joliveau, Smith & Wolfe (2004), *Nature*; Henrich, Smith &
  Wolfe (2011), JASA (https://hal.archives-ouvertes.fr/hal-00569451/file/Henrich_JASA_2011.pdf;
  https://www.phys.unsw.edu.au/jw/reprints/Joliveauetal.pdf)
- H1–H2 vs open quotient and asymmetry, H1–A3 as spectral tilt: Hanson (1997);
  Henrich et al. (2001) (https://www.ee.columbia.edu/~dpwe/papers/HenAD01-glottal.pdf);
  DiCanio (2009) (https://www.acsu.buffalo.edu/~cdicanio/pdfs/DiCanio_2009.pdf)
- Rabbit phonation: Novaleski et al. (2016), in vivo rabbit 590 Hz, 9 cmH2O,
  61 dB (https://pmc.ncbi.nlm.nih.gov/articles/PMC5101034); Döllinger et al.
  (2018), ex vivo rabbit larynges, JASA 144(1) (https://escholarship.org/uc/item/93g518r7)
- Nasal coupling, A1–P0: Pruthi & Espy-Wilson; Styler (https://wstyler.ucsd.edu/files/stylerASA2014.pdf)
- Sibilants and the front cavity (https://www.phonetik.uni-muenchen.de/~hoole/pdf/brunnerhoole_langspeech_55_4_2012.pdf)
- Perturbation vs pitch and loudness: Gelfer (1995) (https://pubs.asha.org/doi/epdf/10.1044/jshr.3806.1189)
- Rabbit anatomy: see docs/BUN_MOUTH.md
