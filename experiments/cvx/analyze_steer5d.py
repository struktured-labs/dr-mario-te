"""STEER5d analysis per PREREG_STEER5d.md: powered non-inferiority of HSV512 (declared-reuse older blocks + fresh 464)."""
import sys, os, json, glob
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)
from analyze_steer5 import rows, paired, early, tap
from vs_race import evaluate


def win(r, dl): return int(evaluate(r, 177.0, 0.15, dl)[0] == "win_race")


def merge(*ds):
    out = {}
    for i, d in enumerate(ds):
        for k, v in d.items():
            out[(i, k)] = v
    return out


if __name__ == "__main__":
    # gate b: new 5d pairs (older blocks) + banked fresh 464 pairs (STEER5 control vs STEER5c hsv512)
    gb_b = rows("steer5d/*/gb_s4_base_*.jsonl", "fw540_steer_s4_base")
    gb_h = rows("steer5d/*/gb_s5b_hsv512_*.jsonl", "fw540_steer_s5b_hsv512")
    fr_b = rows("steer5/control/ctl_*.jsonl", "fw540_steer_s5_base")
    fr_h = rows("steer5/c_remote/gb_fresh_*.jsonl", "fw540_steer_s5b_hsv512")
    B = merge(gb_b, fr_b); H = merge(gb_h, fr_h)
    e = paired(H, B, early); t = paired(H, B, tap)
    n = e[3]
    sb = [B[k] for k in B if k in H]; sh = [H[k] for k in H if k in B]
    print(f"GATE (b): n={n} paired (new {len(set(gb_b)&set(gb_h))} + fresh {len(set(fr_b)&set(fr_h))})")
    print(f"  tap<=100  base {100*sum(early(r) for r in sb)/n:5.2f}%  hsv {100*sum(early(r) for r in sh)/n:5.2f}%  d {e[0]:+.2f} [{e[1]:+.2f},{e[2]:+.2f}]")
    print(f"  tap-out   base {100*sum(tap(r) for r in sb)/n:5.2f}%  hsv {100*sum(tap(r) for r in sh)/n:5.2f}%  d {t[0]:+.2f} [{t[1]:+.2f},{t[2]:+.2f}]   BAR upper<=+1.5: {t[2] <= 1.5}")
    # race: new 5d pairs + banked fresh 300 (STEER5c)
    rc_b = rows("steer5d/*/rc_s4_base_*.jsonl", "s4_base~steer")
    rc_h = rows("steer5d/*/rc_s5b_hsv512_*.jsonl", "s5b_hsv512~steer")
    f5_b = rows("steer5/c_remote/race_s4_base_*.jsonl", "s4_base~steer")
    f5_h = rows("steer5/c_remote/race_s5b_hsv512_*.jsonl", "s5b_hsv512~steer")
    RB = merge(rc_b, f5_b); RH = merge(rc_h, f5_h)
    a = paired(RH, RB, lambda r: win(r, 2.65)); b = paired(RH, RB, lambda r: win(r, 2.0))
    m = a[3]; wb = [RB[k] for k in RB if k in RH]; wh = [RH[k] for k in RH if k in RB]
    print(f"RACE: n={m} paired (new {len(set(rc_b)&set(rc_h))} + fresh {len(set(f5_b)&set(f5_h))})")
    print(f"  win d2.65 base {100*sum(win(r,2.65) for r in wb)/m:5.2f}%  hsv {100*sum(win(r,2.65) for r in wh)/m:5.2f}%  d {a[0]:+.2f} [{a[1]:+.2f},{a[2]:+.2f}]   BAR lower>=-2: {a[1] >= -2.0}")
    print(f"  win d2.0  d {b[0]:+.2f} [{b[1]:+.2f},{b[2]:+.2f}]   clear base {100*sum(r['how']=='clear' for r in wb)/m:.1f}% hsv {100*sum(r['how']=='clear' for r in wh)/m:.1f}%")
    print(f"\nVERDICT: {'PASS' if (t[2] <= 1.5 and a[1] >= -2.0) else 'FAIL'}")
