#!/usr/bin/env python3
"""dump_labels.py -- print the CPU addresses of named driver labels for a given flag set.

The #134 site gates instrument the EMITTED driver by exec-callback, and driver addresses move
whenever a flag adds bytes upstream (gate rot, task #120: a gate pinned to an offset rots on
relayout and reads as a cart failure). This asks the emitter itself, under the same DR* env the
cart was built with, where the labels landed -- the single source of truth.

usage:  DRFLAG=... dump_labels.py label [label ...]
prints: label=0xADDR (CPU) per line, or label=MISSING.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import patch_cartridge_copro as pc

level = int(os.environ.get("DRLEVEL", "11"))
speed = int(os.environ.get("DRSPEED", "1"))
_, labels = pc.build_main(level, speed)
for name in sys.argv[1:]:
    if name in labels:
        print(f"{name}=0x{pc.UNIT1_CPU + labels[name]:04X}")
    else:
        print(f"{name}=MISSING")
