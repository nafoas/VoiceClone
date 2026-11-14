# Fresh Sayings: pinned

Status: **paused** (Da Boss, after v2). Resume from here.

Built with exactly the gold-standard technique (`scripts/new_sayings.py`): his
catalogue, the synthesizer at gold settings, units and durations written by
hand, a simple pitch line. No planner / breath support / hum boost / register
placement (those layers made things worse, v12-v16).

## Verdicts so far
| Saying | Verdict |
|---|---|
| munis... nannar | **perfect** |
| nanni | good |
| pee tee... meeni | pretty good; the m of "meeni" had the same m problem as "mama" |
| mama | was heard as "nana", then "rarra" (lip effect too broad, F3 lowered) |
| mama nanni | same problem as "mama" |

## Decisions
- **"mama" = version F** (`out/fresh/mama_variants2.wav`, third): his "ah"
  derived from the "a" of "nannar" with F2 moved 2160 -> **1700 Hz**
  (`derive_vowel(cat, "ɑ", "ã", [(1200,1200),(2160,1700),(3700,3600)])`),
  word-starting m 115 ms at -6 dB (his own m-to-stressed-vowel contrast: the
  vowel is ~4.2 dB louder), `crisp_release=True`, `recolor=0.6, lip_depth=0.28`.
- Lip edges lower F1/F2 only; lowering F3 is heard as "r".
- Remaining gap: his only m sits between r and a rounded u, so it is coloured
  on both sides. Not solvable by edge tricks alone; it is a "phoneme in his
  voice" problem (see docs/PRINCE_IDENTITY.md).
