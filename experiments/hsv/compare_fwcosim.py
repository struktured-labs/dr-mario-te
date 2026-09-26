"""Compare the sharded firmware co-sim runs (run_fallback_gates.sh step 5), cwd = tmp/fwcosim.

HSV-only vs HSV+fallback on the same firmware and boards: the published move AND the GO->DONE clock
count must match board for board. The oracle column in the logs is the OLD py65 oracle for a different
firmware -- it is ignored here; this is an A/B identity check, not an oracle check.
"""
import re
import sys

PAT = re.compile(r"^case (\d+): copro=\((\d+),(\d+)\) oracle=\(\d+,\d+\) clocks=(\d+)")


def load(shard, build):
    idx = [int(x) for x in open("shard%d/idx.txt" % shard).read().split()]
    out = {}
    for line in open("shard%d/run_%s.log" % (shard, build)):
        m = PAT.match(line)
        if m:
            k, c, o, clk = map(int, m.groups())
            out[idx[k]] = (c, o, clk)
    return out, len(idx)


def main():
    alt = sys.argv[1] if len(sys.argv) > 1 else "pipe"      # the fallback build's log name (run_<alt>.log)
    a, b, want = {}, {}, 0
    for s in range(4):
        x, n = load(s, "hsv"); y, _ = load(s, alt); a.update(x); b.update(y); want += n
    bad = [k for k in sorted(a) if a.get(k) != b.get(k)]
    both = sorted(set(a) & set(b))
    tot = sum(a[k][2] for k in both)
    print("boards: hsv %d  %s %d  of %d" % (len(a), alt, len(b), want))
    print("moves identical: %d/%d   clocks identical: %d/%d" % (
        sum(a[k][:2] == b[k][:2] for k in both), len(both), sum(a[k][2] == b[k][2] for k in both), len(both)))
    if both:
        print("GO->DONE clocks: total %d  mean %.0f  (%.3f s/board @ 85.9 MHz)" % (tot, tot / len(both),
                                                                                   tot / len(both) / 85.9e6))
    ok = len(a) == len(b) == want and not bad
    for k in bad[:10]:
        print("DIFF board %d: hsv=%s %s=%s" % (k, a.get(k), alt, b.get(k)))
    print("FWCOSIM %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
