# What makes Prince, Prince

The goal: make sounds he never said that still come out **in his voice**.
A sound is "in his voice" when it matches him on every layer below. So the
table lists each layer, what he does (measured from the reference clip), what
an ordinary voice does, how far the trait reaches (every sound, a class of
sounds, or one sound), and how a new phoneme would inherit it.

Measurements: `analysis/identity_instances.csv` (every recorded sound),
`analysis/REFERENCE_ANALYSIS.md`, `analysis/IPA_TRANSCRIPTION.md`, and the
iteration work (gold rebuild). Graphs: `analysis/identity_*.png`.

Scope key: **ALL** = every voiced sound; **CLASS** = depends on a sound class
or on mouth openness; **ONE** = specific to one sound.

## 1. Source: the hum (his throat)

| Trait | Prince | Ordinary voice | Scope | How a new phoneme inherits it |
|---|---|---|---|---|
| Harmonic shape | H1 dominant, a cliff after H2: overall H2 −12, H3 −32, H4 −46 dB | gentle slope: −7, −11, −16 | ALL (but see 2.3) | same source for every voiced sound; only the mouth changes |
| Tone purity (HNR) | 25–36 dB on nasals/vowels | 15–20 dB | ALL voiced | keep breath/noise low; his recordings already have it |
| Breathiness | low; tails turn breathy only as they die | moderate | ALL | none added, except in fades |
| Steadiness | pitch wobble ≈0.1 st; loudness flutter ≈0.58 dB inside a hum | more jitter/shimmer | ALL | carry his recorded micro-movement, not generated wobble |
| Voicing | 87% of the phrase voiced; hums straight through n, m, r | ~55% | ALL | voiced unless the sound is truly voiceless |

## 2. Filter: his mouth

| Trait | Prince | Ordinary voice | Scope | How a new phoneme inherits it |
|---|---|---|---|---|
| Size / forwardness | "ee": F2 3170–3320 (+37%), F3 3550–4120; F1 *lower* (360–410) | F1 437, F2 2761 | ALL vowels | place the new vowel in **his** vowel space (graph 2), not ours |
| Vowel space | closed vowels close and front even more; open vowels open much wider (his "a" F1 ≈1170 vs English 669) | — | CLASS | map English vowel → his space (5 anchors so far; see open questions) |
| **Hum tuning** | the hum is deepest when F1 sits on his pitch (F1/f0 ≈ 1: H3 −45…−52); medium at 1.4–2× (−20…−30); light for open vowels at 3.7–5.4× (−13…−17) | — | CLASS (openness) | closed sounds: keep F1 near his pitch → deep hum. Open sounds: lighter hum is correct. **Graph 1.** |
| Nasality | a constant hummy nasal colour; ã and the hummy u are nasalised | little | ALL (degree varies) | keep his nasal murmur colour |
| The hummy u | ũ: F1 384, F2 1337: nearly closed, rounded, humming | /ʌ/ F1 753 | ONE (+ tendency) | the route for "simplified" vowels (he only simplifies) |

## 3. Articulation: how he makes consonants

| Trait | Prince | Ordinary voice | Scope | How a new phoneme inherits it |
|---|---|---|---|---|
| Lips weak | p: soft, almost no puff (noise 1%), mostly voiced | /p/ aspirated | CLASS: lip sounds (p, b, m, f, v, w) | lip sounds soft and voiced; lip release lowers F1/F2 only (an F3 drop is heard as "r") |
| Tongue tip strong | tʰ: crisp 40–45 ms burst, 80% noise | normal | CLASS: tongue-tip sounds (t, d, n, s, l) | tongue-tip stops crisp and airy |
| Soft S | ɕ: ~4.4 kHz (vs 9–10), ~16 dB under the vowel, hum continues under it, ends in a voiced puff | sharp ~9 kHz | CLASS: sibilants (s, z, sh, zh, ch, j) | all sibilants soft, partly voiced, from his ɕ |
| Final stops | never close: the vowel drops ~20 dB in 20 ms, then a humming tail of 80–150 ms | released stop | CLASS: final stops | replace with his tail |
| Full vowels | unstressed -er → [ɐ˞], -eys → [iː]; no schwa | reduced to schwa | ALL unstressed | no reduction |
| Coarticulation | a sound's edges carry its neighbours ("n" glide: F2 falling from ~2360) | same | ALL | edges come from the real neighbour (recorded, or rebuilt for its place: lips/tip/palate) |
| Joins | glide about 2.6 dB of spectral change at a join; loudness steady | — | ALL | joins must melt this much: not more (choppy), not less (slurred) |

## 4. Breath and loudness

| Trait | Prince | Scope | How a new phoneme inherits it |
|---|---|---|---|
| One breath, one hum | the loudness range across a phrase ≈9 dB, changing slowly | ALL | the phrase's breath sets loudness, not the individual sound |
| Nasals vs vowels | nasals about as loud as vowels (n 72.6, ã 69.6 dB); before a stressed vowel the m is ~4 dB under it | CLASS | nasals near-vowel loudness; dip only at a stressed release |
| Phrase start | swells in over ~40 ms (−40 → −6 dB) | ALL | — |
| Phrase end | the vowel cuts ~20 dB in 20 ms, then a long humming tail that turns to breath | ALL | — |

## 5. Timing

| Trait | Prince | Scope |
|---|---|---|
| Pace | ~270 ms per syllable in a calm phrase | ALL |
| Durations | phrase-initial nasal 105 ms; medial n 60–75; m 90; ɹ 50; stressed ã 145, ũ 120; unstressed ɐ˞ 95; final iː 200–210 | CLASS |
| Closures | silence before t: 15–40 ms | CLASS (stops) |

## 6. Pitch and prosody

| Trait | Prince | Scope |
|---|---|---|
| Levels | calm ≈215 Hz, raised ≈265, excited 330–390 | ALL |
| Plateaus | flat per syllable; changes happen inside consonants | ALL |
| Onset | a hummed fall of ~8 st into a nasal start, over ~150 ms | CLASS (nasal starts) |
| Main stress | step up ~3.6 st on the stressed word ("nannar → MUnis"), held after | ALL |
| Out of a burst | the vowel rises in from below (p: 347 → 388 in 30 ms) | CLASS (after stops) |
| Excited series | each word a step lower (390 → 350 → 330) | — |

## 7. Idiolect (his words, from Da Boss's spec)
th → d, soft S everywhere, "I's" = "eyes", over-inflection (thinkings, dids),
he only simplifies (vowels shorter/higher/further back, never harder), stressed
key vowels keep their identity ("Boss" keeps its O), cute words with a sincere
voice. See VOICE_SPEC.md.

## Coverage: which sounds exist in his voice

| Status | Sounds |
|---|---|
| Recorded | n, m, ɹ, ã ("a" of nannar), ɐ˞, ũ, iː, ɕ, p, tʰ |
| Derived and approved | ɑ ("ah" of mama: from ã, F2 → 1700 Hz, version F) |
| Missing vowels | ɪ, ɛ, ɔ/o, ʊ/u (plain), ʌ, e, aɪ, aʊ, ɔɪ, oʊ, eɪ, ɜ |
| Missing consonants | b, d, k, ɡ, f, v, θ/ð (→ d/f in his idiolect), s/z (→ his ɕ), ʃ/ʒ, h, l, j, w, ŋ, tʃ/dʒ |

## What this suggests for making new phonemes

1. **Source is shared, mouth is per-sound.** His hum is a property of his
   source *plus* how his mouth tunes F1 to his pitch. A new voiced sound =
   his recorded source and movement, with only the mouth shape moved to the new
   sound's place in **his** vowel/consonant space. (That is what worked for
   "ah": his "a", F2 moved.)
2. **Nearest recorded relative.** Every missing sound has a closest relative he
   did record (b ← p but voiced; d ← tʰ but voiced, softer; s/z ← ɕ; l ← n
   without the nose; w ← ũ; ɪ ← iː opened a little; ɛ ← ã closed a little ...).
   Start from that relative and change only the traits that differ, checking
   each against this table.
3. **Each trait has a check.** Hum (harmonics vs F1/pitch), purity (HNR), joins
   (2.6 dB), loudness (nasal ≈ vowel), timing, pitch: a derived sound passes
   when it measures like his recorded sounds of the same class.

## Open questions (need Da Boss's ear)
- **His vowel space beyond 5 anchors.** Graph 2: with only five vowels, the
  predicted ones collapse (ɛ lands on his "a"; ʌ and ɔ hit the same openness).
  How open is his "eh"? Does "uh" become the hummy u, or stay "uh"?
- **Consonants with no relative at all** (k, g, h): what do they sound like in
  his mouth? (Lips weak, tip strong... is the back of his tongue strong?)
