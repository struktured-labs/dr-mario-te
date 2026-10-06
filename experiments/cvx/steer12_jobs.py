"""STEER12 job lists (steer11_farm.sh-style runner: `TAG SCRIPT ARGS... OUT`, OUT last).
  main   PREREG_STEER12.md sec. 4: every arm on the STEER10 blocks (declared reuse; FAIR's couch11 rows are the steer11
         pilot rows, FAIR's gate-b rows the banked steer8 fD_bdepD rows): LULU race 1,200 seeds, owner race 600, gate b 600
"""
import sys
JOB = 50
LULU = [39134 + 100 * i for i in range(12)] + [40334 + 100 * i for i in range(6)] + [33000 + 100 * i for i in range(6)]
SIX = [39134 + 100 * i for i in range(12)]
ARMS = ("lat_m2", "lat_m4", "lat_m6", "lat_ceil", "ex_perfect", "ex_q02", "ex_q03", "ex_q05")   # PRE-REGISTERED (q grid from steer12/qcal)


def lines(phase):
    assert phase == "main"
    out = []
    for lo in LULU:                                   # arms interleaved per block: a partial farm stays paired
        for a in ARMS:
            out.append(f"m_{a} steer12_run.py race {a} 2.84 lulu202610b {lo} {JOB} 2 steer12/main/lulu12_{a}_{lo}.jsonl")
    for lo in SIX:
        for a in ARMS:
            out.append(f"m_{a} steer12_run.py race {a} 2.36 hartford {lo} {JOB} 2 steer12/main/rc12_{a}_{lo}.jsonl")
            out.append(f"m_{a} steer12_run.py gb {a} owner202610 {lo} {JOB} 2 steer12/main/gb12_{a}_{lo}.jsonl")
    return out


if __name__ == "__main__":
    print("\n".join(lines(sys.argv[1])))
