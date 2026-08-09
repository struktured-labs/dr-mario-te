#!/usr/bin/env python
"""decode_census.py — classify per-pill intended-vs-landed records from census_run.lua.

Input: census.csv rows (raw facts only; all semantics live HERE so they are gate-able).

Committed placement = (ccol, co4) in COPRO space, served by the harness's own mailbox
(we ARE the copro, so the committed placement is known exactly):
  o4: 0 = Vertical A-top, 1 = Vertical B-top, 2 = Horizontal A-left, 3 = Horizontal B-left
  (decide_ship_d3 / gen_m3_hostdata convention; colors cA/cB are 0-based ids from
  $0381/$0382, the exact bytes the driver uploads to $5080/$5081).
Driver copro->game orient map (patch_cartridge_copro.py handle()/nf2): {0:3, 1:1, 2:0, 3:2}
with game $03A5: 0=H, 1=Vccw, 2=Hrev, 3=Vcw. Logged tgtO lets us cross-check adoption.

Landed placement = board delta at lock (newcells "r:c:XX;..."), decoded via the NES tile
encoding: high nibble 4=V-top, 5=V-bottom, 6=H-left, 7=H-right; low nibble = 0-based color.

Classes (precedence: orientation-class flip > color-order flip > column > match):
  b  = vertical landed where a horizontal was committed ("nonsensical vertical")
  d  = horizontal landed where a vertical was committed (wrong orientation class)
  c  = same orientation class, REVERSED color order ("backward" = 180 rotation-phase
       error); subtags c_horiz / c_vert; column error tracked alongside
  a  = wrong column, orientation + color order kept
  e  = match
Same-color pills (cA==cB) cannot express a color-order flip (and a flip would be
harmless); they are classified on geometry only and counted in `amb`.

--mutant swapped-colors: decodes landed color order against (cB,cA) instead of (cA,cB).
KILL CRITERION: on real data it must flag ~100% of non-ambiguous class-(e) pills as (c).
"""
import argparse, csv, math, sys
from collections import Counter, defaultdict

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    den = 1 + z*z/n
    ctr = p + z*z/(2*n)
    adj = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((ctr-adj)/den, (ctr+adj)/den)

def parse_cells(s):
    out = []
    if not s: return out
    for part in s.split(";"):
        if not part: continue
        r, c, b = part.split(":")
        out.append((int(r), int(c), int(b, 16)))
    return out

def decode_landed(cells):
    """-> dict(kind='V'|'H', col, first, second) or None.
    V: first=top color, second=bottom color. H: first=left, second=right."""
    if len(cells) != 2: return None
    (r1, c1, b1), (r2, c2, b2) = sorted(cells, key=lambda t: (t[0], t[1]))
    n1, n2 = b1 >> 4, b2 >> 4
    if c1 == c2 and r2 == r1 + 1:
        if (n1, n2) != (0x4, 0x5): return None
        return dict(kind='V', col=c1, first=b1 & 0xF, second=b2 & 0xF)
    if r1 == r2 and c2 == c1 + 1:
        if (n1, n2) != (0x6, 0x7): return None
        return dict(kind='H', col=c1, first=b1 & 0xF, second=b2 & 0xF)
    return None

CG_MAP = {0: 3, 1: 1, 2: 0, 3: 2}   # copro o4 -> game $03A5

def classify(row, mutant_swap=False, mutant_col=False):
    ccol, co4 = int(row['ccol']), int(row['co4'])
    cA, cB = int(row['cA']), int(row['cB'])
    if mutant_swap:
        cA, cB = cB, cA
    if mutant_col and ccol >= 0:
        ccol = ccol + 1
    cells = parse_cells(row['newcells'])
    landed = decode_landed(cells)
    if landed is None:
        return ('undecodable', {})
    if ccol < 0 or co4 < 0:
        return ('nocommit', {'landed': landed})
    ckind = 'V' if co4 in (0, 1) else 'H'
    amb = (cA == cB)
    info = {'landed': landed, 'amb': amb, 'colerr': landed['col'] - ccol}
    if landed['kind'] != ckind:
        return (('b' if landed['kind'] == 'V' else 'd'), info)
    # same orientation class: committed color order in landed's (first,second) sense
    if ckind == 'V':
        want = (cA, cB) if co4 == 0 else (cB, cA)
    else:
        want = (cA, cB) if co4 == 2 else (cB, cA)
    got = (landed['first'], landed['second'])
    if not amb and got == (want[1], want[0]):
        return (('c_vert' if ckind == 'V' else 'c_horiz'), info)
    if not amb and got != want:
        return ('colormix', info)     # neither order matches -> wrong pill colors entirely
    if landed['col'] != ccol:
        return ('a', info)
    return ('e', info)

def phase(vc):
    return 'open(vc>32)' if vc > 32 else ('mid(9-32)' if vc >= 9 else 'end(<=8)')

def hbin(h):
    return '0-3' if h <= 3 else ('4-6' if h <= 6 else ('7-9' if h <= 9 else '10+'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+')
    ap.add_argument('--mutant', choices=['swapped-colors', 'col-off1'], default=None)
    ap.add_argument('--per-pill', action='store_true', help='print one line per pill')
    args = ap.parse_args()

    rows = []
    for path in args.csvs:
        with open(path) as f:
            for row in csv.DictReader(f):
                rows.append(row)
    ok = [r for r in rows if r['flag'] in ('ok', 'latecatch')]
    other = Counter(r['flag'] for r in rows if r['flag'] not in ('ok', 'latecatch'))

    cls = Counter(); byphase = defaultdict(Counter); byh = defaultdict(Counter)
    amb_n = 0; colerr_c = Counter(); details = []
    for r in ok:
        k, info = classify(r, mutant_swap=(args.mutant == 'swapped-colors'),
                           mutant_col=(args.mutant == 'col-off1'))
        cls[k] += 1
        if info.get('amb'): amb_n += 1
        if k in ('c_horiz', 'c_vert'): colerr_c[info['colerr']] += 1
        byphase[phase(int(r['vc_go']))][k] += 1
        byh[hbin(int(r['h_go']))][k] += 1
        details.append((r, k, info))
        if args.per_pill:
            li = info.get('landed')
            ls = f"{li['kind']}@{li['col']} {li['first']}{li['second']}" if li else "-"
            print(f"seq={r['seq']:>4} rnd={r['round']} cA={r['cA']} cB={r['cB']} "
                  f"commit=({r['ccol']},{r['co4']}) tgt=({r['tgtC']},{r['tgtO']}) "
                  f"landed={ls} h={r['h_go']} vc={r['vc_go']} -> {k}")

    n = len(ok)
    dec = n - cls['undecodable'] - cls['nocommit']
    print(f"\n== decode_census {'MUTANT=' + args.mutant if args.mutant else ''} ==")
    print(f"rows={len(rows)} locked-ok={n} decodable={dec} same-color(amb)={amb_n} "
          f"other-flags={dict(other)}")
    order = ['e', 'a', 'b', 'c_horiz', 'c_vert', 'd', 'colormix', 'nocommit', 'undecodable']
    for k in order:
        v = cls.get(k, 0)
        if dec:
            lo, hi = wilson(v, dec)
            print(f"  {k:12s} {v:5d}  {100*v/dec:6.2f}%  CI95 [{100*lo:.2f}, {100*hi:.2f}]")
    if colerr_c:
        print(f"  column-error distribution among class-c: {dict(sorted(colerr_c.items()))}")
    # cross-check: driver's adopted game-space target vs our served copro result
    xmap = Counter()
    for r, k, info in details:
        if int(r['co4']) >= 0 and int(r['tgtO']) >= 0:
            xmap['tgtO==map(co4)' if int(r['tgtO']) == CG_MAP[int(r['co4'])]
                 else 'tgtO!=map(co4)'] += 1
        if int(r['ccol']) >= 0 and int(r['tgtC']) >= 0:
            xmap['tgtC==ccol' if int(r['tgtC']) == int(r['ccol']) else 'tgtC!=ccol'] += 1
    print(f"  driver-adoption cross-check: {dict(xmap)}")
    print("\n-- by game phase (virus count at GO) --")
    for ph in ('open(vc>32)', 'mid(9-32)', 'end(<=8)'):
        c = byphase.get(ph)
        if not c: continue
        d = sum(v for kk, v in c.items() if kk not in ('undecodable', 'nocommit'))
        mm = d - c.get('e', 0)
        print(f"  {ph:12s} n={d:5d} mismatch={mm:4d} ({100*mm/d if d else 0:5.2f}%)  " +
              " ".join(f"{kk}={c[kk]}" for kk in order if c.get(kk)))
    print("-- by board height at GO --")
    for hb in ('0-3', '4-6', '7-9', '10+'):
        c = byh.get(hb)
        if not c: continue
        d = sum(v for kk, v in c.items() if kk not in ('undecodable', 'nocommit'))
        mm = d - c.get('e', 0)
        print(f"  h={hb:5s} n={d:5d} mismatch={mm:4d} ({100*mm/d if d else 0:5.2f}%)  " +
              " ".join(f"{kk}={c[kk]}" for kk in order if c.get(kk)))

if __name__ == '__main__':
    main()
