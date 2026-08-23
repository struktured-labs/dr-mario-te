#!/usr/bin/env python3
"""endframe_scorer.py -- adjudicate a match from an END-FRAME capture alone.

This is the scorer for the tier-1/tier-2 detector: given save-states captured
because a screenshot classifier said "this looks like an end-of-match frame",
decide who lost.

Priority of evidence (strongest first):
  1. $0309 / $0389 -- the ROM's own per-player TOPPED-OUT flags, live during
     modes $05/$07 (set before L9532_TOP_5 writes mode 7 at $9585). Decisive.
  2. occ_top3 -- occupied cells in playfield rows 0-2. Viruses are never placed
     in the top three rows at level 11, so at a top-out the loser reads >0 and
     the winner reads 0. Corroborating; ABSTAINS on a tie.
Anything else is UNREADABLE. The scorer never guesses.
"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_winner as E

END_MODES = (3, 5, 7)


def occ_top3(blob, base, board):
    o = base + board
    return sum(1 for r in range(3) for c in range(8) if blob[o + r * 8 + c] != 0xFF)


def adjudicate(blob, base):
    """-> ('P1'|'P2'|None loser, reason)"""
    if blob[base + E.MODE] not in END_MODES:
        return None, "not_an_end_frame"
    t1, t2 = blob[base + E.TOP1], blob[base + E.TOP2]
    c1 = occ_top3(blob, base, 0x400)
    c2 = occ_top3(blob, base, 0x500)
    match (bool(t1), bool(t2)):
        case (True, False): flag = "P1"
        case (False, True): flag = "P2"
        case _:             flag = None
    match (c1 > c2, c2 > c1):
        case (True, False): occ = "P1"
        case (False, True): occ = "P2"
        case _:             occ = None
    if flag and occ and flag != occ:
        return None, f"UNREADABLE:flag_occ_conflict flags=({t1},{t2}) occ3=({c1},{c2})"
    if flag:
        return flag, f"topout_flag corroborated={occ==flag} occ3=({c1},{c2})"
    if occ:
        return occ, f"occ_top3_only occ3=({c1},{c2})"
    return None, f"UNREADABLE:no_discriminator flags=({t1},{t2}) occ3=({c1},{c2})"


def main(out_dir):
    tot = dec = 0
    tally = {"P1": 0, "P2": 0}
    reasons = {}
    for d in sorted(glob.glob(os.path.join(out_dir, "artifacts", "*"))):
        hint = None
        for f in sorted(glob.glob(os.path.join(d, "s*.ss"))):
            blob = open(f, "rb").read()
            try:
                base = hint = E.find_base(blob, hint)
            except ValueError:
                continue
            if blob[base + E.MODE] not in END_MODES:
                continue
            tot += 1
            loser, why = adjudicate(blob, base)
            if loser:
                dec += 1
                tally["P2" if loser == "P1" else "P1"] += 1   # winner = the other side
            else:
                reasons[why.split()[0]] = reasons.get(why.split()[0], 0) + 1
    print(f"end-frames={tot}  adjudicated={dec}  UNREADABLE={tot-dec} "
          f"({100*(tot-dec)/max(tot,1):.2f}%)")
    print(f"WINNER tally: P1={tally['P1']}  P2={tally['P2']}")
    print("unreadable reasons:", reasons)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
