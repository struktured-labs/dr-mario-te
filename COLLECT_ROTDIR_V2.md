# How to collect the #114 verdict (the runs finish unattended)

Three batches are chained and detached (`setsid nohup`); each waits on the previous one's
completion artifact, so nothing races:

    tools/gate/batch_rotdir_v2b.sh   -> tmp/rotdir_v2b.log     ends with V2_BATCH_DONE
    tools/gate/batch_rotmut2.sh      -> tmp/rotmut2_batch.log  ends with MUT2_BATCH_DONE

When `MUT2_BATCH_DONE` is present, run:

    python3 tools/gate/verdict_rotdir_v2.py

It prints the per-seed table, applies PREREG_ROTDIR_V2's P1/P3 and the >=8/16 power bar,
scores all four mutants on BOTH halves, and exits 0 only on a full GO. Exit 1 is a real
verdict (NO-GO / under-powered / surviving mutant); it never exits 0 on missing data —
a missing cell is a FAILURE, not a skip.

If a batch died, relaunch it; every cell is deterministic given (cart, seed), so re-running
a cell reproduces it exactly. Check for dropped cells with:

    command grep -ac refusing tmp/rotdir_v2b.log tmp/rotmut2_batch.log     # must be 0

DO NOT relax PREREG_ROTDIR_V2's inclusion rule or power bar to obtain a verdict. If fewer
than 8 pairs survive, the answer is NO-VERDICT and the blocker is #131, not this fix.
