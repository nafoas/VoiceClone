# Building Prince's voice: what changes are allowed

> **RULE ZERO (Da Boss): "from now on, if you deviate from my idea, I need you to
> actually tell me that first."** When Da Boss gives an approach and it fails or
> I want to do something else, STOP and say so plainly, *before* doing it: what
> his idea was, what went wrong, what I want to do instead, and ask. Never slide
> into a substitute (e.g. a modeled buzz in place of his recovered voice) and
> mention it in passing afterwards.

> **Priority order (Da Boss, revised).** "A rabbit can't talk... I was using Bun
> Realism as a stand-in for 'This needs to be objective and replicatable, using
> only changes to his mouth, no post processing or anything that couldn't be
> replicated with just the mouth model itself'. What matters here is that all
> our changes contribute to a mouth where saying 'nannarmunis... peet teet tee'
> isn't a fluke of editing, it'll be a little bnuy mouth that actually sounds
> like that." Biology roots his abilities; it never blocks them.
>
> 1. **Sounds like him.** The gold standard is the judge; Da Boss's ear is final.
> 2. **Made entirely by one mouth model.** His voice box + his tube + his head:
>    every sound comes from moving that one mouth. No editing, no
>    post-processing, no effects, nothing from the clip in the output.
>    Reproducible: the same mouth and the same movements give the same sound.
> 3. **Physically valid.** The model has to work as physics: sound leaves
>    through an open mouth (no sealed-mouth leaks), no exploits of numerical
>    limits. Departures in shape and size are allowed; impossible physics is not.
> 4. **Rooted in bun biology, preferably.** Start from a small bun with his one
>    adaptation. Where a sound he makes needs his mouth to go beyond a normal
>    rabbit's, it may, and the departure is **logged with the ability it
>    serves**. Prefer the explanation that keeps him "just a little guy", but
>    never refuse a sound he really makes because a normal rabbit couldn't.
> 2b. **His one neutral voice is the source** (Da Boss): instead of a drawn buzz,
>    the sound his own voice box made, recovered from the clip by undoing the
>    mouth model, ONE voice shared by every sound, enters the mouth as its input.
>    Nothing else from the clip enters the output. Re-pitching or lengthening it is
>    done to the source only, before the mouth. Honesty checks: one shared voice
>    (never a per-sound source), and each sound rebuilt with voice cycles taken
>    from OTHER sounds.
> 5. **One anatomy, many movements.** His anatomy (sizes, cavities) is shared
>    by every sound; only articulation (how the mouth moves) differs per sound.
>
> Where older sections below are stricter about anatomy (e.g. the ±15% natural
> variation as a hard limit), this priority order wins: ±15% is now a
> preference with a cost, not a wall.

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
| Breath + roughness | **Da Boss's pick, step 1e ladder step 3**: breath 0.0375, cycle jitter 0.2%, shimmer 1.5% | none = "just a tone" (1c); 1b level = breathy/jittery |
| Pitch micro-movement | slow smooth drift ~6 cents (<6 Hz) | his measured wobble |
| Laryngeal cavity | ~5 mm cavity, ~3 mm inlet at 15% of the throat | his "ee" F4 (~5 kHz); every larynx has one (Takemoto et al.) |
| Larynx depth | "ee" asks ~1.6–2.5 cm (step 3h fits) | to be settled across all his sounds |
| Head | radius 2.6 cm (a small round bun head): sound radiates from a small sphere | three "ee" fits chose 2.5–2.65 cm independently |
| Laryngeal cavity | ~6.8 mm long, about throat width, inlet ~3 mm (narrow ring); its shape changes a little per utterance (±12–17%) as a gesture | four "ee" fits chose it independently; the epilarynx is an articulator (Esling's Laryngeal Articulator Model; MRI: varies with vowel and pitch) |

### Nose: turbinate surface (normal rabbit anatomy, made physical)
His nasal hum is extremely pure (tones above the 1st are 40-75 dB down on "n"). The nose
model damped only at the nostril, equally at all frequencies, so it let 10-24 dB too much
through at 1-5 kHz. A rabbit's nasal passage is filled with turbinate scrolls: many narrow
channels (fractions of a mm), roughly 10-15x the wall surface of a round tube of the same
cross-section. Wall losses grow with surface and with frequency. The nasal passage now
carries those losses (fitted factor, bounded 1-25x a smooth tube). This is NOT the rejected
"tissue damping" (that was the mouth walls, for the ee); it is the nose, on new evidence:
x16 alone took the nasal tone errors from 10.7 to 8.1 dB ("n") and 10.4 to 7.8 dB ("m").

### Walls radiate (physics the model already implied)
The model's walls yield (Sondhi & Schroeter's wall term, the ~200 Hz wall resonance), but the
sound those moving walls give off was never added to the output. With the mouth shut ("m",
"n"), much of a hum leaves through the cheeks and throat. Wall-radiated sound is naturally
hum-heavy (a ~6 dB/octave tilt vs an opening), which is exactly the extra tilt his nasals
needed (fitted voice tilt -4.5 to -6.5 dB/oct on "m"/"n", unrelated to loudness, r = -0.03).
Now: output = lips + nostrils + walls. Not a new part; the motion was already modelled.
Effect before refitting: overall 7.59 -> 7.03 dB; "m" 10.6 -> 8.2; "n" 7.7 -> 6.7.
Tried and dropped: turbinate slits (Stinson slit-pore channels) changed almost nothing.

### The vocal-cord gap is an opening (physics the model left out)
Da Boss heard listen2c as "a little tinny". Measured: a sharp ring near 6 kHz (bandwidth
~200 Hz) in nearly every sound (n, ɹ, m, ũ, iː), living in the short laryngeal cavity just
above the cords (its pressure peaks at the cords). The model treated the cords as a closed
wall, but they are open for part of every buzz, and that gap soaks up exactly this ring
(Flanagan's glottal impedance; Fant's glottal damping). Now the gap loads the tube with
its resistance and air mass, both from one fitted setting (its mean opening) plus physics:
air speed from a soft-voice lung pressure (0.8 kPa, later set by effort, PLAN 5b) and a
small-bun fold depth (1.5 mm). A zero opening is the old model exactly. Before refitting:
whole phrase 6.77 -> 6.52 dB at 0.002 cm2; the 6 kHz ring is gone.

### Losses grow as his tubes narrow (physics the model left out)
Air rubbing on the walls (viscous + heat boundary layers) costs energy per cm in proportion
to wall perimeter over area, i.e. 1/radius. The tube model used Sondhi & Schroeter's single
constant, set for human-sized tubes (~3 cm2). His sections are 0.01-2 cm2, so his losses
are several times larger, most in narrow gaps. Now each section's loss is scaled by
sqrt(3 cm2 / its area). No new setting. Fast capacity tests (everything free): his four
ee's 4.51 -> 4.28; all 12 steady sounds 5.33 -> 5.00 dB tone error; ee upper tones
(4.5-7 kHz) no longer starved; head radius returns to a small bun's 2.6 cm.

### Three anatomical controls per sound (biology he has; Da Boss: "rooted in biology")
A test let each sound bend its tube shape freely; the bends it chose fell into three places,
each a real muscle system. They are now controls of his mouth, set per sound like the jaw and
tongue, moving smoothly between sounds, with a small cost for using them:
| Control | Where | Mechanism | Used for |
|---|---|---|---|
| throat width | lower/mid throat (12-45% of the tube) | pharyngeal constrictors narrow it; the hyoid lowering widens it (rabbits move the hyoid a lot when chewing and swallowing) | "ã" (tongue root back, x0.5), nasals (wider) |
| soft palate into the passage | behind the tongue (45-62%) | palatoglossus draws the soft palate down, narrowing the passage between mouth and throat; a rabbit's long soft palate rests low (the epiglottis tucks over it) | "m", "ũ" (x0.4-0.5) |
| lip spread | lips (88-100%) | levator labii, zygomaticus draw the lips wide | "ee", "i" (x1.4-1.8) |
Steady-sound fit (everything free): 4.32 -> 4.15 dB. Free per-sound shape corrections (not
adopted) reached about 0.3 dB further; the rest of their gain has no named mechanism yet.
Sources: rabbit epiglottis over the soft palate (obligate nose breathing); palatoglossus
narrows the oropharyngeal isthmus; English /r/ uses throat, palate and lip constrictions (MRI).
Also: the "i" ending "munis" (unstressed) now has its own position, separate from the stressed
"ee" of "peet teet tee": it wants a much lower first resonance (his hum), they do not.

### Per-sound smooth shape terms (Da Boss approved: "Both")
On top of the bun controls and the three anatomical controls, each sound may bend its tube with
6 slow smooth terms (log-area DCT along the tube), stored once per sound and gliding between
sounds like every other control. Not post-processing: it is the shape of his mouth for that
sound. They cost more than named controls (no muscle named yet), so the fit uses them only where
they clearly help. To do: find the pattern behind them (which muscles) so they carry over to
sounds not in the clip. Steady-sound fit: 4.15 -> 4.04 dB. His measured mouth response (from
the voice recovery, every frequency, 1/3-octave smooth) is an extra guide in the fit (weight 0.3).

### Size 0.80 of the reference rabbit (natural variation; was 0.75)
Overnight diagnostic: the age model hears his own clip as 4 years old when every frequency is shifted
up 11%, and as 28 when shifted down 9%; the model's pitch is his, so its younger sound came from
resonances a few percent too high (its first resonance was measured too high in ee, n, m). Scaling the
whole mouth +6.7% (0.75 -> 0.80) lowers them together, with no new part: apparent age 8 -> 13 (his 13),
naturalness up. A deeper larynx (3.0 cm) also fixed age but added a narrow pipe that rang at 7 kHz
(tinny, less natural), so the larynx stays at ~2.4 cm. He is still a small bun (0.80 of the reference).

### Consonants are gestures of their own articulator (2026-11-20; Da Boss: "something wrong in how you make and voice consonants")
Every sound used to be one whole fitted shape, and the fit shut "m" with the tongue and sealed the tip in
"ɹ" (the gestures of "n"/"l"), because a steady hum barely shows where a mouth is shut. Now (`GEST=1`):
| Sound | Its own gesture | The rest of the mouth |
|---|---|---|
| m, p | lips shut (+ jaw); m: soft palate open | carried by the neighbouring sounds (coarticulation) |
| n, t | tongue tip sealed at the ridge, tongue front behind it (+ jaw); n: soft palate open | same |
| vowels, ɹ | none: open sounds may not touch anywhere (>= 0.008 cm²) | their own position |
| phrase start | his REST posture: lips shut, soft palate open (a rabbit breathes through its nose), tongue filling the mouth (fitted) | the first sound moves out of it |
Not new biology: the same controls, used by the part of the mouth that really makes each sound. Stops are
closure-and-release movements on the moving mouth (the seal breaks at his burst); their noises go through
the mouth as it moves; the breath stops where the voice starts; a sealed mouth's voice falls to half and
then fades (fitted to his closures, 20 ms). Details and numbers: docs/CONSONANT_FINDINGS.md.

### Rejected (do not reintroduce without new evidence)
2× size; puffed cheeks; wider jaw drop; wider lip opening; extra lip
protrusion; 2.5 cm larynx travel; stamped hum; free per-frame poses; formant
warping for new sounds; the intents prosody planner (v10–v16); ElevenLabs,
Kokoro and Seed-VC as sources; breath to brighten his tone (1b: airy, shrill); random cycle-to-cycle jitter (rough); hand-added pitch scoops, falling tails and random drift ('phlegmatic', 'dying'); random variation layered on a crude renderer ('stuttery', 'computery'); for his "ee" tones: a nose side branch, cheek pockets, and tissue damping (tested, no help).

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

## 9. Lesson: don't over-correct
When Da Boss names a problem ("breathy", "jittery"), turn it DOWN, don't
remove it. 1c removed breath and roughness entirely and became "just a tone".
Offer a ladder of amounts and let his ear pick (that's how step 3 was found).

## 10. Process
- Measure, don't assume. Report honestly: what failed, what's open, what was
  skipped.
- Keep `out/` as scratch; copy anything with a verdict to `reference/archive/`
  (the container is temporary). Commit and push.
- Keep the docs true: BUN_MOUTH.md (anatomy and adaptations), PRINCE_PHYSICS.md
  (mechanisms), PRINCE_IDENTITY.md (what he is), this file (rules and ledgers).
