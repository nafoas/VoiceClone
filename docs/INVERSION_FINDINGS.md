# What his mouth is doing, read from the clip (acoustic-to-articulatory inversion)

Da Boss's idea: instead of fitting the mouth to the sound and letting the fit bend it however it
likes, first read the mouth from the sound with independent, objective tools, then make Step 3
match what they agree on.

## Methods (independent of each other and of our mouth model)
1. **SPARC** (Cho et al. 2024, Berkeley; open source, MIT). A model trained on real speakers whose
   tongue, lips and jaw were tracked with sensors (EMA). From audio it gives 12 articulator
   positions every 20 ms: tongue back, tongue body, tongue tip, jaw, upper and lower lip (forward /
   up). Human-trained, so it reads him in human terms; trustworthy for *which articulator does what,
   and when*. Resynthesis check: `reference/archive/sparc_resynth_his_movements.wav`; movements saved in `models/sparc_articulation.npz` (the tool's own voice saying his
   movements).
2. **Tube shape from the sound** (Wakita's method: LPC reflection coefficients -> relative widths
   along a lossless tube). Valid for oral sounds only (no nose branch); least reliable near the
   vocal folds.
3. **Resonance spacing -> tube length** (formant dispersion).

## What they agree on
| Sound | SPARC (movements) | Tube shape from sound | Model was doing |
|---|---|---|---|
| "ee" | tongue body high and front | wide throat, narrow front, **narrow lips** | lips spread wide (x2.7) and fully rounded at once |
| "ã" | jaw well down, tongue low, lips wide open | narrow throat, wide front | similar; lips wider than his |
| "ɐ˞" | lips rounded and pulled back | narrow lips | lips spread x2 |
| "ɹ" | **lips nearly closed** (closing early for the "m") | narrow lips | lips open |
| "m", "p" | lips shut | (nasal: not readable) | lips shut |
| "ũ" | tongue back, lips rounded | (nasal) | ok |
| "n" (0.30, 0.73) | tongue tip up | (nasal) | ok |
| "n" (0.05) | tongue tip barely up | (nasal) | tip sealed |
| throat | | narrower than the model's in most oral sounds | shared anatomy widens it ~1.9x |

## Corrections to what I said before
- **Tube length.** I claimed his resonances need a 12.5-15 cm tube. That assumed a single plain tube.
  Side spaces (laryngeal cavity, nose, throat pockets) add resonances of their own, and his close
  pairs (e.g. 1930/2270 Hz in "ã", 3070/3550 in "ee") look like exactly that. Read straight from the
  sound at 8.9 cm, his vowels come out as sensible shapes; at 14.5 cm the extra length is empty.
  **The 9 cm bun mouth can account for his sound. No larynx change is needed.**

## What this means for Step 3
The fit has been free to bend the mouth anywhere, and it bent the lips the wrong way (spread where he
narrows or rounds) and widened the throat. That is the Frankenstein quality, and likely much of the
vowel colouring ("ee" -> "eh", "r"/"m" -> "l"). Next, with Da Boss's go-ahead:
1. Make the lips follow what both tools agree on: narrow for "ee", rounded for "ɐ˞", nearly closed
   through "ɹ" into "m". No spreading and rounding at once.
2. Keep the throat from being widened as a compensation.
3. Use SPARC's timing (when each closure and release happens) for the movement between sounds.
4. Refit only within those limits, and check each vowel by ear before anything else.
