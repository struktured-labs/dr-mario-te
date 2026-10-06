#!/usr/bin/env python3
"""Turn a run_release_qa.sh matrix into PASS/FAIL assertions + SUMMARY.md.

  usage: summarize_qa.py <out_root> <summary.md> [summary.json]
Exit 1 if any assertion fails. Every assertion that rules something OUT is paired with a positive
control showing the same instrument detects it on the published v9 ROM.
"""
from __future__ import annotations
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_qa import compare  # noqa: E402

ROOT, MD = sys.argv[1], sys.argv[2]
JS = sys.argv[3] if len(sys.argv) > 3 else None
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def log(tag: str) -> str:
    p = os.path.join(ROOT, tag, "qa.log")
    return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""


def stats(tag: str) -> dict:
    m = re.search(r"^STATS (.*)$", log(tag), re.M)
    return {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", m.group(1))} if m else {}


def done_code(tag: str):
    m = re.search(r"^DONE (\d+)", log(tag), re.M)
    return int(m.group(1)) if m else None


RUNS = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)) and os.path.exists(os.path.join(ROOT, d, "qa.log")))
V10 = [r for r in RUNS if r.startswith("v10")]

# 1. liveness on every run (incl. controls)
for r in RUNS:
    s, L = stats(r), log(r)
    bad = re.findall(r"^(FREEZE|SCRIPT_ERROR|NAV_TIMEOUT|WAIT_TIMEOUT|ROUND_TIMEOUT).*$", L, re.M)
    check(f"{r}: completed, no freeze", done_code(r) == 0 and s.get("ramExec", 1) == 0 and s.get("maxClockStall", 999) <= 2 and not bad,
          f"DONE={done_code(r)} frames={s.get('frames')} ramExec={s.get('ramExec')} maxClockStall={s.get('maxClockStall')} {bad[:2]}")

# 2. DRSTUDYEND behaviour on every v10 run
for r in V10:
    s, L = stats(r), log(r)
    ends = re.findall(r"^ENDSCREEN .*$", L, re.M)
    if not ends:
        continue
    kept = all("keptLoser=false" not in e and "keptWinner=false" not in e for e in ends)
    # the bottle on screen must equal the board in RAM at +150: always for the loser; for the winner
    # too unless it won by a clear (its last clear can leave popped cells drawn as empty)
    nt150 = all(re.search(r"\+150 [^|]*ntLoser=true", e) and ("clearWin=true" in e or re.search(r"\+150 [^|]*ntWinner=true", e))
                for e in ends)
    check(f"{r}: every end screen keeps both final boards, no sign", kept and s["signSpritesSeen"] == 0 and
          s["lowerWipes"] == 0 and s["gameOverFills"] == 0,
          f"{len(ends)} end screens ({s['finals']} match finals); signSprites={s['signSpritesSeen']} wipes={s['lowerWipes']} "
          f"gameOverFills={s['gameOverFills']}")
    check(f"{r}: drawn bottles == board RAM at +150", nt150, f"{len(ends)} end screens")
    if s.get("matches", 0) > 1:
        check(f"{r}: next match starts clean", s["nextDirty"] == 0 and s["nextClean"] >= 1,
              f"clean={s['nextClean']} dirty={s['nextDirty']}")

# 2b. virus-clear wins: non-final clear screens keep the loser's board (and are stock -- see comparisons)
for r in V10:
    cl = re.findall(r"^CLEARSCREEN .*$", log(r), re.M)
    if cl:
        check(f"{r}: virus-clear round ends keep the loser's board, no sign", all("keptLoser=false" not in c and
              "signSprites=0" in c and "ntLoser=false" not in c for c in cl), f"{len(cl)} clear-win round ends")

# 3. positive controls: the same instrument sees the stock behaviour on the published v9
for r in [x for x in RUNS if x.startswith("v9d") and stats(x).get("roundEnds", 0) > 0]:
    s = stats(r)
    check(f"{r} (positive control, published v9): sign/wipe/GAME OVER detected", s["signSpritesSeen"] > 0 and
          s["lowerWipes"] > 0 and (s["gameOverFills"] > 0 or s["finals"] == 0),
          f"signSprites={s['signSpritesSeen']} wipes={s['lowerWipes']} gameOverFills={s['gameOverFills']}")

# 4. STUDY pause layout + freeze + resume (every v10 run that paused)
for r in V10:
    L = log(r)
    st = re.findall(r"^STUDY \S+ players=(\d) letterY=([\d,]+) tiles=(\S+) previews\(Y:X\)=(\S+) frozenP1=(\w+) frozenP2=(\w+)", L, re.M)
    if not st:
        continue
    ok = True
    for players, ys, tiles, prev, f1, f2 in st:
        want_y = "8,8,8,8,8" if players == "2" else "15,15,15,15,15"
        want_p = "51:56,51:64,51:184,51:192" if players == "2" else "69:190,69:198,255:255,255:255"
        ok &= (ys == want_y and prev == want_p and tiles == "0D,A0,0C,A1,A2" and f1 == "true" and f2 == "true")
    res = re.findall(r"^RESUME \S+ moved=(\w+)", L, re.M)
    ok &= bool(res) and all(x == "true" for x in res)
    check(f"{r}: STUDY pause (text, per-player previews, frozen board, clean resume)", ok,
          f"{len(st)} pauses ({sum(1 for x in st if x[0] == '1')} 1P / {sum(1 for x in st if x[0] == '2')} 2P), {len(res)} resumes")

# 5. frame-by-frame comparisons
cmp_out = {}


def pair(a: str, b: str):
    if a in RUNS and b in RUNS:
        c = compare(os.path.join(ROOT, a), os.path.join(ROOT, b))
        cmp_out[f"{a} vs {b}"] = c
        return c
    return None


c = pair("v9d_cpuidle", "v10_cpuidle")
c = pair("v9d_clearwin", "v10_clearwin")
if c:
    fin = int(re.search(r"^MODE f=(\d+) 4->7", log("v10_clearwin"), re.M).group(1))
    ta, tb = ([(int(f), t) for f, t in re.findall(r"^MODE f=(\d+) (\S+)$", log(x), re.M) if int(f) <= fin]
              for x in ("v9d_clearwin", "v10_clearwin"))
    check("clear-win rounds == published v9 until the clear-win match final", c["first_diff_full_ram"] is not None and
          c["first_diff_full_ram"] > fin and ta == tb,
          f"RAM identical through {log('v10_clearwin')[:re.search(r'^MODE f=\d+ 4->7', log('v10_clearwin'), re.M).start()].count(chr(10) + 'CLEARSCREEN')} "
          f"virus-clear round ends; first "
          f"difference f{c['first_diff_full_ram']} = inside the final (state 7 from f{fin}, after its 64-frame wait)")
for a, b in (("v9d_onep", "v10_onep"), ("v9d_onep_np", "v10_onep_np")):
    c = pair(a, b)
    if c:
        check(f"1P {b} == published v9 on every frame", c["frames_differing_minus_stack"] == 0 and c["first_diff_full_ram"] is None
              and c["mode_sequence_identical"], f"{c['frames'][0]} frames, full RAM incl. stack identical")
c = pair("v9d_twop", "v10_twop")
if c:
    first_end = int(re.search(r"^MODE f=(\d+) 4->5", log("v10_twop"), re.M).group(1)) + 1
    wins = [re.findall(r"^ENDSCREEN (\S+) final=(\w+) winner=(P\d)", log(t), re.M) for t in ("v9d_twop", "v10_twop")]
    ta, tb = (re.findall(r"^MODE f=(\d+) (\S+)$", log(t), re.M) for t in ("v9d_twop", "v10_twop"))
    same_t = next((i for i, (x, y) in enumerate(zip(ta, tb)) if x != y), min(len(ta), len(tb)))
    check("2P v10 == published v9 until the first round end; same match results after", c["first_diff_full_ram"] == first_end
          and wins[0] == wins[1] and len(ta) == len(tb),
          f"first RAM difference at f{c['first_diff_full_ram']} = the first round-end frame f{first_end}; "
          f"{len(wins[1])} rounds with identical winners/finals; mode transitions {len(ta)} vs {len(tb)}, the first {same_t} on "
          f"the same frame; frames {c['frames'][0]} vs {c['frames'][1]} (later drift = one-frame input-latch / NMI-phase "
          f"shifts after the lighter round-end frame -- stock behaviour, PR #28 EVIDENCE.txt section 5)")
for a, b in (("v10_twop", "v10ni_twop"), ("v10_onep", "v10ni_onep")):
    c = pair(a, b)
    if c:
        check(f"No-Intro NES 2.0 header ({b}) == classic header on every frame", c["first_diff_full_ram"] is None and
              c["mode_sequence_identical"], f"{c['frames'][0]} frames")
c = pair("base_onep_np", "v10_onep_np")   # informational: stock vs TE
if c:
    check("stock base vs v10 (1P, informational)", True,
          f"first RAM difference f{c['first_diff_full_ram']} (title: footer sprites in the OAM shadow); "
          f"mode sequence identical={c['mode_sequence_identical']}; differing frames by mode {c['differing_frames_by_mode']}")

# 6. soak duration
for r in [x for x in V10 if "soak" in x]:
    s = stats(r)
    check(f"{r}: >= 36,000 frames (10 min) of mixed play", s.get("frames", 0) >= 36000,
          f"{s.get('frames')} frames = {s.get('frames', 0) / 60.0988 / 60:.1f} min; {s.get('games1p')} 1P games, "
          f"{s.get('matches')} 2P matches ({s.get('finals')} finals, {s.get('roundEnds')} round ends), {s.get('pauses')} STUDY pauses")

npass = sum(1 for _, ok, _ in results if ok)
lines = [f"# TE v10 Mesen QA summary — {npass}/{len(results)} PASS", "",
         "| result | check | detail |", "|---|---|---|"]
for name, ok, detail in results:
    lines.append(f"| {'PASS' if ok else '**FAIL**'} | {name} | {detail} |")
lines += ["", "## Runs", "", "| run | rom md5 | frames | DONE |", "|---|---|---|---|"]
for r in RUNS:
    ex = open(os.path.join(ROOT, r, "exit.txt")).read().strip() if os.path.exists(os.path.join(ROOT, r, "exit.txt")) else ""
    md = re.search(r"rom md5 ([0-9a-f]{32})", ex)
    lines.append(f"| {r} | {md.group(1) if md else '?'} | {stats(r).get('frames')} | {done_code(r)} |")
open(MD, "w").write("\n".join(lines) + "\n")
if JS:
    json.dump({"results": results, "comparisons": cmp_out, "stats": {r: stats(r) for r in RUNS}}, open(JS, "w"), indent=1)
print("\n".join(lines[:len(results) + 4]))
sys.exit(0 if npass == len(results) else 1)
