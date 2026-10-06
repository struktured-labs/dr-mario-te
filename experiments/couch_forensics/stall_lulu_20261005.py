"""Endgame stall characterisation for any 2026-10-05 game (stall_fair_20261004.main on this recording): per AI pill the
allowed virus-clearing moves, silicon vs the faithful brain, and cell provenance (V / own pill P / dr. lulu's garbage G)
above every remaining virus; stalls = runs of >= 10 placements at one virus count.
Usage: GAME=m1g2 python stall_lulu_20261005.py -> stall_<game>_lulu_20261005.json + cases_stall_<game>_lulu_20261005.jsonl"""
import os
import shutil
import sys
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
GAME = os.environ["GAME"]
import m4g2_fair_20261004 as M  # noqa: E402,F401  (pins the braingap paths)
import lulu_20261005 as L  # noqa: E402
import stall_fair_20261004 as SF  # noqa: E402
SF.GAME = GAME
tmp = tempfile.mkdtemp(dir=os.path.join(L.FX, "scan"))
SF.HERE = tmp
SF.main()
for a, b in ((f"cases_stall_{GAME}_fair_20261004.jsonl", f"cases_stall_{GAME}_lulu_20261005.jsonl"),
             (f"stall_{GAME}_fair_20261004.json", f"stall_{GAME}_lulu_20261005.json")):
    shutil.move(os.path.join(tmp, a), os.path.join(HERE, b))
os.rmdir(tmp)
