#!/usr/bin/env python3
"""Compare two probe_final.lua runs (stock vs DRSTUDYEND) frame by frame.

  usage: compare_final.py <out_dir> <stock_tag> <flag_tag>

Reads <tag>_frames.txt (per frame: frame mode ramhash prgramhash maskedhash, plus full `R frame hex` rows from the
match-final screen on) and <tag>_final.log (MODE transitions). Prints:
  - whether mode transitions are identical (= matched START timing and identical flow);
  - the first frame the $0000-$07FF hash differs, and whether PRG-RAM ever differs;
  - every frame OUTSIDE the end screens (mode 5/7 and the START->level-init walk) whose RAM differs beyond the
    DRNMITMP pad-read scratch $BF/$C7 and the stack page (around SP at end-of-frame sit the NMI's pushed return
    address/flags, i.e. which instruction the main loop was on when the NMI landed: CPU phase, not game state);
  - in the full-RAM window: when the fields, OAM shadow, $55/$61 and everything else last differ, the frame from which
    $0000-$07FF is identical except those single-frame $BF/$C7/stack-page blips, and victories at the next match.
Exit 1 if play frames before the final differ beyond the scratch, or the next match does not converge.
"""
import sys

out, a_tag, b_tag = sys.argv[1], sys.argv[2], sys.argv[3]


def load(tag):
    H, R = {}, {}
    for line in open(f"{out}/{tag}_frames.txt"):
        if line.startswith("R "):
            _, f, h = line.split()
            R[int(f)] = bytes.fromhex(h)
        else:
            f, mode, h, g, m = line.split()
            H[int(f)] = (int(mode), h, g, m)
    modes = [l for l in open(f"{out}/{tag}_final.log") if l.startswith("MODE")]
    return H, R, modes


aH, aR, aM = load(a_tag)
bH, bR, bM = load(b_tag)
ok = True
print(f"mode transitions identical: {aM == bM}  ({len(aM)} transitions)")
ok &= aM == bM
n = min(max(aH), max(bH))
ram = [f for f in range(1, n + 1) if aH[f][1] != bH[f][1]]
prg = [f for f in range(1, n + 1) if aH[f][2] != bH[f][2]]
print(f"frames {n}; first $0000-$07FF difference at f{ram[0] if ram else None}; PRG-RAM differs on {len(prg)} frames")
# end-screen windows: from each mode-5 entry until the next mode-4 entry (end screen + menus + level init)
ends, lo = [], None
for f in range(1, n + 1):
    m = aH[f][0]
    if m in (5, 7) and lo is None:
        lo = f
    if m == 4 and lo is not None:
        ends.append((lo, f + 2)); lo = None
if lo is not None:
    ends.append((lo, n))
inside = lambda f: any(a <= f <= b for a, b in ends)
masked = [f for f in range(1, n + 1) if aH[f][3] != bH[f][3] and not inside(f)]
blips = [f for f in range(1, n + 1) if aH[f][1] != bH[f][1] and aH[f][3] == bH[f][3]]
print(f"end-screen windows (mode 5 .. next play+2): {ends}")
print(f"play frames differing beyond $BF/$C7 + stack page: {masked[:20]}{' ...' if len(masked) > 20 else ''} ({len(masked)})")
print(f"frames differing ONLY in $BF/$C7 / stack page: {len(blips)}  e.g. {blips[:8]}")
ok &= not masked
if aR:
    fr = sorted(set(aR) & set(bR))
    def region(i):
        if i < 0x100: return "zp"
        if i < 0x200: return "stack"
        if i < 0x300: return "OAM shadow"
        if 0x400 <= i < 0x600: return "fields"
        return "other"
    last, d = {}, {}
    for f in fr:
        d[f] = [i for i in range(0x800) if aR[f][i] != bR[f][i]]
        for i in d[f]:
            key = "$55/$61" if i in (0x55, 0x61) else region(i)
            last[key] = f
    noise = {0xBF, 0xC7} | set(range(0x100, 0x200))
    conv = next((f for f in fr if all(set(d[g]) <= noise for g in fr if g >= f)), None)
    nxt = [int(l.split()[1][2:]) for l in aM if l.split()[2].endswith("->4")][-1]
    print(f"full-RAM window f{fr[0]}..f{fr[-1]}: last difference per region {last}")
    print(f"$0000-$07FF identical from f{conv} except single-frame $BF/$C7/stack-page blips; next match play from f{nxt}")
    print(f"victories P1/P2 at next-match play: stock {aR[nxt][0x31E]}/{aR[nxt][0x39E]}  flag {bR[nxt][0x31E]}/{bR[nxt][0x39E]}")
    ok &= conv is not None and conv <= nxt
print("COMPARE_PASS" if ok else "COMPARE_FAIL")
sys.exit(0 if ok else 1)
