#!/usr/bin/env python
"""annotate_gate.py — overlay decoded landed cells + committed placement on lock shots.
P2 bottle playfield origin (measured from lock_001): col c -> x = 160 + 8c, row r -> y = 72 + 8r.
Green box = decoded landed cell (from newcells RAM delta). Cyan box = committed placement
cells (from served ccol/co4 + colors), drawn at the landed row for comparison of col/orient.
Caption: seq, cA/cB, committed (col,o4), decoded class.
"""
import csv, glob, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode_census import parse_cells, decode_landed, classify

X0, Y0, CS = 160, 72, 8
GATE = sys.argv[1] if len(sys.argv) > 1 else 'logs/gate1'
rows = {r['seq']: r for r in csv.DictReader(open(os.path.join(GATE, 'census.csv')))}
outdir = os.path.join(GATE, 'annotated'); os.makedirs(outdir, exist_ok=True)

for path in sorted(glob.glob(os.path.join(GATE, 'lock_*.png'))):
    seq = str(int(os.path.basename(path).split('_')[1]))
    r = rows[seq]
    cells = parse_cells(r['newcells'])
    landed = decode_landed(cells)
    k, info = classify(r)
    im = Image.open(path).convert('RGB').resize((256 * 3, 240 * 3), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    for (rr, cc, b) in cells:
        x, y = (X0 + CS * cc) * 3, (Y0 + CS * rr) * 3
        dr.rectangle([x, y, x + CS * 3 - 1, y + CS * 3 - 1], outline=(0, 255, 0), width=2)
    # committed cells (cyan), drawn at landed row(s) for visual col/orient comparison
    ccol, co4 = int(r['ccol']), int(r['co4'])
    if landed and ccol >= 0:
        base_r = min(c[0] for c in cells)
        if co4 in (0, 1):
            com = [(base_r, ccol), (base_r + 1, ccol)] if landed['kind'] == 'V' else [(base_r, ccol), (base_r - 1, ccol)]
        else:
            com = [(base_r if landed['kind'] == 'H' else base_r + 1, ccol),
                   (base_r if landed['kind'] == 'H' else base_r + 1, ccol + 1)]
        for (rr, cc) in com:
            x, y = (X0 + CS * cc) * 3 + 3, (Y0 + CS * rr) * 3 + 3
            dr.rectangle([x, y, x + CS * 3 - 7, y + CS * 3 - 7], outline=(0, 255, 255), width=1)
    cap = (f"seq={seq} cA={r['cA']} cB={r['cB']} commit=({r['ccol']},{r['co4']}) "
           f"landed={landed['kind']}@{landed['col']} {landed['first']}{landed['second']}"
           if landed else f"seq={seq} UNDECODABLE") + f" -> {k}"
    dr.rectangle([0, 0, 768, 14], fill=(0, 0, 0))
    dr.text((4, 2), cap, fill=(255, 255, 255))
    im.save(os.path.join(outdir, os.path.basename(path)))
    print(os.path.basename(path), cap)
print("annotated ->", outdir)
