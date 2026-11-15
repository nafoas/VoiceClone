"""Watch his little mouth say the clip: the fitted mouth trajectory drawn
frame by frame, with the clip's spectrogram and a cursor, and the audio.

    python scripts/bun_animate.py [--audio rebuild|clip]  -> out/bunmouth/mouth_clip.mp4
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from prince_voice.bunmouth import BunMouth, Pose, draw, NAMES  # noqa: E402
import iterate as I  # noqa: E402

FPS = 25


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--audio", default="rebuild")
    a = ap.parse_args()
    z = np.load(ROOT / "models/bun_trajectory.npz")
    m = BunMouth(float(z["size"]), neck_mm=float(z["neck"]) if "neck" in z else 0.0)
    SR = I.SR
    if a.audio == "rebuild":
        y, _ = sf.read(ROOT / "out/bunmouth/rebuild.wav")
    else:
        ref = I.reference(); pause = np.zeros(int(0.34 * SR))
        y = np.concatenate([ref[int(z["t0"] * SR): int(z["t0"] * SR) + len(z["Z0"]) * 120], pause,
                            ref[int(z["t1"] * SR): int(z["t1"] * SR) + len(z["Z1"]) * 120]])
    # pose track on the rebuild's timeline (5 ms frames; the pause holds a rest pose)
    rest = Pose(jaw=0.15, lips=0.3, velum=0.6).vec()
    Z = np.vstack([z["Z0"], np.tile(rest, (int(0.34 * 200), 1)), z["Z1"]])
    dur = len(y) / SR
    tmp = Path(tempfile.mkdtemp())
    fig = plt.figure(figsize=(9, 7.2))
    axm = fig.add_axes([0.02, 0.28, 0.62, 0.70]); axb = fig.add_axes([0.66, 0.30, 0.32, 0.62])
    axs = fig.add_axes([0.06, 0.05, 0.9, 0.2])
    axs.specgram(y, NFFT=512, Fs=SR, noverlap=384, cmap="magma"); axs.set_ylim(0, 6000)
    axs.set_yticks([0, 2000, 4000, 6000]); axs.set_xlabel("s"); cur = axs.axvline(0, color="c", lw=2)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS; k = min(len(Z) - 1, int(t * 200))
        p = Pose.from_vec(Z[k])
        axm.clear(); draw(axm, m, p, f"Prince's mouth   t = {t:.2f} s"); axm.set_xlim(-60, 130); axm.set_ylim(-90, 110)
        axb.clear(); v = p.vec()
        axb.barh(range(len(NAMES)), v, color=["#e58c9a" if x >= 0 else "#8ab" for x in v])
        axb.set_yticks(range(len(NAMES))); axb.set_yticklabels(NAMES); axb.set_xlim(-1, 1); axb.invert_yaxis()
        axb.set_title("articulators", fontsize=9)
        cur.set_xdata([t, t])
        fig.savefig(tmp / f"f{i:05d}.png", dpi=80)
    plt.close(fig)
    wav = tmp / "a.wav"; sf.write(wav, y, SR)
    out = ROOT / "out/bunmouth" / f"mouth_{a.audio}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png"),
                    "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-c:a", "aac", "-shortest", str(out)], check=True)
    print(out)


if __name__ == "__main__":
    main()
