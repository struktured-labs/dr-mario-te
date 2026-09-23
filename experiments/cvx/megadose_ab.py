"""MEGADOSE A/B: winner k_clock=0 vs k_clock=40 on live base drmario.nes via Mesen."""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0, CVX)
import import_pin
import_pin.pin()
from vs_choose import VsPolicy

LIVE = "/home/struktured/projects/dr-mario-mods/rl-training-new/scripts"
sys.path.insert(0, LIVE)
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods/rl-training-new/src")
import play_rom_live as PL
from drmario.faithful_game import Pill

OUT = Path("/home/struktured/projects/dr-mario-h16-wt/tmp/megadose")
OUT.mkdir(parents=True, exist_ok=True)
RELEASE = PL.RELEASE
LEVEL, SPEED = 11, 1
SEED0, N = 40, 8  # 8-bit RNG; paired A/B


class ClockPlanner:
    def __init__(self, k_clock=0.0):
        self.pol = VsPolicy(k_clock=k_clock)
        self.k_clock = k_clock

    def choose(self, board, cur, nxt):
        from fb import FB
        import root_search as RS
        fb = FB.from_board(board)
        col, vir = RS.board_flat_from_fb(fb)
        ctx = {
            "own_vleft": board.virus_count(), "opp_vleft": board.virus_count(),
            "own_t": 0.0, "opp_t": 0.0, "opp_spawn_h": 0, "own_spawn_h": 0,
        }
        return self.pol.decide(col, vir, int(cur.a), int(cur.b),
                               int(nxt.a), int(nxt.b), ctx)

    def simulate(self, board, action, cur):
        return None


def play_arm(it, rd, k_clock, seeds):
    planner = ClockPlanner(k_clock)
    rows = []
    for seed in seeds:
        t0 = time.time()
        r = PL.play_one_game(it, rd, planner, LEVEL, SPEED, verbose=False, seed=seed)
        r["k_clock"] = k_clock
        r["seed"] = seed
        r["wall_s"] = round(time.time() - t0, 1)
        rows.append(r)
        print(f"kc{k_clock:g} seed={seed} won={r['won']} "
              f"{r['start_v']}->{r['end_v']} pills={r['pills']} {r['wall_s']}s",
              flush=True)
        with open(OUT / "games.jsonl", "a") as fh:
            fh.write(json.dumps(r) + "\n")
    return rows


def summarize(tag, rows):
    n = len(rows) or 1
    w = sum(1 for r in rows if r["won"])
    pills = sum(r["pills"] for r in rows) / n
    print(f"{tag}: {w}/{len(rows)} clear  mean_pills={pills:.1f}", flush=True)
    return w, pills


def main():
    it = PL.MesenInterface(work_dir=RELEASE)
    if not it.connect(timeout=12):
        print("no bridge", flush=True)
        return 2
    rd = lambda a: it.read_memory(a, 1)[0]
    it.set_step_mode(True)
    seeds = [SEED0 + i for i in range(N)]
    try:
        print(f"MEGADOSE L{LEVEL} MED n={N} seeds {seeds[0]}-{seeds[-1]}", flush=True)
        a = play_arm(it, rd, 0.0, seeds)
        b = play_arm(it, rd, 40.0, seeds)
    finally:
        it.set_input(0, []); it.set_step_mode(False); it.release(0); it.disconnect()
    wa, pa = summarize("k=0", a)
    wb, pb = summarize("k=40", b)
    delta = (wb / N) - (wa / N)
    hold = delta >= -0.10
    rec = {"n": N, "k0_clear": wa, "k40_clear": wb, "k0_pills": pa, "k40_pills": pb,
           "delta_clear": delta, "HOLD": hold}
    (OUT / "SUMMARY.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(("HOLD" if hold else "FAIL") + f" delta_clear={delta:+.2f}", flush=True)
    return 0 if hold else 1


if __name__ == "__main__":
    raise SystemExit(main())
