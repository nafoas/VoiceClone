"""Render a mouth (perc state or mouth_inverse z + a state's movements) and check its consonants.

    GEST=1 python cons_eval.py STATE.json [ZFILE.json] [--save out.npy] [--recog]
  STATE: a perc state (z, tp, cp, size); ZFILE: replace its z with this fitted mouth
"""
import json
import os
import sys

ARGS = sys.argv[1:]
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import perc as P  # noqa: E402
import cons_check as C  # noqa: E402

st = json.load(open(ARGS[0]))
pos = [a for i, a in enumerate(ARGS[1:], 1) if not a.startswith("--") and ARGS[i - 1] != "--save"]
if pos:
    _j = json.load(open(pos[0])); st["z"] = _j["z"]
    if "rest" in _j:
        st["rest"] = _j["rest"]
z = P.load_state(st); z = P.M.pad(z)
for k in [k for k in os.environ if k.startswith("CN_")]:   # consonant settings to try, e.g. CN_ASP_AG=0.03
    setattr(P.CN, k[3:], float(os.environ[k]))
y, sp = P.render(z, st["tp"])
print(f"whole-phrase spectral likeness {sp:.2f} dB")
res = C.report(y, P.X)
if "--save" in ARGS:
    np.save(ARGS[ARGS.index("--save") + 1], y)
if "--recog" in ARGS:
    j = P.judge(y, sp, detail=True)
    print(f"recogniser (secondary): diction {j['diction']:.3f}  speaker {j['speaker']:.3f}  MOS {j['mos']:.2f}")
    for k, v in j["heard"].items():
        print(f"    {k:9} heard {v}")
