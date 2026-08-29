#!/usr/bin/env python3
"""stale_check.py — STANDING CHECK for stale supersession + dangling links in the memory store.

WHY THIS EXISTS
---------------
2026-08-25: the next-gen coproc core was believed BLOCKED for six days on "1 of 54 samples
unexplained / arm (b) NOT PASSED". It was not. A later lane had run the full pre-registered
experiment and recorded CLOSED-BENIGN (zero discordance in 300,867 stores) in a SIBLING memory
16 minutes later -- but the first memory's `description:` line was never updated, so the stale
headline kept propagating and the main lane sat "blocked" on a resolved question.

An audit then found SEVEN instances of the same shape across 330 files, including one on the
program's #1 Read-first entry and one on a memory whose own body says "SELF-REFUTED ... the truth
inverts it". The tell is mechanical, so it should be a check and not a rediscovery.

Separately: `dr-mario-smarter-experiments.md` is linked from NINE memories and does not exist on
disk or in either index backup. A memory can be deleted while its inbound links survive and
nothing detects it. Hence check D.

WHAT IT CHECKS
--------------
  A  DANGLING LINKS      [[target]] with no target.md.  <- HARD FAILURE, unambiguous
  B  ORPHAN INBOUND      a file every link points at, that no longer exists (same as A, grouped
                         by target so you see "9 memories point at a deleted file")
  C  UNACKNOWLEDGED      body carries a reversal marker (SELF-REFUTED / RETRACTED / SUPERSEDED /
     REVERSAL           OVERTURNED / DO NOT BUILD / "was WRONG") while the `description:` carries
                         no correction marker at all.  <- this is the clean-failure-geometry and
                         endgame-planner-win shape, the two worst instances found.
  D  STATUS + LATER      description contains a STATUS WORD and at least one memory it links to
     SIBLING            was modified LATER. Cannot adjudicate contradiction automatically --
                         this RANKS candidates for a human read.

⚠ THIS IS A SCREEN, NOT A DECIDER. Per this project's own law (dr-mario-label-budget-rules,
"PROXIES RULE OUT, NEVER RULE IN") checks C and D rule candidates IN for reading; they do not
prove staleness, and a clean run does not prove freshness. A and B are exact.

POSITIVE CONTROL: run with --self-test. It injects a known-stale description into a temp copy of
the store and asserts the check FIRES. A check that has only ever been run on a clean store is
the "half-tested gate" this project has been bitten by (dr-mario-gate-standard-killed-mutants
rule 8: refute absence claims by REBUILDING, not asserting). --self-test must pass before any
zero from this script is believed.

USAGE
    python3 stale_check.py                 # report on the live store
    python3 stale_check.py --self-test     # positive control; exits non-zero if it fails to fire
    python3 stale_check.py --dir <path>    # check another copy
Exit code 1 if any HARD failure (A/B) is found, else 0. C/D never fail the run; they are a
worklist.
"""
from __future__ import annotations
import argparse, os, re, shutil, sys, tempfile

MEM_DEFAULT = os.path.expanduser(
    "~/.claude/projects/-home-struktured-projects-dr-mario-rl/memory")

# Words that assert a lifecycle state, i.e. that carry an expiry date.
STATUS = re.compile(r"\b(BLOCKED|NOT PASSED|NOT YET|PENDING|OPEN|REOPENED|IN FLIGHT|WAITING|"
                    r"STAGED|DRAFT|AWAITING|TODO|UNRESOLVED|UNEXPLAINED|UNTESTED|NEVER "
                    r"OBSERVED|NO_GO|NO-GO|VOID|FAILED|STANDS)\b", re.I)
# Markers that a claim somewhere has been reversed.
REVERSAL = re.compile(r"(SELF-REFUTED|RETRACTED|RETRACTION|SUPERSEDED|OVERTURNED|"
                      r"DO NOT BUILD|WAS WRONG|IS WRONG|NOW EXPLAINED|CORRECTED|"
                      r"NO LONGER|REVERSES THE)", re.I)
# If the description already says "I have been corrected", it is not unacknowledged.
ACKED = re.compile(r"(RETRACTED|SUPERSEDED|CORRECTED|OVERTURNED|STALE|⚠|CLOSED-BENIGN|ERRATUM)")
LINK = re.compile(r"\[\[([^\]|#]+?)\]\]")


def load(mem):
    out = {}
    for fn in sorted(os.listdir(mem)):
        if not fn.endswith(".md") or fn.startswith("MEMORY"):
            continue
        p = os.path.join(mem, fn)
        txt = open(p, encoding="utf-8", errors="replace").read()
        # description: may be a quoted string spanning lines, or a bare line
        desc = ""
        m = re.search(r"^description:\s*", txt, re.M)
        if m:
            seg = txt[m.end():]
            if seg.lstrip().startswith('"'):
                q = re.search(r'"(.*?)"\s*\n', seg, re.S)
                desc = q.group(1) if q else seg.split("\n")[0]
            else:
                desc = seg.split("\n")[0]
        desc = " ".join(desc.split())
        end = txt.find("\n---", txt.find("\n---") + 1)
        body = txt[end:] if end > 0 else txt
        out[fn[:-3]] = dict(file=p, name=fn[:-3], desc=desc, body=body,
                            mtime=os.path.getmtime(p),
                            links=sorted(set(LINK.findall(txt))))
    return out


def run(mem, quiet=False):
    M = load(mem)
    hard, soft = [], []

    # ---- A / B : dangling links, grouped by missing target
    missing = {}
    for n, d in M.items():
        for t in d["links"]:
            if t not in M:
                missing.setdefault(t, []).append(n)
    for t, srcs in sorted(missing.items(), key=lambda kv: -len(kv[1])):
        hard.append((len(srcs), t, srcs))

    # ---- C : body reversal the headline does not acknowledge
    for n, d in sorted(M.items()):
        if not d["desc"]:
            continue
        hits = [h.group(0) for h in REVERSAL.finditer(d["body"])]
        if hits and not ACKED.search(d["desc"]):
            soft.append(("C", n, sorted(set(h.upper() for h in hits))[:4], d["desc"][:130]))

    # ---- D : status word + a linked sibling modified later
    for n, d in sorted(M.items()):
        s = STATUS.search(d["desc"] or "")
        if not s:
            continue
        later = [t for t in d["links"] if t in M and M[t]["mtime"] > d["mtime"] + 60]
        if later:
            soft.append(("D", n, [s.group(0).upper()] + later[:3], d["desc"][:130]))

    if not quiet:
        print(f"stale_check: {len(M)} memories in {mem}\n")
        print("=" * 78)
        print("A/B  DANGLING LINK TARGETS (hard failure — a memory was deleted, links survived)")
        print("=" * 78)
        if not hard:
            print("  none")
        for cnt, t, srcs in hard:
            print(f"  ✗ [[{t}]] does not exist — linked from {cnt} memor{'y' if cnt==1 else 'ies'}:")
            for s in srcs:
                print(f"        {s}")
        print()
        print("=" * 78)
        print("C  BODY CARRIES A REVERSAL THE HEADLINE DOES NOT ACKNOWLEDGE  (read these)")
        print("=" * 78)
        cs = [x for x in soft if x[0] == "C"]
        print(f"  {len(cs)} candidates")
        for _, n, hits, desc in cs:
            print(f"  ? {n}\n      body says: {','.join(hits)}\n      headline : {desc}")
        print()
        print("=" * 78)
        print("D  STATUS WORD IN HEADLINE + A LINKED SIBLING MODIFIED LATER  (read these)")
        print("=" * 78)
        ds = [x for x in soft if x[0] == "D"]
        print(f"  {len(ds)} candidates")
        for _, n, info, desc in ds:
            print(f"  ? {n}  [{info[0]}]  later sibling(s): {', '.join(info[1:])}\n      {desc}")
        print()
        print("REMINDER: C and D are a SCREEN. They rule candidates IN for a human read; they do "
              "not\nprove staleness, and an empty C/D does not prove the store is fresh. "
              "A/B are exact.")
    return hard, soft


def self_test(mem):
    """POSITIVE CONTROL — inject known-stale content and assert the check fires."""
    tmp = tempfile.mkdtemp(prefix="stalecheck_pc_")
    try:
        for fn in os.listdir(mem):
            if fn.endswith(".md"):
                shutil.copy2(os.path.join(mem, fn), tmp)
        # mutant 1: a description asserting BLOCKED, linking a sibling touched later
        sib = "__pc_sibling__"
        open(os.path.join(tmp, sib + ".md"), "w").write(
            "---\nname: __pc_sibling__\ndescription: \"resolved\"\n---\n\nresolved.\n")
        open(os.path.join(tmp, "__pc_stale__.md"), "w").write(
            "---\nname: __pc_stale__\ndescription: \"lane is BLOCKED on one unexplained sample\"\n"
            "---\n\nblocked, see [[__pc_sibling__]].\n")
        os.utime(os.path.join(tmp, sib + ".md"), (9e9, 9e9))
        # mutant 2: body reversal, headline silent
        open(os.path.join(tmp, "__pc_reversal__.md"), "w").write(
            "---\nname: __pc_reversal__\ndescription: \"the thing WINS, proven\"\n---\n\n"
            "## SELF-REFUTED: it does not win\n")
        # mutant 3: dangling link
        open(os.path.join(tmp, "__pc_dangling__.md"), "w").write(
            "---\nname: __pc_dangling__\ndescription: \"x\"\n---\n\nsee [[__pc_no_such_file__]].\n")

        hard, soft = run(tmp, quiet=True)
        got_a = any(t == "__pc_no_such_file__" for _, t, _ in hard)
        got_c = any(k == "C" and n == "__pc_reversal__" for k, n, _, _ in soft)
        got_d = any(k == "D" and n == "__pc_stale__" for k, n, _, _ in soft)
        print("POSITIVE CONTROL (the check must FIRE on planted staleness):")
        print(f"  A dangling link detected .................. {'PASS' if got_a else 'FAIL'}")
        print(f"  C unacknowledged body reversal detected ... {'PASS' if got_c else 'FAIL'}")
        print(f"  D status word + later sibling detected .... {'PASS' if got_d else 'FAIL'}")
        ok = got_a and got_c and got_d
        print("  ⇒ " + ("CONTROL PASSES — a zero from this script is meaningful."
                        if ok else "CONTROL FAILED — DO NOT TRUST ANY ZERO FROM THIS SCRIPT."))
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=MEM_DEFAULT)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test(a.dir) else 1)
    hard, _ = run(a.dir)
    sys.exit(1 if hard else 0)
