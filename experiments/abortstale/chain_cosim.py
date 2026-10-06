#!/usr/bin/env python3
"""Chained-pipeline co-sim driver (sim_pubchain.cpp): does a copro search's publish timeline depend on what the copro
was doing when its GO arrived?

The banked publish timelines (tmp/fair_v1_replay/timelines/pubtrace_*.jsonl, tools/lateflip/sim_pubtrace.cpp on
claude/late-flip) run EVERY decision in a fresh Verilator process: an idle, never-used copro at GO. On the cart the
copro is never fresh: the previous search has either DONE'd and spins (today's driver), or -- with DRABORTSTALE -- is
still RUNNING while the new board is uploaded and the GO's reset pulse lands. Subcommands:

  fresh FW_HEX TIMELINE.jsonl OUT.jsonl [--only p,..] [-j J]
        every decision in its own process (= the banked method), raw clocks kept: the reference
  pairs FW_HEX TIMELINE.jsonl FRESH.jsonl OUT.jsonl --q 0.3,0.6,0.9 [--wgap N] [--only p,..] [-j J]
        for every consecutive pair (A, B) and q: one process uploads A, aborts it at q * DONE(A) (fresh), uploads B
        WHILE A's search still runs (board bytes N NES cycles apart, as the cart's loop), GO, runs B to DONE
  run   FW_HEX TIMELINE.jsonl OUT.jsonl SCHED [--abort] [--wgap N] [--only p,..]
        a whole game in ONE process. SCHED = "mesen:<lateflip log>" (GO frames of that Mesen run; the same pill
        order), "frac:<q>" (pill i uploaded at q * DONE(i-1)), "after:<frames>". --abort: the upload starts on
        schedule even if the previous search has not DONE'd (DRABORTSTALE); else it waits for DONE (today).
  window FW_HEX TIMELINE.jsonl FRESH.jsonl OUT.jsonl --log <A-cart lateflip log> [--tail 2] [--wgap N] [-j J]
        the abort arm restricted to its non-idle stretches (see cmd_window); records carry window / lead
  cmp   FRESH.jsonl OUT.jsonl      exact comparison vs the fresh reference (see classify())

Every record: p, end DONE|ABORT, end_clk (master clocks since GO), raw [[clk, col, orient], ...] (every change the
poll saw), pubs (pubtrace_g2.py conversion: valid publishes after the firmware's $FF store, frames to 0.01), done_f,
final, tuck; pairs/run records also upl_clk and (pairs) q / a.
"""
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

FRAME = 29780.5 * 48
VSIM = os.environ.get("VSIM", "/home/struktured/projects/dr_mario_rl/tmp/abort_stale/cosim/obj_chain/vsim_chain")
sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/experiments/cosim_farm")
from cosim import VAR_OF_O4  # noqa: E402  (copro o4 -> action variant)


def act_of(col, o4):
    return VAR_OF_O4[o4] * 8 + col if 0 <= o4 < len(VAR_OF_O4) else -1   # o4 $FF: nothing published yet


def valid(raw):
    """The publishes after the firmware's $FF store (the entries before it are the previous search's mailbox)."""
    out, seen = [], False
    for clk, c, o in raw:
        if o == 0xFF:
            seen = True; continue
        if seen:
            out.append([clk, c, o])
    return out


def convert(raw):
    return [[round(clk / FRAME, 2), c, o, act_of(c, o)] for clk, c, o in valid(raw)]


def parse(line):
    t = line.split()
    assert t[0] == "PUB", line
    n = int(t[1]); raw = [[int(t[2 + 3 * k]), int(t[3 + 3 * k]), int(t[4 + 3 * k])] for k in range(n)]
    i = 2 + 3 * n
    assert t[i] == "END"
    return dict(end=t[i + 1], end_clk=int(t[i + 2]), col=int(t[i + 3]), o4=int(t[i + 4]),
                tuck=[int(t[i + 6]), int(t[i + 7])], upl_clk=int(t[i + 9]), raw=raw)


def record(p, d, **extra):
    return dict(p=p, end=d["end"], end_clk=d["end_clk"], upl_clk=d["upl_clk"], raw=d["raw"], pubs=convert(d["raw"]),
                done_f=round(d["end_clk"] / FRAME, 2), final=[d["col"], d["o4"], act_of(d["col"], d["o4"])],
                tuck=d["tuck"], **extra)


PAUSE = os.environ.get("COSIM_PAUSE", "/home/struktured/projects/dr_mario_rl/tmp/abort_stale/PAUSE")


def sim(fw, lines, wgap=0):
    import time
    while os.path.exists(PAUSE):          # shared-box pause switch: start no new co-sim while it exists
        time.sleep(5)
    simdir = os.path.dirname(os.path.abspath(fw))
    assert os.path.basename(fw) == "copro_rom.hex", "FW_HEX must be a .../copro_rom.hex (the RTL $readmemh's it)"
    proc = subprocess.run(["nice", "-n", "19", VSIM, "64", str(wgap), "0"], cwd=simdir,
                          input="\n".join(lines) + "\nBYE\n", capture_output=True, text=True)
    reps = [parse(l) for l in proc.stdout.splitlines() if l.startswith("PUB")]
    if len(reps) != len(lines):
        raise RuntimeError(f"sim returned {len(reps)} of {len(lines)}: {proc.stdout[-300:]} {proc.stderr[-300:]}")
    return reps


def load_tl(tl, only=None):
    R = [json.loads(l) for l in open(tl)]
    return [r for r in R if not only or r["p"] in only]


def cmd_fresh(fw, tl, out, only, j):
    R = load_tl(tl, only)
    with ThreadPoolExecutor(j) as ex:
        reps = list(ex.map(lambda r: sim(fw, [f"0 0 {r['upload']}"])[0], R))
    with open(out, "w") as f:
        for r, d in zip(R, reps):
            f.write(json.dumps(record(r["p"], d)) + "\n")
    print(f"fresh: {len(R)} -> {out}")


def cmd_pairs(fw, tl, fresh, out, qs, wgap, only, j):
    R = load_tl(tl)
    Fr = {x["p"]: x for x in map(json.loads, open(fresh))}
    jobs = []
    for a, b in zip(R, R[1:]):
        if only and b["p"] not in only:
            continue
        if a["p"] not in Fr or b["p"] not in Fr:
            continue
        for q in qs:
            go_at = int(q * Fr[a["p"]]["end_clk"])
            jobs.append((a, b, q, [f"0 1 {a['upload']}", f"{go_at} 1 {b['upload']}"]))
    with ThreadPoolExecutor(j) as ex:
        reps = list(ex.map(lambda x: sim(fw, x[3], wgap), jobs))
    with open(out, "w") as f:
        for (a, b, q, _), (da, db) in zip(jobs, reps):
            f.write(json.dumps(record(b["p"], db, q=q, a=a["p"], a_end=da["end"], a_end_clk=da["end_clk"],
                                      a_raw=da["raw"])) + "\n")
    print(f"pairs: {len(jobs)} -> {out}")


def mesen_go_frames(log):
    """Absolute frame of each case pill's GO in a lateflip_probe log: INJECT f + (f - k) of the first T line with
    pend == 0 and k >= 0."""
    import re
    inj, go = {}, {}
    I = re.compile(r"^INJECT p(\d+) at f=(\d+)")
    T = re.compile(r"^T p(\d+) f=(\d+) .*? pend=(\d+) .*? k=(-?\d+)")
    for line in open(log, errors="replace"):
        m = I.match(line)
        if m:
            inj[int(m.group(1))] = int(m.group(2)); continue
        m = T.match(line)
        if m:
            p, f, pend, k = (int(x) for x in m.groups())
            if p not in go and pend == 0 and k >= 0:
                go[p] = inj[p] + f - k
    return go


def cmd_run(fw, tl, out, sched, abort, wgap, only, fresh=None):
    R = load_tl(tl, only)
    Fr = {x["p"]: x for x in map(json.loads, open(fresh))} if fresh else {}
    kind, _, arg = sched.partition(":")
    gos = mesen_go_frames(arg) if kind == "mesen" else None
    lines, prev = [], None
    for r in R:
        p = r["p"]
        if prev is None:
            go_at = 0
        elif kind == "mesen":
            go_at = int(round((gos[p] - gos[prev["p"]]) * FRAME))
        elif kind == "frac":
            dc = Fr[prev["p"]]["end_clk"] if prev["p"] in Fr else prev["done_clk"]
            go_at = int(float(arg) * dc)
        elif kind == "after":
            go_at = int(round(float(arg) * FRAME))
        else:
            raise SystemExit("bad SCHED " + sched)
        lines.append(f"{go_at} {1 if abort else 0} {r['upload']}")
        prev = r
    reps = sim(fw, lines, wgap)
    with open(out, "w") as f:
        for r, d in zip(R, reps):
            f.write(json.dumps(record(r["p"], d)) + "\n")
    print(f"run: {len(R)} -> {out}")


def cmd_window(fw, tl, fresh, out, log, wgap, j, tail=2):
    """Abort-arm co-sim restricted to the stretches where the pipeline is NOT idle at GO. A pill is aborted-into when
    its Mesen GO (DRABORTSTALE cart run `log`) comes before the previous pill's fresh DONE. Each cluster of such pills
    runs in ONE process from the pill before the cluster (whose own GO found a DONE'd copro) through `tail` pills past
    the last abort, on the Mesen GO schedule, aborting on schedule. Every other pill's GO finds a copro that DONE'd and
    spins: the wait-mode chains measure that state (and the window's own lead-in / tail pills re-check it)."""
    R = load_tl(tl)
    Fr = {x["p"]: x for x in map(json.loads, open(fresh))}
    gos = mesen_go_frames(log)
    R = [r for r in R if r["p"] in gos]
    idx = {r["p"]: i for i, r in enumerate(R)}
    ab = [False] * len(R)
    for i in range(1, len(R)):
        gap = (gos[R[i]["p"]] - gos[R[i - 1]["p"]]) * FRAME
        ab[i] = gap < Fr[R[i - 1]["p"]]["end_clk"] + 2 * FRAME     # +2 f: frame-quantised GO, decide in the sim
    wins = []
    for i in range(1, len(R)):
        if not ab[i]:
            continue
        s0, e0 = i - 1, min(len(R) - 1, i + tail)
        if wins and s0 <= wins[-1][1]:
            wins[-1][1] = max(wins[-1][1], e0)
        else:
            wins.append([s0, e0])
    jobs = []
    for s0, e0 in wins:
        lines = []
        for k in range(s0, e0 + 1):
            go_at = 0 if k == s0 else int(round((gos[R[k]["p"]] - gos[R[k - 1]["p"]]) * FRAME))
            lines.append(f"{go_at} 1 {R[k]['upload']}")
        jobs.append(([R[k]["p"] for k in range(s0, e0 + 1)], lines))
    with ThreadPoolExecutor(j) as ex:
        reps = list(ex.map(lambda x: sim(fw, x[1], wgap), jobs))
    n = 0
    with open(out, "w") as f:
        for (ps, _), ds in zip(jobs, reps):
            for k, (pp, d) in enumerate(zip(ps, ds)):
                f.write(json.dumps(record(pp, d, window=[ps[0], ps[-1]], lead=(k == 0))) + "\n"); n += 1
    print(f"window: {sum(ab)} aborted-into pills, {len(wins)} windows, {n} records -> {out}")


def served(clk):
    """The frame (since GO) at which lateflip_probe.lua serves an event at `clk`: its schedule holds times rounded to
    0.01 f and serves an event once the integer frame count k >= t."""
    return math.ceil(round(clk / FRAME, 2) - 1e-9)


def classify(c, f):
    """exact      : same valid publishes (clock, col, orient), same end clock, final and tuck
       mesen-same : same valid publish VALUES in order, same final/tuck, and every event served on the same Mesen frame
       timing     : same values / final / tuck, some event on a different frame
       DECISION   : a different publish value sequence, final or tuck
    ABORT-ended records compare the valid publishes strictly before the abort with the fresh run's."""
    vc, vf = valid(c["raw"]), valid(f["raw"])
    if c["end"] == "ABORT":
        vf = [x for x in vf if x[0] < c["end_clk"]]
        vc = [x for x in vc if x[0] < c["end_clk"]]
        if vc == vf:
            return "exact"
        if [x[1:] for x in vc] == [x[1:] for x in vf]:
            return "mesen-same" if [served(x[0]) for x in vc] == [served(x[0]) for x in vf] else "timing"
        return "DECISION"
    same_vals = [x[1:] for x in vc] == [x[1:] for x in vf] and c["final"] == f["final"] and c["tuck"] == f["tuck"]
    if not same_vals:
        return "DECISION"
    if vc == vf and c["end_clk"] == f["end_clk"]:
        return "exact"
    if [served(x[0]) for x in vc] == [served(x[0]) for x in vf] and served(c["end_clk"]) == served(f["end_clk"]):
        return "mesen-same"
    return "timing"


def cmd_cmp(fresh, out, quiet=False):
    Fr = {x["p"]: x for x in map(json.loads, open(fresh))}
    import collections
    cnt = collections.Counter(); ex = collections.defaultdict(list); dmax = 0
    n = 0
    for l in open(out):
        c = json.loads(l)
        if c["p"] not in Fr:
            cnt["no-ref"] += 1; continue
        n += 1
        k = classify(c, Fr[c["p"]])
        cnt[k] += 1; cnt[c["end"]] += 1
        f = Fr[c["p"]]
        vc, vf = valid(c["raw"]), valid(f["raw"])
        if k in ("mesen-same", "timing") and len(vc) == len(vf):
            d = max([abs(a[0] - b[0]) for a, b in zip(vc, vf)] + ([abs(c["end_clk"] - f["end_clk"])] if c["end"] == "DONE" else [0]))
            dmax = max(dmax, d)
        if k != "exact":
            ex[k].append(c["p"] if "q" not in c else (c["a"], c["p"], c["q"]))
    if n == 0:
        print(f"{os.path.basename(out)}: EMPTY -- no records (a crashed or missing run is not a pass)")
        return 1
    print(f"{os.path.basename(out)}: n={n} DONE {cnt['DONE']} ABORT {cnt['ABORT']} | exact {cnt['exact']} "
          f"mesen-same {cnt['mesen-same']} timing {cnt['timing']} DECISION {cnt['DECISION']} | max |dclk| "
          f"{dmax} ({dmax / FRAME:.4f} f)")
    if not quiet:
        for k in ("timing", "DECISION", "mesen-same"):
            if ex[k]:
                print(f"  {k}: {ex[k][:30]}")
    return cnt["DECISION"] + cnt["timing"]


def opt(rest, name, default=None, conv=str):
    return conv(rest[rest.index(name) + 1]) if name in rest else default


if __name__ == "__main__":
    a = sys.argv[1:]
    rest = a
    only = opt(rest, "--only", None, lambda s: set(int(x) for x in s.split(",")))
    j = opt(rest, "-j", 4, int)
    wgap = opt(rest, "--wgap", 0, int)
    if a[0] == "fresh":
        cmd_fresh(a[1], a[2], a[3], only, j)
    elif a[0] == "pairs":
        cmd_pairs(a[1], a[2], a[3], a[4], [float(x) for x in opt(rest, "--q", "0.3,0.6,0.9").split(",")], wgap, only, j)
    elif a[0] == "run":
        cmd_run(a[1], a[2], a[3], a[4], "--abort" in rest, wgap, only, opt(rest, "--fresh"))
    elif a[0] == "window":
        cmd_window(a[1], a[2], a[3], a[4], opt(rest, "--log"), wgap, j, opt(rest, "--tail", 2, int))
    elif a[0] == "cmp":
        sys.exit(1 if cmd_cmp(a[1], a[2]) else 0)
    else:
        raise SystemExit(__doc__)
