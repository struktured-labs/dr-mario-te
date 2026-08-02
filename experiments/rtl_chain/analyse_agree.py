#!/usr/bin/env python3
"""Agreement-vs-K from the publish traces in agree69.log.

The question this answers: if the Pocket's tighter clock forces the driver to commit the
copro's best-so-far BEFORE the search finishes, how often is that move the same move the
search would finally have returned?

Two curves, because they answer different things:

  NORMALISED (agreement vs completion fraction) -- the convergence profile. This is the one
  that generalises to tail boards we have NOT sampled: it says nothing about how long a
  search takes, only about how early within a search the answer stops moving.

  ABSOLUTE (agreement at a fixed clock budget) -- what the Pocket actually experiences,
  since its budget is a wall-clock deadline, not a fraction.

The driver's view is modelled honestly: orient==0xFF is the firmware's "no candidate yet"
sentinel, so a sample there is NOT an answer the driver may commit -- it is counted
separately rather than scored as a disagreement.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 200            # clocks; sim_mister.cpp quantises DONE to a 48-clock CPU cycle
SENTINEL = 255


def load_trace(path):
    boards = {}
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "BOARD":
            boards[int(p[1])] = {"carry": (int(p[3]), int(p[4])), "pub": []}
        elif p[0] == "PUB":
            boards[int(p[1])]["pub"].append((int(p[2]), int(p[3]), int(p[4])))
        elif p[0] == "DONEB":
            b = boards[int(p[1])]
            b.update(T=int(p[3]), sent=int(p[5]), first=int(p[7]),
                     settle=int(p[9]), ntrans=int(p[11]),
                     final=(int(p[13]), int(p[14])))
        elif p[0] == "FAIL":
            sys.exit("trace reports a hard failure: " + line.strip())
    return boards


def load_control(path):
    """From the ORIGINAL bus-polled rig: DONE clocks AND the move it read back.

    Both halves are gates. The clocks catch a perturbing instrument; the move catches a
    mis-addressed one -- if I had the wram indices wrong, the trace would still produce a
    plausible-looking curve out of whatever bytes happen to live at 0x834/0x835.
    """
    ctl = {}
    for line in open(path):
        if line.startswith("case ") and "clocks=" in line:
            k = int(line.split()[1].rstrip(":"))
            mv = line.split("copro=(")[1].split(")")[0].split(",")
            ctl[k] = (int(line.split("clocks=")[1].split()[0]),
                      (int(mv[0]), int(mv[1])))
    return ctl


def state_at(b, tau):
    """(col, orient) the host would read at clock offset tau"""
    cur = b["carry"]
    for (t, c, o) in b["pub"]:
        if t > tau:
            break
        cur = (c, o)
    return cur


def main():
    tr = load_trace(os.path.join(HERE, "agree69.log"))
    done = {k: v for k, v in tr.items() if "T" in v}
    if len(done) != len(tr):
        print(f"NOTE: {len(tr)-len(done)} board(s) still running; analysing {len(done)}")
    ks = sorted(done)

    # ---- GATE: the instrument must not have perturbed the thing it measures -------------
    ctl = load_control(os.path.join(os.path.dirname(HERE), "donelat", "dist69.log"))
    worst = (0, None)
    missing = [k for k in ks if k not in ctl]
    if missing:
        sys.exit(f"control has no entry for boards {missing[:5]} -- cannot certify")
    for k in ks:
        d = abs(done[k]["T"] - ctl[k][0])
        if d > worst[0]:
            worst = (d, k)
    print(f"NON-PERTURBATION GATE: max |T_peek - T_bus| = {worst[0]} clocks "
          f"(board {worst[1]}), tolerance {TOL}")
    if worst[0] > TOL:
        sys.exit("GATE FAILED: the instrumented run does not reproduce dist69's latencies.\n"
                 "  Direct-peek sampling was supposed to be free; it was not. Every number\n"
                 "  below would describe a perturbed search. Stop.")
    print("  PASS -- clock counts reproduce the bus-polled rig, so peeking is free.")

    bad = [k for k in ks if done[k]["final"] != ctl[k][1]]
    print(f"ADDRESS GATE: peeked final move == bus-read move on {len(ks)-len(bad)}/{len(ks)}")
    if bad:
        sys.exit("GATE FAILED: peek and bus disagree on the final move for boards "
                 f"{bad[:5]}.\n  The wram indices are wrong, so the whole trace is bytes from\n"
                 "  somewhere else that merely look like a convergence curve.")
    print("  PASS -- the trace reads the same mailbox the NES does.\n")

    # ---- convergence profile ------------------------------------------------------------
    fs = sorted(done[k]["settle"] / done[k]["T"] for k in ks)
    ff = sorted(done[k]["first"] / done[k]["T"] for k in ks)
    n = len(ks)

    def pct(v, q):
        return v[min(int(q * len(v)), len(v) - 1)]

    print(f"CONVERGENCE PROFILE ({n} boards, stomp180 = the shipped Combo Stomper arm)")
    print("  settle fraction = clock of the LAST change to the published move / total search")
    print(f"    min {fs[0]:.4f}  median {pct(fs,0.5):.4f}  p90 {pct(fs,0.9):.4f}  "
          f"p95 {pct(fs,0.95):.4f}  max {fs[-1]:.4f}")
    print("  first-answer fraction = clock the FIRST candidate is published / total search")
    print(f"    min {ff[0]:.6f}  median {pct(ff,0.5):.6f}  p90 {pct(ff,0.9):.6f}  "
          f"max {ff[-1]:.6f}")
    print(f"  publishes per search: min {min(done[k]['ntrans'] for k in ks)}  "
          f"max {max(done[k]['ntrans'] for k in ks)}  "
          f"mean {sum(done[k]['ntrans'] for k in ks)/n:.1f}")
    print()

    print("AGREEMENT vs COMPLETION FRACTION  (commit best-so-far at f*T, compare to final)")
    print("     f     agree   differ   no-answer")
    for f in (0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.88, 0.95, 1.00):
        ag = dif = na = 0
        for k in ks:
            b = done[k]
            c, o = state_at(b, f * b["T"])
            if o == SENTINEL:
                na += 1
            elif (c, o) == b["final"]:
                ag += 1
            else:
                dif += 1
        print(f"  {f:5.2f}   {ag:4d}   {dif:4d}   {na:4d}      "
              f"{100.0*ag/n:5.1f}% agree")
    print()

    # ---- absolute budget ---------------------------------------------------------------
    print("ABSOLUTE BUDGET  (Pocket deadline is wall-clock, not a fraction)")
    print("   budget(Mclk)  complete  truncated-agree  truncated-DIFFER  truncated-no-answer")
    for K in (40e6, 50e6, 60e6, 72.9e6, 80e6, 100e6):
        comp = ag = dif = na = 0
        for k in ks:
            b = done[k]
            if b["T"] <= K:
                comp += 1
                continue
            c, o = state_at(b, K)
            if o == SENTINEL:
                na += 1
            elif (c, o) == b["final"]:
                ag += 1
            else:
                dif += 1
        tag = "  <- Pocket" if abs(K - 72.9e6) < 1 else ""
        print(f"   {K/1e6:9.1f}    {comp:5d}      {ag:8d}        {dif:9d}        {na:9d}{tag}")
    print()

    # ---- the number the Pocket decision actually turns on --------------------------------
    # For a fixed budget K, the board that suffers most is the SLOWEST one: it gets the
    # smallest fraction K/T of its search done. Pair that worst-case fraction with the
    # normalised curve and the exposure is bounded WITHOUT having to have sampled the tail --
    # which matters, because 81.9M is the worst search we observed, not the worst that exists.
    K = 72.9e6
    Tmax = max(done[k]["T"] for k in ks)
    kslow = max(ks, key=lambda k: done[k]["T"])
    fmin = min(K / Tmax, 1.0)
    print(f"WORST-CASE COMPLETION AT THE POCKET BUDGET ({K/1e6:.1f}M clocks)")
    if K >= Tmax:
        print(f"  slowest board {kslow} (T={Tmax}) still FINISHES inside the budget "
              f"({100*K/Tmax:.0f}% of budget would be needed); nothing truncates.")
    else:
        print(f"  slowest board {kslow} (T={Tmax}) gets {100*fmin:.1f}% of its search done")
    agree_at = sum(1 for k in ks
                   if state_at(done[k], fmin * done[k]["T"]) == done[k]["final"])
    print(f"  agreement if EVERY board were truncated to that fraction: {agree_at}/{n}")
    print("  Bounding the unsampled tail: a board 2x slower than anything observed here "
          f"would sit at {100*K/(2*Tmax):.0f}% completion,")
    print("  and the normalised curve above prices that completion fraction directly.")
    print()

    # ---- name the late settlers ---------------------------------------------------------
    # If the curve is not 100% at the budget, THESE are the boards a paired h2h should run
    # on. Naming them keeps the follow-up narrow instead of re-running the whole corpus.
    late = sorted(((done[k]["settle"] / done[k]["T"], k) for k in ks), reverse=True)[:8]
    print("LATEST-SETTLING BOARDS (the deep search overturned the shallow favourite here)")
    for fr, k in late:
        b = done[k]
        print(f"  board {k:3d}  settle {fr:6.3f} of T={b['T']:>10d}  "
              f"cands~{(b['ntrans']-1)//2 + 1}  final {b['final']}")
    print()

    # ---- torn-pair exposure -------------------------------------------------------------
    # The firmware publishes col then orient as two consecutive stores, so between them the
    # mailbox holds (NEW col, OLD orient): a pair that looks valid but never was a candidate.
    tear_clocks = tear_n = 0
    for k in ks:
        b = done[k]
        ev = b["pub"] + [(b["T"], None, None)]
        for i in range(len(ev) - 1):
            t, c, o = ev[i]
            tn, cn, on = ev[i + 1]
            if o != SENTINEL and cn == c and on != o and (tn - t) < 1000:
                tear_clocks += tn - t
                tear_n += 1
    total = sum(done[k]["T"] for k in ks)
    print(f"TORN-PAIR EXPOSURE: {tear_n} windows, {tear_clocks} clocks total of "
          f"{total} ({100.0*tear_clocks/total:.7f}% of search time)")
    print("  = mailbox showing (new col, previous orient). Real, but a host read lands in one")
    print("  with probability ~1e-6 per poll; the sentinel does not mask this case.")


if __name__ == "__main__":
    main()
