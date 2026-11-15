# Prince's little mouth (bun anatomy)

`prince_voice/bunmouth.py` is a side-view model of a rabbit's vocal tract. The
picture and the sound come from the same geometry: what you see is what makes
the sound.

## Anatomy it is built on (rabbit, *Oryctolagus cuniculus*)

| Part | Rabbit fact | In the model |
|---|---|---|
| Larynx | High in the throat. At rest it is locked into the nasopharynx (rabbits are obligate nose-breathers) | Short laryngopharynx; `larynx` raises it (shorter throat) |
| Soft palate | Long; its free edge reaches about the middle of the epiglottis | The nasal port sits just above the larynx (17 mm on a 74 mm tract); `velum` opens it |
| Nose | Long nasal cavity full of turbinate scrolls | 58 mm side tube to the nostrils, heavily damped |
| Oral cavity | Long and narrow, narrowest at the diastema (the gap between the incisors and the cheek teeth) | Width profile 12 mm at the back, 6 mm at the diastema |
| Tongue | About 52 mm long (2.9 kg rabbit), with a big dorsal hump at the back (the lingual torus) and a thin, mobile front | `body` raises the torus; `front` slides its peak 40–56 mm; `tip` lifts the front to the ridge behind the incisors; `root` widens or narrows the throat |
| Jaw | Rotates, so the opening grows toward the front | `jaw` drops the floor more at the front and stretches the cheeks |
| Teeth and lips | Chisel incisors; split (cleft) upper lip | Incisors at 68 mm; `lips` opens them, `round` pushes them forward and narrows them |

Sources: Morphometry of the rabbit upper digestive tract (PMC12249223), tongue
length 52.4 ± 1.8 mm in 2.9 kg rabbits; rabbit soft palate and epiglottis
(PMC7711434); rabbit oral cavity is elongated and narrow rostrally (comparative
study, agmv.ro); MediRabbit, anatomy of the rabbit tongue (lingual torus).

## Size: an honest tension

Fitting his four recorded vowels gives the best size at **1.5–1.6 × the
reference 2.9 kg rabbit** (an 11–12 cm tract). A small round bun is about
**0.75 ×**, with a tract of about 5.5 cm. A mouth that small would put every
resonance about twice as high, which is the "chipmunk" failure in his negative
space. So the voice we have, and that you said is recognisably him, comes from
a bun-*shaped* mouth about twice the size of a real small bun's.

The model keeps rabbit **proportions** fixed, and `size` is one number. Every
drawing has a 1 cm bar, so this is always visible rather than hidden.
