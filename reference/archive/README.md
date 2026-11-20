# Archive: clips worth keeping

`out/` is scratch (git-ignored, and the cloud container is temporary). Clips
that record a decision or a verdict are copied here.

- `fresh_pinned/`: Fresh Sayings made with the gold technique (pinned).
  Verdicts: munis... nannar "perfect", nanni "good", mama_F the best mama
  ("still nanner"; later "strained/choking"), mama_A_none = "nana". The diag_*
  sets wait for picks.
- `mouth/`: first VocalTractLab-mouth tests. compare_mama_minny = old warp vs
  mouth "ah" (x2 lip methods); compare_ee_vs_ih = neenee / ninny / minny (old
  ee) / minny (mouth ɪ). Verdict: "alright, but fairly robotic, a little
  constrained, and without enough hum".
- `bunmouth/`: the bun mouth. rebuild_one_change_bun.wav = the gold clip rebuilt
  by a normal small bun's mouth with only a lower larynx (LSD 9.3).
  mouth_rebuild.mp4 and true_size.png show the earlier version with extras
  (cheeks, mobile larynx), since dropped for parsimony. poses.png is the first
  (2x-size) bun. Da Boss on the 2x rebuild: "I like it".
- `diagnostics/`: compare_v9 (gold v9 vs clip), v16 intents (rejected:
  "worse, robotic"), english_ref (the ordinary adult voice used as a negative).

The gold standard itself is in `reference/gold/`, the source clip in
`reference/source/`, his sentences (the audit, V8) in `reference/sentences/`.

- `build/`: the model-only build (his "ee"). Verdicts: step 1 "the least
  computery" of the run; 1b breathy/jittery/shrill; 1c very computery (just a
  tone); 1d stuttery/phlegmatic/"dying"; engine check "dial-up". **1e ladder:
  Da Boss picked step 3** (`ee_tone_approved.json`).

## onevoice_P1_clip_vs_model.wav
Clip phrase, then model phrase. One physical puff voice (the same vocal cords for all
12 voiced sounds) through the one reverse-engineered mouth (mouth_inverse_P1, 10.7 dB
tone error), moving between sound positions. Loudness = breath pressure on the source,
no output processing. Consonants silent (phase C). Verdict: pending.

## listen2_his_voice_his_mouth.wav (PLAN step 3, Listen 2)
Clip phrase, then model phrase. His real voice (cycles recovered from the clip by
quasi-closed-phase inverse filtering), buzz by buzz through the one mouth refitted to
that voice (mouth_inverse_H2: 9.5 dB fit, m sealed). Consonants silent. Verdict: pending.

## listen2b_whole_phrase_fit.wav (step 3 tightening)
Clip phrase, then model. His real voice buzz by buzz; mouth positions, anatomy and the
movement between sounds fitted together on every 5 ms of the phrase (phrase_fit F1);
smooth breath contour, voicing eases in/out, tube validity per shape. Whole-phrase
likeness 7.28 dB (Listen 2: 8.62). Verdict: pending.

## listen2c_walls_radiate.wav (step 3 tightening)
Clip phrase, then model. Same as listen2b, plus two physical additions to the one mouth:
the nose's turbinate surface (fitted x10.9 viscous loss) and the yielding walls of his
mouth and throat radiating sound (output = lips + nostrils + walls). Refit on the whole
phrase (phrase_fit F4). Whole-phrase likeness 6.77 dB (listen2b 7.28, Listen 2 8.62);
tone error 8.1 dB. Verdict: pending.

## ladder_voice_cleanness.wav (step 3, a question for Da Boss)
Per phrase: the clip, then the model three times (mouth F4, no cord gap yet):
1. his recovered cycles as they are (listen2c);
2. each cycle averaged with its two neighbours (his clarity of upper tones measured
   2-5 kHz 16.7 dB / 5-9 kHz 4.7 dB; this gives 18.9 / 7.1; as-is gives 13.6 / 0.2);
3. averaged over five cycles (21.1 / 9.4, cleaner than him).
Whole-phrase 6.77 / 6.41 / 6.47 dB. Verdict: pending.

## listen2d_cord_gap_clean_cycles.wav (step 3 tightening)
Clip phrase, then model. Since listen2c: the vocal-cord gap loads the tube (fitted mean
opening 0.0018 cm2; removes the sharp 6 kHz ring heard as "tinny"), and his cycles are each
averaged with their two neighbours (Da Boss approved; recovery error removed, upper tones
as clean as his). Whole-phrase refit (F5). Whole-phrase likeness 6.04 dB (listen2c 6.77);
tone error 8.0 dB; "ee" 7.3 -> 6.0, "ã" 4.3 -> 3.4. Verdict: pending.

## listen2e_top_end.wav (step 3 tightening)
Clip phrase, then model. Since listen2d: the fit's judge now scores every band that stands
above the recording's hiss (the old -50 dB cut hid his 7-11 kHz "air"). Refit F6.
Average gap at 7.2 / 9 / 11.4 kHz: listen2d -18 / -14 / -9 dB, now +2 / -2 / +1.
Whole phrase, new judge 8.41 -> 7.42 dB; old judge 6.04 -> 6.65 (the low mids, 450-900 Hz,
came out 1-2 dB fuller); tone error 8.0 -> 7.8. Head radius 4.0 -> 3.46 cm. Verdict: pending.

## listen2f_size_losses_pooled_voice.wav (step 3 tightening)
Clip phrase, then model. Since listen2e: (1) tube losses grow as his small tubes narrow
(boundary-layer physics; no new setting); (2) the fit's judge weights each band by how far it
stands above the hiss (the flat judge had traded his hum for faint air); (3) buzzes rendered at
their exact instants with one continuous fold rhythm (jitter roughly halved where worst); (4) his
cycles pooled by pitch (three pools), blending over 4 cycles at pool changes, so no voice jumps at
sound joins. Refit F9. Whole phrase (audibility judge) 6.66 -> 6.19 dB; old judge 6.41 -> 5.96;
ee hum up 2-5 dB, ee F1 down 30-45 Hz. Verdict: pending.

## listen2g_anatomical_controls.wav (step 3 tightening)
Clip phrase, then model. Since listen2f: three anatomical controls per sound (throat width,
soft palate lowered into the passage, lip spread; BUILD_RULES ledger), the "i" of "munis" with
its own position, and each recovered cycle's slow level drift removed (his old loudness swells
no longer replayed). Refit F12. Whole phrase (audibility judge) 6.19 -> 5.87 dB; all bands
6.94 -> 6.60; old judge 5.96 -> 5.58. Verdict: pending.

## listen3_provisional_consonants.wav (PROVISIONAL: the whole phrase with consonants)
Da Boss: "provisionally reconstruct the whole thing with consonants ... maybe that's why I'm
hearing this." Clip phrase, then model. Mouth F13 (anatomical controls + per-sound shape terms +
measured-mouth guide). New, all from the same mouth (scripts/build/consonants.py):
- voiced closures: his voice hums on (as long as the clip shows pitch) while the tongue tip closes
  for "t" (the "n" position, nose shut), heard through the walls; tails match his (~-35 dB)
- soft s: turbulence at the tongue-front gap, shaped by the mouth in front of it
- t: a burst where the tip lets go, then breath from the cords through the opening mouth
- p: his weak p, breath through the lips opening wide
- noise spectrum from the jet (Strouhal frequency from the soft-voice lung pressure and gap width),
  plane-wave limit applied as for the voice
PROVISIONAL: each consonant's loudness over time is matched to the clip (relative to his vowels).
Brightness centre his/model: t 4.1-4.9/4.5-5 kHz; soft s 4.4-5.2/~7 kHz; p ~2/~4.5 kHz.
Voiced-sound whole-phrase likeness 5.56 dB. Verdict: pending.

## listen3b_consonants_resonances.wav (PROVISIONAL, with consonants)
After Da Boss on listen3 ("La La Lillies", "Kekeke", higher/tinny/monotone, static buzz, no warmth):
- fast tongue tip and lips (closures open/shut in ~15 ms; the slow 40-70 ms glides made n sound like l)
- "t" before "ee": hiss where the tongue blade lets go at the front palate, then breath (was breath
  shaped by the "ee" into one mid peak, heard as "k"); turbulence falls ~12 dB/octave above its jet
  frequency; t centre 5.3-6.2 kHz (his 4.7-4.9), soft s 4.8-5.9 (3.6-5.2), p 2.2-3.3 (~2)
- the fit now targets his resonances (F1/F2, read the same way from his measured mouth and the tube)
- the judge counts audible excess (a buzz where he is quiet) as well as shortfall
Refit F14. Pitch identical to his. Whole phrase (current judge) listen3 6.33 -> 6.12 dB.
NOT fixed: nasal buzz (his voice in hums has weak upper tones; the model's voice is recovered from
open vowels only), warmth of the first "ee" and "ã". Verdict: pending.

## listen3c_fixed_spike_same_loudness.wav (listen3b, repaired)
listen3b had a bug: the consonant loudness matching divided by a near-silent frame edge and made a
spike in the first "t" hiss ~30 dB above everything; the file scales each phrase by its peak, so
"peet teet tee" played ~30 dB too quiet. Fixed (smoothed energies, capped gain). Also, clip and model
are now played at the same loudness (rms over his voiced sounds) instead of the same peak (the
model's voice is a little peakier, so it always played 1-2 dB quieter than the clip). Same mouth
(F14) as listen3b. Verdict: pending.

## ab_previous_vs_his_movements.wav (A/B for Da Boss)
Per phrase: the clip, then the previous mouth (listen3c, F14), then the mouth driven by his measured
movements (inversion tool, SPARC: jaw, tongue height, tongue forward, lips, rounding come from his
movements; the mouth's anatomy and conversions fitted around them; refit T2). Both with consonants.
Scores say the new one is worse (whole phrase 6.1 -> 7.9 dB; the "i" of "munis" nearly closes, the
middle "n" and "ũ" worse). Your ear decides. Verdict: pending.

## abc_previous_movements_combined.wav (A/B/C for Da Boss)
Per phrase: the clip, then (1) previous mouth (listen3c), (2) driven by his measured movements (T2),
(3) combined: his measured movements set each sound, each may fine-tune within +-0.15 (costed),
glides refitted (T3). All with consonants. Whole phrase: 6.1 / 7.7 / 6.4 dB. In (3) the "i" of
"munis" opens again (0.2 mm gap; 10.6 -> 7.1 dB). Verdict: pending.

## step1_ee_lips.wav (version 1 + one change)
Per phrase: the clip, version 1 (listen3c mouth), version 1 with ONE change: the "ee"s and the "i" of
"munis" no longer round and spread their lips at once; the lips are relaxed as the inversion tool reads
him, and only those sounds' other controls refit with the whole-phrase judge (top end included).
Trade-off: tones up to ~5 kHz match better, but the top end (>7 kHz, his "air") is weaker; on the "ee"
frames the whole-phrase judge goes 6.0 -> 6.75 dB. Everything else untouched. Verdict: pending.

## overnight_1_diction.wav (overnight tuning, checkpoint 1)
Per phrase: the clip, then the model tuned by ear-models (phoneme recogniser, apparent age, speaker
likeness; docs/OVERNIGHT_REPORT.md), starting from version 1. Heard per sound now vs version 1:
m: m 0.88 (was l 0.65); middle n: n 0.62; t: t 0.86 (was tʃ/k); p: p 0.61 (was k 0.76); soft s: s 0.80
(was sh 0.77); ɹ: l 0.30 / r 0.24 (was l 0.39 / r 0.13). Apparent age 8.4 (his 13; version 1 ~7-9).
Adds breath (pulsed aspiration at the folds) at his measured level. State: models/perc_state_overnight1.json.

## overnight_2_older.wav (overnight tuning, checkpoint 2)
Per phrase: the clip, then the model. Larynx at 3.0 cm (within his approved adaptation's existing range,
1.1-3.4 cm; was 2.3-2.4) with the vowels, nasals, r-sounds and consonants re-tuned for that length.
Apparent age 13.2 (his 13.1; version 1 ~7-9). Heard per sound: m 0.75, middle n 0.87, ɹ r 0.60, p 0.83,
soft s 0.90, t 0.78/0.73; open: the last t (heard r 0.32) and ɐ˞. State: models/perc_state_overnight2.json.

## overnight_3_size080.wav (overnight tuning, checkpoint 3: current best)
Per phrase: the clip, then the model. His mouth scaled to 0.80 of the reference rabbit (was 0.75; +6.7%,
within natural variation; still a small bun): his resonances had been several percent too high, which is
what made him sound younger (diagnostic: shifting his own clip up 11% makes the age model hear 4 years).
Larynx back at 2.4 cm (the deeper 3.0 cm larynx fixed age but rang at 7 kHz: tinny, less natural).
Mouth re-tuned at the new size. Apparent age 12.9 (his 13.1), naturalness MOS 4.12 (clip 3.23;
version 1 2.51), diction 0.060 (version 1 0.21). Heard: p 0.84, t 0.86/0.76, s 0.87, n 0.90-0.98,
m 0.47; still wrong: ɹ (r/l 0.28 each), last t. State: models/perc_state_overnight3.json.

## overnight_4_glides.wav (overnight tuning, checkpoint 4: current best)
Checkpoint 3 plus the glides into and out of ɹ and m retimed by ear-model (ɹ lasts 50 ms, so it is mostly
movement). Heard: m 0.85, ɹ r 0.44 / l 0.33, n 0.94-0.98, ũ u 0.67, p 0.87, s 0.89, t 0.86/0.76;
diction mismatch 0.041 (version 1: 0.21), naturalness 4.15, speaker likeness 0.74, apparent age 11.8.
State: models/perc_state_overnight4.json.

## overnight_5_smoother.wav (overnight tuning, checkpoint 5)
Checkpoint 4 with the tongue starting to close for each "t" 15 ms before the vowel's label ends (the
loudness steps you hear after each "ee"), consonants re-tuned around it. Loudness tracking vs his
2.95 -> 2.41 dB; diction 0.045, apparent age 12.7, naturalness 4.11, speaker likeness 0.71.
State: models/perc_state_overnight5.json. Compare with overnight_4_glides.wav by ear.

## overnight_6_best.wav (overnight tuning, checkpoint 6: CURRENT BEST)
Checkpoint 5 plus: his voice starts when his own pitch starts (during the release of his weak, voiced p),
consonants re-tuned. Diction mismatch 0.042 (version 1: 0.21); p heard as p 0.83 (version 1: k 0.76);
loudness steps vs his 2.12 dB (checkpoint 4: 2.95); naturalness 4.34 (version 1: 2.51); apparent age 13.0
(his 13.1); speaker likeness 0.75 (version 1: 0.62). State: models/perc_state_overnight6.json.
