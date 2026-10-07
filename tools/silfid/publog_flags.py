#!/usr/bin/env python3
"""Print the env assignment list for the silfid debug-log cart family.
  publog_flags.py BASE [extra K=V ...]
BASE:
  fairD     the FAIR couch cart dbbb5007: couch_c960dd49 snapshot + DRLATEGUARD=1 DRSTUDYEND=1 DRSETTLE=3 DRSETTLEPIN=0
            DRPROPHFIRST=1 (a branded couch build; listed for the negative controls)
  cvcp2     the debug-log cart's base: the FAIR couch P2 driver (fairD minus DRSTUDYEND) on the CvC seat/menu config:
            P1 = the native AI (DRP1NATIVE=1) sliced (DRP1SLICE=1, the certified pairing with DRPRESPIPE), autonav,
            no study/pause screens (DRHUMAN=0 DRNAVDWELL=0 DRSTUDY=0 DRSTUDYCOUNTS=0 DRSTUDY_Y=0x08, tag TCVC), L11."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base = sys.argv[1]
snap = json.load(open(os.path.join(ROOT, "experiments/lateflip/couch_c960dd49_flags.json")))["flag_snapshot"]
D = {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1"}
snap.update(D)
if base == "cvcp2":
    snap.pop("DRSTUDYEND"); snap.pop("DRSTUDY2P_INV", None)
    snap.update({"DRHUMAN": "0", "DRP1NATIVE": "1", "DRP1SLICE": "1", "DRNAVDWELL": "0", "DRSTUDY": "0",
                 "DRSTUDYCOUNTS": "0", "DRSTUDY_Y": "0x08", "DRBUILDID_TAG": "TCVC"})
elif base != "fairD":
    raise SystemExit("unknown base " + base)
for kv in sys.argv[2:]:
    k, v = kv.split("=", 1); snap[k] = v
print(" ".join(f"{k}={v}" for k, v in sorted(snap.items()) if v is not None and v != "None"))
