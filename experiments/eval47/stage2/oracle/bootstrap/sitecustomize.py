"""Oracle-only interpreter bootstrap for the sealed capsule-source module.

The historical decision tree mutates ``sys.path`` at import time.  Merely
putting the QA directory first in PYTHONPATH is therefore insufficient: a
later insertion can make the mutable upstream pillrng copy win.  Python loads
this module during normal site initialisation, before the oracle imports, so
the exact sealed QA module is already fixed in ``sys.modules``.
"""
import importlib.util
import os
import sys


CANONICAL = "/home/struktured/projects/dr-mario-qa-wt/experiments/nes_pills.py"

if not os.path.isfile(CANONICAL):
    raise ImportError(f"sealed oracle capsule source is missing: {CANONICAL}")

spec = importlib.util.spec_from_file_location("nes_pills", CANONICAL)
if spec is None or spec.loader is None:
    raise ImportError(f"cannot load sealed oracle capsule source: {CANONICAL}")
module = importlib.util.module_from_spec(spec)
sys.modules["nes_pills"] = module
spec.loader.exec_module(module)
