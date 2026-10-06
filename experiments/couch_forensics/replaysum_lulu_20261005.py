"""Summarise the brain-only replays (replay_<game>_lulu_20261005.jsonl; M1 G4 also replay[_early]_m1g4) per game:
for each start pill, the AI outcome under perfect execution of the silicon-faithful brain, scored against what dr. lulu
actually did:
  AI-WIN    the brain clears before she clears (or she topped out in reality and the brain is still alive at her top-out)
  AI-LOSS   the brain tops out first, or she cleared in reality and the brain is still alive then
  OPEN      the observed capsules run out first and nothing is decided (games the AI won by clearing, M1 G4)
Usage: python replaysum_lulu_20261005.py -> replaysum_lulu_20261005.json"""
import json, os
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
S = {g["game"]: g for g in json.load(open(os.path.join(HERE, "summary_lulu_20261005.json")))["games"]}
out = {}
for g in ("m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4"):
    files = [f"replay_{g}_lulu_20261005.jsonl"] + ([f"replay_early_{g}_lulu_20261005.jsonl"] if g == "m1g4" else [])
    R = [json.loads(l) for f in files if os.path.exists(os.path.join(HERE, f)) for l in open(os.path.join(HERE, f))]
    if g == "m1g4":
        for r in R:
            r.setdefault("end_t", None)
    w, how = S[g]["winner"], S[g]["how"]
    c = Counter(); rows = []
    for r in R:
        if r["end"] == "CLEAR":
            k = "AI-WIN"
        elif r["end"] == "TOPOUT":
            k = "AI-LOSS"
        elif how == "lulu topped out":
            k = "AI-WIN"
        elif w == "lulu" and how == "cleared":
            k = "AI-LOSS"
        else:
            k = "OPEN"
        c[k] += 1
        rows.append((r["p0"], k, r["viruses_end"]))
    out[g] = {"actual": f"{w} ({how})", "starts": len(R), "classes": dict(c),
              "open_viruses_at_end": sorted(v for p, k, v in rows if k == "OPEN"),
              "by_start": rows}
    print(g, out[g]["actual"], len(R), dict(c), "OPEN viruses:", out[g]["open_viruses_at_end"][:40])
json.dump(out, open(os.path.join(HERE, "replaysum_lulu_20261005.json"), "w"), indent=1)
