"""Turn the tuned state into a side-by-side for Da Boss: per phrase, the clip then the model (equal loudness
over his voiced sounds; one fixed gain per piece, nothing else done to the sound).

    python make_listen.py reference/archive/NAME.wav [models/perc_state.json] [--prev other_state.json]
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perc as P  # noqa: E402
import transitions as TRm  # noqa: E402

out = sys.argv[1]
states = [a for a in sys.argv[2:] if not a.startswith("--")] or ["models/perc_state.json"]
ys = []
for sp in states:
    st = json.loads((P.ROOT / sp).read_text())
    z = np.array(st["z"]); P.CN.CP.update(st["cp"]); TRm.Z[:] = z
    y, _ = P.render(z, st["tp"]); ys.append(y)
SR = P.SR; gap = np.zeros(int(0.6 * SR)); pieces = []
for (a, b), ph in zip(P.PHR, P.R.PHRASES):
    vs = [(s, e) for l, s, e, _ in ph if l in P.M.SOUNDS]
    xs = P.X[int(a * SR): int(b * SR)]; rx = np.sqrt(np.mean(np.concatenate([P.X[int(s * SR): int(e * SR)] for s, e in vs]) ** 2))
    segs = [xs]
    for y in ys:
        ym = y[int(a * SR): int(b * SR)]; ry = np.sqrt(np.mean(np.concatenate([y[int(s * SR): int(e * SR)] for s, e in vs]) ** 2))
        segs.append(ym * rx / ry)
    k = 0.7 / max(np.abs(s_).max() for s_ in segs)
    for s_ in segs:
        pieces += [s_ * k, gap]
    pieces += [gap]
sf.write(P.ROOT / out, np.concatenate(pieces), SR)
print("wrote", out)
