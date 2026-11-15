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
