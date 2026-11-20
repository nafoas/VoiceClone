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

## 4. Progress log
(filled in through the night)
