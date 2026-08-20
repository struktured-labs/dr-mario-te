#!/usr/bin/env python3
"""score_rows.py -- offline scorer for the sileval A/B (PREREG_SLICE_SILICON.md).

Pure read pass over OUT_DIR: never touches hardware. For every row it decodes the
sampled save-states with the vendored seedjit_ss module (signature-located RAM
base -- never hardcoded) and emits a per-sample timeline CSV:

  seed,arm,sample,mode,virus_p1,virus_p2,occ_top3_p1,occ_top3_p2

virus counters are BCD (the on-screen digits) and are decoded, not raw-compared.
occ_top3_* = occupied cells in playfield rows 0-2 (the prereg's NEAR-DEATH key).

Match-winner adjudication (E1) and the McNemar read run on this CSV + the
end-of-cycle screenshots, per the prereg's reading rule; matches that cannot be
adjudicated are counted UNREADABLE, never dropped silently.
"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))
import seedjit_ss  # noqa: E402

def bcd(x): return (x >> 4) * 10 + (x & 0x0F)

def occ_top3(blob, base, board):
    off = base + board
    return sum(1 for r in range(3) for c in range(8) if blob[off + r * 8 + c] != 0xFF)

def main(out_dir):
    out_dir = Path(out_dir)
    w = csv.writer(sys.stdout)
    w.writerow(["seed", "arm", "sample", "mode", "virus_p1", "virus_p2",
                "occ_top3_p1", "occ_top3_p2"])
    unreadable = 0
    for row_file in sorted((out_dir / "rows").glob("*.json")):
        row = json.loads(row_file.read_text())
        if row.get("status") != "OK":
            continue
        adir = out_dir / "artifacts" / f"{row['seed']}_{row['arm']}"
        for ss in sorted(adir.glob("s*.ss")):
            blob = ss.read_bytes()
            try:
                base = seedjit_ss.find_base(blob)
            except Exception:
                unreadable += 1
                continue
            w.writerow([row["seed"], row["arm"], ss.stem,
                        f"{blob[base + seedjit_ss.MODE]:02x}",
                        bcd(blob[base + 0x324]), bcd(blob[base + 0x3A4]),
                        occ_top3(blob, base, 0x400), occ_top3(blob, base, 0x500)])
    print(f"# unreadable_samples={unreadable}", file=sys.stderr)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "out")
