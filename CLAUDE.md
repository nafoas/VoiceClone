# Prince's voice (VoiceClone)

Building the voice of Prince ("Little Prince"), Da Boss's small round white
rabbit, from a physical model of his own little mouth and voice box.

**Before changing anything about how he sounds, read `docs/BUILD_RULES.md`**
(acceptable vs unacceptable changes, the ledgers, the checklist), then:
- `VOICE_SPEC.md`: who he is and how he speaks (idiolect, principles)
- `docs/PRINCE_IDENTITY.md`: what makes him him (measured)
- `docs/PRINCE_PHYSICS.md`: which physical mechanism makes each property
- `docs/BUN_MOUTH.md`: his mouth model, anatomy and his one adaptation
- `reference/gold/`: the gold standard (the judge; never an ingredient)
- `reference/archive/README.md`: saved clips and Da Boss's verdicts

Environment: Python 3.12 venv in `.venv` (`uv`); VocalTractLab via
`vocaltractlab_cython` (CPU). `out/` is scratch and git-ignored.
