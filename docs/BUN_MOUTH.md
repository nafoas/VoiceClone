# Prince's little mouth (bun anatomy)

`prince_voice/bunmouth.py` is a side-view model of a rabbit's vocal tract. The
picture and the sound come from the same geometry: what you see is what makes
the sound.

## Principle (Da Boss)

**His abilities first, rooted in biology.** The question is never "what can a
normal rabbit do?" A normal rabbit couldn't talk at all. It is "how would rabbit
anatomy make *his* abilities possible?" His clip sets what the mouth must do.
Rabbit anatomy is the starting point and a gentle pull that keeps the mouth
grounded (proportions, parts, how they move). It is not a hard constraint.
Every place his mouth departs from a normal rabbit is listed below as an
**adaptation**, with the ability it serves. No departure without a reason.

## His adaptation: one, a slightly lower larynx

**Parsimony (Da Boss):** Prince is a normal small bun with one difference, a
larynx that sits lower in his neck. That could be an ordinary mutation. Nothing
else is changed. The mouth's ranges are the ones written *before* fitting him
(`BunMouth(extras=False)`, the default), so nothing has been tuned to him
except larynx height.

What the one change does, all at once:
1. **His resonances.** A longer air tube in the same small body (tract 5.6 ->
   ~9.3 cm, larynx ~3.8 cm lower).
2. **Speaking through his mouth.** A normal rabbit's larynx is plugged into the
   back of the nose (they breathe and call through the nose). A lower larynx
   is unplugged from it, so the soft palate can seal and he can speak orally.
3. **His vowel range.** A long throat behind the tongue is what lets a mouth
   make both a bright "ee" and a dark "oo".

Precedents: red and fallow deer pull the larynx down to roar; koalas have a
permanently low larynx; in humans the low larynx is part of how we talk.

| mouth (his real size) | error over his 4 vowels (Bark) | whole clip, mouth only (LSD) |
|---|---|---|
| normal small bun | 15.1: cannot make his vowels | - |
| **+ larynx lower (his mouth)** | **5.2-6.2** (3-5 cm lower) | **9.3** |
| + extras: puffed cheeks, wider jaw/lips, mobile larynx (dropped) | 1.7 | 8.7-9.0 |
| 2x-sized bun (dropped: he is small) | 1.7 | 8.0 |

The extras improved the vowel fit on paper but barely changed the real clip,
so they're not worth the departures from biology. Still open: with one fixed
larynx height, "ee" fits best at ~1.5 cm lower and "oo" at ~5 cm lower (his
normal small larynx movement covers only part of that).

## Anatomy it is built on (rabbit, *Oryctolagus cuniculus*)

| Part | Rabbit fact | In the model |
|---|---|---|
| Larynx | High in the throat. At rest it is locked into the nasopharynx (rabbits are obligate nose-breathers) | Short laryngopharynx; `larynx` raises it (shorter throat) |
| Soft palate | Long; its free edge reaches about the middle of the epiglottis | The nasal port sits just above the larynx (17 mm on a 74 mm tract); `velum` opens it |
| Nose | Long nasal cavity full of turbinate scrolls | 58 mm side tube to the nostrils, heavily damped |
| Oral cavity | Long and narrow, narrowest at the diastema (the gap between the incisors and the cheek teeth) | Width profile 12 mm at the back, 6 mm at the diastema |
| Tongue | About 52 mm long (2.9 kg rabbit), with a big dorsal hump at the back (the lingual torus) and a thin, mobile front | `body` raises the torus; `front` slides its peak 40–56 mm; `tip` lifts the front to the ridge behind the incisors; `root` widens or narrows the throat |
| Jaw | Rotates, so the opening grows toward the front | `jaw` drops the floor more at the front and stretches the cheeks |
| Teeth and lips | Chisel incisors; split (cleft) upper lip | Incisors at 68 mm; `lips` opens them, `round` pushes them forward and narrows them |

Sources: Morphometry of the rabbit upper digestive tract (PMC12249223), tongue
length 52.4 ± 1.8 mm in 2.9 kg rabbits; rabbit soft palate and epiglottis
(PMC7711434); rabbit oral cavity is elongated and narrow rostrally (comparative
study, agmv.ro); MediRabbit, anatomy of the rabbit tongue (lingual torus).

## Size (superseded: he is his real size; see above)

Fitting his four recorded vowels gives the best size at **1.5–1.6 × the
reference 2.9 kg rabbit** (an 11–12 cm tract). A small round bun is about
**0.75 ×**, with a tract of about 5.5 cm. A mouth that small would put every
resonance about twice as high, which is the "chipmunk" failure in his negative
space. So the voice we have, and that you said is recognisably him, comes from
a bun-*shaped* mouth about twice the size of a real small bun's.

The model keeps rabbit **proportions** fixed, and `size` is one number. Every
drawing has a 1 cm bar, so this is always visible rather than hidden.

## Rebuilding the gold clip with only the mouth (`scripts/bun_rebuild.py`)

From the clip the rebuild takes only the voice box's controls: pitch, loudness,
brightness and how voiced each frame is. Every resonance and movement comes
from the mouth. One fixed voice-box spectrum is shared by the whole clip, plus
his hum cliff, which follows his pitch.

The fit is a codebook of mouth poses, then the smoothest good path through
them (Viterbi), then a local refinement. The transcription sets what each sound
physically requires: m = lips shut and nose open, n = tongue tip sealed and
nose open, vowels = mouth open and tip down, and so on.

| version | LSD | LSDshape | flux | p95 | H2 / H3 / H4 |
|---|---|---|---|---|---|
| clip | - | - | 3.85 | 7.44 | -12 / -32 / -46 |
| gold v9 (catalogue) | 3.4 | 3.0 | 3.42 | 7.13 | -10 / -30 / -48 |
| ceiling (his own envelope through this pipeline) | 3.2 | 2.9 | 3.63 | 7.08 | -10 / -30 / -48 |
| mouth v1 (fixed source, frame-by-frame search) | 9.6 | 8.8 | 3.22 | 7.21 | -9 / -25 / -34 |
| mouth v2 (codebook + Viterbi, tilt, pitch-following hum) | 7.9 | 7.3 | 3.44 | 8.42 | -10 / -34 / -44 |
| mouth v3 (+ the physical needs of each sound) | 8.0 | 7.3 | 3.28 | 7.61 | -10 / -35 / -42 |

- The hum is now right: the harmonic profile matches the clip.
- Without the physical needs, the fit "cheated": it never opened the velum
  (not even for n/m) and made "a" with nearly shut lips and the tip up. Adding
  the needs cost nothing in score.
- The remaining gap (fit error about 5.7 dB per frame) is the mouth's anatomy,
  not the pipeline (the ceiling is 3.2). Next: calibrate his anatomy within
  rabbit ranges (wall losses, nasal cavity and turbinate damping, the torus's
  width, size) against the clip.

## Build step 1: his "ee" from the model alone (`scripts/build/ee.py`)

One shared "ee" mouth shape and one shared voice box for his four "ee"s (264,
391, 350, 330 Hz). Per "ee", only the pitch level (a plateau) and loudness.
Nothing from the clip in the output; no stamped hum.

- **The hum emerges.** H1–H2 model vs him: 10.9 / 29.6 / 29.7 / 24.7 vs 9.6 /
  31.8 / 18.5 / 12.2 dB. The cliff (H3, H4) is within ~5–10 dB. Harmonic error
  over the hum region: 5.9 dB.
- **Voice box:** gentle. Folds open ~46% of each cycle, opening slowly and
  closing very gradually (Ta at the 3 ms limit). Steady (jitter ~0.4%).
- **Larynx depth:** his "ee" asks for the larynx **~2.2 cm lower** (error
  0.55), not 3.8 cm (2.44). Mouth size ±15% can't substitute. To be settled
  with all his sounds (the open vowels and "oo" preferred deeper in the
  vowel-only fit).
- **OPEN, a structural gap:** his "ee" has an upper-resonance cluster (F2 3323,
  F3 4119, F4 4963). The bun mouth gives F3 ~4.3–4.5 kHz but F4 ~7.2–7.6 kHz,
  whatever the pose. Not fixed by: mouth size ±15%, nasal coupling, or a
  laryngeal vestibule (added to the model, default off; a realistic length
  only adds a resonance near 6.2 kHz). A human-shaped mouth at his size does
  have it (4.9 kHz), so it comes from the shape of the cavity. Fitting the
  voice box to all harmonics made it harsh to compensate (rejected). Fitting
  it to the hum region (<2.5 kHz) leaves the 3–5 kHz region weaker than his.

### Step 1b: research on the upper resonances, and the "ee" rebuilt

`analysis/physics/resonances.py` (A: which part of the mouth owns each
resonance; B: rabbit side spaces swept) and the literature:
- Human upper formants come from (1) the **laryngeal cavity** above the folds,
  a Helmholtz resonator that makes its own extra formant (the 4th in adults,
  ~3–3.7 kHz; Takemoto, Honda et al. 2006); (2) the **piriform fossae**, side
  pockets that carve an anti-resonance at 4–5 kHz and pull neighbours down
  (Dang & Honda 1997); (3) **side spaces in the mouth** (between the cheek
  teeth and cheeks), which act as side branches for "ee"-type vowels (Honda,
  Takano & Takemoto 2010). A rabbit has all of these, and its larynx is
  relatively large (child-sized: airway ~8.6 mm at the arytenoids).
- In his "ee": F1 belongs to the narrow front channel plus the cavity behind it
  (the bottle that tunes F1 onto his pitch: the hum); F2 to the throat (so
  larynx depth sets it); F3 to the front cavity; F4 needed the laryngeal cavity.
- Side spaces swept with the "ee" refitted (F1..F4 error, Bark): none 1.66 (F4
  7580); **laryngeal cavity 0.64 (F4 5160)**; + piriform 0.89 (worse); cheek
  spaces 0.58 (F4 5380); both 0.66–0.72 (no better than one). Chosen: the
  laryngeal cavity (one part, supported for all vowels by the human
  literature): cavity ~5 mm, inlet ~3 mm narrowed to 15% of the throat.
- Tissue damping barely changes anything (tested 0.25–1x).
- **His bright 3–5 kHz cluster is lit partly by breath.** Gentle voice + a
  little breath gives both the deep hum valley and the bright cluster. His
  purity at 3–5 kHz is 8.6–14 dB (partly noisy); the model's is 6–8 dB.
  Breath is modelled physically: glottal turbulence, rising toward high
  frequencies, in puffs while the folds are open.
- Result: all four "ee" resonances in place (340 / 2990 / 4360 / 5060 vs his
  362 / 3323 / 4119 / 4963). Voice box: Oq ~0.44, gentle closure, a little
  breath.
- OPEN: (1) per-"ee" F1 differs in him (362–408 Hz); one shared shape gives
  ~335–400 Hz, so the model hums too deeply at 330/350 Hz. Probably context
  (what comes before each "ee"), for the dynamics step. (2) Measured jitter
  is inflated by breath in the model (0.5–1.7% vs his 0.2%) even with near-
  perfect fold steadiness: an analysis interaction, not settled.

### Step 1c: a warm, pure hum (`scripts/build/ee_tone.py`, `analysis/physics/tone.py`)

Da Boss on 1b: "very breathy, jittery, not a pure, smooth hum tone... airy...
almost shrill... needs to be a warm, pure, bnuy hum tone." Measured per band
(harmonics vs the noise between them, dB re H1):
- **His bright 3–5 kHz band is harmonic**: noise 17–23 dB below. The breath of
  1b was wrong (my band-filtered purity measure had misled me). Breath removed.
- **His top (5–8 kHz) is quiet** (−32…−42); 1b's was −17 (shrill).
- **His pitch drifts slowly** (5–25 cents, under 8 Hz) with almost no fast
  wobble (2–3 cents). Random cycle-to-cycle jitter is audible roughness.
  Rendered now as slow, smooth drift (~6 cents) + tiny cycle variation.
- A chain of compensation was found and undone: fitting the voice box to the
  hum region only made it too gentle, which starved the bright band, which
  breath then patched.
- Joint fit (one "ee" shape + larynx depth + one voice box, on band levels and
  his hum): voice box **closes cleanly** (Oq 0.61, am 0.59, Ta 0): an ordinary,
  relaxed-but-firm closure. **His "ee" asks for the larynx ~1.5 cm lower.**
  Resonances 380 / 3450 / 4690 / 5390. Noise 28–50 dB under the tone; wobble
  slow/fast 4–9 / 1–4 cents; top −29…−39 dB.
- OPEN: at 350 and 330 Hz the model hums too deeply and its bright band is
  6–10 dB weak (his F1 is higher in those "ee"s: context, for the dynamics step).

### Step 1d: why 1c sounded "very, very, very computery" (`analysis/physics/ee_props.py`)

Every property of his four "ee"s, over time and cycle by cycle, vs the model:

| inside one "ee" | him | 1c model |
|---|---|---|
| cycle-to-cycle period / loudness variation | 0.2–0.55% / 2–7% | 0.1–1.2% / 3–4.5% (fine) |
| F1 / F2 / F3 wandering (sd) | 5–13 / 32–136 / 70–317 Hz | 0.1–0.5 / 1–5 / 2–6 Hz |
| hum depth (H1–H2) / bright-band flicker | 0.6–1.1 / 1.3–2.1 dB | 0.1 / 0.1–0.3 dB |
| loudness swell | 0.2–0.7 dB | 0.02–0.16 dB |
| F2 trend across the "ee" | −131 to +310 Hz (after p: rising out of the lips) | ~0 |
| phrase-final end | ~150 ms tail | 25 ms |
| noise under the bright band | ~20 dB below the harmonics | 30–40 dB below |

**The folds were already fine. The mouth and breath were frozen.** His
fluctuations split into slow, purposeful movement (out of the consonant,
toward what follows, settling into a tail) and fast timbre flicker
(14–40 Hz). A tongue or jaw can't move that fast, so the flicker is the folds
closing slightly differently every cycle; formant-tracker noise on his
high-pitched clip, and the neural generator the clip came from, also add to it.

Physical, ordinary-physiology ingredients (no new biology):
1. a moving mouth: in from the consonant before, out into a phrase-final tail
   (lips closing, the hum carrying on through the nose)
2. a living mouth: small slow drift of tongue, jaw and lips (under 6 Hz)
3. living folds: each cycle's closure slightly different
4. breath pressure that swells gently
5. a whisper of glottal turbulence (about a tenth of 1b's)

`prince_voice/voicebox.py`: a renderer whose mouth can move (pose every 5 ms,
overlap-add). An automatic calibration on the fluctuation measures chose no
drift and no cycle variation, partly because the model's F1 sits so exactly on
its pitch that drift swings its loudness more than his. These measures are
noisy on short sounds. So four versions, each adding one factor at modest
physiological amounts, go to Da Boss's ear: A frozen, B moving mouth,
C + living mouth and folds, D + a whisper of turbulence.

### Step 1d verdict and diagnosis

Da Boss: "increasingly computery... very weird, stuttery, with odd pitch
changes that range from 'he is very phlegmatic' to 'he sounds like he is
dying'". Rejected: A–D.
- The odd pitch was mine: an added onset scoop, a falling tail, random drift.
  Never add pitch movement without his reason (BUILD_RULES §4).
- The root cause is my renderer: pulses through a frame-switched filter, with
  randomness layered on top. A living voice's variation comes from physics
  interacting (airflow, folds and tract), which that renderer doesn't simulate.
- VocalTractLab's time-domain physical simulation can be driven with our own
  tube (`prince_voice/vtlsynth.py`, via its C API `vtlSynthesisAddTube`). With
  an ordinary human "ee" tube it is steady, full and naturally variable on its
  own (wobble 3.9/1.2 cents vs his 5.7/2.4; noise 28–51 dB down). With the bun
  tube it fails (a near-sine, unstable pitch): its vocal folds are human-sized
  and the bun airway is 10–50x smaller in cross-section. Next: give the
  simulation a bun-sized larynx (a small animal has a small larynx; a rabbit's
  is about child-sized).

### Step 1e: back to 1c, with breath and roughness put back (`scripts/build/ee_ladder.py`)

Da Boss: it sounded fine earlier; 1c over-corrected (breath and roughness
removed almost completely: "just a tone"). Everything after 1c tried to add
life back the wrong way. 1e is 1c exactly (mouth, voice box, slow drift),
with only breath and cycle-to-cycle roughness in five equal steps from 1c (0)
to 1b's level (4). Da Boss picks by ear.

**Da Boss's pick: step 3** → `models/ee_tone_approved.json`. His "ee" tone:
1c's mouth and voice box (clean closure, Oq 0.61), breath 0.0375 (3/4 of 1b),
cycle jitter 0.2%, cycle shimmer 1.5%, slow pitch drift ~6 cents, loudness
drift 0.15 dB. Measured at 264 Hz: noise 22–49 dB under the harmonics per
band, wobble slow/fast 8.4/10.2 cents. This is the tone to build on.

### Step 1f: his "ee" tone by tone (`analysis/physics/ee_decompose.py`, `scripts/build/ee_tones.py`)

Da Boss: "it is a collection of tones... we can figure out how to make this
specific sound." His "ee" decomposed into every harmonic's level, flicker and
phase (place in the cycle), every 2.5 ms; all four of his "ee"s agree:
- **Levels:** a very deep valley (harmonics 4–11 at −43…−63 dB re H1), a bright
  cluster near 3.2–4 kHz, a quiet top.
- **Phase:** only harmonics 1–2 (3) keep their place in each cycle; higher
  ones wander (steadiness 0.1–0.8). The model had every harmonic locked (every
  cycle identical): a machine signature.
- **Flicker:** harmonics 1–3 steady (~1 dB); higher ones 2–6 dB.

Mechanism, tested: the folds' **closing moment varies ~0.1 ms per cycle** while
the bulk airflow of each cycle stays steady. High tones scramble, low ones stay
locked, which is exactly his pattern. Varying the whole pulse shape instead
was wrong: it scrambled his steady low tones and made them flicker up to 19 dB.
Result: phase and flicker profiles in his range; breath 0.01; cycle loudness
variation 0.5%; larynx ~2 cm lower; level error 7.3 dB (his H2 at 264 Hz and
his bright cluster still a little stronger than the model's).

### Step 2: where every tone comes from (`scripts/build/ee_recipe.py`, `ee_inverse.py`)

**The tone map of his "ee"** (264 Hz; the other three agree, shifted by pitch):

| tones | his level (dB re H1) | what makes them |
|---|---|---|
| H1 (264 Hz) | 0 | the hum: the mouth's first resonance (F1) sits on his pitch and lifts it |
| H2–H3 (0.5–0.8 kHz) | −10, −32 | the skirt of F1: how far each lies above it |
| H4–H11 (1–2.9 kHz) | −43…−63 | the valley between F1 and F2; its depth is set by how narrow the tongue channel is (and the folds' fall-off) |
| H12–H14 (3.2–3.7 kHz) | −24…−28 | F2, the throat behind the tongue (set by larynx depth) |
| H15–H20 (4–5.3 kHz) | −30…−37 | F3 (the cavity in front of the tongue) and F4 (the laryngeal cavity) |

- Inverse filtering (his tones ÷ the fitted mouth) recovers a textbook vocal-
  fold puff at 389 and 350 Hz: smooth rise, quicker fall, closed pause. His
  tones are a real larynx through a real mouth. The method can't fix the
  recipe by itself (with only 2–3 steady tones it opens the mouth to cheat;
  rejected).
- **Bug found:** every "ee" fit so far (steps 1–1f, including the approved step-3
  tone) had the tongue channel almost sealed (0.003–0.004 cm², step 1f
  0.000): effectively a closed-mouth hum leaking through a numerical sliver,
  because nothing required the channel to be open.
- With an open channel required (≥0.04 cm²) his deep valley can't be reached
  (10–20 dB too shallow); the fit presses toward ~0.017 cm². So his "ee" is a
  **very close "ee"**: a very narrow tongue-palate channel. Physics says such a
  channel also makes its own small hiss, shaped by the cavity in front of the
  tongue (F3 ~4.4 kHz), which would be phase-random. That matches his wandering,
  bright 3–5 kHz tones. Not yet tested.

### Step 3: puff and tube fitted together (`scripts/build/ee_exact.py`)

A free, smooth, bun-sized tube (tongue channel narrow but open) and a flexible
vocal-fold puff, fitted together on every tone's strength and his steady low
tones' timing; one shared "ee" tube, then each "ee" nudged by its context.

| run | 264 Hz | 389 Hz | 350 Hz | 331 Hz | notes |
|---|---|---|---|---|---|
| ceiling: a free tube per "ee" (KLGLOTT puff) | 8.0 | 9.5 | 5.9 | 10.3 | before the joint fit |
| joint fit | 8.5 | 8.6 | 6.4 | 5.9 | presses the channel limit (0.015 cm²) and length limit (8.6 cm); puff open 95% |
| A: puff forced open half, even | 7.3* | 9.3 | 7.3 | 7.1 | *264 not reproduced; no harmonic-4 dip: the dip is NOT the puff (rejected) |
| B: narrower (≥0.006) and longer (≤9.5 cm) allowed | 6.8 | 8.8 | 6.1 | 6.0 | barely better |

A single tube + a puff levels off at ~6–9 dB. The misses are the same few
tones: a sharp dip at harmonic 4 (264, 350, 389 Hz) / 3 (331 Hz), 15–20 dB
deeper in him, and a much purer hum at 389 Hz (his H2 −32, model −6). Bun
translation of the B tube: larynx ~1.8 cm lower, shape match 0.87.
