"""Summarize pinned seat-balanced follow-up + lines probe."""
import json, collections
from pathlib import Path
from math import erfc, sqrt

OUT = Path("/home/struktured/projects/dr-mario-h16-wt/experiments/cvx/pinned")

def p_two_sided(k, n):
    if n <= 0:
        return 1.0
    mu, sd = n * 0.5, sqrt(n * 0.5 * 0.5)
    z = abs(k - mu) / sd
    return erfc(z / sqrt(2))

def load(prefix):
    wins = collections.Counter()
    how = collections.Counter()
    sentA, sentB = [], []
    A = B = None
    n = 0
    meta = {}
    for f in sorted(OUT.glob(f"{prefix}_*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            n += 1
            wins[r["winner"]] += 1
            how[r.get("how")] += 1
            A, B = r.get("A") or A, r.get("B") or B
            s = r.get("sent") or [0, 0]
            if isinstance(s, list) and len(s) == 2:
                sentA.append(s[0]); sentB.append(s[1])
            meta["ws"] = r.get("ws"); meta["send_rule"] = r.get("send_rule")
    return dict(n=n, wins=wins, how=how, A=A, B=B, sentA=sentA, sentB=sentB, meta=meta)

def line(prefix):
    d = load(prefix)
    n = d["n"]
    if n == 0:
        return f"{prefix}: NO ROWS"
    k = d["wins"][0]
    wr = k / n
    p = p_two_sided(k, n)
    ma = sum(d["sentA"]) / len(d["sentA"]) if d["sentA"] else 0
    mb = sum(d["sentB"]) / len(d["sentB"]) if d["sentB"] else 0
    return (f"{prefix}: A={d['A']} vs B={d['B']}  {k}/{n}={wr*100:.1f}% p≈{p:.3g}  "
            f"how={dict(d['how'])} sent {ma:.1f}v{mb:.1f}  "
            f"ws={d['meta'].get('ws')} rule={d['meta'].get('send_rule')}")

def pair_report(a_first, b_first, label):
    da, db = load(a_first), load(b_first)
    # A-first: candidate is A so cand wins = wins[0]
    # B-first: candidate is B so cand wins = wins[1]
    lines = [line(a_first), line(b_first)]
    if da["n"] and db["n"]:
        cand = da["wins"][0] + db["wins"][1]
        n = da["n"] + db["n"]
        wr = cand / n
        p = p_two_sided(cand, n)
        lines.append(f"  SEAT-BALANCED {label}: candidate {cand}/{n}={wr*100:.1f}% p≈{p:.3g}")
    return "\n".join(lines)

def main():
    chunks = [
        pair_report("winner_vs_h80", "h80_vs_winner", "winner vs holes80"),
        pair_report("h80c_vs_h80", "h80_vs_h80c", "winh80cross40 vs holes80"),
        pair_report("racer1_vs_h80", "h80_vs_racer1", "one-change racer vs holes80"),
        pair_report("lines_winner_vs_h80", "lines_h80_vs_winner", "LINES-rule winner vs holes80"),
    ]
    text = "\n".join(chunks) + "\n"
    print(text, end="")
    (OUT / "SUMMARY.txt").write_text(text)

if __name__ == "__main__":
    main()
