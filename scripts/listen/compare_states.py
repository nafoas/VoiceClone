"""Score saved states under the current objective; write the best to out/listen/perc_state.json."""
import json, sys, shutil
FILES = sys.argv[1:]
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import perc as P
import transitions as TRm
best = None
for f in FILES:
    st = json.loads(Path(f).read_text()); z = np.array(st["z"]); P.CN.CP.update(st["cp"]); TRm.Z[:] = z
    y, sp = P.render(z, st["tp"]); o = P.judge(y, sp); J = P.objective(o)
    print(f"{f}: MOS {o['mos']:.2f} timbre {o['timbre']:.2f} objective {J:.3f} diction {o['diction']:.3f} worst {o['diction_worst']:.3f} age {o['age']:.1f} speaker {o['speaker']:.3f} warmth {o['warmth']:+.2f} env {o['envelope']:.2f}", flush=True)
    if best is None or J < best[0]:
        best = (J, f)
shutil.copy(best[1], P.ROOT / "out/listen/perc_state.json"); print("best:", best[1])
