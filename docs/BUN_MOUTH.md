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

## His adaptations (where his mouth differs from a normal rabbit, and why)

He is a **small round bun at his real size** (0.75 x the 2.9 kg reference
rabbit; mouth and head unchanged). His resonances come from a longer throat,
not a bigger body.

| adaptation | normal rabbit | Prince | the ability it serves | precedent in nature |
|---|---|---|---|---|
| **Descended larynx** | high, locked into the back of the nose (breathes and calls through the nose) | about 4.5 cm down his neck, inside the fluff; the throat runs down to it | (1) his resonances: tract 5.6 -> 10.1 cm in the same small body; (2) unplugs the larynx from the nose, so he can speak through his mouth; (3) a long throat behind the tongue gives a wide vowel range (his ee F2 3300 to oo F2 1300) | red and fallow deer (pull the larynx down to roar), koalas (permanently low larynx), humans |
| **Mobile larynx** | fixed | rises up to ~1.9 cm for ee, sinks for oo | ee and oo need different throat lengths | humans (larynx higher for "ee", lower for "oo"); deer |
| **Velum seals** | at rest the larynx is locked into the nose | the soft palate lifts and seals, or opens on purpose (m, n, nasal vowels) | speaking through the mouth | follows from the descended larynx |
| **Puffed cheeks** | loose, fleshy cheeks (they fold into the gap behind the incisors) | can puff out, widening the front of the mouth | his low-F2 "oo" (without them, oo's F2 stuck near 1700 Hz; with them 1380) | rabbits' extensible cheeks |
| **Wider jaw drop** | small gape | jaw drops further, cheeks stretch at the front | his open "a" (F1 ~1180 Hz) | |
| Lips | very mobile split lip | pushed forward up to ~5 mm (real), puckered | rounding for oo | rabbits' constantly moving lips |

How it was decided (`scripts/bun_rebuild.py`; vowel fit as in `scripts/fit_mouth.py`):
error over his four vowels, in Bark.

| mouth | his vowels |
|---|---|
| small bun, high larynx (a normal rabbit) | 12.9: cannot make his vowels |
| 2x-sized bun (rejected: he is small) | 1.7 |
| small bun + larynx 3-5 cm down the neck | 3.3-3.7 |
| + puffed cheeks | 2.1-2.3 |
| **+ mobile larynx (his mouth now)** | **1.72**: as good as the 2x bun |

Whole clip, mouth only: 2x bun 8.0 LSD; his real size 8.7-9.0. Vowels fit
equally well; consonants and transitions are a bit worse. Doubling the pose
search didn't change that, so the gap is anatomy detail (calibration next).

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

## Size (superseded: see the adaptations above)

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
