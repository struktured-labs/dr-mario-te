"""STEER14 job lists (`TAG SCRIPT ARGS... OUT`, OUT last).
  cal    STAGE-1 SCREEN of the slam-gate cut (EXECUTION METRICS ONLY, before the prereg; steer14_cal_read.py): LULU
         race, 400 seeds of the STEER10/12/13 calibration block (39134-39932, step 2), DIST4 at every steer14_run.GATES
         configuration + the MIN_THINK 2 f model check.
  main   PREREG_STEER14.md sec. 4, in this order (R23: the number the owner relies on first):
           (1) RE-DERIVATION of STEER13's V11-vs-1488 under the slam gate on STEER13's own seeds (41100.., declared reuse)
           (2) the 2x2 + the q 2 % sensitivity pair on the new block (44300.., declared reuse), arms interleaved per block
           (3) the gate dose-response (DIST4, LULU only: every screened configuration but k32 and G*) on the first
               N_DOSE seeds of the new block
"""
import sys
JOB = 50
CAL = [39134 + 100 * i for i in range(8)]
GATE_NAMES = ("k32", "k24", "k16", "k8", "k4", "e32", "e16", "v4", "u16", "u8")       # == steer14_run.GATES
CAL_ARMS = tuple(f"S14_d4_{g}" for g in GATE_NAMES) + ("CAL_d4_k32_mt2",)
LO, LO13 = 44300, 41100
N_LULU, N_GUARD, N_SENS, N_DOSE = 5100, 1000, 2000, 600       # PREREG_STEER14 sec. 4 (steer14/sizing.txt)
N13_LULU, N13_GUARD = 1600, 600                                # == STEER13's cells
GS = None                                                       # the gate cut G*, from steer14/cal/gate_cut.txt (prereg)
REDERIVE = ("C13_14886", "C13_v116")


def main_arms():
    assert GS is not None, "set GS from steer14/cal/gate_cut.txt before the main phase"
    return ("S14_d4_k32", "S14_d16_k32", f"S14_d4_{GS}", f"S14_d16_{GS}")


def sens_arms():
    return ("S14_d4_k32_q02", f"S14_d16_{GS}_q02")


def dose_arms():
    return tuple(f"S14_d4_{g}" for g in GATE_NAMES if g not in ("k32", GS))


def blocks(n, lo=LO):
    return [lo + 2 * JOB * i for i in range(n // JOB)]


def seeds(n, lo=LO):
    return [lo + 2 * i for i in range(n)]


def lines(phase):
    out = []
    if phase == "cal":
        for lo in CAL:
            for a in CAL_ARMS:
                out.append(f"c_{a} steer14_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer14/cal/lulu14c_{a}_{lo}.jsonl")
        return out
    assert phase == "main"
    for lo in blocks(N13_LULU, LO13):                              # (1) re-derivation first
        for a in REDERIVE:
            out.append(f"r_{a} steer14_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer14/main/lulu14_{a}_{lo}.jsonl")
        if lo in blocks(N13_GUARD, LO13):
            for a in REDERIVE:
                out.append(f"r_{a} steer14_run.py race {a} 2.36 hartford {lo} {JOB} 2 steer14/main/rc14_{a}_{lo}.jsonl")
                out.append(f"r_{a} steer14_run.py gb {a} owner202610 {lo} {JOB} 2 steer14/main/gb14_{a}_{lo}.jsonl")
    for lo in blocks(N_LULU):                                      # (2) the 2x2 + sensitivity
        for a in main_arms():
            out.append(f"m_{a} steer14_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer14/main/lulu14_{a}_{lo}.jsonl")
        if lo in blocks(N_SENS):
            for a in sens_arms():
                out.append(f"m_{a} steer14_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer14/main/lulu14_{a}_{lo}.jsonl")
        if lo in blocks(N_GUARD):
            for a in main_arms():
                out.append(f"m_{a} steer14_run.py race {a} 2.36 hartford {lo} {JOB} 2 steer14/main/rc14_{a}_{lo}.jsonl")
                out.append(f"m_{a} steer14_run.py gb {a} owner202610 {lo} {JOB} 2 steer14/main/gb14_{a}_{lo}.jsonl")
    for lo in blocks(N_DOSE):                                      # (3) the dose-response
        for a in dose_arms():
            out.append(f"d_{a} steer14_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer14/main/lulu14_{a}_{lo}.jsonl")
    return out


if __name__ == "__main__":
    print("\n".join(lines(sys.argv[1])))
