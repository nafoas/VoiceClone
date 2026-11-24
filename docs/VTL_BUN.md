# VocalTractLab's physics with our bun mouth on top (feasibility, 2026-11-21)

Da Boss: "take VocalTractLab's full physics and engine, and simply put our Bnuy mouth on top of it."

## It can be done
- VocalTractLab's library (API 2.4.2, installed) has `vtlSynthesisAddTube`: its full time-domain engine
  driven by ANY tube we give it, changing every 2.5 ms: 40 section lengths and areas (our bun mouth also
  has 40), which articulator forms each section (tongue / teeth / lower lip / other: decides where hiss is
  made), the teeth position, the soft palate's opening, the tongue tip's side lowering (TS3: side channels,
  the "l" mechanism), and its vocal-fold model's settings. The Python wrapper does not expose it; we call the
  library directly: `scripts/build/vtl_tube.py`.
- Its anatomy outside the tube comes from a speaker file; `models/bun.speaker` makes it bun-sized: nose
  6.05 cm (our bun model's), larynx pockets and windpipe x0.55, vocal folds 0.5 cm long, 0.25 cm thick,
  resting pitch 300 Hz (human: 1.6 cm, 0.45 cm, 120 Hz).

## First tests (our checkpoint-8 bun shapes, uncalibrated)
- Stable at bun size (sections 2.5 mm).
- With HUMAN vocal folds the bun "ee" choked: human airflow through his 0.01 cm^2 gap; everything above
  2 kHz 50-130 dB down. With bun-sized folds nearly closed at rest, his harmonics come back up to ~3 kHz;
  3.5-5 kHz still too weak, an odd dip at 4-6 kHz.
- "ee-tee": the tip seals, pressure builds, the release is a real pressure click, the voice weakens and
  recovers by itself. But little breath hiss after the release (his t is ~80% noise) and a strong hum
  inside the closure: the folds, the aspiration and the noise sources need calibrating to his size.

## What it would mean
1. **His voice would be made by VocalTractLab's vocal-fold model** (sized and tuned to sound like him: his
   pitch, breathiness, closure), not by his recovered voice cycles. The engine has no input for a recorded
   voice: its realism comes from the folds and the mouth acting on each other. This departs from rule 2b
   ("his one neutral voice is the source") and needs Da Boss's OK.
2. His vowel shapes need refitting inside its physics (its losses and walls differ from our tube's).
3. Movement is still ours: we drive the tube; articulator dynamics (mass, muscle) still to be added.
4. It is a much richer tube (folds and mouth interacting, airflow, turbulence placed by articulator, side
   channels for l, nasal sinuses, larynx pockets, yielding walls), but still a tube: not a 3D soft mouth.
   And it has no room.

## Da Boss's goal (2026-11-21)
"My explicit goal was to be able to turn this into simply the way he talks, such that you don't need to
constantly edit the sound for it to sound properly. So it's useless if you need to constantly apply post
processing." So: calibration happens ONCE (his folds, his mouth shapes: who he is); after that every new
line comes straight out of his folds and mouth, nothing applied to the sound. No room is added to his
output; his recording's room is only accounted for when comparing against it.

## Da Boss (2026-11-21), for later
- "You could just make it so he constantly speaks in a room. But we can do that later."
- Pitch, loudness, timing: "fitted simply to the way the little guy talks". "nannarmunis... peet teet tee"
  is not a one-off: it shows a broader pattern of how he talks. Wanted: a cohesive, coherent little bun
  with similar (not robotically identical) ways of pronouncing words, and consistent, context-dependent
  pitch and diction (excited? out of breath?) built into the way he speaks. No external fitting.
  Matching the clip is part of learning that pattern, not the goal itself. Both come after the mouth and
  folds are right.
- Taken as the go-ahead for VocalTractLab's vocal folds (set once to sound like him) in place of his
  recovered voice cycles (rule 2b changes on this path); Da Boss hears each step.

## Step 1: his vocal folds and his "ee" (2026-11-21)
Calibrated ONCE, inside VocalTractLab, with his bun mouth's tube (scripts/build/vtl_calib.py; models/vtl_folds.json):
- Judged on the tones of his three "ee"s (1.52, 1.77, 2.09 s), the same yardstick his mouth was fitted with.
- Folds alone: tone error 27.3 -> 7.8 dB. Folds + the "ee" shape together (his bun controls, no contact):
  5.20 dB (the old engine with his recorded voice: ~4.5-5.9 dB on the same "ee"s).
- His folds: short (0.25 cm) and thick (0.60 cm, at the edge of the range allowed), soft lung pressure
  (4716 dPa), resting a little apart (0.021-0.025 cm) with a leak (0.03 cm^2, at the edge), small swing
  (0.31), aspiration at its minimum (-40 dB, at the edge). Three settings at the edges of their ranges:
  to be looked at when more of his sounds join the fit.
- His "ee" in VocalTractLab: tongue body high, tip down, gap 0.029 cm^2 (was 0.010), lips a little wider,
  soft palate just open (his constant nasal colour).
- Listening file: reference/archive/vtl_ee_step1.wav (his ee | checkpoint 8 | VocalTractLab + bun mouth, x3).
- Library note: reloading the speaker file on every try leaks memory; the search loads it once per worker.

## Step 2 finding: the engine used human side parts (2026-11-24)
- `vtlSynthesisAddTube` takes only the pharynx-mouth tube and the velum opening. The synthesizer's own
  working tube is built once with VocalTractLab's human defaults and `Tube::interpolate` copies only the
  moving parts, so every synthesis so far (step 1, step 2) ran his 9.8 cm bun tube with a human 23 cm
  windpipe (2.5-4 cm^2), a human nose (Dang & Honda subject 1, 0.8-4.2 cm^2) with 57 cm^3 of sinuses and a
  human 3 cm / 2 cm^3 piriform fossa. models/bun.speaker's windpipe, nose and fossa never reached the sound.
  The nose also always branches after section 16 of the 40 (0.40 of his length; his velum is at 0.51).
- Fix in our build: `Tube::copyStaticParts` (the working tube takes the side parts of the tube it is
  given) and `vtlSetSideAnatomy` (windpipe length/area, 19 nose sections, sinus scale, fossa). Without the
  call, output is bit-identical to the unmodified library.
- His side parts (`scripts/build/bun_vtl.py`, all search variables later): windpipe 6 cm x 0.33 cm^2
  (rabbit trachea ~6-7 mm across), the bun model's nose (0.30-0.12 cm^2 x size^2) behind a 0.3 cm velum
  port, sinuses negligible (the bun model had none), no piriform fossa (the bun model rejected it); his
  tube re-cut into 16 + 24 sections so the nose branches at his velum (1/area averaged: seals stay sealed).
- Tube response (`scripts/build/vtl_probe.py`, pulse above closed folds): peaks 0.34/2.34/3.24/4.6/6.0 kHz
  with the human parts, 0.37/3.21/4.6/5.42 with his; the old bun mouth model: 0.38/3.2/4.69/5.56.
- Walls: rigid walls leave the response above 1 kHz unchanged (relative), and damp only the first
  resonance (~4.5 dB). Not the cause of the weak 2.5-5 kHz cluster. In the voiced "ee", rigid walls make
  it worse (the 389 Hz "ee" changes regime): walls matter through the folds, so bun tissue (Step 3.1).
