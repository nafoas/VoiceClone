"""His vocal folds as VocalTractLab's self-oscillating triangular glottis, bun-sized (roadmap Step 2).

make_speaker(static, path): writes a speaker file from models/bun.speaker with the triangular glottis
selected and its static parameters set (lower limits opened for bun sizes: folds of a few mm and mg).
"""
import re

BUN_TRI = dict(COL=0.40, LRT=0.12, URT=0.03, LRM=0.006, URM=0.0015, LDR=0.1, UDR=0.6,
               LSK=15000.0, USK=1500.0, LCK=45000.0, UCK=4500.0, CSK=4800.0, IL=0.02, OL=0.005,
               NF0=300.0, dF0=300.0)
MINS = dict(COL=0.15, LRT=0.03, URT=0.005, LRM=0.0005, URM=0.0001)
CONTROL = ["F0", "PR", "XB", "XT", "AA", "AS"]


def make_speaker(static, path, base="models/bun.speaker"):
    s = open(base).read()
    s = s.replace('<glottis_model type="Geometric glottis" selected="1">', '<glottis_model type="Geometric glottis" selected="0">')
    s = s.replace('<glottis_model type="Triangular glottis" selected="0">', '<glottis_model type="Triangular glottis" selected="1">')
    i = s.index('<glottis_model type="Triangular glottis"'); j = s.index('</static_params>', i)
    block = s[i:j]
    for n, v in static.items():
        m = re.search(rf'<param index="\d+"\s+name="{re.escape(n)}".*?/>', block)
        p = m.group(0)
        p = re.sub(r'neutral="[^"]*"', f'neutral="{v:.6f}"', p)
        if n in MINS:
            p = re.sub(r'min="[^"]*"', f'min="{MINS[n]:.6f}"', p)
        block = block.replace(m.group(0), p, 1)
    s = s[:i] + block + s[j:]
    open(path, "w").write(s)
    return path
