# Roadmap: Prince's voice, from here (2026-11-23)

The single ordered plan, compiled from everything Da Boss and I agreed. It supersedes the step list in
`docs/PLAN.md` (kept for history). Work top to bottom; do not skip ahead. Each step ends with its
**done when** check and, where marked 🎧, a listening file for Da Boss before the next step starts.

---

## 0. Ground rules (every step, always)
- **RULE ZERO:** if I deviate from Da Boss's idea, I say so plainly *before* doing it, and ask.
- **His ear is the final judge.** Numbers support it; they never overrule it. When a measure disagrees
  with his verdicts, the measure is wrong.
- **The goal:** "simply the way he talks". The mouth, folds and habits are calibrated **once** (who he is);
  after that every new line comes straight out of the physics. **No post-processing, no per-utterance
  editing or fitting, nothing from the clip in the output.**
- **His speech is a pattern, not a recording:** similar (not robotically identical) pronunciations,
  consistent and context-dependent pitch and diction (calm / excited / out of breath), built into how he
  speaks. The clip teaches the pattern; matching it is not the goal.
- **One bun:** one anatomy shared by every sound; biology roots his abilities but never blocks a sound he
  really makes; departures are logged with the ability they serve (`docs/BUILD_RULES.md` ledgers).
- **No narrow patches / Frankensteining:** fix causes, not symptoms; don't let one setting do another's job.
- **Every step:** read BUILD_RULES first; log changes in the ledgers; archive every listening file with
  Da Boss's verdict (`reference/archive/README.md`); commit and push; report honestly (what got worse too).
- **Never trust an optimizer's shortcut:** every search so far found one (recogniser pleased while the
  "r" was wrecked; "m" shut by the tongue; "ɹ" sealed; leaky breathy folds). The cure is complete
  measures (Step 4) and physical limits (Step 5), not hand-tweaks.

## Where we are (start of this roadmap)
- **Active version: checkpoint 8** (`models/perc_state.json` = `perc_state_overnight8.json`), still heard as
  "Lannlillies / Pekeke", muffled, computery (harsh volume steps), no warm bun hum.
- **Rejected:** the gesture fix (`perc_state_cons1.json`: "still L, still K, more artificial"); the airflow
  consonant rebuild (rolled back: "Pekeke" -> "Lelele", "La La Lillies" worse); the first VocalTractLab
  "ee" (`vtl_ee_step1.wav`: "breathier, but not in a nice, warm, hummy, *him* way": the fold fit found a
  leaky-folds shortcut because breathiness was not measured).
- **Da Boss's diagnosis (accepted):** structural. A rigid tube with air blown through it; the mouth does not
  move like a bun's; no vibration; no room.
- **Built and kept:** the VocalTractLab bridge (`scripts/build/vtl_tube.py`: its full engine driven by OUR
  40-section bun tube); `models/bun.speaker` (bun-sized nose 6.05 cm, larynx pockets, windpipe, folds);
  `scripts/build/vtl_calib.py` (once-only calibration search); `scripts/listen/cons_check.py` (consonant
  checks vs his clip); the full VocalTractLab engine source (GPL; can be rebuilt here: cmake + g++).
- **Known facts to carry forward:**
  - His consonants as measured (`PRINCE_IDENTITY.md` §3, `PRINCE_PHYSICS.md` §6-8): **p** soft, ~1% noise,
    mostly voiced (split upper lip leaks ~0.03-0.04 cm²); **final t** ("pee-t", "tee-t") never closes:
    vowel drops ~20 dB in ~20 ms, then a hum tail; **tʰ** tip seals fully, crisp burst ~40-45 ms, ~80%
    noise, centre ~4.2-4.5 kHz; **ɕ** made ~2 cm behind the lips (blade up, tip down), ~4 kHz, ~16-21 dB
    under the vowels, hum underneath, ends in a voiced puff; **n, m, r**: he hums straight through.
  - His "ɹ", "ɐ˞", "m" (and "n") share a ~2.5 kHz resonance (r-colour; partly through the nose); a high
    third resonance reads as "l".
  - His clip has a **room**: after each sound stops it lingers ~100 ms (high frequencies too; ~100-600
    dB/s); the model goes to digital silence 5-15x faster. Part of the "hum in his closures" is room.
  - Human-sized vocal folds choke his tiny mouth (human airflow through a 0.01 cm² gap): his folds must be
    bun-sized.
  - VocalTractLab library note: reloading the speaker file on every try leaks memory: load once per worker.

## Starting over (Da Boss, 2026-11-23: "fold the current checkpoints into this new roadmap and then start over")
Nothing from the old fits carries forward as a starting point: the new mouth starts from bun biology and
his measurements. The old versions become the **reference set** (what every measure in Step 4 is checked
against, and the baseline to beat), with Da Boss's verdicts (`reference/archive/README.md`):

| Version (archive file) | What it was | Da Boss |
|---|---|---|
| listen3 | first whole phrase with provisional consonants | "really bad": La La Lillies, Kekeke; babyish, tinny, monotone, buzz, no warmth |
| listen3b | consonants + resonances | "straight up worse": muted, tinny, buzz, no hum, quieter |
| **listen3c = version 1** (F14) | the same, repaired | uncanny, muffled, robotic, monotone, low fidelity; "a lot closer than how bad it's been" |
| ab / abc | movements read from the clip | mixed / "the first is still the best" (version 1) |
| step1_ee_lips | version 1 + relaxed lips | still babyish, muffled, volume steps, no hum, La La Lillies / Kekeke |
| overnight_1..8 | overnight perceptual tuning | (heard as a whole in morning_compare) |
| **morning_compare: checkpoint 8** | best so far | "Better": still muffled, harsh volume steps, Lannlillies / Pekeke, a pitch and inflection unlike him |
| cons1_compare | consonants by their own articulators | "still isn't fixed": still L and K; increasingly artificial |
| rebuild1_compare | consonants rebuilt on airflow | "worse": Pekeke -> Lelele, La La Lillies much worse (rolled back) |
| vtl_ee_step1 | VocalTractLab + bun mouth "ee" | "breathier, but not in a nice, warm, hummy, him way" |

Known order (best first): checkpoint 8 > version 1 > the rest; rebuild1 < cons1 < checkpoint 8.
Any measure that does not reproduce these verdicts is not trusted.

## Decided (Da Boss, 2026-11-23)
- **Size and head radius:** "whatever makes him sound better": both are search variables (Step 5), kept or
  changed by the grid and his ear, not fixed by me.
- **Milestones:** "yes, but not so often it loses the benefit of it being autonomous": a few candidates at
  the END of each search stage only (Step 6.4 stages); fully autonomous in between.

---

## Step 1. Our own build of the VocalTractLab engine
1.1 Build the backend from the shipped source (`vocaltractlab_cython` sdist, `VocalTractLabBackend-dev`)
    into our own shared library; keep our changes as patches in the repo (`engine/`), never edit the
    installed package.
1.2 Point the bridge (`vtl_tube.py`) at our library (switchable: installed vs ours).
1.3 **Done when:** our unmodified build gives sample-identical (or within rounding) output to the installed
    library for the same tube and folds, and runs at least as fast.
    **DONE (2026-11-23):** `engine/VocalTractLabBackend` (vendored, GPL), `bash engine/build.sh` (-O3, ~30 s) ->
    `engine/build/libVocalTractLabApi_bun.so`; `vtl_tube.py` talks to either library through the C API
    (`VTL_LIB=ours|installed`, default ours). Bun "ee", "ã", "n", "m" and a moving closure/release:
    identical or within 3e-13 of peak; speed equal (0.98-1.02 s vs 1.02-1.05 s for the test set).

## Step 2. Folds that really vibrate (the source of his hum)
2.1 Switch from the prescribed-opening glottis to a **self-oscillating** model (two-mass or triangular
    glottis, both in the engine): fold masses and springs set vibrating by his breath, interacting with his
    mouth.
2.2 Size them for a bun (length, thickness, mass, stiffness, rest gap; pitch by tension), within
    rabbit-plausible ranges; his documented closure: clean and relaxed, steady (jitter ~0.3-0.5%, small
    shimmer), little breath.
2.3 Calibrate once on his "ee"s and his nasal hums, judged on his tones AND on breathiness (HNR), hum
    strength (H1-H2; F1 near his pitch in closed sounds), steadiness (jitter/shimmer). No leaky shortcut.
2.4 🎧 his "ee" and a hum ("nnn") vs his clip. **Done when:** Da Boss hears a warm, hummy him, not breathy.

## Step 3. A soft, vibrating, shaped mouth (engine physics, in our build)
3.1 **Tissue per region:** each region gets its own wall mass, damping and stiffness (the engine stores them
    per slice but uses one human value): lips, cheeks, gums, hard palate, soft palate, tongue, throat,
    larynx, nose. Rabbit-plausible ranges ("elasticity of his gums" is a real variable).
3.2 **Tissue radiates:** every vibrating region gives off sound (today only lips, nostrils and one throat
    patch do). With his mouth shut, much of a hum leaves through cheeks, throat and nose.
3.3 **Soft closures:** where lips or tongue press together, the flesh gives under air pressure (area
    depends on pressure): closures leak and puff like flesh, not valves. His split upper lip leaks.
3.4 **Side spaces** his mouth has: cheek pockets, the space under the tongue, the channels beside the tongue
    (the "l" mechanism, to be controlled, not avoided), the pockets beside the larynx, the nose's turbinate
    maze and sinuses (bun-sized).
3.5 Each mechanism: verify it does what physics says (a test sound), then 🎧 the hum, "n", "m" after 3.1-3.2
    and the closures after 3.3. **Done when:** each new part changes the sound the way physics predicts and
    Da Boss hears the hum/nasals move toward him.
3.6 Known remaining gap: a soft 3D tongue squashing against the roof cannot be expressed in a tube; list it,
    don't pretend. (For his ~1 cm wide mouth the tube itself is valid up to ~15 kHz.)

## Step 4. The measurable "him" (the scoring grid)
4.1 **Rows:** every sound instance in the clip on its own (n@0.05, ã, n@0.30, ɐ˞, ɹ, m, ũ, n@0.73, i, ɕ;
    p, iː, final-t tail, closure, tʰ release, iː, ..., tʰ, iː), every join between sounds, and the whole
    phrase.
4.2 **Columns (qualities):** his tones (spectral shape), resonances incl. the third (r-colour), hum (H1-H2,
    F1 vs pitch), breathiness (HNR), steadiness (jitter, shimmer), nasality, where a consonant is made
    (formant movement into/out of it, burst spectrum and centre, aspiration length, frication centre),
    voicing through it, loudness and its envelope. Whole phrase: flow, smoothness (no harsh volume steps,
    joins melt ~2.6 dB), warmth, timbre balance up to 12.8 kHz, size cues, and the **negative space**: not
    human/teen, not babyish, not robotic, not tinny, not muffled (BUILD_RULES §8 failure signatures).
4.3 **Tolerance bands from his own variation** (his three "ee"s, three "n"s...): inside the band = his.
4.4 **Room-aware comparison:** judge against his clip with its room accounted for (or a dry measure); his
    output stays dry until Step 9.
4.5 **Validate every measure against Da Boss's past verdicts** (archive: version 1/listen3c, the overnight
    checkpoints, morning compare, cons1, rebuild1, vtl_ee_step1...): a measure that ranks them differently
    from his ear is fixed or dropped. The phoneme recogniser and age/naturalness models are secondary at
    most (the recogniser disagreed with his ear on exactly these consonants).
4.6 **Done when:** Da Boss has reviewed the list of measures.

## Step 5. The variable inventory (everything that could differ in his mouth, folds and movement)
5.1 **Anatomy:** tube length and shape map, palate, teeth/incisor position, lips (incl. split-lip leak),
    tongue, larynx depth, nose (length, turbinates, port), head; each with a normal-bun value, a range and
    a cost for departing from normal.
5.2 **Tissue** per region (Step 3), **folds** (Step 2), **breath** (lung pressure).
5.3 **Articulation:** one shared target per sound; consonants made by their own articulator (m/p lips;
    n/t tip; ɕ blade; ɹ an open bunched r; final t a near-closure; tʰ tip seal + cords parting); open sounds
    may not touch; phrases start from his rest posture (lips shut, soft palate open, tongue up).
5.4 **Movement:** articulators with mass and muscle (target-approximation / task dynamics): speeds,
    stiffness, timing; transitions and coarticulation emerge instead of being interpolated.
5.5 **Limits:** biological ranges, design rules (no post-processing, one anatomy, no new biology without
    approval), what the engine can express vs listed gaps.
5.6 **Done when:** the inventory is written (with ranges and sources) and Da Boss has seen it.

## Step 6. The autonomous search (Da Boss's genetic-algorithm idea)
6.1 Evolutionary search (GA / CMA-ES) over the Step-5 variables, on our engine, judged by the Step-4 grid.
6.2 **Ranking that never trades one thing for another:** (1) how many grid cells are outside his bands,
    (2) the worst cell, (3) only then the average. **Ratchet:** a cell inside his band may not leave it.
6.3 **Conflicts are findings:** cells that cannot be satisfied together are reported as a missing mechanism
    (e.g. this week: purifying the first "n" via the nose erased the "r"), sent back to Step 3/5.
6.4 Staged: folds + vowels -> nasals -> r-sounds -> consonants -> whole phrase. Checkpoints saved to the repo;
    long runs in chunks (the container is reclaimed when idle).
6.5 **Guard against over-fitting** one 2.3 s clip: shared anatomy, biological priors, checks on sounds not
    used for tuning.
6.6 🎧 **Milestones (sparse):** only at the end of each stage in 6.4: a few of the best candidates; Da Boss
    picks; his picks steer the next stage. Autonomous in between.
6.7 **Done when:** every cell is inside his band (or its gap is explained) and Da Boss says it is him.

## Step 7. His way of talking (later, after the mouth and folds are right)
7.1 Pitch, loudness, timing and diction as HIS patterns, learned from the clip, not copied: his pitch levels
    (calm ~215 Hz, raised ~265, excited 330-390), plateaus with changes inside consonants, stress steps,
    final stops dissolving, breath and effort as loudness (old Step 5b), context (excited? out of breath?).
7.2 Similar, not robotically identical: natural variation in how he says the same sound.
7.3 Text -> his idiolect (`VOICE_SPEC.md`) -> his movements -> sound. **Done when:** a new sentence he never
    said sounds like him without any per-utterance work.

## Step 8. New things in his voice
Words and phrases outside the clip; check them against the Step-4 grid's "him" qualities and Da Boss's ear.

## Step 9. The room (later; Da Boss: "you could just make it so he constantly speaks in a room")
A fixed room as part of his world (his call whether and which); until then his output stays dry and the
room is only accounted for when comparing against his recording.

---

## Notes
- Size: his "ee" fit better at 0.75 than 0.80 in the old engine (tone error 4.5 vs 6.4 dB); head radius was
  3.9 cm in every fit vs 2.6 cm in the ledger. Both are now search variables (see Decided).
- Licence: the engine is GPL; fine for our use; if ever distributed, our engine changes are shared too.
