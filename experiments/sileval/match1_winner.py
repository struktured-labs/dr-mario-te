#!/usr/bin/env python3
"""match1_winner.py -- adjudicate the MATCH-1 winner of one cycle's samples.

Used by the AMENDMENT-1 repeatability tripwire. The rule is deliberately
conservative: anything it cannot see, it calls UNREADABLE rather than guessing,
because a wrong noise-floor number would gate the whole replication.

Rule (from the sampled virus timeline, BCD-decoded $0324/$03A4):
  - A match ends when a side reaches 0 viruses; that side won.
  - A ROLLOVER (either counter INCREASING vs the previous sample) marks the
    start of a new match, so match 1 is everything before the first rollover.
  - If a side is seen at 0 within match 1  -> that side is the winner.
  - If match 1 ends (rollover) without either side observed at 0, the 20 s
    cadence stepped over the finish -> UNREADABLE.
  - If no rollover and no 0 within the cycle, match 1 never finished
    -> UNREADABLE.
Both-at-0 in the same sample is also UNREADABLE (cannot order them).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
import seedjit_ss

def bcd(x): return (x >> 4) * 10 + (x & 0x0F)

def timeline(adir):
    out = []
    for ss in sorted(Path(adir).glob("s*.ss")):
        blob = ss.read_bytes()
        try:
            base = seedjit_ss.find_base(blob)
        except BaseException:  # find_base raises SystemExit, not Exception, when the
            # counters disagree with the board mid-clear-animation — that is a
            # skippable sample, not a reason to abort the whole adjudication.
            continue
        out.append((bcd(blob[base + 0x324]), bcd(blob[base + 0x3A4])))
    return out

def winner(adir):
    t = timeline(adir)
    if not t:
        return "UNREADABLE:no-samples"
    for i, (p1, p2) in enumerate(t):
        if i > 0:
            pp1, pp2 = t[i - 1]
            if p1 > pp1 or p2 > pp2:          # rollover -> match 1 already over
                return "UNREADABLE:rollover-without-zero"
        if p1 == 0 and p2 == 0:
            return "UNREADABLE:both-zero"
        if p1 == 0:
            return "P1"
        if p2 == 0:
            return "P2"
    return "UNREADABLE:match1-unfinished"

if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(f"{d}\t{winner(d)}")
