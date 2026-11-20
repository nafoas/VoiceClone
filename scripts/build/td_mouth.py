"""His mouth in the time domain: air moving through it, sample by sample (2026-11-20 consonant rebuild).

Why: the frequency-domain mouth (ee_bunfit.tube_H_nose) can only FILTER his voice through a frozen shape,
so every consonant had to be pasted on as noise. Here the air itself moves, so consonants come out of the
physics: a closure builds pressure, a release bursts, a narrow gap hisses, a sealed mouth stops the voice.

Same physics and constants as the frequency-domain mouth (which every shape was fitted with):
  - tube sections (area, length) from the bun mouth; air mass and springiness per section
  - Sondhi & Schroeter's yielding walls (mass-spring-damper; they also radiate, as before)
  - boundary-layer losses, larger in narrow sections (sqrt(3 cm^2 / area)), x NOSE_SURF^2 in the nose
  - the nose branching off at the soft palate (port area, port tube 0.3 cm), nostril radiation + damping
  - radiation from the lips and nostrils (piston in a sphere), then the small round head (first order)
New, from aerodynamics (standard; Flanagan 1972, Maeda 1982, Stevens 1998):
  - his lungs push a steady pressure; his cords are an opening whose size follows HIS recovered voice
    (his flow pulses), so the air through them is set by the pressure actually across them: when the
    mouth seals, the pressure behind it rises and his voice dies by itself
  - air leaving a narrow gap loses its speed's pressure (jet separation)
  - turbulence where the jet's Reynolds number exceeds ~1800: a noise pressure source just downstream
    of the gap (strength ~ Re^2 - Re_c^2), so hiss and bursts happen only where the air really rushes
  - the moving walls of the mouth push air (volume change), so moving articulators pump

    y48 = simulate(areas, dx, port, ag, plung, ...)   (all at SRT = 192 kHz; see run())
"""
import numpy as np
from numba import njit

RHO, C = 1.14e-3, 35000.0
NU = 0.15            # kinematic viscosity of air, cm^2/s
SRT = 192000         # simulation rate (sections 0.24 cm: needs > c / dx = 146 kHz)
RE_C = 1800.0        # critical Reynolds number for turbulence


# Boundary-layer loss per cm is (rho/A) sqrt(j w q) (Sondhi & Schroeter, as in the frequency-domain mouth).
# sqrt(s) ~ LC0 + sum_k LCK[k] s / (s + LPK[k]) within 6.5% over 150 Hz - 14 kHz: a constant resistance
# plus four resistance-inertance pairs per junction.
LC0 = 7.74
LCK = np.array([17.11, 40.19, 87.7, 472.78])
LPK = 2 * np.pi * np.array([100.0, 669.0, 4481.0, 30000.0])


@njit(cache=True)
def _sim(Aor, dx, kv, port_t, Ag_t, Pl_t, Nas_a, Nas_dx, nose_visc, damp, wall_r, wall_m, visc, area_loss,
         gnoise, seed, fr_hop, walls_rad, lc0, lck, lpk, pump=1.0):
    """Aor: (F, N) oral areas per frame (frames every fr_hop steps, linearly interpolated);
    port_t: (F,) nose port area; Ag_t: (T,) cord opening per step; Pl_t: (T,) lung pressure per step.
    Returns the radiated sound (d/dt of all flow leaving lips, nostrils and walls) per step, and the
    pressure in the mouth just above the cords (diagnostics)."""
    F, N = Aor.shape
    T = Ag_t.shape[0]
    Nn = Nas_a.shape[0]
    np.random.seed(seed)
    out = np.zeros(T)
    p0 = np.zeros(T)
    remax = np.zeros(T); reidx = np.zeros(T)    # diagnostics: the fastest jet, and where it is
    dt = 1.0 / SRT
    NK = lck.shape[0]
    iL = np.zeros((N + 1, NK))   # loss-ladder states per junction
    iLn = np.zeros((Nn + 1, NK))
    U = np.zeros(N + 1)          # flows at junctions (0 = cords, N = lips)
    P = np.zeros(N)              # pressures in sections
    q = np.zeros(N); qd = np.zeros(N)       # wall states (Uw = qd per section)
    dVf = np.zeros(N)            # the air pushed by moving articulators, smoothed (they have mass: < ~50 Hz)
    kpf = dt / 0.003            # articulators move at ~10-30 Hz; their pushed air carries nothing faster
    Un = np.zeros(Nn + 1)        # nose: 0 = port (from oral section kv), Nn = nostrils
    Pn = np.zeros(Nn)
    qn = np.zeros(Nn); qdn = np.zeros(Nn)
    UL = 0.0; ULn = 0.0          # radiation inductance branches (lips, nostrils)
    wa = 130.0 * np.pi * wall_r
    wb = (30.0 * np.pi) ** 2
    w0sq = (406.0 * np.pi) ** 2 * wall_m ** 2
    wr = 2.0 * np.pi * 1000.0    # boundary-layer loss taken at 1 kHz (sqrt(jw q) -> resistance)
    Aprev = Aor[0].copy()
    A = Aor[0].copy()
    prev_out = 0.0
    png = 0.0                    # turbulence pressure just above the cords (from the previous step)
    nf1 = np.zeros(N + 1); nf2 = np.zeros(N + 1)   # turbulence spectrum: falls above St v / d (two poles), per jet
    gf1 = 0.0; gf2 = 0.0
    for n in range(T):
        f = n / fr_hop
        k0 = int(f)
        if k0 >= F - 1:
            k0 = F - 2
            u = 1.0
        else:
            u = f - k0
        for i in range(N):
            a_ = (1 - u) * Aor[k0, i] + u * Aor[k0 + 1, i]
            A[i] = a_ if a_ > 1e-6 else 1e-6     # a seal (the flow path); volumes below use >= 1e-3
        prt = (1 - u) * port_t[k0] + u * port_t[k0 + 1]
        # ---- flows inside the mouth (momentum): junction j between sections j-1 and j
        for j in range(1, N):
            a1 = A[j - 1]; a2 = A[j]
            L = RHO * (0.5 * dx[j - 1] / a1 + 0.5 * dx[j] / a2)
            q1 = 4.0 * visc * (np.sqrt(3.0 / a1) if area_loss else 1.0)
            q2 = 4.0 * visc * (np.sqrt(3.0 / a2) if area_loss else 1.0)
            sc = RHO * (0.5 * dx[j - 1] / a1 * np.sqrt(q1) + 0.5 * dx[j] / a2 * np.sqrt(q2))
            R = sc * lc0
            lad = 0.0; Rk = 0.0
            for k in range(NK):
                Rk += sc * lck[k]
                lad += sc * lck[k] * iL[j, k]
            Uj = U[j]
            K = 0.0              # jet separation: speed lost when leaving a narrower section
            if Uj > 0 and a2 > a1:
                K = 0.5 * RHO * Uj * (1.0 / (a1 * a1) - 1.0 / (a2 * a2))
            elif Uj < 0 and a1 > a2:
                K = -0.5 * RHO * Uj * (1.0 / (a2 * a2) - 1.0 / (a1 * a1))
            dp = P[j - 1] - P[j]
            if j == 1:
                dp += png
            # turbulence downstream of a gap: Reynolds number of the jet leaving the narrower side
            if gnoise > 0:
                amin = a1 if a1 < a2 else a2
                Re = 2.0 * abs(Uj) / (NU * np.sqrt(np.pi * amin))
                if Re > remax[n]:
                    remax[n] = Re; reidx[n] = j
                wn = np.random.normal()
                fc = 0.2 * (abs(Uj) / amin) / (2.0 * np.sqrt(amin / np.pi))   # eddies' size and speed set the hiss's pitch
                ka = np.exp(-2.0 * np.pi * fc * dt)
                nf1[j] = ka * nf1[j] + (1 - ka) * wn
                nf2[j] = ka * nf2[j] + (1 - ka) * nf1[j]
                if Re > RE_C and ((Uj > 0 and a2 > a1 * 1.05) or (Uj < 0 and a1 > a2 * 1.05)):
                    dp += gnoise * (Re * Re - RE_C * RE_C) * 1e-6 * nf2[j]
            U[j] = (Uj + dt / L * (dp + lad)) / (1.0 + dt * (R + Rk + K) / L)
            for k in range(NK):
                iL[j, k] = (iL[j, k] + dt * lpk[k] * U[j]) / (1.0 + dt * lpk[k])
        # ---- the cords: an opening following his voice, air through it set by the pressure across it
        ag = Ag_t[n]
        dP = Pl_t[n] - P[0]
        png = 0.0
        if ag > 1e-6 and dP > 0:
            ug = ag * np.sqrt(2.0 * dP / RHO)
            if gnoise > 0:   # turbulence just above the cords (his breath), the same law
                Re = 2.0 * ug / (NU * np.sqrt(np.pi * ag))
                fc = 0.2 * (ug / ag) / (2.0 * np.sqrt(ag / np.pi))
                ka = np.exp(-2.0 * np.pi * fc * dt)
                gf1 = ka * gf1 + (1 - ka) * np.random.normal()
                gf2 = ka * gf2 + (1 - ka) * gf1
                if Re > RE_C:
                    png = gnoise * (Re * Re - RE_C * RE_C) * 1e-6 * gf2
        else:
            ug = 0.0
        U[0] = ug
        # ---- lips: radiation load (R parallel L), piston in a sphere
        aL = A[N - 1]
        Rr = 128.0 * RHO * C / (9.0 * np.pi ** 2 * aL)
        Lr = 8.0 * RHO / (3.0 * np.pi * np.sqrt(np.pi * aL))
        Llip = RHO * 0.5 * dx[N - 1] / aL
        U[N] = (U[N] + dt / Llip * (P[N - 1] + Rr * UL)) / (1.0 + dt * Rr / Llip)   # (implicit: stiff when small)
        UL = (UL + dt * Rr * U[N] / Lr) / (1.0 + dt * Rr / Lr)
        # ---- nose: port flow from oral section kv, then the nasal passage
        if prt > 1e-4:
            Lp = RHO * (0.3 / prt + 0.5 * Nas_dx[0] / Nas_a[0])
            Kp = 0.0
            if Un[0] > 0 and Nas_a[0] > prt:
                Kp = 0.5 * RHO * Un[0] * (1.0 / (prt * prt) - 1.0 / (Nas_a[0] * Nas_a[0]))
            elif Un[0] < 0:
                Kp = -0.5 * RHO * Un[0] * (1.0 / (prt * prt))
            Un[0] = (Un[0] + dt / Lp * (P[kv] - Pn[0])) / (1.0 + dt * Kp / Lp)
        else:
            Un[0] = 0.0
        for j in range(1, Nn):
            a1 = Nas_a[j - 1]; a2 = Nas_a[j]
            L = RHO * (0.5 * Nas_dx[j - 1] / a1 + 0.5 * Nas_dx[j] / a2)
            q1 = 4.0 * nose_visc * (np.sqrt(3.0 / a1) if area_loss else 1.0)
            q2 = 4.0 * nose_visc * (np.sqrt(3.0 / a2) if area_loss else 1.0)
            sc = RHO * (0.5 * Nas_dx[j - 1] / a1 * np.sqrt(q1) + 0.5 * Nas_dx[j] / a2 * np.sqrt(q2))
            lad = 0.0; Rk = 0.0
            for k in range(NK):
                Rk += sc * lck[k]
                lad += sc * lck[k] * iLn[j, k]
            Un[j] = (Un[j] + dt / L * (Pn[j - 1] - Pn[j] + lad)) / (1.0 + dt * (sc * lc0 + Rk) / L)
            for k in range(NK):
                iLn[j, k] = (iLn[j, k] + dt * lpk[k] * Un[j]) / (1.0 + dt * lpk[k])
        aN = Nas_a[Nn - 1]
        Lrn = 8.0 * RHO / (3.0 * np.pi * np.sqrt(np.pi * aN))
        Ln = RHO * 0.5 * Nas_dx[Nn - 1] / aN
        Rr0 = 128.0 * RHO * C / (9.0 * np.pi ** 2 * aN)
        Rd = RHO * C / aN * damp                 # the nostril's damping (as in the frequency-domain nose)
        Un[Nn] = (Un[Nn] + dt / Ln * (Pn[Nn - 1] + Rr0 * ULn)) / (1.0 + dt * (Rd + Rr0) / Ln)
        ULn = (ULn + dt * Rr0 * Un[Nn] / Lrn) / (1.0 + dt * Rr0 / Lrn)
        # ---- pressures (mass conservation), walls, articulator pumping
        uw_tot = 0.0
        for i in range(N):
            Ci = (A[i] if A[i] > 1e-3 else 1e-3) * dx[i] / (RHO * C * C)
            # yielding wall: qdd + a qd + b q = Ci w0^2 P   (Uw = qd)
            qdd = Ci * w0sq * P[i] - wa * qd[i] - wb * q[i]
            qd[i] += dt * qdd
            q[i] += dt * qd[i]
            uw_tot += qd[i]
            dV = ((A[i] if A[i] > 1e-3 else 1e-3) - (Aprev[i] if Aprev[i] > 1e-3 else 1e-3)) * dx[i] / dt
            dVf[i] += (dV - dVf[i]) * kpf
            inflow = U[i] - U[i + 1] - qd[i] - pump * dVf[i]
            if i == kv:
                inflow -= Un[0]
            P[i] += dt / Ci * inflow
        for i in range(Nn):
            Ci = Nas_a[i] * Nas_dx[i] / (RHO * C * C)
            qdd = Ci * w0sq * Pn[i] - wa * qdn[i] - wb * qn[i]
            qdn[i] += dt * qdd
            qn[i] += dt * qdn[i]
            Pn[i] += dt / Ci * (Un[i] - Un[i + 1] - qdn[i])
        for i in range(N):
            Aprev[i] = A[i]
        tot = U[N] + Un[Nn] + (uw_tot if walls_rad else 0.0)
        out[n] = (tot - prev_out) * SRT        # radiated sound ~ d/dt of the flow leaving him
        prev_out = tot
        p0[n] = P[0]
    return out, p0, remax, reidx


def head_filter(y, radius_cm, sr):
    """The small round head (ee_bunfit.head_baffle: H = (1+s)/(2+s), s = j w a / c), bilinear."""
    from scipy.signal import bilinear, lfilter
    tau = radius_cm / C
    b, a = bilinear([tau, 1.0], [tau, 2.0], fs=sr)
    return lfilter(b, a, y)


def to48(y):
    from scipy.signal import resample_poly
    return resample_poly(y, 1, SRT // 48000)
