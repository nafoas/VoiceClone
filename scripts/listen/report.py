"""What a listener-model hears in the current best state (per sound), and its scores."""
import json, sys
from pathlib import Path
import numpy as np, soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parent))
import perc as P
import transitions as TRm
st = json.loads((P.ROOT / "models/perc_state.json").read_text())
z = np.array(st["z"]); P.CN.CP.update(st["cp"]); TRm.Z[:] = z
y, sp = P.render(z, st["tp"]); o = P.judge(y, sp, detail=True)
print({k: round(v, 3) for k, v in o.items() if isinstance(v, float)}, "objective", round(P.objective(o), 3), "| clip age", round(P.AGE_CLIP, 1))
for k in o["heard"]:
    print(f"  {k:10} JS {o['per_sound'][k]:.2f}  heard {o['heard'][k]}")
if len(sys.argv) > 1:
    sf.write(sys.argv[1], y / np.abs(y).max() * 0.7, P.SR)
