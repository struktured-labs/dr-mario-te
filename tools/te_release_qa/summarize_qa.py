#!/usr/bin/env python3
"""Turn a run_release_qa.sh matrix (TE v11 vs v10) into PASS/FAIL assertions + SUMMARY.md.

  usage: summarize_qa.py <out_root> <summary.md> [summary.json]
Exit 1 if any assertion fails. Every assertion that rules something OUT is paired with a positive
control showing the same instrument detects it: the published v9 for the 2P sign/wipe, v10 (= stock
1P) for the 1P GAME OVER wipe.
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
NEW = [r for r in RUNS if r.startswith("v11")]

# 1. liveness on every run (incl. controls)
for r in RUNS:
    s, L = stats(r), log(r)
    bad = re.findall(r"^(FREEZE|SCRIPT_ERROR|NAV_TIMEOUT|WAIT_TIMEOUT|ROUND_TIMEOUT).*$", L, re.M)
    check(f"{r}: completed, no freeze", done_code(r) == 0 and s.get("ramExec", 1) == 0 and s.get("maxClockStall", 999) <= 2 and not bad,
          f"DONE={done_code(r)} frames={s.get('frames')} ramExec={s.get('ramExec')} maxClockStall={s.get('maxClockStall')} {bad[:2]}")

# 2. DRSTUDYEND behaviour on every v11 run
for r in NEW:
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
for r in NEW:
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

# 4. STUDY pause layout + freeze + resume (every v11 run that paused)
for r in NEW:
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

# 4b. 1P GAME OVER hold (DRSTUDYEND 1P): every v11 game over keeps the final board + capsule until START,
# no GAME OVER box, nothing drawn over the bottle, START from +192 continues the stock way
GO_OK = {"keptToHold": "true", "firstFieldChange": "never", "firstNtChange": "never", "boxSeen": "false",
         "startLoopFrom": "+192", "maxBottleSprites": "0", "modeAfterStart": "1", "fieldsFE": "true",
         "optionsReached": "true"}


def go_lines(tag: str) -> list[dict]:
    return [dict(re.findall(r"(\w+)=(\S+)", m)) | {"tag": t} for t, m in re.findall(r"^GO1P (\S+) (.*)$", log(tag), re.M)]


for r in NEW:
    g = go_lines(r)
    if not g:
        continue
    s_ = stats(r)
    bad = [x["tag"] + ":" + ",".join(f"{k}={x.get(k)}" for k, v in GO_OK.items() if x.get(k) != v) for x in g
           if any(x.get(k) != v for k, v in GO_OK.items())]
    lv = sorted({(int(x["lvl"]), int(x["spd"])) for x in g})
    check(f"{r}: 1P game over keeps the final board until START, then stock", not bad and s_["over1pKept"] == len(g) ==
          s_["over1p"] and s_["over1pWiped"] == 0 and s_["over1pBox"] == 0 and s_["over1pToOptions"] == len(g),
          f"{len(g)} game overs (level,speed) {lv}; held to +{max(int(x['holdFrames']) for x in g)}; "
          f"START loop from +192; 0 bottle sprites; fields $FE + options after START {bad[:2]}")
    early = [x for x in g if x.get("earlyStart") == "true"]
    if early:
        check(f"{r}: START during the stock 192-frame wait is ignored (as stock)", all(x["keptToHold"] == "true" for x in early),
              f"{len(early)} game overs with START pressed at +100")
    if s_.get("next1pClean", 0) + s_.get("next1pDirty", 0):
        check(f"{r}: every 1P game starts clean (after a held game over too)", s_["next1pDirty"] == 0 and s_["next1pClean"] >= 1,
              f"clean={s_['next1pClean']} dirty={s_['next1pDirty']}")
for r in [x for x in RUNS if x.startswith("v10") and go_lines(x)]:
    g, s_ = go_lines(r), stats(r)
    check(f"{r} (positive control, v10 = stock 1P): wipe + GAME OVER box + START over the bottle detected",
          s_["over1pWiped"] == s_["over1p"] == len(g) and s_["over1pBox"] == len(g) and
          all(x["firstFieldChange"] == "+193" and x["maxBottleSprites"] == "5" for x in g),
          f"{len(g)} game overs: wiped at +193, box, 5 START sprites inside the bottle")
d = os.path.join(ROOT, "v11_shots", "dump_sh1p_gameover_prompt.txt")
if os.path.exists(d):
    oam = re.findall(r"^OAM \d+ Y=\s*(\d+) tile=(\w\w) attr=\w\w X=\s*(\d+)$", open(d).read(), re.M)
    start = [(int(y), t, int(x)) for y, t, x in oam if t in ("0D", "0F", "0B", "14") and 100 <= int(x) <= 150 and int(y) < 0xEF]
    check("v11_shots: the 1P START prompt is drawn below the bottle (Y=$D8)", [y for y, _, _ in start] == [216] * 5 and
          [x for _, _, x in start] == [109, 117, 125, 133, 141], f"OAM {start}")

# 4c. 1P stage clears
for r in [x for x in NEW if "clear1p" in x]:
    cl = re.findall(r"^CLEAR1P (clr\d) cleared .*$", log(r), re.M)
    nxt = re.findall(r"^CLEAR1P (clr\d) next level lvl=(\d+) clean=(\w+)", log(r), re.M)
    check(f"{r}: 1P stage clears (STAGE CLEAR, START, next level) still work", len(cl) >= 1 and len(nxt) == len(cl) and
          all(c == "true" for _, _, c in nxt), f"{len(cl)} clears, next levels {[(k, int(l)) for k, l, _ in nxt]}")

# 5. frame-by-frame comparisons
cmp_out = {}


def pair(a: str, b: str):
    if a in RUNS and b in RUNS:
        c = compare(os.path.join(ROOT, a), os.path.join(ROOT, b))
        cmp_out[f"{a} vs {b}"] = c
        return c
    return None


for sc in ("twop", "cpuidle", "clearwin"):
    c = pair(f"v10_{sc}", f"v11_{sc}")
    if c:
        check(f"2P v11_{sc} == v10 on every frame (full RAM)", c["first_diff_full_ram"] is None and c["mode_sequence_identical"]
              and c["frames"][0] == c["frames"][1], f"{c['frames'][0]} frames; {len(re.findall(r'^ENDSCREEN', log('v11_' + sc), re.M))} end screens")


def holds(tag: str) -> list[tuple[int, int]]:
    """1P scenarios only: per game over, [5->7 frame + 193 (the first frame the stock wipe shows), the 7->1
    START frame)."""
    L = log(tag)
    t7 = [int(f) for f in re.findall(r"^MODE f=(\d+) 5->7$", L, re.M)]
    t1 = [int(f) for f in re.findall(r"^MODE f=(\d+) 7->1$", L, re.M)]
    return [(a + 193, next(x for x in t1 if x > a)) for a in t7 if any(x > a for x in t1)]


def framesdiff(a: str, b: str):
    from analyze_qa import load
    A, B = load(os.path.join(ROOT, a)), load(os.path.join(ROOT, b))
    n = min(len(A), len(B))
    full = [A[i][0] for i in range(n) if A[i][2] != B[i][2]]
    nofield = [A[i][0] for i in range(n) if A[i][4] != B[i][4]]
    return len(A), len(B), full, nofield


for sc in ("go1p", "onep", "onep_np", "clear1p"):
    a, b = f"v10_{sc}", f"v11_{sc}"
    c = pair(a, b)
    if not c:
        continue
    na, nb, full, nofield = framesdiff(a, b)
    H = [(lo, hi) for lo, hi in holds(b)]
    inside = all(any(lo <= f < hi for lo, hi in H) for f in full)
    each = all(any(lo <= f < hi for f in full) for lo, hi in H)
    check(f"1P v11_{sc} == v10 except the boards during each held game over", na == nb and c["mode_sequence_identical"] and
          not nofield and inside and each and len(H) >= 1,
          f"{na} frames, mode sequence identical; RAM outside the fields $0400-$05FF, $00/$01 and the 5 START-letter OAM Y "
          f"bytes identical on every frame; full-RAM "
          f"differences only inside the {len(H)} holds [+193, START) ({len(full)} frames) and identical again from START")
for a, b in (("v11_twop", "v11ni_twop"), ("v11_go1p", "v11ni_go1p")):
    c = pair(a, b)
    if c:
        check(f"No-Intro NES 2.0 header ({b}) == classic header on every frame", c["first_diff_full_ram"] is None and
              c["mode_sequence_identical"], f"{c['frames'][0]} frames")
c = pair("base_onep_np", "v11_onep_np")   # informational: stock vs TE
if c:
    check("stock base vs v11 (1P, informational)", True,
          f"first RAM difference f{c['first_diff_full_ram']} (title: footer sprites in the OAM shadow); "
          f"mode sequence identical={c['mode_sequence_identical']}; differing frames by mode {c['differing_frames_by_mode']}")

# 6. soak duration
for r in [x for x in NEW if "soak" in x]:
    s_ = stats(r)
    check(f"{r}: >= 36,000 frames (10 min) of mixed play", s_.get("frames", 0) >= 36000,
          f"{s_.get('frames')} frames = {s_.get('frames', 0) / 60.0988 / 60:.1f} min; {s_.get('games1p')} 1P games "
          f"({s_.get('over1pKept')} held game overs), {s_.get('matches')} 2P matches ({s_.get('finals')} finals, "
          f"{s_.get('roundEnds')} round ends), {s_.get('pauses')} STUDY pauses")

npass = sum(1 for _, ok, _ in results if ok)
lines = [f"# TE v11 Mesen QA summary — {npass}/{len(results)} PASS", "",
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
