"""Put this checkout's search modules on sys.path.

The VS arena's import pin (`import_pin.py`) points at absolute paths on the
machines that ran the September screens. Those trees are not part of this
repo. `install()` orders the in-repo copies so `fast_rtl_x` comes from
`experiments/cvx` (not the older `depth4/snap` copy) and `nes_pills` comes
from `experiments/vendor` (the deepcopy-safe `_PillDraw` build).
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# First entry is searched first. snap/ contains its own fast_rtl_x.py; it
# must stay behind cvx or the live leaf is silently replaced by the snapshot.
_FRONT = (
    os.path.join(_ROOT, "experiments", "vendor"),
    os.path.join(_ROOT, "experiments", "cvx"),
    os.path.join(_ROOT, "experiments", "eval47"),
    os.path.join(_ROOT, "experiments", "tuck_v3"),
    os.path.join(_ROOT, "experiments"),
    os.path.join(_ROOT, "experiments", "depth4", "snap"),
)


def install():
    for p in _FRONT:
        if p in sys.path:
            sys.path.remove(p)
    for p in reversed(_FRONT):
        sys.path.insert(0, p)
    return _ROOT
