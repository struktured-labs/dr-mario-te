"""Summarize n=600 confirmation pairings. Exit 0 always; prints binomial vs 50%."""
import json, glob, os, collections, math
from pathlib import Path

OUT = Path("/home/struktured/projects/dr-mario-h16-wt/experiments/cvx/confirm")

def binom_p(k, n, p=0.5):
    # two-sided exact binomial via regularized incomplete beta if scipy missing
    try:
        from math import comb
        tail = sum(comb(n, i) for i in range(n + 1) if abs(i / n - p) >= abs(k / n - p) - 1e-15)
        return min(1.0, tail / (2 ** n)) if n <= 40 else None
    except Exception:
        return None

def binom_p_normal(k, n, p=0.5):
    # two-sided normal approx with continuity correction; fine at n=600
    from math import erfc, sqrt
    mu, sd = n * p, sqrt(n * p * (1 - p))
    z = abs(k - mu) / sd
    return erfc(z / sqrt(2))

def main():
    lines = []
    for prefix in ["winner_vs_h80", "winner_x40_vs_h80", "racer_vs_h80"]:
        files = sorted(OUT.glob(f"{prefix}_*.jsonl"))
        wins = collections.Counter()
        how = collections.Counter()
        sentA, sentB = [], []
        A = B = None
        n = 0
        for f in files:
            for l in open(f):
                r = json.loads(l)
                n += 1
                wins[r["winner"]] += 1
                how[r.get("how")] += 1
                A, B = r.get("A") or A, r.get("B") or B
                s = r.get("sent") or [0, 0]
                if isinstance(s, list) and len(s) == 2:
                    sentA.append(s[0]); sentB.append(s[1])
        if n == 0:
            lines.append(f"{prefix}: NO ROWS")
            continue
        k = wins[0]
        wr = k / n
        p = binom_p_normal(k, n)
        meanA = sum(sentA) / len(sentA) if sentA else 0
        meanB = sum(sentB) / len(sentB) if sentB else 0
        flag = "PASS >55%" if wr > 0.55 and p < 0.05 else ("NULL/NOISE" if wr <= 0.50 else "POSITIVE-UNSIZED")
        lines.append(
            f"{prefix}: A={A} vs B={B}  {k}/{n} = {wr*100:.1f}%  p≈{p:.4g}  "
            f"how={dict(how)}  sent {meanA:.1f}v{meanB:.1f}  => {flag}"
        )
    text = "\n".join(lines) + "\n"
    print(text, end="")
    (OUT / "SUMMARY.txt").write_text(text)
    print("CONFIRM_DONE")

if __name__ == "__main__":
    main()
