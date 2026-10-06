"""Per-AI-pill cases for one 2026-10-05 game (dr. lulu vs ANTIBODY_DIST_FAIR), with the 10/04 M4 G2 code path
(m4g2_fair_20261004.cases: hidden-spawn tracker + clear-pop repair + the SILICON-FAITHFUL brain braingap Leaf6FwDecider
(fw 1488e158's main search = FAIR exactly) + classify_g2 category + mechanics + garbage received), pointed at this
recording through lulu_20261005 (which re-targets fair_20261004.SCAN / GAMES).
Usage: GAME=m1g4 python cases_lulu_20261005.py   -> cases_ai_<game>_lulu_20261005.jsonl (pubtrace_g2.py CASES format)"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
GAME = os.environ["GAME"]
import m4g2_fair_20261004 as M  # noqa: E402  (first: pins the braingap paths, as brain_fair_20261004 does)
import lulu_20261005  # noqa: E402,F401  (FA.SCAN / FA.GAMES -> this recording; same fair_20261004 module object)
M.GAME = GAME
M.CASES = os.path.join(HERE, f"cases_ai_{GAME}_lulu_20261005.jsonl")
if __name__ == "__main__":
    M.cases()
