# Prince — Bona Fide Voice Specification

Status: **draft** — open questions at the bottom.

This describes Prince's settled, natural voice: Prince at full ease with his own
little instrument. Intermediate/learning stages are out of scope for now.

## Guiding principles

1. **He is not a magical, gifted or genius rabbit.** He has the biology of any
   other rabbit. He is extremely curious and dedicated and tries his best.
2. **His mind is uncapped.** Nothing in the voice limits what he can learn,
   understand or express. The body shapes the *sound*, never the *mind*.
3. **He is cute because of what he is, not because he performs it.**
   Test for every line and setting: *does this sound like him being himself,
   or like him being presented?* If the latter, it's out.
4. **Cute words, sincere voice.** The idiolect already lives in the text. The
   voice must not add cuteness on top (no babyish pitch, no sing-song). He
   means everything literally and at face value.
5. **Balance.** Not grave or clinical, not kawaii. A little round guy trying
   his best.

## Instrument (timbre)

| Property | Target |
|---|---|
| Size | Strongly raised formants — clearly a very small body. Main "smallness" cue. |
| Pitch | Moderately high, noticeably lower than the formants suggest. This mismatch keeps him out of "child" territory. |
| Breath | Lightly breathy in normal/soft speech. Excited sounds are **firm and fully voiced**. |
| Nasality | Constant, gentle nasal resonance (obligate nose-breather). Baseline colour, not a cold. |
| Placement | Forward. Resonance sits far forward and high in the mouth. |

## Pronunciation

- **Text is the phonology.** Say exactly what is written (`dis`, `dat`, `dere`,
  `den`, `da`, `fank`, `peets`, `sleeb`, `nanner`, `oogly`, `smol`, `youse`…).
  No additional pronunciation rules beyond those listed here.
- **S and Z → soft alveolo-palatal [ɕ] / [ʑ].** Tongue tip down behind the
  lower teeth, tongue body raised forward toward the palate. Between "s" and
  "sh", closer to "sh" but not a full "sh". Short and quiet.
  Reference sounds: Mandarin *x* (xièxie), Polish *ś*.
- **The vowel carries the word.** Vowels before S/Z lengthen slightly and are
  pulled forward. "Boss" ≈ [bɵːɕ] — almost "Bosh", weight on the O.
- Applies everywhere, including over-inflected endings:
  `thinkings` → soft trailing [ɕ], `maybees` → soft trailing [ʑ].
- **"I's"** is said like "eyes" — so it ends in the soft [ʑ]: [aɪʑ].
- Over-inflected forms (`thinkings`, `dids`, `happeneds`) are pronounced fully
  and sincerely, as real attempts at the word.

## Signature sounds

These get individually tuned renderings rather than plain TTS.

| Sound | Notes |
|---|---|
| **OH!!** | His most identifying sound. Discovery, realization, recognition, delight. Must be right. |
| **Bnuy!!** | Excited, near-onomatopoeic. [bnuːi]: B and N fused (no vowel between), long full "oo" as in *moon*, quick "ee". Firm and voiced. Not "buh-nuy", not "bn-uh-y". |
| oh. / ohhhh... | Soft realization / contentment. Length follows letters. |
| awwwwww... | Disappointment or sympathy. Drawn out, descending. |
| hmmmmm... | Thinking hum (Bun Brain Case™ working). |
| mhm | Quiet assent. |
| nooo... / zzzz | Sleepy. |

## Prosody — the text is the markup

| In the text | Delivery |
|---|---|
| lowercase | Normal soft, casual voice |
| `!!` | Excited, brighter, more energy |
| ALL CAPS | Very excited. Pent-up energy from a little round body. Noticeable volume increase, higher pitch, faster, firm and fully voiced — but never screaming or adult-yelling. A small body's "loud". |
| `??` | Eager, rising question |
| `?` | Gentle, curious question |
| `...` | Real pause — Bun Brain Case™ working |
| stretched vowels | Held sounds, length scaled by letter count |

Wide emotional range on one small instrument: near-whisper (sleepy,
comforting, scared) through full delighted "OH!!". Never sing-song, never eager
to please. Deadpan-sincere lines ("is round." / "wasn't secrets." / "yes.")
are delivered completely straight.

## Layers

1. **Voice** — his speech and vocal sounds.
2. **Nose** — sniffs, interleaved naturally with speech.
3. **Foley** — peets, binkies, zoom, nibble, scritch. Separate layer; never
   sounds like he is *saying* them.

Narration is never spoken.

## Must never sound like

- A human child, or a pitched-up adult (chipmunk effect)
- A cartoon or creature voice (squeaky, growly, gravelly)
- A performer: sing-song, eager-to-please, "aww"-bait
- Hissy: no sharp S anywhere

## Open questions

1. **"Bun Brain Case™"** — is the ™ spoken?
2. **Forward placement** — only on S words, or his general mouth posture for
   all speech?
3. Recordings of Prince's real sniffs/huffs available?
4. Runtime: Python locally? GPU? Existing TTS engine to integrate with?
