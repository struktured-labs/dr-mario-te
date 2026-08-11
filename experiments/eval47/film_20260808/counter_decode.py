#!/usr/bin/env python3
"""Decode the game's own P2 virus counter from the 2026-08-08 full-frame capture."""
from __future__ import annotations

import argparse
import csv
import json
import os

import numpy as np
from PIL import Image

FRAMES = ("/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/"
          "tmp/dr_lulu_20260808/frames")
TENS = (977, 1015, 926, 959)
ONES = (1021, 1059, 926, 959)
TEMPLATE_SECONDS = {0: 568, 1: 565, 2: 604, 3: 561, 4: 628,
                    5: 559, 6: 616, 7: 555, 8: 613, 9: 571}
WINDOWS = {
    "m1": {"start": 45, "end": 260, "anchors": {45: 11, 260: 6}},
    "m2": {"start": 265, "end": 549, "anchors": {265: 48, 549: 2}},
    "m3": {"start": 555, "end": 738,
           "anchors": {555: 47, 567: 41, 738: 6}},
}
MAX_BEST = 0.01
MIN_MARGIN = 0.12


def frame_path(second):
    return os.path.join(FRAMES, f"f{int(second):04d}.jpg")


def glyph_mask(arr, box):
    x0, x1, y0, y1 = box
    return arr[y0:y1, x0:x1].max(axis=2) < 100


def shifted(box, dx):
    x0, x1, y0, y1 = box
    return x0 + dx, x1 + dx, y0, y1


def templates(label_swap=False):
    out = {}
    for digit, second in TEMPLATE_SECONDS.items():
        arr = np.asarray(Image.open(frame_path(second)).convert("RGB"))
        label = 7 if label_swap and digit == 1 else 1 if label_swap and digit == 7 else digit
        out[label] = glyph_mask(arr, ONES)
    return out


def decode_glyph(mask, refs):
    distances = sorted((float(np.mean(mask != ref)), int(digit))
                       for digit, ref in refs.items())
    best, digit = distances[0]
    return digit, best, distances[1][0] - best


def decode_second(second, refs, box_shift=0):
    arr = np.asarray(Image.open(frame_path(second)).convert("RGB"))
    td, tb, tm = decode_glyph(glyph_mask(arr, shifted(TENS, box_shift)), refs)
    od, ob, om = decode_glyph(glyph_mask(arr, shifted(ONES, box_shift)), refs)
    return {"second": int(second), "value": 10 * td + od,
            "tens": td, "ones": od, "tens_best": tb, "ones_best": ob,
            "tens_margin": tm, "ones_margin": om}


def decode_window(name, refs, box_shift=0):
    w = WINDOWS[name]
    return [decode_second(s, refs, box_shift)
            for s in range(w["start"], w["end"] + 1)]


def validate(name, rows):
    w = WINDOWS[name]
    by_second = {r["second"]: r for r in rows}
    anchors = {str(s): {"expected": v, "observed": by_second[s]["value"],
                        "pass": by_second[s]["value"] == v}
               for s, v in w["anchors"].items()}
    vals = [r["value"] for r in rows]
    increases = [(rows[i - 1]["second"], vals[i - 1], rows[i]["second"], vals[i])
                 for i in range(1, len(rows)) if vals[i] > vals[i - 1]]
    confidence_bad = [r["second"] for r in rows
                      if max(r["tens_best"], r["ones_best"]) > MAX_BEST
                      or min(r["tens_margin"], r["ones_margin"]) < MIN_MARGIN]
    return {"n_seconds": len(rows), "first": vals[0], "last": vals[-1],
            "anchors": anchors, "increases": increases,
            "confidence_bad_seconds": confidence_bad,
            "max_best_distance": max(max(r["tens_best"], r["ones_best"]) for r in rows),
            "min_second_best_margin": min(min(r["tens_margin"], r["ones_margin"])
                                          for r in rows),
            "pass": (all(x["pass"] for x in anchors.values()) and not increases
                     and not confidence_bad)}


def evaluate(refs, box_shift=0):
    rows = {name: decode_window(name, refs, box_shift) for name in WINDOWS}
    gates = {name: validate(name, rs) for name, rs in rows.items()}
    return rows, gates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out", "p2_counter"))
    a = ap.parse_args()
    refs = templates()
    rows, gates = evaluate(refs)
    if not all(g["pass"] for g in gates.values()):
        raise SystemExit("COUNTER GATE FAILED: " + json.dumps(gates))

    _, swap_gates = evaluate(templates(label_swap=True))
    _, shift_gates = evaluate(refs, box_shift=8)
    mutants = {
        "swap_1_7_rejected": not all(g["pass"] for g in swap_gates.values()),
        "shift_boxes_8px_rejected": not all(g["pass"] for g in shift_gates.values()),
    }
    if not all(mutants.values()):
        raise SystemExit("COUNTER MUTANT GATE FAILED: " + json.dumps(mutants))

    os.makedirs(a.outdir, exist_ok=True)
    for name, rs in rows.items():
        with open(os.path.join(a.outdir, f"{name}_p2_counter.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rs[0]))
            wr.writeheader(); wr.writerows(rs)
    result = {"authority": "OBSERVATION_INSTRUMENT",
              "prereg": "PREREG_P2_COUNTER.md", "windows": gates,
              "killed_mutants": mutants, "pass": True}
    with open(os.path.join(a.outdir, "RESULT.json"), "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
