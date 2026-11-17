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
