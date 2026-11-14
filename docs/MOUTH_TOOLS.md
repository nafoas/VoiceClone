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
