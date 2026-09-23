"""#15 arena end-mode probe: send_rule / gcols / halves_cap vs winner-vs-holes80.

Default arena is 97-99% clear. Hartford tape is ~70% topout. Sweep until the
how-mix moves; then report win rate next to how. Seeds 50134+ DECLARED REUSE.
"""
from __future__ import annotations
import json, os, sys, collections, itertools
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
from vs_choose import VsPolicy
import vs_sim

OUT = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx/arena15"
os.makedirs(OUT, exist_ok=True)
NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 80
SEED0 = 50134
LEVEL = 11

CFGS = [
    dict(name="cells_g6_h4", send_rule="cells", gcols=None, halves_cap=4),
    dict(name="lines_g6_h4", send_rule="lines", gcols=None, halves_cap=4),
    dict(name="cells_g8_h4", send_rule="cells", gcols=list(range(8)), halves_cap=4),
    dict(name="cells_g6_h8", send_rule="cells", gcols=None, halves_cap=8),
    dict(name="lines_g8_h8", send_rule="lines", gcols=list(range(8)), halves_cap=8),
]


def _one(args):
    seed, seat, send_rule, gcols, halves_cap = args
    import import_pin
    import_pin.pin()
    import pressure_rig as PR
    PR._init(11, 0, 0)
    from vs_choose import VsPolicy
    import vs_sim
    win = VsPolicy(trunk="winner")
    h80 = VsPolicy(trunk="winholes80")
    A, B = (win, h80) if seat == 0 else (h80, win)
    r = vs_sim.play_vs(seed, LEVEL, A, None, B, None, wt=0, ws=0,
                       send_rule=send_rule, gcols=gcols, halves_cap=halves_cap)
    winner_is_win = False
    if r["winner"] in (0, 1):
        winner_is_win = (seat == 0 and r["winner"] == 0) or (seat == 1 and r["winner"] == 1)
    return r["how"], int(winner_is_win), sum(r["sent"])


def main():
    from multiprocessing import Pool
    ledger = []
    jobs_base = [(SEED0 + i * 2, seat) for i in range(NSEED) for seat in (0, 1)]
    with Pool(10) as pool:
        for cfg in CFGS:
            jobs = [(s, seat, cfg["send_rule"], cfg["gcols"], cfg["halves_cap"])
                    for s, seat in jobs_base]
            how = collections.Counter()
            wins = sent = 0
            n = 0
            for how_i, win_i, sent_i in pool.imap_unordered(_one, jobs, chunksize=4):
                how[how_i] += 1
                wins += win_i
                sent += sent_i
                n += 1
            top = how.get("opp_topout", 0) + how.get("opp_crushed", 0)
            rec = {"name": cfg["name"], "send_rule": cfg["send_rule"],
                   "gcols": "all8" if cfg["gcols"] else "g6",
                   "halves_cap": cfg["halves_cap"], "n": n,
                   "winner_vs_h80": wins, "how": dict(how),
                   "topout_share": top / n, "mean_sent": sent / n}
            ledger.append(rec)
            print(f"{cfg['name']}: winner {wins}/{n}={100*wins/n:.1f}%  "
                  f"topout_share {100*top/n:.1f}%  how={dict(how)}  sent={sent/n:.1f}",
                  flush=True)
    path = f"{OUT}/LEDGER.json"
    json.dump(ledger, open(path, "w"), indent=2)
    print("WROTE", path, flush=True)


if __name__ == "__main__":
    main()
