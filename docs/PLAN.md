# The plan: his real voice through his one mouth

Rule zero applies throughout (docs/BUILD_RULES.md): if a step fails or I want to
deviate from Da Boss's idea, I stop and say so first. A listening check is a stop:
I send the clip and wait for the verdict.

Measured gaps in the current rebuild (onevoice_P1), which this plan is meant to close:
- **Muted:** the modeled buzz is 54 dB down at 1.5-3 kHz. The open vowels are 13-18 dB
  short at 1.5-3 kHz, and the "ee" ring at 3-6 kHz is about 10 dB short.
- **Weak hum:** "m" and "ɹ" leak mid and high sound (600-1500 Hz is 9-11 dB down
  instead of 20-28 dB). The fitted "m" has its lips 0.03 cm² open.
- **Too steady:** brightness inside a sound moves 8-55 Hz; his moves 60-310 Hz. Every
  cycle is an identical copy.

## Step 1. Recover his real voice from the clip (Da Boss's idea)
- Glottal inverse filtering (IAIF) on his open, steady sounds ("ã", "ɐ˞", the long
  "ee"s). This undoes his mouth using his own recording, not my mouth model.
- Checks: it is pitched; it looks like vocal-cord pulses (a smooth opening, then a
  closure); it is consistent from one sound to the next.
- **Listen 1:** his recovered voice alone, played next to the old buzz.
- If it comes out unclean: stop, report, ask.

## Step 2. His voice bank
- Store the recovered cycles as they are, each tagged with pitch and loudness.
- When he speaks, each cycle is drawn from his own cycles at a matching pitch and
  loudness. This carries his real cycle-to-cycle variation (old proposal C2). It also
  carries his real "harder push gives a brighter voice" behaviour (old proposal B),
  measured from him instead of modeled.
- This replaces the modeled buzz everywhere. Nothing is modeled here unless Da Boss
  agrees.

## Step 3. Refit his one mouth to his real voice
- The voice is held fixed, so the mouth can no longer trade off against it: no dulled
  voice and no notches.
- Old proposal A goes in here: "m" is a true lip seal, and the hum comes out of the
  nose. The same applies to the closures in "n".
- Score each sound against the clip's tones. Check the hum bands on "m", "n" and "ɹ",
  and the brightness bands on the vowels and "ee".
- **Listen 2:** clip vs rebuild, "nannarmunis... peet teet tee", voiced sounds only.

## Step 4. A mouth that isn't frozen (old proposal C1)
- Small, slow wanders of the tongue and jaw while he holds a sound. The target is his
  measured brightness movement (60-310 Hz) and loudness flicker.
- Built as a ladder of about 4 steps, from none to his full measured amount.
- **Listen 3:** Da Boss picks the step.

## Step 5. Movement between sounds (old proposal D, phase B)
- Fit the timing and shape of each glide between positions to his clip, replacing the
  plain 30 ms smoothing.

## Step 6. The consonants (phase C)
- The soft S, "p" and "t" made by the same mouth: air through a narrow gap for the S,
  a closure and release for the stops.

## Step 7. The whole phrase (phase D)
- Score against the gold standard. **Listen 4.**

## Step 8. New things in the same voice
- His real voice bank and the one mouth, saying sentences from VOICE_SPEC, with
  nothing re-tuned per sentence.
