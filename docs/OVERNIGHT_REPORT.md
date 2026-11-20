# Overnight report (2026-11-20)

Da Boss's brief: tighten it as much as possible, by any means, as long as it stays his little bun mouth
doing it and nothing is post-processed; work out how to measure the subjective qualities (diction, hum,
babyishness, fidelity), not just spectra; research the vocal cords; keep iterating all night.

## 1. Measuring what you hear (the big change)
My spectral scores kept saying "closer" while your ear said "worse". So I brought in listener-models
(off-the-shelf neural models trained on human speech) and checked them against your past verdicts:

| Measure | Model | What it caught |
|---|---|---|
| Diction | wav2vec2 phoneme recogniser (facebook/wav2vec2-lv-60-espeak-cv-ft) | Hears the clip correctly ("nanʌmunis \| pititi") and hears version 1 as "nalal-muniʃ \| kikki": exactly your "la la lillies" and "kekeke". Per sound: m heard as l, the middle n as a, ɹ as l, t and p as k, the soft s as sh. |
| Babyish | audeering age/gender model | Clip: ~13 years. Every version you heard: 4-10 years. The models sound much younger than him. |
| Same speaker | WavLM speaker verification | Similarity to the clip, 0..1 |
| Volume steps | loudness every 10 ms vs his, consonants and gaps included | |
| Warmth | energy below 600 Hz vs 600-3000 Hz in his voiced sounds | clip 19.9; versions heard 17.5-18.5 |
| Guard | the old whole-phrase spectral judge | kept, weak weight |

Code: `scripts/listen/perc.py` (render + judge), `scorecard.py`, `report.py` (what is heard per sound).

## 2. Tuning his mouth by ear (overnight)
`scripts/listen/tune.py` + `overnight.sh`: CMA-ES over one group of his mouth's settings at a time
(consonants; nasals and nose; r-sounds; voice box and larynx; vowels; glides), cycling, each stage
starting from the best so far. Only his mouth's own settings move; anatomy stays within its limits.

## 3. Vocal cords
- **Breath in his voice (pulsed aspiration).** Real folds make turbulent noise while open, pulsing with
  each cycle's airflow. The model's voice had none (clean buzz up high, where his upper tones sit only
  4-20 dB above the noise). Added as a source at the folds; its level is set by measurement: 0.003
  matches his tone-over-noise at 0.5-2 / 2-5 / 5-9 kHz (37.5/18.7/5.0 dB vs his 37.4/20.9/3.8).
- **Size cues.** Listeners judge size/age mainly by vocal tract length (resonance spacing), pitch less,
  voice-source tilt a little. Larynx depth (your approved adaptation, within its existing limits) moves
  apparent age strongly in the probe (2.3 cm: 7 yrs; 3.4 cm: 19 yrs), so the voice-box stage tunes it.

## 4. What changed his sound, in order of impact
1. **Consonants by ear** (stage 1): where the air is squeezed, how narrow, the lips, burst length, tuned
   until the recogniser hears his consonants. "kekeke" -> "titi": t heard as t 0.86 (was k/tʃ), p as p
   0.84 (was k 0.76), the soft s as s 0.87 (was sh 0.77).
2. **Nasals and r-sounds by ear**: m heard as m (was l 0.65; the "soft palate into the passage" control
   I added had been choking his hum), the middle n as n 0.90 (was a/l). This is most of "la la lillies".
3. **Breath in his voice** (vocal-fold turbulence at his measured level): less clean buzz, more natural.
4. **Size 0.80** (see BUILD_RULES): the babyish sound was his resonances sitting a few percent too high.
   Scaling his whole mouth +6.7% (still a small bun) puts the age model at 12.9 years (his clip 13.1)
   and raises naturalness. A deeper larynx also fixed age but rang at 7 kHz (tinny) - rejected.
5. **Two more measures** after finding blind spots: timbre balance to 12.8 kHz (the 16 kHz listener
   models cannot hear the top) and naturalness (torchaudio SQUIM subjective MOS).

## Headline
The phoneme recogniser (the measure that reproduced your "la la lillies" and "kekeke") now transcribes:

| | heard as |
|---|---|
| His clip | **nanʌmunis \| pititi** |
| Version 1 | nalalmuniʃ \| kikki |
| Checkpoints 6 and 7 | **nanmunis \| pititi** |

"Peet teet tee" now comes out as his does; "nannarmunis" is one vowel (the ʌ) short of his.
Independent scorecard: warmth 20.0 (his 19.9), apparent age 13.4 (his 13.2), loudness flutter 1.45 (his 1.53).

## 5. Scorecard: version 1 vs the current best (overnight_6_best.wav, models/perc_state.json)
| | Version 1 (listen3c) | Now |
|---|---|---|
| Recogniser hears | nalalmuniʃ \| kikki | his phonemes, sound by sound (below) |
| Diction mismatch (0 = his) | 0.21 | 0.042 |
| Apparent age (his clip 13.1) | ~7-9 | 13.0 |
| Child probability (his 0.96) | 1.00 | 0.96 |
| Naturalness MOS (his clip 3.2) | 2.5 | 4.3 |
| Speaker likeness to his clip | 0.62 | 0.75 |
| Loudness steps vs his (rms dB, 10 ms) | ~3.0 | 2.1 |
| Warmth vs his | -1.5 dB | +0.1 dB |
| Timbre balance to 12.8 kHz | - | 1.9 dB rms |

Heard per sound now (version 1 in brackets): m: m 0.85 (l 0.65) · middle n: n 0.94 (n 0.49/l 0.38) ·
ɹ: r 0.44/l 0.33 (l 0.39) · ũ: u 0.67 (m 0.44) · p: p 0.83 (k 0.76) · t: t 0.86 / 0.82 (tʃ/k) ·
last t: weak (his own is only t 0.52) · soft s: s 0.8-0.9 (sh 0.77) · vowels: unchanged, correct.

Listen: **`reference/archive/overnight_6_best.wav`** (clip, then model, per phrase). Checkpoints in order:
overnight_1_diction, overnight_2_older (deep larynx; rejected: tinny), overnight_3_size080,
overnight_4_glides, overnight_5_smoother, overnight_6_best.

**Checkpoint 7** (`overnight_7_r.wav`): the r-sounds re-tuned with focus on ɹ, now heard as r 0.60 /
l 0.19; diction mismatch 0.038; apparent age 14.1; naturalness 4.21. Slightly less natural than
checkpoint 6 by the measure; which of 6 and 7 is better is for your ear.

### Later changes (checkpoints 5-7)
- The tongue starts closing for each "t" 15 ms before the vowel's label ends (labels mark where the sound
  changes, not where the movement starts): the loudness step after each "ee" shrinks.
- His voice starts when his own pitch starts (during his weak, voiced p release), instead of exactly at
  the vowel label: fewer steps, more natural.

## What I tried that did not work (and why it was dropped)
- Deeper larynx (3.0 cm): his age, but a narrow pipe at the bottom rang at 7 kHz (tinny, less natural).
- A per-sound "breath pressure" level instead of the copied loudness: worse loudness tracking.
- Voice push falling during closures (pressure build-up): spoils his humming tail; off.
- Widening the lower throat: too old, worse diction.
- Wider search steps once converged: no further gain.

## What is still open
- The volume steps you hear are mostly right after each "ee" before a "t" (model 10-16 dB too loud for
  20-30 ms) and at the "p" onset; nothing I tried fixed it without spoiling something else.
- Loudness and pitch are still copied from the clip (the effort step is not built yet).
- ɹ is half r, half l.
- My measures are proxies; your ear is the judge.

## 6. Progress log
=== 06:13 machine restarts when idle: tuning now runs in foreground chunks
=== stage nasal start 06:13 objective 5.849 diction 0.074 age 8.5 speaker 0.698 spec 6.02
=== stage nasal done 06:22 after 117 evals; best objective 5.387
=== stage r start 06:23 objective 5.832 diction 0.088 age 8.3 speaker 0.731 spec 6.18
=== stage voicebox start 06:33 objective 5.980 diction 0.059 age 6.4 speaker 0.731 spec 6.61
=== [deep_state.json] stage vowels start 06:45 objective 7.230 diction 0.125 age 11.8 speaker 0.626 spec 7.62
=== [deep_state.json] stage nasal start 06:54 objective 6.816 diction 0.116 age 12.0 speaker 0.629 spec 8.09
=== [deep_state.json] stage r start 07:03 objective 6.231 diction 0.095 age 12.4 speaker 0.636 spec 8.12
=== [deep_state.json] stage cons start 07:13 objective 4.913 diction 0.063 age 12.9 speaker 0.642 spec 8.13
=== stage cons done 07:21 after 120 evals; best objective 4.146
=== [perc_state.json] stage glides start 07:23 objective 4.146 diction 0.045 age 13.2 speaker 0.680 spec 8.13
=== stage glides done 07:31 after 112 evals; best objective 4.146
=== [perc_state.json] stage voicebox start 07:34 objective 6.212 diction 0.045 age 13.2 speaker 0.680 spec 8.13
=== [perc_state.json] stage vowels start 07:43 objective 5.944 diction 0.059 age 13.0 speaker 0.657 spec 7.77
=== [perc_state.json] stage throat start 07:53 objective 5.944 diction 0.059 age 13.0 speaker 0.657 spec 7.77
=== 08:06 naturalness added; working state back to checkpoint 1 (MOS 3.83 vs 2.66)
=== [perc_state.json] stage voicebox start 08:06 objective 6.408 diction 0.057 age 8.4 speaker 0.757 spec 6.81
=== stage voicebox done 08:15 after 99 evals; best objective 6.408
=== [mid_state.json] stage vowels start 08:16 objective 9.463 diction 0.109 age 9.3 speaker 0.740 spec 7.83
=== stage vowels done 08:24 after 96 evals; best objective 8.494
=== [mid_state.json] stage nasal start 08:24 objective 8.494 diction 0.094 age 11.7 speaker 0.698 spec 7.47
=== stage nasal done 08:33 after 91 evals; best objective 8.494
=== [mid_state.json] stage r start 08:33 objective 8.494 diction 0.094 age 11.7 speaker 0.698 spec 7.47
=== [size80_state.json] stage nasal start 08:46 objective 6.742 diction 0.078 age 12.4 speaker 0.675 spec 7.32
=== stage nasal done 08:55 after 91 evals; best objective 6.390
=== [size80_state.json] stage r start 08:55 objective 6.390 diction 0.087 age 12.5 speaker 0.700 spec 7.33
=== stage r done 09:04 after 96 evals; best objective 6.021
=== [size80_state.json] stage cons start 09:04 objective 6.021 diction 0.077 age 13.5 speaker 0.676 spec 7.30
=== [size80_state.json] stage vowels start 09:14 objective 5.438 diction 0.060 age 12.9 speaker 0.695 spec 7.30
=== stage vowels done 09:22 after 96 evals; best objective 5.438
