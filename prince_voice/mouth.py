"""Prince's mouth: a tube model of his vocal tract.

Shapes (where the tongue, lips, jaw and velum are) come from VocalTractLab's
3D articulatory model (Birkholz; MRI-based), computed as an area function: 40
tube sections from the glottis to the lips. The acoustics are our own
chain-matrix (transmission-line) model with losses and a nasal branch at the
velum, so the whole tract can be scaled to HIS size (12.2 cm, from his formant
dispersion) and fitted to the sounds he really made.

The mouth produces only the FILTER. His source (the hum, its purity, its
steadiness) and his movement come from his recordings: a new sound is made by
taking one of his real sounds and multiplying its spectrum by
|H(new shape)| / |H(the shape that reproduces his real sound)|.

    from prince_voice.mouth import Mouth
    m = Mouth(); H = m.response(m.shape("a"), freqs)
"""
from __future__ import annotations

import numpy as np

RHO, C = 1.14e-3, 35000.0          # air density g/cm^3, speed of sound cm/s
SR_VTL = 44100

# nasal tract (human, from glottis-side port to the nostrils), cm and cm^2;
# coarse profile after Maeda (1982) / Dang et al. (1994), no sinuses
NASAL_LEN = 11.4
NASAL_AREA = np.array([1.0, 1.6, 2.4, 3.0, 3.2, 3.0, 2.6, 2.1, 1.6, 1.2, 0.9, 0.7])


def _vtl():
    import vocaltractlab_cython as cy
    return cy


# tissue: scale factors on Sondhi & Schroeter's human values. wall_r: how much the
# soft walls absorb (damping); wall_m: how much the walls yield (sets the closed-
# tract floor resonance); visc: air friction at the walls. 1.0 = human.
TISSUE = dict(wall_r=1.0, wall_m=1.0, visc=1.0)
# Boundary-layer (viscous + heat) loss per unit length grows with wall perimeter over area,
# i.e. as 1/radius. Sondhi & Schroeter's constant is for human-sized tubes; with AREA_LOSS on,
# each section's loss is scaled by sqrt(LOSS_REF_AREA / its area) (off = the old constant loss).
AREA_LOSS = False
LOSS_REF_AREA = 3.0   # cm^2, a typical human vocal-tract cross-section


def _section_matrices(area, length, w):
    """Lossy chain matrices for every section at every frequency (Sondhi &
    Schroeter 1987 wall + viscous losses). Returns A, B, C, D of shape (S, F)."""
    jw = 1j * w[None, :]
    a, b, w0sq, q = (130 * np.pi * TISSUE["wall_r"], (30 * np.pi) ** 2, (406 * np.pi) ** 2 * TISSUE["wall_m"] ** 2,
                     4.0 * TISSUE["visc"])
    if AREA_LOSS:
        q = q * np.sqrt(LOSS_REF_AREA / np.maximum(np.asarray(area, float), 1e-4))[:, None]
    alpha = np.sqrt(jw * q)
    beta = jw * w0sq / ((jw + a) * jw + b) + alpha
    gam = np.sqrt((alpha + jw) / (beta + jw))
    sig = gam * (beta + jw)
    x = sig * length[:, None] / C
    Z0 = RHO * C / np.maximum(area[:, None], 1e-4)
    ch, sh = np.cosh(x), np.sinh(x)
    return ch, Z0 * gam * sh, sh / (Z0 * gam), ch


def _chain(area, length, w):
    """Product of section matrices, input side first: [P_in;U_in] = K [P_out;U_out]."""
    A, B, Cm, D = _section_matrices(area, length, w)
    K = np.zeros((2, 2, len(w)), complex); K[0, 0] = K[1, 1] = 1
    for s in range(len(area)):
        K = np.einsum("ijf,jkf->ikf", K, np.array([[A[s], B[s]], [Cm[s], D[s]]]))
    return K


def _radiation(area, w):
    """Piston-in-a-sphere radiation impedance at an opening of `area` cm^2."""
    area = max(area, 1e-4)
    Rr = 128 * RHO * C / (9 * np.pi ** 2 * area)
    Lr = 8 * RHO / (3 * np.pi * np.sqrt(np.pi * area))
    jwL = 1j * w * Lr
    return jwL * Rr / (Rr + jwL + 1e-30)


class Mouth:
    """A vocal tract: VocalTractLab articulators, scaled to `scale` x human size."""

    def __init__(self, scale: float = 1.0, nasal_scale: float | None = None):
        self.scale = scale
        self.nasal_scale = scale if nasal_scale is None else nasal_scale
        self.cy = _vtl()
        self.info = self.cy.get_param_info("tract")
        self.names = [p["name"] for p in self.info]
        self.lo = np.array([p["min"] for p in self.info], float)
        self.hi = np.array([p["max"] for p in self.info], float)

    # ---- shapes ---------------------------------------------------------------
    def shape(self, name: str) -> np.ndarray:
        return np.asarray(self.cy.get_shape(name, "tract"), float)

    def tube(self, params: np.ndarray):
        """Area function (glottis -> lips), section lengths, velum port area."""
        tb = self.cy.tract_state_to_tube_state(np.clip(params, self.lo, self.hi))
        length = np.asarray(tb["tube_length"], float) * self.scale
        area = np.asarray(tb["tube_area"], float) * self.scale ** 2
        velum = float(tb["velum_opening"]) * self.scale ** 2
        L = np.asarray(tb["tube_length"])
        branch = int(np.argmax(np.abs(np.diff(L)) > 1e-3)) + 1     # end of the pharynx tube
        return area, length, velum, branch

    # ---- acoustics ------------------------------------------------------------
    def response(self, params: np.ndarray, freqs: np.ndarray, radiate: bool = True) -> np.ndarray:
        """Complex transfer function: glottal flow -> radiated sound (lips + nose)."""
        area, length, velum, br = self.tube(params)
        return self.response_tube(area, length, velum, br, freqs, radiate)

    def response_tube(self, area, length, velum, br, freqs, radiate=True):
        w = 2 * np.pi * np.maximum(np.asarray(freqs, float), 1.0)
        Kp = _chain(area[:br], length[:br], w)                 # glottis -> velum
        Ko = _chain(area[br:], length[br:], w)                 # velum -> lips
        Zl = _radiation(area[-1], w)
        Pb = 1.0
        Ul = Pb / (Ko[0, 0] * Zl + Ko[0, 1])
        Ub = (Ko[1, 0] * Zl + Ko[1, 1]) * Ul
        Un = 0.0
        if velum > 0.01 * self.nasal_scale ** 2:
            na = NASAL_AREA * self.nasal_scale ** 2
            na = np.concatenate([[velum], na])
            nl = np.full(len(na), NASAL_LEN * self.nasal_scale / len(na))
            Kn = _chain(na, nl, w)
            Zn = _radiation(na[-1], w)
            Un = Pb / (Kn[0, 0] * Zn + Kn[0, 1])
            Ub = Ub + (Kn[1, 0] * Zn + Kn[1, 1]) * Un
        Ug = Kp[1, 0] * Pb + Kp[1, 1] * Ub
        H = (Ul + Un) / Ug
        if radiate:
            H = H * (1j * w / (2 * np.pi * 1000.0))          # radiation: pressure ~ d(flow)/dt
        return H

    def formants(self, params, fmax=6000.0, n=4, df=5.0):
        f = np.arange(50.0, fmax, df)
        m = 20 * np.log10(np.abs(self.response(params, f, radiate=False)) + 1e-12)
        k = np.where((m[1:-1] > m[:-2]) & (m[1:-1] >= m[2:]))[0] + 1
        out = [float(f[i]) for i in k][:n]
        return out + [np.nan] * (n - len(out))
