#!/usr/bin/env python3
"""S0-A verdict router — implements PREREG_S0A.md sec 5, 6 and 7 verbatim.

The rules below were fixed before any screen row existed.  Kept in its own file
so `gate_s0a.py` can mutate it in isolation and prove each rule is load-bearing:
a check that cannot fail is not a check.

VERDICTS
  VOID           a sec-7 condition fired.  Not a null -- the run tells us nothing
                 and must be re-scoped.
  CLOSE          U(overall) < 2%  OR  U(>=45% fill) < 2%
  PROCEED        L(>=45% fill) > 2%
  INDETERMINATE  otherwise; report the n that would resolve it

The asymmetry is deliberate (PREREG sec 5): EITHER population may close the
lane, but only the HIGH-FILL population may license it.  A lane aimed at the
near-death regime does not get to be licensed by mid-board flips.
"""
from __future__ import annotations

import json
import math

FLOOR = 0.02              # PREREG sec 5, the project's standing argmax-flip floor
MIN_HIGH_FILL = 100       # PREREG sec 7.1, coverage void threshold
HIGH_FILL = ("45-60", ">=60")


def wilson(k, n, z=1.96):
    """Wilson score interval.  (0, 1) for n == 0 -- maximal ignorance."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n)))
    return ((c - h) / d, (c + h) / d)


def tally(rows, kind):
    """(k, n) overall and per fill bin for one readout kind."""
    sel = [r for r in rows if r.get("kind") == kind]
    out = {"ALL": [sum(r["flip"] for r in sel), len(sel)]}
    for r in sel:
        b = r.get("fill_bin", "?")
        out.setdefault(b, [0, 0])
        out[b][0] += r["flip"]
        out[b][1] += 1
    hk = sum(out.get(b, [0, 0])[0] for b in HIGH_FILL)
    hn = sum(out.get(b, [0, 0])[1] for b in HIGH_FILL)
    out[">=45"] = [hk, hn]
    return out


def route(rows, floor=FLOOR, min_high=MIN_HIGH_FILL):
    """The registered decision rule.  Returns a dict; never raises on data."""
    deep = tally(rows, "deepen")
    prepost = tally(rows, "prepost")

    k_all, n_all = deep["ALL"]
    k_hi, n_hi = deep[">=45"]

    # --- sec 7: void conditions, checked FIRST
    voids = []
    if n_all == 0:
        voids.append("non-vacuity: zero tie post-garbage plies observed")
    if n_hi < min_high:
        voids.append(f"coverage: only {n_hi} tie plies at >=45% fill "
                     f"(need {min_high})")
    if voids:
        return {"verdict": "VOID", "reasons": voids,
                "deepen": deep, "prepost": prepost}

    l_all, u_all = wilson(k_all, n_all)
    l_hi, u_hi = wilson(k_hi, n_hi)

    if u_all < floor or u_hi < floor:
        verdict = "CLOSE"
        why = (f"U(overall)={u_all:.4f}" if u_all < floor
               else f"U(>=45% fill)={u_hi:.4f}") + f" < floor {floor}"
    elif l_hi > floor:
        verdict = "PROCEED"
        why = f"L(>=45% fill)={l_hi:.4f} > floor {floor}"
    else:
        verdict = "INDETERMINATE"
        why = (f"L(>=45% fill)={l_hi:.4f} <= {floor} <= "
               f"U(>=45% fill)={u_hi:.4f}; neither rule fires")

    return {"verdict": verdict, "why": why,
            "overall": {"k": k_all, "n": n_all, "rate": k_all / n_all,
                        "ci": [l_all, u_all]},
            "high_fill": {"k": k_hi, "n": n_hi, "rate": k_hi / n_hi,
                          "ci": [l_hi, u_hi]},
            "deepen": deep, "prepost": prepost}


def report(rows):
    r = route(rows)
    lines = [f"VERDICT: {r['verdict']}"]
    if r["verdict"] == "VOID":
        lines += ["  " + x for x in r["reasons"]]
    else:
        lines.append(f"  {r['why']}")
        lines.append("")
        lines.append("PRIMARY (sec 5) — deepening argmax flip, by board fill")
        lines.append("  bin      flips/n      rate     95% CI")
        for b in ("<30", "30-45", "45-60", ">=60", ">=45", "ALL"):
            if b not in r["deepen"]:
                continue
            k, n = r["deepen"][b]
            lo, hi = wilson(k, n)
            rate = (k / n) if n else float("nan")
            lines.append(f"  {b:8s} {k:5d}/{n:-6d}  {rate:7.2%}  "
                         f"[{lo:6.2%}, {hi:6.2%}]")
        lines.append("")
        lines.append("SECONDARY (sec 6) — pre- vs post-garbage champion argmax "
                     "(re-derives the 50.5%, task #121)")
        lines.append("  bin      flips/n      rate     95% CI")
        for b in ("<30", "30-45", "45-60", ">=60", ">=45", "ALL"):
            if b not in r["prepost"]:
                continue
            k, n = r["prepost"][b]
            lo, hi = wilson(k, n)
            rate = (k / n) if n else float("nan")
            lines.append(f"  {b:8s} {k:5d}/{n:-6d}  {rate:7.2%}  "
                         f"[{lo:6.2%}, {hi:6.2%}]")
    return "\n".join(lines), r


def load_rows(path):
    rows = []
    for line in open(path):
        g = json.loads(line)
        rows.extend(g.get("rows", []))
    return rows


if __name__ == "__main__":
    import sys
    rows = load_rows(sys.argv[1])
    text, r = report(rows)
    print(text)
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w"), indent=2)
