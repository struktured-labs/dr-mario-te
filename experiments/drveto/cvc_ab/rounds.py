"""Round-transition detection from a virus-counter series. PURE -- no I/O, no box.

WHY A SERIES AND NOT A DEATH FRAME: the death board is on screen ~2.13 s
(endLevel_delay = 128 frames), which no practical poll cadence catches. Virus
counts are on screen continuously and are NON-INCREASING within a round, so a
round boundary is any INCREASE. That is robust to arbitrarily many missed frames:
losing samples costs precision on the boundary time, never a lost transition.

OUTCOME INFERENCE, and its honest limit:
  * a seat reaching 0 CLEARED -- it won, the other seat lost by being cleared out.
    This is exact.
  * otherwise the round ended in a TOPOUT, and WHICH seat plugged is NOT
    determined by the counts. Discriminated by the ROM's OWN loss condition --
    the throat cells (0,3)/(0,4) -- at the last pre-reset sample.

⚠ WHY NOT BOARD-FILL DIFFERENCE (the first rule I wrote, and rejected before any
data was scored): fill difference tracks WHO IS LOSING, not who died, and P1 is
the weak native d1 AI so its board is systematically fuller -- the rule would have
called nearly every round TOPOUT_P1 while reflecting the skill gap, not deaths.
⚠ AND WHY THROAT ALONE IS NOT ENOUGH: the ACTIVE CAPSULE spawns in exactly those
cells, so throat-occupied fires on ordinary mid-round spawn frames (measured: a
healthy P2 with 23 viruses read throat=True). PLUGGED therefore requires the
throat AND a real stack in the top three rows; a lone spawning capsule is ~2 cells.
Both rules were fixed BEFORE any round was scored (R28).
"""
RESET_MIN = 40          # a reset goes to the level's virus count (48 at L11)
TOPCELLS_MIN = 4        # occupied cells in rows 0-2 that mean "stack", not "capsule"


def transitions(series):
    """series = [(t, p1, p2, fill1, fill2, throat1, throat2, topcells1, topcells2)];
    p1/p2 may be None (unreadable).
    Returns a list of round records, one per detected boundary."""
    out = []
    prev = None                     # last sample with BOTH counts readable
    start_t = series[0][0] if series else None
    for s in series:
        t, p1, p2 = s[0], s[1], s[2]
        if p1 is None or p2 is None:
            continue
        if prev is not None:
            pp1, pp2 = prev[1], prev[2]
            up1, up2 = p1 > pp1, p2 > pp2
            if (up1 or up2) and (p1 >= RESET_MIN or p2 >= RESET_MIN):
                out.append(_classify(start_t, t, prev))
                start_t = t
        prev = s
    return out


def plugged(throat, topcells):
    """The ROM's loss condition, guarded against the spawning capsule."""
    return bool(throat) and topcells >= TOPCELLS_MIN


def _classify(start_t, end_t, prev):
    pt, pp1, pp2, pf1, pf2, t1, t2, n1, n2 = prev
    r = dict(start=start_t, end=end_t, dur_s=round(end_t - start_t, 1),
             last_t=pt, last_p1=pp1, last_p2=pp2,
             fill_p1=round(pf1, 4), fill_p2=round(pf2, 4),
             plug_p1=plugged(t1, n1), plug_p2=plugged(t2, n2))
    if pp1 == 0 and pp2 == 0:
        r["outcome"] = "AMBIGUOUS"; r["why"] = "both seats read 0"
    elif pp1 == 0:
        r["outcome"] = "CLEAR_WIN_P1"          # P1 cleared out; P2 lost, NOT a topout
    elif pp2 == 0:
        r["outcome"] = "CLEAR_WIN_P2"          # P2 (champion) cleared out
    elif r["plug_p1"] and not r["plug_p2"]:
        r["outcome"] = "TOPOUT_P1"
    elif r["plug_p2"] and not r["plug_p1"]:
        r["outcome"] = "TOPOUT_P2"             # <- the DRPROPH signal
    else:
        r["outcome"] = "AMBIGUOUS"
        r["why"] = "topout; both seats plugged" if r["plug_p1"] else "topout; neither seat plugged at the last sample"
    return r


def tally(records):
    t = {}
    for r in records:
        t[r["outcome"]] = t.get(r["outcome"], 0) + 1
    return t
