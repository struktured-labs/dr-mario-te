"""Build per-AI-pill cases for any 10/04 couch game with the couch-forensics M4 G2 code path (m4g2_fair_20261004.cases:
tracker + clear-pop repair + silicon-faithful brain + mechanics + garbage received), written to execfid/cases/.
Usage: GAME=m3g1 python build_cases.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.abspath(os.path.join(HERE, "..", "couch_forensics"))
sys.path.insert(0, CF)
GAME = os.environ["GAME"]
import m4g2_fair_20261004 as M  # noqa: E402  (chdir's into couch_forensics)
M.CASES = os.path.join(HERE, "cases", f"cases_{GAME}_fair_20261004.jsonl")
M.cases()
