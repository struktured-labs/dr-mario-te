"""doc_void_check.py — catch a VOIDED number before it reaches anyone.

WHY THIS EXISTS
    2026-08-29: a reader quoted §2's power table (~6,000 pairs, "44% of the
    seed space") to the owner AFTER S1.3 had voided it and S1.7(a) had replaced
    it with ~286 pairs / 2.1%. A 21x error on an irreversible seed decision.
    The information needed to stop it was machine-readable and in the file.

    Root cause is structural, not carelessness: these registrations are
    APPEND-ONLY (R25), so the front is the oldest text and the binding text is
    at the end. Front-to-back is the wrong reading order, and nothing enforced
    a different one.

⚠ WHY A KEYWORD HEURISTIC IS NOT ENOUGH — measured, not asserted (R80).
    Scanning headings for SUPERSEDED/VOID/RETRACTED across this lane's own
    registrations:
      REGISTRATION_A5_BACKFILL.md has FOUR revisions that between them void the
      cost model TWICE, replace the whole production procedure, and reverse the
      primary arm. Its 9 revision headings match the keyword regex **0 times**
      (`# REVISION 1`, `## R1.2 — THE COST MODEL WAS 3.8-5x TOO HIGH`, ...).
      And where a heading DOES match, the TARGET is prose — "§2's POWER TABLE",
      "THE ... FINDING" — not a parseable reference.
    ⇒ A prose regex is a PROXY for supersession. Per this project's own law
      (PROXIES RULE OUT, NEVER RULE IN) it may rank candidates but must not be
      trusted to find them. So the convention below is PINNED, and unannotated
      supersession-looking sections are reported LOUDLY rather than skipped.

THE CONVENTION (pinned 2026-08-29)
    Inside each superseding section, one machine-readable line:

        <!-- VOIDS: §2 power table | BY: S1.7a | STALE: 6,000 pairs; 44%; -1.09pp -->

    VOIDS  what is now dead (free text, for the human)
    BY     the section that replaces it
    STALE  semicolon-separated strings that MUST NOT be quoted any more

MODES
    --doc  PATH        list the void table; flag STALE strings that still
                       appear OUTSIDE their own voided section
    --quote PATH FILE  ⇒ THE ONE THAT PREVENTS THE FAILURE: scan a draft
                       message/report for any STALE string from PATH
    --self-test        positive control; exits non-zero if it fails to fire

Exit 1 if a stale quote is found (or self-test fails), else 0.
"""
from __future__ import annotations
import argparse, re, sys, os, tempfile

ANNOT = re.compile(
    r"<!--\s*VOIDS:\s*(?P<voids>.*?)\s*\|\s*BY:\s*(?P<by>.*?)\s*"
    r"(?:\|\s*STALE:\s*(?P<stale>.*?)\s*)?-->", re.S)
# supersession-LOOKING headings, used ONLY to demand an annotation
LOOKS = re.compile(
    r"^#{1,3} .*\b(SUPERSEDED|SUPERSEDES|RETRACT\w*|VOID|CORRECTION|REVERSED|"
    r"DEMOTED|REVISION|REVISED)\b", re.I | re.M)


def parse(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    voids = []
    for m in ANNOT.finditer(txt):
        stale = [s.strip() for s in (m.group("stale") or "").split(";")
                 if s.strip()]
        voids.append(dict(voids=m.group("voids"), by=m.group("by"),
                          stale=stale, at=txt[:m.start()].count("\n") + 1))
    # ⚠ An annotation covers the SECTION IT IS IN — not "anything within N
    # lines". The first version used a 12-line proximity window and the
    # self-test caught it silently marking a LATER unannotated section as
    # covered: proximity is a PROXY for containment, and it fails exactly
    # where sections are short. Map by enclosing heading instead; that is
    # exact.
    heads = [(m.start(), txt[:m.start()].count("\n") + 1,
              len(m.group(0).strip()))
             for m in re.finditer(r"^#{1,6} ", txt, re.M)]

    def covered_by(pos):
        """The enclosing heading AND all its ancestors. An annotation inside a
        `##` child also covers the `#` parent it lives under — otherwise the
        parent is reported as unannotated forever and the check cries wolf,
        which converts a safety net into a liability (R27)."""
        stack = []
        for off, ln, lvl in heads:
            if off > pos:
                break
            while stack and stack[-1][1] >= lvl:
                stack.pop()
            stack.append((ln, lvl))
        return {ln for ln, _ in stack}

    annotated_secs = set()
    for v in voids:
        annotated_secs |= covered_by(txt.find(f"<!-- VOIDS: {v['voids']}"))
    unannot = []
    for h in LOOKS.finditer(txt):
        ln = txt[:h.start()].count("\n") + 1
        if ln not in annotated_secs:
            unannot.append((ln, txt[h.start():h.end()].strip()))
    return txt, voids, unannot


def cmd_doc(path):
    txt, voids, unannot = parse(path)
    print(f"=== {os.path.basename(path)}: {len(voids)} annotated supersession(s)")
    rc = 0
    for v in voids:
        print(f"  L{v['at']:<5} VOIDS {v['voids']!r}  ->  BY {v['by']}")
        for s in v["stale"]:
            print(f"           STALE: {s!r}")
    if unannot:
        rc = 1
        print(f"\n⚠ {len(unannot)} supersession-LOOKING heading(s) with NO "
              f"annotation — cannot map, so cannot protect:")
        for ln, h in unannot:
            print(f"  L{ln:<5} {h[:88]}")
        print("  => add a <!-- VOIDS: ... | BY: ... | STALE: ... --> line")
    return rc


def cmd_quote(path, draft):
    _txt, voids, _u = parse(path)
    text = open(draft, encoding="utf-8", errors="replace").read()
    hits = []
    for v in voids:
        for s in v["stale"]:
            if re.search(re.escape(s), text, re.I):
                hits.append((s, v["voids"], v["by"]))
    if not hits:
        print(f"OK — no stale figure from {os.path.basename(path)} appears in "
              f"{os.path.basename(draft)}")
        return 0
    print(f"⛔ {len(hits)} STALE FIGURE(S) IN {os.path.basename(draft)}:")
    for s, vd, by in hits:
        print(f"  {s!r} — voided with {vd!r}; use {by} instead")
    return 1


SELFTEST_DOC = """# Fake registration
## 2. Sizing
We need ~6,000 pairs, about 44% of the free streams.

## S1.3 — power table void
<!-- VOIDS: §2 power table | BY: S1.7a | STALE: 6,000 pairs; 44% -->
Superseded: the real demand is ~286 pairs.

# REVISION 9 — unannotated on purpose
This heading looks like a supersession but carries no annotation.
"""
SELFTEST_DRAFT = "I am telling the owner we need ~6,000 pairs, i.e. 44% of the commons.\n"
SELFTEST_CLEAN = "I am telling the owner we need ~286 pairs, i.e. 2.1% of the commons.\n"


def self_test():
    d = tempfile.mkdtemp()
    doc = os.path.join(d, "reg.md"); open(doc, "w").write(SELFTEST_DOC)
    bad = os.path.join(d, "bad.md"); open(bad, "w").write(SELFTEST_DRAFT)
    good = os.path.join(d, "good.md"); open(good, "w").write(SELFTEST_CLEAN)
    ok = True
    print("[self-test] 1. planted stale quote MUST be caught")
    if cmd_quote(doc, bad) != 1:
        print("  *** FAIL: did not fire on a known stale quote ***"); ok = False
    print("[self-test] 2. clean draft MUST stay silent (R21 non-fault control)")
    if cmd_quote(doc, good) != 0:
        print("  *** FAIL: fired on a clean draft ***"); ok = False
    print("[self-test] 3. unannotated supersession heading MUST be reported")
    if cmd_doc(doc) != 1:
        print("  *** FAIL: did not demand an annotation ***"); ok = False
    print("[self-test] " + ("ALL PASS" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc")
    ap.add_argument("--quote", nargs=2, metavar=("REG", "DRAFT"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if a.quote:
        sys.exit(cmd_quote(*a.quote))
    if a.doc:
        sys.exit(cmd_doc(a.doc))
    ap.print_help(); sys.exit(2)


if __name__ == "__main__":
    main()
