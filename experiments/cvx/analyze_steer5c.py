"""STEER5c analysis per PREREG_STEER5c.md: HSV512 confirmatory holdout (fresh block), race secondary, descriptive
600-block + pooled."""
import sys, os, json, glob
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)
from analyze_steer5 import rows, paired, early, tap, boot
from vs_race import evaluate


def win(r, dl): return int(evaluate(r, 177.0, 0.15, dl)[0] == "win_race")


if __name__ == "__main__":
    ctl = rows("steer5/control/ctl_*.jsonl", "fw540_steer_s5_base")
    fresh = rows("steer5/c_remote/gb_fresh_*.jsonl", "fw540_steer_s5b_hsv512")
    base = rows("steer4/remote/s4_base_*.jsonl", "fw540_steer_s4_base")
    reuse = rows("steer5/c_local/s5b_hsv512_*.jsonl", "fw540_steer_s5b_hsv512")
    e = paired(fresh, ctl, early); t = paired(fresh, ctl, tap)
    s = list(fresh.values()); n = len(s); c = list(ctl.values())
    print(f"PRIMARY fresh block (n={e[3]} paired): tap<=100 {100*sum(early(r) for r in s)/n:.2f}% vs ctl {100*sum(early(r) for r in c)/len(c):.2f}%  "
          f"d {e[0]:+.2f} [{e[1]:+.2f},{e[2]:+.2f}]  |  tap-out {100*sum(tap(r) for r in s)/n:.2f}% vs {100*sum(tap(r) for r in c)/len(c):.2f}%  "
          f"d {t[0]:+.2f} [{t[1]:+.2f},{t[2]:+.2f}]  |  win {100*sum(r['won'] for r in s)/n:.1f}% vs {100*sum(r['won'] for r in c)/len(c):.1f}%")
    gate1 = e[0] < 0; gate2 = t[2] <= 2.0
    rb = rows("steer5/c_remote/race_s4_base_*.jsonl", "s4_base~steer")
    rh = rows("steer5/c_remote/race_s5b_hsv512_*.jsonl", "s5b_hsv512~steer")
    race_ok = None
    if rb and rh:
        a = paired(rh, rb, lambda r: win(r, 2.65)); b = paired(rh, rb, lambda r: win(r, 2.0))
        print(f"RACE fresh (n={a[3]} paired, lam 6, 177-s human): win d2.65 {100*sum(win(r,2.65) for r in rh.values())/len(rh):.1f}% vs "
              f"{100*sum(win(r,2.65) for r in rb.values())/len(rb):.1f}%  d {a[0]:+.2f} [{a[1]:+.2f},{a[2]:+.2f}]   "
              f"d2.0 d {b[0]:+.2f} [{b[1]:+.2f},{b[2]:+.2f}]")
        race_ok = a[1] >= -2.0
    print(f"BAR: tap<=100 point<0 {gate1} ; tap-out upper CI<=+2 {gate2} ({t[2]:+.2f}) ; race lower CI>=-2 {race_ok} "
          f"=> {'PASS' if (gate1 and gate2 and race_ok) else 'FAIL'}")
    if reuse:
        e2 = paired(reuse, base, early); t2 = paired(reuse, base, tap)
        print(f"\nDESCRIPTIVE 600 reuse block (not counted): hsv512 tap<=100 d {e2[0]:+.2f} [{e2[1]:+.2f},{e2[2]:+.2f}]  "
              f"tap-out d {t2[0]:+.2f} [{t2[1]:+.2f},{t2[2]:+.2f}]   (hsv540 there: -3.00 / -2.67)")
        P = {**{("f", k): v for k, v in fresh.items()}, **{("r", k): v for k, v in reuse.items()}}
        B = {**{("f", k): v for k, v in ctl.items()}, **{("r", k): v for k, v in base.items()}}
        e3 = paired(P, B, early); t3 = paired(P, B, tap)
        print(f"POOLED 600+464 (descriptive): tap<=100 d {e3[0]:+.2f} [{e3[1]:+.2f},{e3[2]:+.2f}]  tap-out d {t3[0]:+.2f} [{t3[1]:+.2f},{t3[2]:+.2f}]  n={e3[3]}")
