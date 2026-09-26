"""Pre-treatment stratum for STEER5(a): the INITIAL count of HIGH spawn-column viruses per seed (cols 3-5, rows above
row 9, i.e. row index < 9, row 0 = top), from the ROM-faithful virus placement at reset (L11). Arm-independent.
Usage: python hsv_census.py OUT.json"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
from drmario.faithful_env import FaithfulDrMarioEnv


def hsv(board, row_lt=9):
    return int(sum(1 for r in range(row_lt) for c in (3, 4, 5) if board.is_virus[r, c]))


if __name__ == "__main__":
    seeds = list(range(36734, 36734 + 2 * 600, 2))
    for lo, n in ((4002, 231), (40934, 83), (17000, 50), (17300, 50), (20900, 50)):
        seeds += list(range(lo, lo + 2 * n, 2))
    out = {}
    for s in seeds:
        env = FaithfulDrMarioEnv(level=11, seed=s, max_pills=600); env.reset()
        out[s] = {"hsv9": hsv(env.board, 9), "hsv10": hsv(env.board, 10), "nvir": int(env.board.virus_count())}
    json.dump(out, open(sys.argv[1], "w"))
    import collections
    print("hsv9 distribution (reused block):", sorted(collections.Counter(out[s]["hsv9"] for s in seeds[:600]).items()))
