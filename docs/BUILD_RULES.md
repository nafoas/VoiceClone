# Building Prince's voice: what changes are allowed

My own rulebook. **Read it before making any change to how Prince sounds**, and
check every proposed change against it. When a change is not clearly
acceptable, ask Da Boss first. Da Boss's ear is the final judge; this guide
exists so I bring him changes that have a chance of being right.

---

## 1. The goal and the judge

- **Goal:** a little bun that talks the way Da Boss envisions him, built
  *entirely* from his own model: a bun mouth plus a voice box, with physics
  producing the sound.
- **Judge:** the gold standard (`reference/gold/rebuild_gold_v9.wav`, scores in
  `reference/gold/rebuild_gold_v9_scores.txt`), with the original clip
  (`reference/source/prince_reference.wav`) reported alongside. The gold is used
  **only to compare against**. Nothing from it, or from the clip, goes into his
  output.
- **Final word:** Da Boss's ear. A change that improves every number but sounds
  less like him is rejected. Report numbers *and* send audio.

## 2. Principles (Da Boss's own words where possible)

1. **Him first, rooted in biology.** Start from his abilities (what the gold
   shows he does) and ask *how bun biology makes that possible*. Never the
   other way around ("what can a normal rabbit do?"). Biology and his abilities
   are in harmony, not in conflict.
2. **Parsimony.** As few departures from a normal small bun as possible. The
   current count is **one**: a slightly lower larynx (see ledger, §6).
3. **Vary the biology he has; never invent biology.** "Bnuy mouths can be
   slightly longer or shorter, same with his little tongue, teeth, nasal
   cavity, etc., but what we can't do is invent new biology out of nowhere."
4. **He stays small.** "His entire identity is around being a small round
   fluffy creature." Never make him bigger to fix a sound.
5. **Every change needs a *why*.** No arbitrary variation, no randomness for
   its own sake. A change must answer: what about *him* (his anatomy, his
   physics, how he says things) makes this so?
6. **He is not performing.** Cute because of what he is. No babyish pitch, no
   sing-song, no added cuteness. Cute words, sincere voice (VOICE_SPEC.md).
7. **Not a child, not a cartoon, not a performer**: a little round creature
   trying his best. Not magical or gifted; normal rabbit biology, uncapped mind.
8. **The idiolect lives in the text.** Say what is written (VOICE_SPEC.md:
   dis/dat/da, "I's" = [aɪʑ], soft S [ɕ], "Bnuy!!" = [bnuːi], he only
   simplifies, stressed key vowels keep their identity, CAPS = excited, not
   screaming).

## 3. ACCEPTABLE changes

### 3a. Natural variation of the biology he has (anatomy)
Allowed: adjusting the size or shape of parts a normal small bun has, **within
normal variation**.

| Part | Examples of acceptable variation |
|---|---|
| Mouth / palate | slightly longer or shorter, a little wider or narrower |
| Tongue | length; the torus's size, height and position; tip and blade mobility |
| Teeth | incisor position or length (within rabbit norms) |
| Lips | the split upper lip's leak area; lip mobility within rabbit range |
| Nose | nasal cavity length, port size, how damped it is (turbinates) |
| Throat | pharynx width; tongue-root reach |
| Vocal folds | length, mass, how relaxed (tension), how smoothly they close |
| Walls | soft-tissue losses (how damped the tract is) |

Rules for anatomy changes:
- **Working range: within about ±15% of the normal small-bun value.** This is my
  assumption for within-breed variation. Beyond it, the change becomes an
  *adaptation*: stop and ask (§5).
- Every change costs something. When fitting, add a penalty for moving away
  from normal, so a change happens only if it clearly earns its place.
- Log each change in the natural-variation ledger (§6) with the property of his
  voice that needed it.
- Prefer one change that explains several properties over several changes
  that each explain one (the split lip explains weak "p" *and* voicing through
  it; a lower larynx explains size *and* oral speech *and* vowel range).

### 3b. How he says things (behaviour)
Allowed when it has a reason in *him*:
- **Mouth targets per sound**: one shared target per sound (his "ee" is one
  shape everywhere). Instances differ only by real movement dynamics (never
  quite reaching a target; anticipating the next one).
- **Timing**: durations, closures, joins, from his habits (PRINCE_IDENTITY.md §5).
- **Movement speed**: how quickly his mouth moves between targets.
- **Voice box controls**: pitch targets, loudness, breath, and how gently the
  folds close, from his prosody habits (calm ~215 Hz, raised ~265, excited
  330–390; pitch moves inside consonants; loudness steady across a breath;
  pitch made by fold tension, not breath pressure).
- **Pronunciation**: his tendencies (VOICE_SPEC.md), applied with their reason:
  simplification, forward placement where it suits him, the hummy u in its
  contexts.

### 3c. Fixing the model itself
Allowed, and encouraged:
- **Better physics**: a more faithful nose, losses, radiation, frication
  sources, a time-domain tube. The physics must be standard and documented, not
  a fudge.
- **Bug fixes and measurement fixes**: say what was wrong and how it changed
  the numbers.
- **Search and fitting improvements**: these change how we *find* his settings,
  not what he *is*.

## 4. UNACCEPTABLE changes

| Never | Why | Example of when it nearly happened |
|---|---|---|
| **Invent biology** (new organs, air sacs, extra vocal folds, inflatable pouches) | not a bun | considered and rejected: air sacs (howler monkeys), velar vocal folds (koalas) |
| **Make him bigger** | he is small and round | the 2× bun mouth (dropped) |
| **Stack adaptations** that each buy a little | parsimony | puffed cheeks, wider jaw/lips, a mobile larynx with 2.5 cm travel: improved vowels on paper, barely changed the clip (dropped) |
| **Stamp an effect on** instead of making it physically | it isn't his mouth doing it | the hard-coded hum cliff (`_cliff_db`, `HUM` in bun_rebuild.py): the hum must come from F1 tuning plus gentle folds |
| **Put anything from the clip or gold into the output** (copied pitch, loudness, aperiodicity, spectra, source estimates) | then it's a recording, not him | the mouth-only rebuild still borrows pitch, loudness, brightness and breath per frame: to be removed |
| **Fit each frame freely** | that traces the clip through a mouth; it isn't a mouth saying it | ~4,000 free pose numbers in bun_rebuild.py: replace with shared targets plus dynamics |
| **Impossible articulation** (a vowel with lips shut, m without the nose) | physically dishonest | the first fit "cheated" exactly like this (fixed with the NEEDS constraints) |
| **Arbitrary or random variation** | every variation needs a why | early rejected outputs: "formulaic", "inserted pitch", "arbitrary changes" |
| **Tune to pass a checker** | checkers support the ear; they don't replace it | — |
| **Generate new material with external voice tools** (ElevenLabs, TTS voices, voice conversion) | "nonsense with no guarantee it sounds like him" | ElevenLabs (rejected for new material), Kokoro voices ("synthetic"), Seed-VC ("not close") |
| **Warp formants to fake a new sound** | warping can't create an articulation he never made | derive_vowel warps: "mama" → "rarra", strained/choking |
| **Hide a departure** | everything shown, everything logged | each drawing carries a 1 cm bar; the ledger in §6 |
| **Change the gold standard** | it's the judge | — |

## 5. Grey zone: ask Da Boss first
- Any anatomy change beyond ~±15%, or any new adaptation.
- How far the larynx sits lower (currently ~3.8 cm in a small bun). Da Boss
  approved "a little lower" as the concept; the amount is fitted. If a fit
  wants much more, ask.
- Anything that changes his pitch levels, his idiolect or how CAPS behaves.
- Accepting a result that scores better but that he hasn't heard.
- Removing a recorded verdict or pinned item.

## 6. Ledgers (keep current)

### Adaptations (departures from a normal small bun): **1**
| # | Adaptation | Amount | Abilities it serves | Approved |
|---|---|---|---|---|
| 1 | Larynx lower in the neck | ~3.8 cm (`neck_mm` 50 at size 0.75) | his resonances; unplugs the larynx from the nose (oral speech); vowel range | concept yes ("a little lower"); amount fitted |

### Natural variation in use (within ~±15%)
| Part | Value | Why |
|---|---|---|
| Split upper lip leak | ~0.03–0.04 cm² (to be fitted) | weak, voiced "p" (PRINCE_PHYSICS.md §7) |
| Fold tension | relaxed (~4–13 kPa) | his pitch 215–390 Hz (§5) |
| Fold closure | clean, relaxed (Oq ~0.6, Ta ~0) | his band balance and hum (step 1c); "gentle" + breath was rejected: airy, jittery |
| Breath | none in his tone (his bright band is harmonic) | step 1c; breath sounded airy/shrill |
| Pitch micro-movement | slow smooth drift ~6 cents (<6 Hz), tiny cycle variation | his measured wobble; random jitter sounded rough |
| Laryngeal cavity | ~5 mm cavity, ~3 mm inlet at 15% of the throat | his "ee" F4 (~5 kHz); every larynx has one (Takemoto et al.) |
| Larynx depth | "ee" asks ~1.5 cm (step 1c; 2.2 in 1b) | to be settled across all his sounds |

### Rejected (do not reintroduce without new evidence)
2× size; puffed cheeks; wider jaw drop; wider lip opening; extra lip
protrusion; 2.5 cm larynx travel; stamped hum; free per-frame poses; formant
warping for new sounds; the intents prosody planner (v10–v16); ElevenLabs,
Kokoro and Seed-VC as sources; breath to brighten his tone (1b: airy, shrill); random cycle-to-cycle jitter (rough).

## 7. Before every change: checklist
1. **Which property of him does it serve?** Name it (PRINCE_IDENTITY.md /
   PRINCE_PHYSICS.md).
2. **What is the physical mechanism?** If none, it's a fudge: stop.
3. **Is it biology he has?** Variation within range = OK. New biology = no.
   Beyond range = ask.
4. **Is it the most parsimonious option?** Could an existing setting explain it?
5. **Does it borrow anything from the clip or gold into the output?** If yes: no.
6. **Measure it:** gold scores (LSD, timbre shape, flux/p95, hum H2/H3/H4), then
   `scripts/check_voice.py` (his ranges and negative space), then
   `scripts/check_phoneme.py` (identity, class, transitions).
7. **Run the held-out test** where relevant: fit without one instance (e.g. the
   last "tee") and check that the mouth says it from its shared targets.
8. **Listen for the known failure signatures** (§8).
9. **Log it** (ledger, docs), archive the audio in `reference/archive/`, commit
   and push, and send it to Da Boss with numbers *and* audio.

## 8. Failure signatures (what he is NOT), with measurements
From `analysis/negative_space.csv` and Da Boss's verdicts:
- **"A child":** hum overdone, H1–A3 above ~38.5 (candidates A, A2, C).
- **Chipmunk:** pitch and resonances up together; tract too short.
- **Ordinary or synthetic:** too little hum (H1–A3 below ~31), jitter 1.3–3%.
- **Robotic:** too steady (HNR <500 ≈ 50, shimmer ≈ 0.26), frozen spectra.
- **Choppy:** jumps at joins (flux p95 high); **slurred:** too melted (low).
- **Breathy:** HNR <500 ≈ 22.
- **"Rarra":** an F3 drop (r-colour) where there shouldn't be one.
- **"Choking"/strained:** an instant F1 jump with a purity collapse at a release.
- **"Nana" for "mama":** the lip cue missing (the edge says tongue tip).
- **Inserted pitch, formulaic, volume peaks or fades mid-utterance**: prosody
  added without a reason.

## 9. Process
- Measure, don't assume. Report honestly: what failed, what's open, what was
  skipped.
- Keep `out/` as scratch; copy anything with a verdict to `reference/archive/`
  (the container is temporary). Commit and push.
- Keep the docs true: BUN_MOUTH.md (anatomy and adaptations), PRINCE_PHYSICS.md
  (mechanisms), PRINCE_IDENTITY.md (what he is), this file (rules and ledgers).
