#!/usr/bin/env python
"""aggregate.py — batch-level census aggregation, split by DLAT arm.
Usage: aggregate.py logs/main1 [more dirs...]   (each dir holds run*/census.csv + run.log)"""
import glob, os, re, subprocess, sys

dirs = []
for root in sys.argv[1:]:
    dirs += sorted(glob.glob(os.path.join(root, 'run*')))
    if os.path.exists(os.path.join(root, 'census.csv')):
        dirs.append(root)

arms = {}
for d in dirs:
    rl = os.path.join(d, 'run.log')
    csvp = os.path.join(d, 'census.csv')
    if not (os.path.exists(rl) and os.path.exists(csvp)):
        continue
    head = open(rl, errors='replace').readline()
    m = re.search(r'DLAT=(\d+)', head)
    dlat = m.group(1) if m else '?'
    arms.setdefault(dlat, []).append(csvp)
    tail = open(rl, errors='replace').read()
    sm = re.search(r'SUMMARY frames=(\d+) rounds=(\d+) pills=(\d+) goes=(\d+) dones=(\d+)', tail)
    seeds = re.findall(r'ROUND \d+ start f=\d+ seed=([0-9A-F]+)', tail)
    print(f"{d}: dlat={dlat} summary={sm.groups() if sm else 'INCOMPLETE'} seeds={seeds}")

here = os.path.dirname(os.path.abspath(__file__))
py = sys.executable
for dlat, csvs in sorted(arms.items()):
    print(f"\n########## ARM DLAT={dlat} ({len(csvs)} sessions) ##########")
    subprocess.run([py, os.path.join(here, 'decode_census.py')] + csvs)
print(f"\n########## ALL ARMS POOLED ##########")
allc = [c for v in arms.values() for c in v]
subprocess.run([py, os.path.join(here, 'decode_census.py')] + allc)
