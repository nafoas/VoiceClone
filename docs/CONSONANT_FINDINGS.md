# Why "nannarmunis... peet teet tee" came out as "Lannlillies... Pekeke" (2026-11-20)

Da Boss: *"why does it always make L and K sounds ... I think there's just something wrong in how you
make and voice consonants."* He was right. Checked against his clip directly (spectra, resonances,
loudness through each consonant), not against the phoneme recogniser (it disagreed with his ear).

## What was wrong

### 1. The consonants were not made by the parts of the mouth that make them
Every sound's shape was fitted only to its own steady hum. A steady hum barely shows *where* a mouth is
shut, so the fit shut it wherever it was convenient:

| Sound | Model was doing (every version since F14) | That gesture is ... |
|---|---|---|
| m | tongue pressed to the roof at 80% of the tube (lips shut too) | an "n"/"l" (tongue contact) |
| ɹ | tongue tip sealed on the ridge (0.0001-0.0007 cm²), lips almost shut | an "l" (tip contact) |
| ũ | back of the tongue nearly sealed (F14), lips 0.004 cm² | a velar near-closure |
| n | one fixed whole-mouth shape for all three n's | his three n's differ (each takes the tongue of its neighbours) |

The ear finds out where a consonant is made from how the resonances MOVE into and out of it, so it heard
the gestures the model really made: tongue contacts, i.e. "l".

### 2. His r-colouring was missing (the "l" in "Lannlillies")
Read the same way from his measured mouth response and from the model's:

| | his resonances (Hz) | checkpoint 8 |
|---|---|---|
| ɹ | 564 / 1653 / **2555** | 1053 / 2023 / 4295 |
| ɐ˞ | 885 / 1992 / 3425 | 767 / 2326 / 4209 |
| m | 438 / 1580 / **2668** | 545 / 1539 / 4218 |

His "ar-m" carries a lowered THIRD resonance (~2.6 kHz): that is what an r is. A high third resonance is
what an "l" is. The fit only ever targeted the first two resonances, so nothing asked for it, and the
overnight perceptual tuning then made "ɹ" and "ɐ˞" worse against his own spectra (tone error 2.1 -> 9.4 dB
and 4.5 -> 11.5 dB) while the recogniser was satisfied.

### 3. The stops were not made by the mouth at all (the "k" in "Pekeke")
- A "t" closure pulled the WHOLE tongue into the fitted "n" shape: his second resonance stays at ~3.3 kHz
  into the closure, the model's plunged from 3.3 to 1.3 kHz.
- The vowel after a "t" started already wide open: there was no tongue-tip release at all.
- The burst and breath noises went through one fixed "ee" mouth, not the mouth as it opens: burst centre
  7.4-7.5 kHz vs his 4.2-4.5 kHz; the "p" burst 15 dB too loud.

### 4. How the closures were voiced (part of the "harsh volume steps")
His voice dies away gradually inside a sealed mouth (0.4-1 dB per ms, down to -40..-50 dB). The model's
voice stopped dead where his pitch track ended: digital silence (-90..-105 dB) in the middle of the phrase.

## What changed (all inside the one mouth; nothing done to the sound afterwards)
1. **Consonants as gestures** (`GEST=1`, mouth_inverse + render_his): "m" = lips shut + soft palate open;
   "n" (and the "t" closure) = tongue tip sealed at the ridge with the tongue front behind it + soft palate.
   Everything else is the mouth its neighbours are carrying it through (coarticulation; Öhman 1966,
   articulatory phonology). Open sounds (vowels, ɹ) may not touch anywhere.
2. **His rest posture**: a rabbit breathes only through its nose, so before a phrase the lips are shut, the
   soft palate open and the tongue fills the mouth. The first "n" starts from there (one shared posture,
   fitted: tongue body and root up, jaw nearly shut).
3. **His third resonance** is a target for "ɐ˞", "ɹ", "m" (`FMT3=1`), read the same way as the first two.
4. **A global search** (CMA-ES, `sound_search.py`) for those shapes, because a local fit cannot jump from a
   tongue contact to a bunched r. It found a **bunched-tongue r** (tongue body up, tip down, lips rounded,
   mouth open): 569 / 1643 / 2531 Hz vs his 565 / 1655 / 2561; tone error 9.4 -> 1.8 dB.
5. **Stops as gestures on the moving mouth** (render_his `stop_gestures`): the tip (t) or lips (p) close and
   open on top of the vowel-to-vowel movement; the seal breaks exactly at his burst.
6. **Noises through the moving mouth** (consonants `_through_moving_mouth`, every 2 ms): the burst is made
   at the opening gap; the breath at the vocal cords spread for breathing (0.05 cm²).
7. **Voicing in a closure**: the push across the folds drops to half within 10 ms of the seal (pressure
   builds behind it) and, past his last clear pitch, dies away (time constant 20 ms) until the release.
   Fitted to his two closures: closure loudness error 10.1 -> 6.4 dB; no more dead silence.
