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
