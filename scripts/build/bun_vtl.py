"""His bun mouth inside VocalTractLab (our engine build): the tube, cut so the nose branches at HIS velum,
and his side anatomy (windpipe, nose, sinuses, throat pockets) instead of VocalTractLab's human defaults.

Why (2026-11-24): VocalTractLab's synthesizer keeps its own working tube whose side parts are always the human
defaults (a 23 cm windpipe of 2.5-4 cm2, a human nose of 0.8-4.2 cm2 with 57 cm3 of sinuses, a 3 cm piriform
fossa): the speaker file's sizes never reach it when the tube is given directly. And the nose always branches
after section 16 of 40, wherever that falls in our tube. Our engine build now carries the side parts through
(Tube::copyStaticParts) and takes them from vtlSetSideAnatomy; here they are set to his.

His values (starting points; each is a search variable, ROADMAP Step 5):
- windpipe: 6.0 cm long, 0.33 cm2 (rabbit trachea ~6-7 mm across, CT; BUN_MOUTH Step 3i)
- nose: the bun model's nasal passage (BunMouth.nasal: 0.30..0.12 cm2 x size^2, length x nlen),
  behind a 0.3 cm velum port, as in the frequency-domain mouth
- sinuses: none to speak of (the bun model had none): VocalTractLab's human sinuses x SINUS^3 in volume
- piriform fossa: FOSSA = (length cm, volume cm3) or None (the bun model rejected it: worse "ee"s);
  models/bun.speaker's 1.375 cm / 0.2496 cm3 (human x0.55) when on
"""
import os

import numpy as np

import vtl_tube as V

N_PHARYNX = 16   # VocalTractLab: the nose branches after this many of the 40 sections
TRACHEA = (float(os.environ.get("TRACHEA_LEN", 6.0)), float(os.environ.get("TRACHEA_AREA", 0.33)))
SINUS = float(os.environ.get("SINUS", 0.05))
FOSSA = None if os.environ.get("FOSSA", "off") == "off" else (1.375, 0.2496)
PORT_LEN = 0.3   # cm, the velum port (as in the frequency-domain mouth)


def his_nose(size, nlen):
    """19 nose sections (velum side first): 4 for the velum port (re-blended by the engine from the opening),
    15 for his nasal passage, resampled from the bun model's 10."""
    from prince_voice.bunmouth import BunMouth
    na, nl = BunMouth(size).nasal(); nl = nl * nlen
    x = np.r_[0.0, np.cumsum(nl)]; xc = 0.5 * (x[1:] + x[:-1])
    L15 = x[-1] / 15; c15 = (np.arange(15) + 0.5) * L15
    area = np.r_[np.full(4, na[0]), np.interp(c15, xc, na)]
    length = np.r_[np.full(4, PORT_LEN / 4), np.full(15, L15)]
    return length, area


def set_his_side(size, nlen, fossa=FOSSA, trachea=TRACHEA, sinus=SINUS):
    nl, na = his_nose(size, nlen)
    fl, fv = fossa if fossa else (0.3, 1e-4)   # "off": a vanishing pocket (the engine always couples one)
    V.set_side_anatomy(trachea[0], trachea[1], nl, na, sinus, fl, fv)
    V.set_options(fossa=bool(fossa))   # off: the option too, so it is truly absent


def frame(a, L, frac, artic, incisor, velum, ts3=0.0, n_old=40):
    """His tube (n_old equal sections over L cm, glottis to lips) re-cut into VocalTractLab's 40: 16 from the
    glottis to his velum (frac of the length, as the bun model rounds it), 24 from the velum to the lips.
    Each new section takes the length-weighted mean of 1/area of the old sections it covers (keeps narrowings
    and seals: their air mass), and the articulator at its centre."""
    lo = np.arange(n_old) * L / n_old; hi = lo + L / n_old
    xb = round(frac * n_old) * L / n_old
    edges = np.r_[np.linspace(0, xb, N_PHARYNX + 1), np.linspace(xb, L, 40 - N_PHARYNX + 1)[1:]]
    na = np.zeros(40); nart = np.zeros(40, np.int32)
    for k in range(40):
        w = np.clip(np.minimum(hi, edges[k + 1]) - np.maximum(lo, edges[k]), 0, None)
        na[k] = w.sum() / np.sum(w / np.maximum(a, 1e-8))
        c = 0.5 * (edges[k] + edges[k + 1]); nart[k] = artic[min(int(c / (L / n_old)), n_old - 1)]
    return dict(lengths=np.diff(edges), areas=na, artic=nart, incisor=incisor, velum=velum, ts3=ts3)
