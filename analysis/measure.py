"""Voice-quality measurements used to compare candidates with the reference.
    python analysis/measure.py file.wav [file2.wav ...]"""
import sys, numpy as np, soundfile as sf, pyworld as pw

def stats(path):
    a, sr = sf.read(path)
    if a.ndim > 1: a = a.mean(1)
    a = a.astype(float)
    f0, t = pw.harvest(a, sr, frame_period=5, f0_floor=80, f0_ceil=1200)
    sp = pw.cheaptrick(a, f0, t, sr); ap = pw.d4c(a, f0, t, sr)
    fq = np.linspace(0, sr / 2, sp.shape[1]); e = 10 * np.log10(sp.sum(1) + 1e-20)
    v = (f0 > 0) & (e > np.percentile(e, 40))
    h12, tilt = [], []
    for k in np.where(v)[0]:
        h = [10 * np.log10(np.interp(f0[k] * n, fq, sp[k]) + 1e-20) for n in range(1, 9)]
        h12.append(h[0] - h[1]); tilt.append(np.polyfit(np.log2(np.arange(1, 9)), h, 1)[0])
    P = sp[v]; vf = f0[v]
    return dict(f0=np.median(vf), span=12 * np.log2(np.percentile(vf, 90) / np.percentile(vf, 10)),
                h12=np.median(h12), tilt=np.median(tilt), cent=np.median((P * fq).sum(1) / P.sum(1)),
                ap=ap[v][:, (fq > 300) & (fq < 4000)].mean(), voiced=np.mean(f0 > 0) * 100)

if __name__ == "__main__":
    print(f"{'':28} f0Hz  span  H1-H2  tilt  centroid  aperiod  voiced%")
    for p in sys.argv[1:]:
        s = stats(p)
        print(f"{p[-28:]:28} {s['f0']:4.0f} {s['span']:5.1f} {s['h12']:6.1f} {s['tilt']:6.1f} {s['cent']:8.0f} {s['ap']:8.2f} {s['voiced']:7.0f}")
