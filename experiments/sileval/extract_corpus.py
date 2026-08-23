#!/usr/bin/env python3
"""extract_corpus.py -- cache the RAM window of every sampled save-state.

Speed: find_base() scans the whole 1.3 MB blob per file, which makes a
corpus-wide pass crawl. The base is empirically constant (0x102b08 across a
random sample), so we USE that but VERIFY it per file via the same NAV_MAGIC
signature find_base keys on -- never trusting the constant blindly. Any file
that fails verification falls back to the full scan; any file that fails both
is recorded as undecodable, never silently skipped.
"""
import pickle, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
import seedjit_ss

FAST_BASE = 0x102B08
WIN = 0x2800            # internal RAM (0x800) + 8K cart WRAM
def bcd(x): return (x >> 4) * 10 + (x & 0x0F)

def base_of(blob):
    b = FAST_BASE
    if 0 <= b and b + WIN <= len(blob) and blob[b + 0x800 + seedjit_ss.NAV_MAGIC_ADDR] == seedjit_ss.NAV_MAGIC:
        return b
    try:
        return seedjit_ss.find_base(blob)
    except BaseException:
        return None

def main(out_dir, cache):
    out_dir = Path(out_dir)
    rows = {}
    import json
    ok = [json.loads(f.read_text()) for f in out_dir.glob("rows/*.json")]
    ok = [r for r in ok if r.get("status") == "OK"]
    for i, r in enumerate(ok):
        key = (r["seed"], r["arm"])
        adir = out_dir / "artifacts" / f"{r['seed']}_{r['arm']}"
        samples = []
        for ss in sorted(adir.glob("s*.ss")):
            blob = ss.read_bytes()
            b = base_of(blob)
            if b is None:
                samples.append(None)          # undecodable, POSITION PRESERVED
                continue
            w = bytes(blob[b:b + WIN])
            samples.append({
                "name": ss.stem, "mode": w[seedjit_ss.MODE],
                "vp1": bcd(w[0x324]), "vp2": bcd(w[0x3A4]),
                "lvl1": w[0x316], "lvl2": w[0x396],
                "win": w,
            })
        rows[key] = samples
        if i % 40 == 0: print(f"  {i}/{len(ok)}", flush=True)
    Path(cache).write_bytes(pickle.dumps(rows))
    n = sum(len(v) for v in rows.values())
    u = sum(1 for v in rows.values() for s in v if s is None)
    print(f"cached rows={len(rows)} samples={n} undecodable={u} ({100*u/n:.1f}%) -> {cache}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
