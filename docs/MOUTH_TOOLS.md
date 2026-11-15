# Building Prince a mouth: tool survey

Goal: a model of his vocal tract that produces sounds he never said, by moving
a tongue, lips, jaw and velum, sized and fitted to him (12.2 cm tract; his
vowels, nasals and hum from docs/PRINCE_SPEC.md).

| Tool | What it is | Nasal | Consonants | Fits to a speaker | Here | Notes |
|---|---|---|---|---|---|---|
| **VocalTractLab** (Birkholz; `pip install vocaltractlab`) | 3D vocal tract from MRI, 1D aero-acoustic simulation, gestural scores, phoneme-to-speech | yes (nasal tubes + sinuses) | yes (MRI-derived consonant shapes) | anatomy adaptation not confirmed in docs | installs; import fails (GPU torchaudio pulled in; needs CPU build) | GPL-3.0, alpha. Most complete; its MRI shapes give articulation targets for every phoneme |
| **Praat articulatory synthesizer** (Boersma) | muscle-driven tube model; Speaker kinds Female/Male/Child (size only) | yes | via muscle targets | size factor only | **runs now** (parselmouth) | physically grounded, hard to steer (muscle activations), crude sound |
| **Pink Trombone** + **vocal-tract-grad** (Südholt 2023) | 2D waveguide (Kelly-Lochbaum); gradient descent fits the tract shape to a recorded vowel | in model, not fitted | no (open vowels only) | yes (that's the point) | not tried | fixed ~16 cm (adult male) in the paper; code available |
| **Own tube model** (chain-matrix / transmission line, textbook acoustics) | area function -> transfer function, with a nasal side branch at the velum | yes (we add it) | yes (constrictions/closures) | yes (we fit it) | to build (scipy) | outputs a spectral envelope: plugs straight into our WORLD pipeline with his real source and movement |

Source: VocalTractLab-Python (github.com/Simon-Stone/VocalTractLab-Python,
pypi.org/project/vocaltractlab), vocaltractlab.de features page, Praat manual
(Create Speaker, Artword & Speaker: To Sound), Südholt et al. "Vocal Tract Area
Estimation by Gradient Descent" (arXiv 2307.04702, code
github.com/dsuedholt/vocal-tract-grad).

## Proposed design (hybrid)
1. **His mouth = our own tube model**, 12.2 cm, with a nasal branch, producing
   only the *filter* (spectral envelope). His *source* (hum, purity, steadiness)
   and his real micro-movement stay from his recordings. That keeps everything
   that already sounds like him.
2. **Fit it to him** (analysis by synthesis, as in vocal-tract-grad): find area
   functions that reproduce each of his 10 recorded sounds (formants,
   bandwidths, nasal murmur, his hum tuning). Pass = check_phoneme/check_voice.
3. **Articulation targets for new sounds from VocalTractLab's MRI shapes**
   (once its CPU install is fixed): take each phoneme's shape, scale it to his
   tract, and correct it with the same fit that maps human shapes to his
   recorded ones.
4. **Validate** every new sound with the spec layers and your ear.

## Built (first pass)

- **VocalTractLab runs on CPU.** The high-level `vocaltractlab` package pulls in
  a GPU torchaudio; its native engine `vocaltractlab-cython` needs nothing else.
  We use the engine directly: articulators -> area function (40 tubes).
- **`prince_voice/mouth.py`**: our chain-matrix tube model with losses and a
  nasal branch. On VocalTractLab's own vowels it agrees with VTL's transfer
  functions within ~5% (a, i, u, schwa).
- **His size**: formant dispersion says the human model is 17.3 cm and he is
  12.5 cm -> scale 0.72.
- **Fitted to him** (`scripts/fit_mouth.py` -> `models/mouth_fit.json`): every
  recorded vowel is reproduced by an ordinary articulation (error 0.15-0.43
  Bark). The fits share a pattern: larynx raised (short throat), lips pulled
  back, jaw a little closed.

  | his vowel | his F1/F2/F3 | scaled human | fitted mouth |
  |---|---|---|---|
  | iː | 362 / 3323 / 4119 | 330 / 3085 / 4365 | 355 / 3280 / 4275 |
  | ũ | 388 / 1325 / 3914 | 375 / 1085 / 3580 | 390 / 1325 / 3780 |
  | ã | 1178 / 2138 / 3679 | 970 / 1750 / 3440 | 1155 / 2135 / 3650 |
  | ɐ˞ | 813 / 1954 / 3082 | 610 / 2225 / 3520 | 820 / 1955 / 3105 |

- **Limits (measured, not assumed)**: human moves do NOT transfer between his
  vowels that are far apart (predicting his ũ from his ã via the human a->u
  move is worse than guessing). His recorded n/m do not look like textbook
  nasal murmurs either (they behave like hummy closed vowels), so his real n/m
  are kept. The mouth is used for SMALL physical changes to his real sounds.
- **How it makes sound** (`prince_voice/mouthderive.py`): new = his real sound
  x |H(new shape)|^2 / |H(shape fitted to that sound)|^2. The model's own error
  cancels; his source, hum and movement stay. Gain capped at +-24 dB, his
  recording untouched above 5-7 kHz.
- **First uses**: ɑ = his nannar ã with the tongue moved back 0.6 cm (and the
  blade 1.4 cm) -> 1100 / 1785 / 3685 (`scripts/mouth_vowels.py`); lips
  opening into a vowel after m (`synth(..., mouth_edges=True)`).
  check_phoneme on "mama": the old warp makes the 2nd syllable measure as the
  r-vowel ɐ˞ ("rarra"); both mouth versions measure as ɑ in both syllables.
  Open issue: the mouth's lip opening into iː (minny) gives almost no F2 dip.
- **ɪ by the mouth** (`scripts/mouth_vowels.py`, MOVES): his fitted iː + the
  human VocalTractLab i->I move (tongue lower and back, jaw opens) -> 555 / 2815
  / 3925. In context: ninny 545 / 2885 vs neenee 321 / 3378 (the old warped ɪ
  only reached F1 ~436, which is why ninny and neenee sounded the same).
  check_voice: ninny 94%, closest approved = nanni ('good').
- **His real lip->ee is tiny**: p->iː in the clip dips F2 only 42 Hz (m->ũ:
  245 Hz). For ee the tongue channel (0.15-0.3 cm^2) dominates until the lips
  are nearly shut, so a small F2 dip after m in "minny" is correct for him.
- **Open**: mouth ɑ has H1-A3 26-28 vs his ã 22.6 (open-vowel range 22-27):
  moving the tongue back lowers F2 away from F3, so the 3-4 kHz harmonics drop
  (real acoustics, but it reads as a deeper hum cliff). mama overall 75% in
  check_voice; the warp version fails F3_low (2576 Hz: the "rarra").
