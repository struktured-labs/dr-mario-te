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
MIN_HIGH_H = 100          # PREREG v2 sec C.2, coverage void threshold
# PREREG v2 sec C.2: stratify on h, NOT on fill.  The window is W = 264 - 16*h, a
# function of HEIGHT.  Near-death boards are narrow towers -- the recovered
# gate_neardeath rig measures fill median 36% at stack 13-16 -- so a fill-keyed
# rule aims at a stratum that barely exists.
H_BANDS = (("h<=7", 0, 7), ("h8-10", 8, 10), ("h11-13", 11, 13), ("h>=14", 14, 99))
HIGH_H = ("h11-13", "h>=14")


def wilson(k, n, z=1.96):
    """Wilson score interval.  (0, 1) for n == 0 -- maximal ignorance."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n)))
    return ((c - h) / d, (c + h) / d)


def h_band(h):
    for name, lo, hi in H_BANDS:
        if lo <= int(h) <= hi:
            return name
    return "h<=7"


def tally(rows, kind, by="h"):
    """(k, n) overall and per band for one readout kind.

    by="h" is the PRIMARY routing (PREREG v2 C.2); by="fill" is the secondary
    readout kept for comparability with the historical rigs.
    """
    sel = [r for r in rows if r.get("kind") == kind]
    out = {"ALL": [sum(r["flip"] for r in sel), len(sel)]}
    for r in sel:
        b = h_band(r.get("h_hit", 0)) if by == "h" else r.get("fill_bin", "?")
        out.setdefault(b, [0, 0])
        out[b][0] += r["flip"]
        out[b][1] += 1
    if by == "h":
        hk = sum(out.get(b, [0, 0])[0] for b in HIGH_H)
        hn = sum(out.get(b, [0, 0])[1] for b in HIGH_H)
        out["h>=11"] = [hk, hn]
    return out


def route(rows, floor=FLOOR, min_high=MIN_HIGH_H):
    """The registered decision rule.  Returns a dict; never raises on data."""
    deep = tally(rows, "deepen")
    prepost = tally(rows, "prepost")

    k_all, n_all = deep["ALL"]
    k_hi, n_hi = deep["h>=11"]

    # --- sec 7: void conditions, checked FIRST
    voids = []
    if n_all == 0:
        voids.append("non-vacuity: zero tie post-garbage plies observed")
    if n_hi < min_high:
        voids.append(f"coverage: only {n_hi} tie plies at h>=11 "
                     f"(need {min_high})")
    if voids:
        return {"verdict": "VOID", "reasons": voids,
                "deepen": deep, "prepost": prepost}

    l_all, u_all = wilson(k_all, n_all)
    l_hi, u_hi = wilson(k_hi, n_hi)

    if u_all < floor or u_hi < floor:
        verdict = "CLOSE"
        why = (f"U(overall)={u_all:.4f}" if u_all < floor
               else f"U(h>=11)={u_hi:.4f}") + f" < floor {floor}"
    elif l_hi > floor:
        verdict = "PROCEED"
        why = f"L(h>=11)={l_hi:.4f} > floor {floor}"
    else:
        verdict = "INDETERMINATE"
        why = (f"L(h>=11)={l_hi:.4f} <= {floor} <= "
               f"U(h>=11)={u_hi:.4f}; neither rule fires")

    return {"verdict": verdict, "why": why,
            "overall": {"k": k_all, "n": n_all, "rate": k_all / n_all,
                        "ci": [l_all, u_all]},
            "high_h": {"k": k_hi, "n": n_hi, "rate": k_hi / n_hi,
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
        lines.append("PRIMARY (sec 5) — deepening argmax flip, by h_hit (PREREG v2 C.2)")
        lines.append("  bin      flips/n      rate     95% CI")
        for b in ("h<=7", "h8-10", "h11-13", "h>=14", "h>=11", "ALL"):
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
        for b in ("h<=7", "h8-10", "h11-13", "h>=14", "h>=11", "ALL"):
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
