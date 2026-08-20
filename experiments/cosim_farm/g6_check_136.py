#!/usr/bin/env python3
"""G6 (prereg 906787d): determinism. Two seeds are re-captured into a SECOND file and
their `lat` rows must be byte-identical to the verdict file's -- compared on the JSON
text of the field, not on parsed floats, so a formatting drift cannot hide a value one.

Run: python3 g6_check_136.py <verdict.jsonl> <rerun.jsonl> <arm>   (exit 0 iff identical)
"""
import json
import sys


def lat_by_seed(path, arm):
    out = {}
    for ln in open(path):
        ln = ln.strip()
        if not ln:
            continue
        r = json.loads(ln)
        if r.get("arm") != arm and r.get("arm") != arm + "_g6":
            continue
        # canonical text of the lat field alone
        out[r["seed"]] = json.dumps(r.get("lat"), separators=(",", ":"))
    return out


def main():
    verdict, rerun, arm = sys.argv[1], sys.argv[2], sys.argv[3]
    v, r = lat_by_seed(verdict, arm), lat_by_seed(rerun, arm)
    common = sorted(set(v) & set(r))
    if not common:
        print(f"G6 FAIL: no common seeds between {verdict} and {rerun} for arm {arm}")
        return 1
    bad = [s for s in common if v[s] != r[s]]
    for s in bad:
        print(f"G6 FAIL seed {s}: lat rows differ")
    print(f"G6 {'PASS' if not bad else 'FAIL'}: {len(common) - len(bad)}/{len(common)} "
          f"seeds byte-identical on lat ({arm})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
