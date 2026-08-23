#!/usr/bin/env python3
"""e1_winner.py -- E1 PRIMARY endpoint reader: per-match winners, from RAM.

Supersedes match1_winner.py, whose virus-counter rule returned UNREADABLE on ~99%
of matches because a 20 s sampler steps over the ~3 s game-over screen.  This
reader does not need to LAND on the match ending at all: it reads two quantities
that PERSIST across it.

WHERE THE BYTES COME FROM (stock ROM, disassembled at L9532_TOP_5 / $9532):

    $9532 LDA $0309 / BNE -> INC $031E      ; P1 did not top out -> P1 wins
    $955F LDA $0389 / BNE -> INC $039E      ; P2 did not top out -> P2 wins
          ... STA $61                       ; result code 1=P1 lost, 2=P2 lost, 0=both
    $9585 LDA #$07 / STA $46                ; then, and only then, mode := 7

  $0309 / $0389  per-player TOPPED-OUT flag   (live only during modes 5/7)
  $031E / $039E  per-player VS WIN COUNTER    (persists into the next match;
                 both are zeroed when one reaches 3 -- the best-of-3 set reset)
  $0061          TOP_5 result code            (live only during modes 5/7)

  $6200..$62C6   the cart's own DRPROBE mode-transition ring (patch_cartridge_copro.py
                 :1020).  Append-only, 3-byte records (mode,$0727,$04) written ON CHANGE.
                 $62C0 = write index, $62C1/$62C2 = 16-bit change count, $62C6 = magic $54.
                 Exactly ONE record with mode==5 is appended per match end, so the ring
                 gives an EXACT, cadence-independent count of matches completed.

METHOD.  Between two consecutive samples, the ring says how many matches ended (m)
and the win counters say who won them (d1,d2).  The adjudication is accepted only if
d1+d2 == m.  That equality is a built-in validity gate, not a formality: it is what
makes a wiped or mirrored counter report UNREADABLE instead of a plausible-looking 0.

The RAM base is located by a 2-anchor signature (ring magic $62C6==$54 AND nav magic
$6149==$A5), never a hardcoded offset; 400/400 population-A samples resolve uniquely.
"""
import collections, glob, json, os, sys

RING_MAGIC_OFF, RING_MAGIC = 0x2c6, 0x54     # $62C6 relative to cart WRAM $6000
NAV_MAGIC_OFF, NAV_MAGIC = 0x149, 0xA5       # $6149
IRAM = 0x800                                  # internal RAM precedes cart WRAM
MODE, RES = 0x46, 0x61
TOP1, TOP2, WIN1, WIN2 = 0x309, 0x389, 0x31e, 0x39e
RING = 0x200


def find_base(blob):
    """Offset of NES $0000 inside the .ss. Raises unless exactly one hit."""
    hits = {w - IRAM for w in range(IRAM, len(blob) - 0x2000)
            if blob[w + RING_MAGIC_OFF] == RING_MAGIC and blob[w + NAV_MAGIC_OFF] == NAV_MAGIC}
    match len(hits):
        case 1: return hits.pop()
        case n: raise ValueError(f"expected 1 RAM base, found {n}")


def match_ends(blob, base):
    """Matches completed so far = count of mode==5 (TOP_5) records in the ring."""
    w = base + IRAM
    n = blob[w + 0x2c1] | (blob[w + 0x2c2] << 8)
    off = blob[w + 0x2c0]
    return sum(1 for k in range(min(n, off // 3)) if blob[w + RING + 3 * k] == 5)


def read_row(adir):
    """-> dict(p1=, p2=, intervals=[...], unreadable=[...], witnesses=[...])"""
    S = []
    for f in sorted(glob.glob(os.path.join(adir, "s*.ss"))):
        blob = open(f, "rb").read()
        try:
            base = find_base(blob)
        except ValueError as exc:
            S.append((os.path.basename(f), None, str(exc)))
            continue
        S.append((os.path.basename(f), blob, base))
    good = [(nm, b, base) for nm, b, base in S if b is not None]
    out = dict(samples=len(S), undecodable=len(S) - len(good),
               p1=0, p2=0, intervals=[], unreadable=[], witnesses=[])
    for i in range(1, len(good)):
        (_, pb, pB), (nm, cb, cB) = good[i - 1], good[i]
        m = match_ends(cb, cB) - match_ends(pb, pB)
        if m <= 0:
            continue
        pw = (pb[pB + WIN1], pb[pB + WIN2])
        cw = (cb[cB + WIN1], cb[cB + WIN2])
        d1, d2 = cw[0] - pw[0], cw[1] - pw[1]
        if d1 < 0 or d2 < 0:                      # best-of-3 set reset inside this gap
            cand = [("P1", 1 + cw[0], cw[1])] if pw[0] == 2 else []
            cand += [("P2", cw[0], 1 + cw[1])] if pw[1] == 2 else []
            if len(cand) != 1:
                out["unreadable"].append((nm, f"reset_ambiguous {pw}->{cw} ends={m}")); continue
            _, d1, d2 = cand[0]
        if d1 + d2 != m:
            out["unreadable"].append((nm, f"count_mismatch d=({d1},{d2}) ends={m} {pw}->{cw}")); continue
        out["p1"] += d1; out["p2"] += d2
        out["intervals"].append((nm, m, d1, d2))
    for nm, b, base in good:                      # independent witness, when a sample lands on 5/7
        if b[base + MODE] in (5, 7) and (b[base + TOP1] or b[base + TOP2]):
            out["witnesses"].append((nm, b[base + MODE], b[base + TOP1], b[base + TOP2], b[base + RES]))
    out["ends_in_window"] = match_ends(good[-1][1], good[-1][2]) - match_ends(good[0][1], good[0][2]) if good else 0
    return out


def main(out_dir):
    rows = []
    for rf in sorted(glob.glob(os.path.join(out_dir, "rows", "*.json"))):
        r = json.loads(open(rf).read())
        if r.get("status") != "OK":
            continue
        d = os.path.join(out_dir, "artifacts", f"{r['seed']}_{r['arm']}")
        rows.append(dict(seed=r["seed"], arm=r["arm"], **read_row(d)))
    ends = sum(x["ends_in_window"] for x in rows)
    adj = sum(x["p1"] + x["p2"] for x in rows)
    ns = sum(x["samples"] for x in rows); nu = sum(x["undecodable"] for x in rows)
    print(f"rows={len(rows)}  samples={ns}  undecodable_samples={nu} ({100*nu/max(ns,1):.2f}%)")
    print(f"match-ends in window={ends}  adjudicated={adj}  "
          f"UNREADABLE={ends-adj} ({100*(ends-adj)/max(ends,1):.2f}%)")
    print("reasons:", collections.Counter(u[1].split()[0] for x in rows for u in x["unreadable"]))
    for arm in sorted({x["arm"] for x in rows}):
        a = [x for x in rows if x["arm"] == arm]
        p1 = sum(x["p1"] for x in a); p2 = sum(x["p2"] for x in a)
        print(f"  arm={arm:6s} rows={len(a):4d}  P1={p1:5d}  P2={p2:5d}  P2 win rate={p2/max(p1+p2,1):.4f}")
    ag = dis = 0
    for x in rows:
        byname = {nm: (m, d1, d2) for nm, m, d1, d2 in x["intervals"]}
        for nm, _mode, t1, t2, _rc in x["witnesses"]:
            if nm not in byname or byname[nm][0] != 1:
                continue
            flag = "P2" if (t1 and not t2) else ("P1" if (t2 and not t1) else None)
            if flag is None:
                continue
            ag += (flag == ("P1" if byname[nm][1] else "P2"))
            dis += (flag != ("P1" if byname[nm][1] else "P2"))
    print(f"cross-check vs topout flags: agree={ag} disagree={dis}")
    return rows


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
