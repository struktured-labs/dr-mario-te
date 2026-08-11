#!/usr/bin/env python3
"""Dual-side held-out gate for the on-screen virus counter decoder."""
from __future__ import annotations

import argparse
import csv
import json
import os

import numpy as np
from PIL import Image

import counter_decode as C

P1_TENS = (861, 899, 926, 959)
P1_ONES = (905, 943, 926, 959)
MAX_BEST = 0.02
MIN_MARGIN = 0.12
SPEC = {
    "m1": {"start": 45, "end": 260, "monotone_from": 46,
           "p1": {45: 11, 46: 48, 260: 14},
           "p2": {45: 11, 46: 48, 260: 6}},
    "m2": {"start": 265, "end": 549, "monotone_from": 265,
           "p1": {265: 48, 549: 5}, "p2": {265: 48, 549: 2}},
    "m3": {"start": 555, "end": 738, "monotone_from": 555,
           "p1": {555: 48, 738: 2},
           "p2": {555: 47, 567: 41, 738: 6}},
}


def decode_second(second, refs, tens_box, ones_box, shift=0):
    arr = np.asarray(Image.open(C.frame_path(second)).convert("RGB"))
    td, tb, tm = C.decode_glyph(C.glyph_mask(arr, C.shifted(tens_box, shift)), refs)
    od, ob, om = C.decode_glyph(C.glyph_mask(arr, C.shifted(ones_box, shift)), refs)
    return {"second": int(second), "value": 10 * td + od,
            "tens": td, "ones": od, "tens_best": tb, "ones_best": ob,
            "tens_margin": tm, "ones_margin": om}


def decode_all(refs, p1_shift=0):
    out = {}
    for name, spec in SPEC.items():
        out[name] = {}
        for side, boxes, shift in (("p1", (P1_TENS, P1_ONES), p1_shift),
                                   ("p2", (C.TENS, C.ONES), 0)):
            out[name][side] = [decode_second(s, refs, *boxes, shift=shift)
                               for s in range(spec["start"], spec["end"] + 1)]
    return out


def validate(name, side, rows):
    spec = SPEC[name]
    by = {r["second"]: r for r in rows}
    anchors = {str(s): {"expected": v, "observed": by[s]["value"],
                        "pass": by[s]["value"] == v}
               for s, v in spec[side].items()}
    kept = [r for r in rows if r["second"] >= spec["monotone_from"]]
    increases = [(kept[i - 1]["second"], kept[i - 1]["value"],
                  kept[i]["second"], kept[i]["value"])
                 for i in range(1, len(kept)) if kept[i]["value"] > kept[i - 1]["value"]]
    bad = [r["second"] for r in rows
           if max(r["tens_best"], r["ones_best"]) > MAX_BEST
           or min(r["tens_margin"], r["ones_margin"]) < MIN_MARGIN]
    return {"anchors": anchors, "increases_after_reset": increases,
            "confidence_bad_seconds": bad,
            "max_best_distance": max(max(r["tens_best"], r["ones_best"]) for r in rows),
            "min_margin": min(min(r["tens_margin"], r["ones_margin"]) for r in rows),
            "pass": all(x["pass"] for x in anchors.values()) and not increases and not bad}


def grade(decoded):
    return {name: {side: validate(name, side, decoded[name][side])
                   for side in ("p1", "p2")} for name in SPEC}


def all_pass(gates):
    return all(gates[n][s]["pass"] for n in gates for s in gates[n])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "counter_v2"))
    a = ap.parse_args()
    decoded = decode_all(C.templates())
    gates = grade(decoded)
    if not all_pass(gates):
        raise SystemExit("V2 GATE FAILED: " + json.dumps(gates))
    swap = grade(decode_all(C.templates(label_swap=True)))
    shift = grade(decode_all(C.templates(), p1_shift=8))
    mutants = {"swap_1_7_rejected": not all_pass(swap),
               "p1_shift_8px_rejected": not all_pass(shift)}
    if not all(mutants.values()):
        raise SystemExit("V2 MUTANT GATE FAILED: " + json.dumps(mutants))
    os.makedirs(a.outdir, exist_ok=True)
    for name in decoded:
        for side, rows in decoded[name].items():
            with open(os.path.join(a.outdir, f"{name}_{side}.csv"), "w", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    result = {"authority": "OBSERVATION_INSTRUMENT", "prereg": "PREREG_COUNTER_V2.md",
              "gates": gates, "killed_mutants": mutants, "pass": True}
    with open(os.path.join(a.outdir, "RESULT.json"), "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
