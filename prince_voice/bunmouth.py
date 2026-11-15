"""Prince's mouth as a little rabbit mouth: a midsagittal (side-view) model with
rabbit proportions, whose shape you can SEE, and whose acoustics come from the
same geometry.

Anatomy (rabbit, Oryctolagus cuniculus; reference animal ~2.9 kg, tongue 52 mm,
scaled to Prince by `size`):
  * a high larynx; the soft palate is long and its free edge sits at the
    epiglottis, so the nasal port (nasopharynx) opens just above the larynx.
    Rabbits are obligate nose-breathers: at rest the larynx is locked into the
    nasopharynx; to make a sound through the mouth the velum must seal.
  * a long, narrow oral cavity; the tongue has a big dorsal hump at the back
    (the lingual torus) and a thin, mobile front; between the incisors and the
    cheek teeth lies a long gap (diastema), where the cavity is narrowest.
  * chisel incisors at the front; a split (cleft) upper lip.

Geometry is defined along the tract's midline s (mm from the glottis to the
lips, reference animal). The roof (posterior pharynx wall, soft and hard
palate, upper incisors and lip) is fixed; the floor (tongue on the jaw, lower
incisors, lower lip) moves. Area = width(s) x gap(s), computed from the same
picture you see.

Articulators (all 0..1 or -1..1, plain words):
  jaw     how far the jaw is dropped (0 closed .. 1 wide)
  body    tongue torus height (-1 low .. 1 high)
  front   where the torus peaks (0 back .. 1 forward)
  tip     tongue tip raised toward the ridge behind the incisors (0 .. 1)
  root    tongue root pulled forward (+, wider throat) or back (-)
  lips    lip opening (0 closed .. 1 open)
  round   lips pushed forward/narrowed (0 .. 1)
  velum   nasal port open (0 sealed .. 1 open)
  larynx  larynx raised (shorter throat) (0 .. 1)
  cheeks  cheeks puffed out (bigger front cavity) (0 .. 1)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

from .mouth import _chain, _radiation, RHO, C

# ---- the reference rabbit (mm) ---------------------------------------------------
REF_LEN = 74.0
S_PORT = 17.0          # nasal port (free edge of the soft palate, at the epiglottis)
S_SOFT = (17.0, 37.0)  # soft palate
S_HARD = (37.0, 62.0)  # hard palate (with rugae)
S_DIAST = (55.0, 66.0) # diastema: narrowest part of the oral cavity
S_INC = 68.0           # incisors
S_JAW_HINGE = 30.0     # the jaw's rotation reaches the floor from about here
NASAL_LEN = 58.0       # nasopharynx + nasal cavity (long, with turbinates)
LARYNX_TRAVEL = 25.0   # how far his descended larynx can rise (reference mm); 0 if no neck

# width of the cavity across (mm) along s, and the neutral gap (mm)
_WS = np.array([0, 4, 10, 17, 30, 40, 52, 58, 64, 68, 71, 74], float)
_W = np.array([5, 7, 9, 10, 12, 12, 10, 6, 6, 8, 9, 9], float)
_G0 = np.array([2.2, 3.5, 5.0, 5.5, 5.5, 4.5, 4.0, 3.5, 3.0, 3.0, 3.0, 3.0], float)
N_SEC = 37


@dataclass
class Pose:
    jaw: float = 0.3
    body: float = 0.0
    front: float = 0.5
    tip: float = 0.0
    root: float = 0.0
    lips: float = 0.7
    round: float = 0.0
    velum: float = 0.0
    larynx: float = 0.0
    cheeks: float = 0.0

    def vec(self):
        return np.array(list(asdict(self).values()), float)

    @classmethod
    def from_vec(cls, v):
        return cls(*[float(x) for x in v])


NAMES = list(asdict(Pose()).keys())
LO = np.array([0, -1, 0, 0, -1, 0, 0, 0, 0, 0], float)
HI = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], float)


def _g(s, mu, sd):
    return np.exp(-0.5 * ((s - mu) / sd) ** 2)


@dataclass
class BunMouth:
    size: float = 1.0                       # x the reference rabbit
    neck_mm: float = 0.0                    # larynx descended into the neck (reference mm): his adaptation
    s: np.ndarray = field(default_factory=lambda: np.linspace(0, REF_LEN, N_SEC + 1))

    # ---- geometry ----------------------------------------------------------------
    def profile(self, p: Pose):
        """Section edges s (mm, reference), gap (mm) and width (mm), and the
        tongue/jaw surface for drawing. Reference-animal units."""
        s0 = self.s.copy()
        # larynx raised: the throat is shorter (the bottom 0..4 mm is removed)
        cut = 4.0 * p.larynx if self.neck_mm <= 0 else 0.0
        s = cut + (s0 - 0) * (REF_LEN - cut) / REF_LEN
        # lips forward: the lip tube is longer
        s_lips_extra = 7.0 * p.round      # rabbit lips are very mobile: push forward up to ~5 mm (real)
        mid = 0.5 * (s[1:] + s[:-1])
        gap = np.interp(mid, _WS, _G0)
        width = np.interp(mid, _WS, _W)
        # jaw: rotation, so the floor drops more toward the front
        jaww = np.clip((mid - S_JAW_HINGE) / (S_INC - S_JAW_HINGE), 0, 1.15)
        gap = gap + (p.jaw - 0.3) * 12.0 * jaww
        # tongue torus: a big hump on the back of the tongue (pos 40..56 mm)
        mu = 40.0 + 16.0 * p.front
        gap = gap - p.body * 5.0 * _g(mid, mu, 6.5)
        # tongue root forward/back widens/narrows the throat
        gap = gap + p.root * 3.0 * _g(mid, 14.0, 7.0)
        # tongue tip up to the ridge behind the incisors
        gap = gap - p.tip * 6.0 * _g(mid, 64.5, 2.2)
        # a dropped jaw stretches the cheeks: the front of the cavity gets wider
        width = width * (1 + 0.5 * p.jaw * np.clip((mid - 48.0) / 8.0, 0, 1))
        # cheeks: loose, fleshy rabbit cheeks (buccal folds) puffed out widen
        # the front of the mouth -> a bigger front cavity (his low-F2 "oo")
        width = width * (1 + 0.9 * p.cheeks * _g(mid, 58.0, 7.0))
        # lips (last ~3 mm): opening and rounding (narrower across)
        lipz = mid > REF_LEN - 3.0
        gap = np.where(lipz, 0.2 + 6.5 * p.lips * (0.6 + 0.6 * p.jaw), gap)
        width = np.where(lipz, width * (1 - 0.7 * p.round), width)
        gap = np.maximum(gap, 0.0)
        length = np.diff(s)
        length[-3:] += s_lips_extra / 3
        return mid, length, gap, width

    def tube(self, p: Pose):
        """Areas (cm^2), lengths (cm), nasal port (cm^2), branch index; scaled."""
        mid, length, gap, width = self.profile(p)
        k = self.size
        area = np.maximum(gap * width, 0.0) / 100.0 * k ** 2
        length = length / 10.0 * k
        port = 0.45 * p.velum * k ** 2
        br = int(np.searchsorted(mid, S_PORT))
        neck = max(0.0, self.neck_mm - LARYNX_TRAVEL * p.larynx)   # a mobile larynx: raised for ee, low for oo
        if neck > 0:
            # the throat continues down into the neck to the descended larynx: a
            # pharynx tube like his lower throat, which the tongue root also shapes
            n = max(2, int(round(neck / 2.0)))
            g = np.full(n, 5.5) + p.root * 4.5                  # root forward widens it (as in ee)
            g[0] = 2.2                                      # the larynx tube itself
            na = np.maximum(g * 9.0, 0.0) / 100.0 * k ** 2
            area = np.concatenate([na, area])
            length = np.concatenate([np.full(n, neck / n / 10.0 * k), length])
            br += n
        return area, length, port, br

    def length_cm(self, p: Pose = Pose()):
        return float(self.tube(p)[1].sum())

    # ---- acoustics ----------------------------------------------------------------
    def nasal(self):
        k = self.size
        na = np.array([0.30, 0.35, 0.30, 0.25, 0.22, 0.20, 0.18, 0.16, 0.14, 0.12]) * k ** 2
        nl = np.full(len(na), NASAL_LEN / 10.0 / len(na) * k)
        return na, nl

    def response(self, p: Pose, freqs, radiate=True, source_at=None):
        """Glottal-flow (or, with source_at=section index, frication) -> radiated
        sound. Same chain-matrix acoustics as mouth.py."""
        area, length, port, br = self.tube(p)
        w = 2 * np.pi * np.maximum(np.asarray(freqs, float), 1.0)
        area = np.maximum(area, 1e-4)
        if source_at is not None:
            # noise made at a constriction: only the cavity in front of it shapes it
            Kf = _chain(area[source_at:], length[source_at:], w)
            Zl = _radiation(area[-1], w)
            H = 1.0 / (Kf[1, 0] * Zl + Kf[1, 1])
        else:
            Kp = _chain(area[:br], length[:br], w)
            Ko = _chain(area[br:], length[br:], w)
            Zl = _radiation(area[-1], w)
            Ul = 1.0 / (Ko[0, 0] * Zl + Ko[0, 1])
            Ub = (Ko[1, 0] * Zl + Ko[1, 1]) * Ul
            Un = 0.0
            if port > 1e-3:
                na, nl = self.nasal()
                Kn = _chain(np.concatenate([[port], na]), np.concatenate([[0.4 * self.size], nl]), w)
                # turbinates: a rabbit nose is full of scrolls (lossy); damp it
                Zn = _radiation(na[-1], w) + RHO * C / na[-1] * 0.15
                Un = 1.0 / (Kn[0, 0] * Zn + Kn[0, 1])
                Ub = Ub + (Kn[1, 0] * Zn + Kn[1, 1]) * Un
            Ug = Kp[1, 0] + Kp[1, 1] * Ub
            H = (Ul + Un) / Ug
        if radiate:
            H = H * (1j * w / (2 * np.pi * 1000.0))
        return H

    def formants(self, p: Pose, fmax=8000.0, df=10.0, n=4):
        f = np.arange(80.0, fmax, df)
        m = np.abs(self.response(p, f, radiate=False))
        k = np.where((m[1:-1] > m[:-2]) & (m[1:-1] >= m[2:]))[0] + 1
        out = [float(f[i]) for i in k][:n]
        return out + [np.nan] * (n - len(out))

    def constriction(self, p: Pose):
        area = self.tube(p)[0]
        i = int(np.argmin(area[5:])) + 5
        return i, float(area[i])


# ---- drawing ----------------------------------------------------------------------
def _midline(s):
    """Map s (mm) to a bent midline in the head (x forward, y up): the throat
    rises steeply, bends under the skull base and runs forward and slightly
    down along the long palate to the incisors."""
    s = np.asarray(s, float)
    ang = np.interp(s, [0, 12, 26, 38, 74], np.radians([95, 90, 35, -8, -18]))
    ds = np.gradient(s) if s.size > 1 else np.array([0.0])
    x = np.cumsum(np.cos(ang) * ds); y = np.cumsum(np.sin(ang) * ds)
    return x - x[0], y - y[0], ang


def draw(ax, mouth: BunMouth, p: Pose, title: str = "", head: bool = True):
    """Side view of the little mouth (reference-rabbit mm, scaled by size)."""
    import matplotlib.patches as mp
    k = mouth.size
    s = np.linspace(0, REF_LEN, 400)
    x, y, ang = _midline(s)
    nx, ny = -np.sin(ang), np.cos(ang)          # 'up' normal (toward the roof)
    mid, length, gap, width = mouth.profile(p)
    g = np.interp(s, mid, gap)
    # roof = midline; floor = midline - gap (along the normal)
    rx, ry = x * k, y * k
    fx, fy = (x - nx * g) * k, (y - ny * g) * k
    allx = np.concatenate([rx, fx]); ally = np.concatenate([ry, fy])
    xmin, xmax, ymin, ymax = allx.min(), allx.max(), ally.min(), ally.max()
    ymin_neck = ymin - max(0.0, mouth.neck_mm) * k
    Wd = 1.30 * (xmax - xmin); Hd = 0.92 * Wd
    hcx, hcy = xmax - 0.5 * Wd + 0.06 * Wd, ymin - 0.04 * Hd + 0.5 * Hd
    if head:
        # a round bun head around the mouth (same scale), with an ear and an eye
        ax.add_patch(mp.Ellipse((hcx, hcy), Wd, Hd, fc="#f7f4ee", ec="#c9c2b5", lw=1.2, zorder=0))
        ax.add_patch(mp.Ellipse((hcx - 0.22 * Wd, hcy + 0.62 * Hd), 0.24 * Wd, 0.75 * Hd, angle=18,
                                fc="#f7f4ee", ec="#c9c2b5", lw=1.2, zorder=0))
        ax.add_patch(mp.Circle((hcx + 0.17 * Wd, hcy + 0.22 * Hd), 0.035 * Wd, fc="#5a3a3a", zorder=1))
        if mouth.neck_mm > 0:   # his round fluffy body below (the neck is hidden in the fluff)
            bh = 1.35 * Hd; top = hcy - 0.28 * Hd        # body top tucked under the head
            ax.add_patch(mp.Ellipse((hcx - 0.22 * Wd, top - bh / 2), 1.55 * Wd, bh, fc="#f7f4ee",
                                    ec="#c9c2b5", lw=1.2, zorder=-1))
            ax.add_patch(mp.Ellipse((hcx, hcy - 0.2 * Hd), 0.9 * Wd, 0.5 * Hd, fc="#f7f4ee", ec="none", zorder=-0.5))
        # 1 cm scale bar
        ax.plot([hcx - 0.45 * Wd, hcx - 0.45 * Wd + 10.0], [hcy - 0.55 * Hd] * 2, color="#555", lw=2)
        ax.text(hcx - 0.45 * Wd, hcy - 0.62 * Hd, "1 cm", fontsize=7, color="#555")
    # nasal cavity: from the port up and forward to the nose
    i_port = np.searchsorted(s, S_PORT)
    px, py = rx[i_port], ry[i_port]
    nose_x, nose_y = hcx + 0.47 * Wd, hcy + 0.05 * Hd
    t = np.linspace(0, 1, 50)
    nxs = px + (nose_x - px) * t - 4 * k * np.sin(np.pi * t)
    nys = py + 6 * k + (nose_y - py - 6 * k) * t + 10 * k * np.sin(np.pi * t)
    ax.plot(nxs, nys, color="#d7a6a6", lw=10 * k * (0.4 + 0.6 * p.velum) + 2, alpha=0.6, solid_capstyle="round")
    ax.plot(nose_x, nose_y, "o", color="#e99", ms=6)
    # cavity fill
    ax.fill(np.concatenate([rx, fx[::-1]]), np.concatenate([ry, fy[::-1]]), color="#ffd9df", zorder=2)
    # roof: pharynx wall, soft palate, hard palate
    soft = (s >= S_SOFT[0]) & (s <= S_SOFT[1]); hard = s >= S_HARD[0]
    ax.plot(rx[s <= S_SOFT[0]], ry[s <= S_SOFT[0]], color="#8a6", lw=3, zorder=3)
    ax.plot(rx[soft], ry[soft], color="#c66", lw=5 * (1 - 0.5 * p.velum), zorder=3)
    ax.plot(rx[hard], ry[hard], color="#777", lw=4, zorder=3)
    # velum gap drawn as an opening into the nose
    if p.velum > 0.05:
        ax.plot([px, nxs[3]], [py, nys[3]], color="#d7a6a6", lw=2 + 6 * p.velum, zorder=3)
    # tongue (floor), drawn as a body down to the jaw
    body = s < S_INC - 1
    ax.fill(np.concatenate([fx[body], fx[body][::-1]]),
            np.concatenate([fy[body], fy[body][::-1] - 12 * k * np.clip((s[body][::-1] - 8) / 30, 0.2, 1)]),
            color="#e58c9a", zorder=4)
    ax.plot(fx[body], fy[body], color="#b04a5a", lw=2, zorder=5)
    if p.cheeks > 0.05:   # puffed cheeks (seen through): a wider front of the mouth
        ic = np.searchsorted(s, 58.0)
        ax.add_patch(mp.Ellipse(((rx[ic] + fx[ic]) / 2, (ry[ic] + fy[ic]) / 2), (10 + 8 * p.cheeks) * k,
                                (6 + 7 * p.cheeks) * k, fc="#f4a7b4", ec="#c77", alpha=0.35 + 0.3 * p.cheeks, zorder=6))
    # his descended larynx: the throat continues down into the neck
    neck = max(0.0, mouth.neck_mm - LARYNX_TRAVEL * p.larynx) * k
    if neck > 0:
        g0 = (5.5 + p.root * 4.5) * k
        ax.fill([rx[0], rx[0], fx[0], fx[0]], [ry[0], ry[0] - neck, ry[0] - neck, fy[0]], color="#ffd9df", zorder=2)
        ax.plot([rx[0], rx[0]], [ry[0], ry[0] - neck], color="#8a6", lw=3, zorder=3)
        ax.plot([rx[0] + g0, rx[0] + g0], [fy[0], ry[0] - neck], color="#b04a5a", lw=2, zorder=3)
        ax.plot([rx[0] - 1 * k, rx[0] + g0 + 1 * k], [ry[0] - neck] * 2, color="#6a4", lw=4, zorder=4)   # vocal folds
        ax.text(rx[0] - 14 * k, ry[0] - neck, "larynx", fontsize=7, color="#6a4")
    # epiglottis / larynx
    ax.plot([rx[0] - 3 * k, fx[0]], [ry[0], fy[0]], color="#8a6", lw=3)
    # incisors (chisel teeth) and the split upper lip
    ia = np.searchsorted(s, S_INC)
    ux, uy = rx[ia], ry[ia]
    lx, ly = fx[ia], fy[ia]
    ax.add_patch(mp.FancyBboxPatch((ux - 1.2 * k, uy - 6 * k), 2.4 * k, 7 * k, boxstyle="round,pad=0.2",
                                   fc="#fffbe6", ec="#bbb", zorder=6))
    ax.add_patch(mp.FancyBboxPatch((lx - 1.0 * k, ly - 1 * k), 2.0 * k, 5 * k, boxstyle="round,pad=0.2",
                                   fc="#fffbe6", ec="#bbb", zorder=6))
    ext = 3 * p.round * k
    ax.plot([rx[-1], rx[-1] + 2 * k + ext], [ry[-1], ry[-1] - 1 * k], color="#d88", lw=4, solid_capstyle="round", zorder=7)
    ax.plot([fx[-1], fx[-1] + 2 * k + ext], [fy[-1], fy[-1] + 1 * k], color="#d88", lw=4, solid_capstyle="round", zorder=7)
    ax.text(rx[-1] + 3 * k + ext, ry[-1] + 1.5 * k, "ᵥ", fontsize=9, color="#c77")   # the cleft
    ax.set_aspect("equal"); ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10)
