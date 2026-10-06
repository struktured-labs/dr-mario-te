"""STEER11 job lists for steer11_farm.sh: one line per 50-game job, `TAG SCRIPT ARGS... OUT` (OUT last).
  pilot    step 1 (before the prereg): s10_base + s10_A16 on the couch11 clock, STEER10 blocks (declared reuse)
  confirm  PREREG_STEER11.md sec. 4 (CONFIRM below is the pre-registered block; edited only by the prereg commit)
"""
import sys

JOB = 50
STEER10_LULU = [39134 + 100 * i for i in range(12)] + [40334 + 100 * i for i in range(6)] + [33000 + 100 * i for i in range(6)]
STEER10_RC = [39134 + 100 * i for i in range(12)]
ARMS = ("s10_base", "s10_A16")
# PRE-REGISTERED confirmation block (PREREG_STEER11.md sec. 4): even seeds step 2 from LO, N seeds per instrument
CONFIRM = {"lo": 41100, "n": 4000}          # PREREG_STEER11 stage B: steer11_sizing.py rule output (steer11/sizing.txt)


def lines(phase):
    out = []
    if phase == "pilot":
        for lo in STEER10_LULU:                           # arms interleaved per block: a partial farm stays paired
            for a in ARMS:
                out.append(f"p_{a} steer11_run.py race {a} 2.84 lulu202610b couch11 {lo} {JOB} 2 steer11/pilot/lulu10b_c11_{a}_{lo}.jsonl")
        for lo in STEER10_RC:
            for a in ARMS:
                out.append(f"p_{a} steer11_run.py race {a} 2.36 hartford couch11 {lo} {JOB} 2 steer11/pilot/rc10_c11_{a}_{lo}.jsonl")
    elif phase == "confirm":
        assert CONFIRM is not None, "confirm block not pre-registered"
        lo0, n = CONFIRM["lo"], CONFIRM["n"]
        assert n % JOB == 0
        blocks = [lo0 + 2 * JOB * i for i in range(n // JOB)]
        for lo in blocks:                                 # arms interleaved per block: a partial farm stays paired
            for a in ARMS:
                out.append(f"c_{a} steer11_run.py race {a} 2.84 lulu202610b couch11 {lo} {JOB} 2 steer11/confirm/lulu11_{a}_{lo}.jsonl")
                out.append(f"c_{a} steer11_run.py gb {a} owner202610 {lo} {JOB} 2 steer11/confirm/gb11_{a}_{lo}.jsonl")
                out.append(f"c_{a} steer11_run.py race {a} 2.36 hartford couch11 {lo} {JOB} 2 steer11/confirm/rc11_{a}_{lo}.jsonl")
    else:
        raise SystemExit(f"phase {phase}?")
    return out


if __name__ == "__main__":
    print("\n".join(lines(sys.argv[1])))
