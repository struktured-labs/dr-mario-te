#!/usr/bin/env python3
"""Run a reach gate with the mask's (T_LAT, G0) set from env DRREACH_TLAT / DRREACH_G0 on BOTH sides: the 6502
emitter (fpga/copro/reach_6502) and the python spec (experiments/reach/reach_fw, kept verbatim -- only its module
constants are rebound here). Defaults 19 / 8 = the pinned-settle carts; the fair-settle cart (DRSETTLE) is 13 / 3.
Usage: DRREACH_TLAT=13 DRREACH_G0=3 run_reachparam.py experiments/reach/gate_reach_mask.py --tap [args...]
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
script = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, os.path.join(ROOT, "experiments", "reach"))
import reach_6502 as RC  # noqa: E402
import reach_fw as RF  # noqa: E402
t, g = int(os.environ.get("DRREACH_TLAT", "19")), int(os.environ.get("DRREACH_G0", "8"))
RC.T_LAT, RC.G0 = t, g
RF.T_LAT, RF.G0 = t, g
print(f"run_reachparam: T_LAT={t} G0={g} on reach_6502 ({RC.__file__}) and reach_fw ({RF.__file__})", flush=True)
sys.argv = [script] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(script))
runpy.run_path(script, run_name="__main__")
