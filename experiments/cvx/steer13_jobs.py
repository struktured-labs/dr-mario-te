"""STEER13 job lists (`TAG SCRIPT ARGS... OUT`, OUT last).
  cal    q_B calibration (PILLS ONLY, before the prereg): LULU race, 400 seeds of the STEER10/12 block (39134-39932),
         A_fair_q04 (part A's silicon dose) + B_14886 (anytime 1488, MT 6) at q 0 / 2 / 3 / 4 %
  main   PREREG_STEER13.md sec. 4 (block 41100.., declared reuse = the abandoned, never-analysed STEER11 confirm block)
"""
import sys
JOB = 50
CAL = [39134 + 100 * i for i in range(8)]
LO = 41100
N_LULU, N_GUARD, N_SENS = 1600, 600, 800       # sized on the measured 2,250 games/h (PREREG_STEER13 sec. 4)
A_MAIN = ("A_fair_q04", "A_a16_q04", "A_r60_q04")                 # PRE-REGISTERED
A_SENS = ("A_fair_q02", "A_a16_q02", "A_r60_q02")                 # PRE-REGISTERED
B_MAIN = ("B_14886_qb", "B_v116_qb", "B_v114_qb", "B_v112_qb", "B_orc6_qb", "B_orc4_qb")   # PRE-REGISTERED (QB = 0)


def blocks(n):
    return [LO + 2 * JOB * i for i in range(n // JOB)]


def lines(phase):
    out = []
    if phase == "cal":
        for lo in CAL:
            for a in ("A_fair_q04", "B_14886_q00", "B_14886_q02", "B_14886_q03", "B_14886_q04"):
                out.append(f"c_{a} steer13_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer13/cal/lulu13_{a}_{lo}.jsonl")
        return out
    assert phase == "main" and B_MAIN is not None
    arms = A_MAIN + B_MAIN
    for lo in blocks(N_LULU):                                      # arms interleaved per block
        for a in arms:
            out.append(f"m_{a} steer13_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer13/main/lulu13_{a}_{lo}.jsonl")
        if lo in blocks(N_SENS):
            for a in A_SENS:
                out.append(f"m_{a} steer13_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer13/main/lulu13_{a}_{lo}.jsonl")
        if lo in blocks(N_GUARD):
            for a in arms:
                if a.startswith("B_orc"):                          # oracle arms: LULU only (survival-ratio references)
                    continue
                out.append(f"m_{a} steer13_run.py race {a} 2.36 hartford {lo} {JOB} 2 steer13/main/rc13_{a}_{lo}.jsonl")
                out.append(f"m_{a} steer13_run.py gb {a} owner202610 {lo} {JOB} 2 steer13/main/gb13_{a}_{lo}.jsonl")
    return out


if __name__ == "__main__":
    print("\n".join(lines(sys.argv[1])))
