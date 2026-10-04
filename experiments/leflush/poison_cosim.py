#!/usr/bin/env python3
"""DRLEFLUSH poison co-sim driver (sim_poison.cpp). Every decision runs in its own process; at its GO's reset release
the selected engine registers are overwritten with random values (an arbitrary superset of what a preempted search can
leave behind), and the search is compared with the FRESH reference of the same firmware (chain_cosim.py fresh, the
banked one-process-per-decision method) using chain_cosim.classify (exact = same valid publishes, clocks, DONE, final,
tuck).

  run   FW_HEX TIMELINE.jsonl OUT.jsonl --spec SPEC --seeds 1,2 [--ram] [--only p,..] [-j J]
        SPEC: none | all | allbut:a,b | only:a,b   (register names: gen_poison.py's table)
  cmp   FRESH.jsonl OUT.jsonl   -> per seed: exact / mesen-same / timing / DECISION / hang counts
  dumpcmp OUT.txt   first BASE issue: differing registers (LIVE-IN ones flagged); BASE duration + outputs; then every
        later engine command's sequence / duration / results, pair vs fresh
  dump  FW_HEX TIMELINE.jsonl A B Q OUT.txt [--k K]   pair A->B, A aborted at Q * fresh DONE(A) (byte gaps 18), the
        register dump at B's first K engine commands (POISON none) -- and B alone, fresh, for the comparison

The poison sim has no wall-clock timeout (a hang is CLOCK_LIMIT master clocks); the shared-box PAUSE file is honoured
before every new process, and running ones are SIGSTOP'ed by the lane throttle.
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale")
import chain_cosim as CC  # noqa: E402

PSIM = os.environ.get("PSIM", "/home/struktured/projects/dr_mario_rl/tmp/v11/cosim/obj_poison/vsim_poison")
PAUSE = os.environ.get("COSIM_PAUSE", "/home/struktured/projects/dr_mario_rl/tmp/v11/PAUSE")


def psim(fw, lines, env, wgap=0):
    while os.path.exists(PAUSE):
        time.sleep(5)
    assert os.path.basename(fw) == "copro_rom.hex"
    e = dict(os.environ, **env)
    proc = subprocess.run(["nice", "-n", "19", PSIM, "64", str(wgap), "0"], cwd=os.path.dirname(os.path.abspath(fw)),
                          input="\n".join(lines) + "\nBYE\n", capture_output=True, text=True, env=e)
    return proc.stdout, proc.returncode


def cmd_run(fw, tl, out, spec, seeds, ram, only, j):
    R = CC.load_tl(tl, only)
    jobs = [(r, s) for s in seeds for r in R]

    def one(x):
        r, s = x
        env = {"POISON": spec, "POISON_SEED": str(s), "POISON_RAM": "1" if ram else "0"}
        o, rc = psim(fw, [f"0 0 {r['upload']}"], env)
        pubs = [l for l in o.splitlines() if l.startswith("PUB")]
        pois = [l for l in o.splitlines() if l.startswith("POISONED")]
        if rc != 0 or len(pubs) != 1 or (spec != "none" or ram) and len(pois) != 1:
            return dict(p=r["p"], seed=s, spec=spec, ram=ram, hang=True, rc=rc, tail=o[-200:])
        return CC.record(r["p"], CC.parse(pubs[0]), seed=s, spec=spec, ram=ram, poisoned=pois[0] if pois else "")
    with ThreadPoolExecutor(j) as ex:
        res = list(ex.map(one, jobs))
    with open(out, "w") as f:
        for d in res:
            f.write(json.dumps(d) + "\n")
    print(f"poison run: {len(res)} ({len(R)} decisions x seeds {seeds}, spec {spec}, ram {ram}) -> {out}")


def cmd_cmp(fresh, out):
    import collections
    Fr = {x["p"]: x for x in map(json.loads, open(fresh))}
    by = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(list)
    n = 0
    for l in open(out):
        c = json.loads(l)
        n += 1
        k = "hang" if c.get("hang") else CC.classify(c, Fr[c["p"]])
        by[c["seed"]][k] += 1
        if k != "exact":
            ex[k].append((c["p"], c["seed"]))
    if n == 0:
        print(f"{os.path.basename(out)}: EMPTY"); return 1
    bad = 0
    for s in sorted(by):
        cnt = by[s]
        tot = sum(cnt.values())
        print(f"{os.path.basename(out)} seed {s}: n={tot} exact {cnt['exact']} mesen-same {cnt['mesen-same']} "
              f"timing {cnt['timing']} DECISION {cnt['DECISION']} hang {cnt['hang']}")
        bad += tot - cnt["exact"]
    for k in ("DECISION", "hang", "timing", "mesen-same"):
        if ex[k]:
            print(f"  {k}: {ex[k][:40]}")
    return bad


def cmd_dump(fw, tl, a, b, q, out, k):
    R = {r["p"]: r for r in CC.load_tl(tl)}
    # fresh DONE of A on THIS firmware (one process, POISON none)
    o, _ = psim(fw, [f"0 0 {R[a]['upload']}"], {})
    da = CC.parse([l for l in o.splitlines() if l.startswith("PUB")][0])
    go_at = int(q * da["end_clk"])
    o_pair, _ = psim(fw, [f"0 1 {R[a]['upload']}", f"{go_at} 1 {R[b]['upload']}"], {"DUMP": str(k)}, wgap=18)
    o_fresh, _ = psim(fw, [f"0 0 {R[b]['upload']}"], {"DUMP": str(k)})
    with open(out, "w") as f:
        f.write(f"# pair {a}->{b} q={q} go_at={go_at} fw={fw}\n")
        f.write("## PAIR\n" + o_pair + "## FRESH\n" + o_fresh)
    print(f"dump {a}->{b} q={q} -> {out}")


LIVE = ("dphase",)                       # read before written by CMD 1/4/6 (gen_poison / LEFLUSH.txt enumeration)
BASE_OUT = ("base_maxh", "base_holes", "base_toprisk", "base_spawn", "base_setup", "base_pol", "base_buried",
            "base_matched", "base_rdy", "base_vrdy", "base_anyvir", "colh", "b_row", "b_colv", "b_top", "b_tvir", "b_tcol",
            "win", "bcell", "blink")


def parse_dump(txt):
    """-> [(event, clk, cmd, {reg: value})] per section (PAIR / FRESH); the pair section keeps only the LAST decision."""
    out = {}
    sec = None
    for l in txt.splitlines():
        if l.startswith("## "):
            sec = l[3:].strip(); out[sec] = []; continue
        if l.startswith("DUMP ") and sec:
            t = l.split()
            out[sec].append((t[1], int(t[2]), int(t[3]), dict(kv.split("=", 1) for kv in t[4:])))
    return out


def cmd_dumpcmp(path):
    S = parse_dump(open(path).read())
    A, F = S["PAIR"], S["FRESH"]
    print(f"{os.path.basename(path)}: events pair {len(A)} fresh {len(F)}")
    # the first BASE (CMD 6) issue and its DONE
    def first(ev, cmd):
        for i, e in enumerate(ev):
            if e[0] == "go" and e[2] == cmd:
                return i
    ia, iff = first(A, 6), first(F, 6)
    if ia is None or iff is None:
        print("  no CMD 6"); return 1
    ga, gf = A[ia], F[iff]
    da, df = A[ia + 1], F[iff + 1]
    diff_go = sorted(k for k in ga[3] if ga[3][k] != gf[3][k])
    print(f"  first BASE issue: clk pair {ga[1]} fresh {gf[1]}; {len(diff_go)} registers differ; LIVE-IN differing: "
          f"{[k for k in diff_go if k in LIVE]} (dphase pair {ga[3]['dphase']} fresh {gf[3]['dphase']})")
    print(f"  first BASE DONE: took pair {da[1] - ga[1]} fresh {df[1] - gf[1]} clocks; BASE outputs differing: "
          f"{[k for k in BASE_OUT if da[3][k] != df[3][k]]}")
    # every later engine command: same command sequence, same per-command duration, and the registers THAT COMMAND
    # PRODUCES identical (a register a command does not write may keep its stale value: e.g. sco after an illegal
    # CMD 7, strand before the first CMD 8 -- the firmware does not read those), plus the CUR board after every command
    PROD = {1: ("sco", "win"), 2: (), 3: (), 4: ("legal", "rv_cells", "rv_vir", "imm", "chain"),
            6: BASE_OUT, 7: ("legal", "rv_cells", "rv_vir", "imm", "chain"), 8: ("strand",)}
    n = min(len(A) - ia, len(F) - iff)
    bad = []
    cmd = None
    for k in range(n):
        a, f = A[ia + k], F[iff + k]
        if a[0] != f[0] or a[2] != f[2]:
            bad.append((k, "sequence")); break
        if k and (a[1] - A[ia + k - 1][1]) != (f[1] - F[iff + k - 1][1]):
            bad.append((k, "duration"))
        if a[0] == "go":
            cmd = a[2]; sl = int(a[3]["lev_a_sl"], 16); continue
        regs = list(PROD.get(cmd, ())) + ["bcell", "blink"]
        # sco/win are produced by a legal NODE, and by a legal NON-clearing DELTA (a clearing one sets dv_fallback, and
        # rv_cells > 0, and leaves sco for the CMD 4 the firmware re-issues; dv_fallback is reset-cleared, not dumped)
        if (cmd == 4 and a[3]["legal"] == "1") or (cmd == 7 and a[3]["legal"] == "1" and a[3]["rv_cells"] == "0"):
            regs += ["sco", "win"]
        dr = [r for r in regs if a[3][r] != f[3][r]]
        if cmd == 3 and a[3]["slotram.mem"].split(".")[sl * 128:(sl + 1) * 128] != f[3]["slotram.mem"].split(".")[sl * 128:(sl + 1) * 128]:
            dr.append(f"slot{sl}")
        if dr:
            bad.append((k, cmd, dr))
    ncmd = sum(1 for e in A[ia:ia + n] if e[0] == "go")
    print(f"  from the first BASE on, {ncmd} engine commands: sequence, durations, produced results and CUR board identical: "
          f"{'YES' if not bad else 'NO ' + str(bad[:6])}")
    still = sorted(k for k in A[ia + n - 1][3] if A[ia + n - 1][3][k] != F[iff + n - 1][3][k])
    print(f"  registers still holding pair-only values after the last dumped command (stale, never read before written): "
          f"{still}")
    return 0 if not bad and da[1] - ga[1] == df[1] - gf[1] else 1


def opt(rest, name, default=None, conv=str):
    return conv(rest[rest.index(name) + 1]) if name in rest else default


if __name__ == "__main__":
    a = sys.argv[1:]
    only = opt(a, "--only", None, lambda s: set(int(x) for x in s.split(",")))
    j = opt(a, "-j", 8, int)
    if a[0] == "run":
        cmd_run(a[1], a[2], a[3], opt(a, "--spec", "all"), [int(x) for x in opt(a, "--seeds", "1").split(",")],
                "--ram" in a, only, j)
    elif a[0] == "cmp":
        sys.exit(1 if cmd_cmp(a[1], a[2]) else 0)
    elif a[0] == "dumpcmp":
        sys.exit(cmd_dumpcmp(a[1]))
    elif a[0] == "dump":
        cmd_dump(a[1], a[2], int(a[3]), int(a[4]), float(a[5]), a[6], opt(a, "--k", 40, int))
    else:
        raise SystemExit(__doc__)
