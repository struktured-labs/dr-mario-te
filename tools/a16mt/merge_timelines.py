#!/usr/bin/env python3
"""a16mt lane: build a whole-game A16 co-sim timeline from the V11 one, and check that the copy is legitimate.

A16 (fw b545d740) differs from V11 (c51d2e21) in ONE byte: the DRDIST gate immediate (CMP #5 -> #17 at $A422). On a board
with more than 16 viruses both images run the same instructions (count, gate not taken, target 0), so their timelines
must be IDENTICAL; with 1..4 viruses both take the target path with the same count, so they must be identical too. Only
5..16-virus boards can differ (A16 runs the D scan and writes a target; V11 writes 0).
  inputs : the V11 whole-game timeline, the A16 timeline of every <= 16-virus pill (pubtrace_games.sh le16), and an A16
           identity sample of > 16-virus pills (gt16s)
  checks : every A16 pill with <= 4 or > 16 viruses == V11 exactly (pubs with frame times, final, DONE frame, tuck)
  output : the merged A16 timeline (A16 records for <= 16 viruses, V11 records re-stamped for > 16), plus a report of
           the 5..16-virus pills: finals changed, first-publish and DONE frame shifts.
Usage: merge_timelines.py V11.jsonl A16_LE16.jsonl A16_GT16S.jsonl OUT.jsonl"""
import json, statistics, sys

A16_MD5 = "b545d74055e4a2b64037e1a3d2c0a150"
KEYS = ("pubs", "final", "done_f", "tuck")


def load(path):
    try:
        return {r["p"]: r for r in map(json.loads, open(path))}
    except FileNotFoundError:
        return {}


def same(a, b):
    return all(a[k] == b[k] for k in KEYS)


def main():
    v11, le, gt, out = sys.argv[1:5]
    V, L, G = load(v11), load(le), load(gt)
    assert V, f"empty V11 timeline {v11}"
    bad = []
    ident = dict(le4=[0, 0], gt16=[0, 0])
    for p, r in list(L.items()) + list(G.items()):
        if r["fw_md5"] != A16_MD5:
            bad.append((p, "fw_md5 " + r["fw_md5"]))
        if p not in V:
            bad.append((p, "not in V11")); continue
        if r["upload"] != V[p]["upload"]:
            bad.append((p, "upload differs")); continue
        k = "le4" if r["vc"] <= 4 else ("gt16" if r["vc"] > 16 else None)
        if k:
            ident[k][0] += 1; ident[k][1] += same(r, V[p])
            if not same(r, V[p]):
                bad.append((p, f"vc {r['vc']}: A16 != V11 " + str({x: (r[x], V[p][x]) for x in KEYS if r[x] != V[p][x]})))
    mid = sorted(p for p, r in L.items() if 5 <= r["vc"] <= 16)
    chg = [p for p in mid if L[p]["final"] != V[p]["final"]]
    d1 = [L[p]["pubs"][0][0] - V[p]["pubs"][0][0] for p in mid if L[p]["pubs"] and V[p]["pubs"]]
    dd = [L[p]["done_f"] - V[p]["done_f"] for p in mid]
    print(f"identity <= 4 viruses: {ident['le4'][1]}/{ident['le4'][0]} exact; > 16 viruses (sample): "
          f"{ident['gt16'][1]}/{ident['gt16'][0]} exact")
    if mid:
        print(f"5..16 viruses: {len(mid)} pills, final changed on {len(chg)} {chg}; first publish A16 - V11: "
              f"median {statistics.median(d1):+.2f} f, max {max(d1):+.2f}, min {min(d1):+.2f}; DONE A16 - V11: median "
              f"{statistics.median(dd):+.2f} f, p10 {sorted(dd)[len(dd) // 10]:+.2f}, p90 {sorted(dd)[9 * len(dd) // 10]:+.2f}")
    missing = [p for p, r in V.items() if r["vc"] <= 16 and p not in L]
    if missing:
        bad.append((missing[:10], f"{len(missing)} <= 16-virus pills have no A16 record"))
    for b in bad:
        print("PROBLEM", b)
    with open(out, "w") as f:
        for p in sorted(V):
            if p in L:
                r = dict(L[p], src="a16")
            else:
                r = dict(V[p], fw_md5=A16_MD5, src="v11 (identical by construction: > 16 viruses)")
            f.write(json.dumps(r) + "\n")
    print(f"MERGE {'OK' if not bad else 'FAIL'}: {len(V)} pills -> {out}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
