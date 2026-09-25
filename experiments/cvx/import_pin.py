"""Pin the VS-arena import graph. Call BEFORE vs_sim.play_vs.

pressure_rig / h16_arm insert qa-wt ahead of pillrng, so `import nes_pills`
silently binds the deepcopy-unsafe lambda attach. This module forces the
paths we intend and asserts __file__ so a shadow cannot pass quietly.

Cart-matched search uses ws=0 (DRSTRAND default 0). The loop gens 0-2 and the
in-flight A-first confirm used ws=20; those rows are a different player.
"""
from __future__ import annotations
import importlib, importlib.util, os, sys

CVX = os.path.dirname(os.path.abspath(__file__))          # portable: works from any clone path
H16_WT = os.path.dirname(os.path.dirname(CVX))
H16 = H16_WT + "/experiments/h16"
VENDOR_DIR = CVX + "/vendor"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ROOT = "/home/struktured/projects/dr_mario_rl"
# DRM_VENDOR: "1" = use the in-repo copies (experiments/cvx/vendor, see VENDOR_MANIFEST.json),
# "0" = the original out-of-repo locations, default "auto" = vendored iff the originals are absent.
_MODE = os.environ.get("DRM_VENDOR", "auto")
VENDORED = _MODE == "1" or (_MODE != "0" and not (os.path.isdir(QA) and os.path.isdir(ROOT)))
if VENDORED:
    E47 = ENDGAME = COMBO = TUCK3 = FAITHFUL = PILLRNG = VENDOR_DIR
    _PATHS_FRONT = (VENDOR_DIR, CVX)
else:
    E47 = QA + "/eval47"
    PILLRNG = ROOT + "/tmp/pillrng"
    FAITHFUL = ROOT + "/.claude/worktrees/faithful-sim/src"
    COMBO = ROOT + "/tmp/combo_term"
    ENDGAME = ROOT + "/tmp/endgame"
    TUCK3 = QA + "/tuck_v3"
    # Last insert(0) is searched first. nes_pills MUST beat QA.
    _PATHS_FRONT = (QA, E47, ENDGAME, COMBO, TUCK3, FAITHFUL, PILLRNG, CVX)

class _VendorFinder:
    """Vendored mode: resolve EXACTLY the modules in VENDOR_MANIFEST.json from VENDOR_DIR, whatever
    sys.path says. Several modules (in-repo pressure_rig, vendored fb/root_search/...) insert their
    ORIGINAL absolute paths into sys.path at import time; ordering tricks cannot beat that reliably."""
    def __init__(self):
        import json
        man = json.load(open(os.path.join(VENDOR_DIR, "VENDOR_MANIFEST.json")))
        self.map = {n: os.path.join(VENDOR_DIR, e["vendored"]) for n, e in man.items()}

    def find_spec(self, fullname, path=None, target=None):
        f = self.map.get(fullname)
        if f is None:
            return None
        if os.path.basename(f) == "__init__.py":
            return importlib.util.spec_from_file_location(fullname, f,
                                                          submodule_search_locations=[os.path.dirname(f)])
        return importlib.util.spec_from_file_location(fullname, f)


if VENDORED and not any(isinstance(x, _VendorFinder) for x in sys.meta_path):
    sys.meta_path.insert(0, _VendorFinder())

PINNED = {
    "fast_rtl_x": CVX + "/fast_rtl_x.py",
    "pressure_rig": CVX + "/pressure_rig.py",
    "vs_sim": CVX + "/vs_sim.py",
    "population": CVX + "/population.py",
    "root_search": TUCK3 + "/root_search.py",
    "fast_sim_x": COMBO + "/fast_sim_x.py",
    "nes_pills": PILLRNG + "/nes_pills.py",
    "fb": ENDGAME + "/fb.py",
    "terms47": E47 + "/terms47.py",
    "drmario.faithful_env": FAITHFUL + "/drmario/faithful_env.py",
    "drmario.faithful_game": FAITHFUL + "/drmario/faithful_game.py",
}


def _front_paths():
    for p in _PATHS_FRONT:
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)


def _load_nes_pills():
    """Bind nes_pills from pillrng even if qa-wt already occupied the name."""
    sys.modules.pop("nes_pills", None)
    if PILLRNG not in sys.path:
        sys.path.insert(0, PILLRNG)
    mod = importlib.import_module("nes_pills")
    src = open(mod.__file__).read()
    assert "_PillDraw" in src, f"nes_pills is the lambda copy: {mod.__file__}"
    assert os.path.realpath(mod.__file__) == os.path.realpath(PINNED["nes_pills"])
    return mod


def pin():
    _front_paths()
    import fast_rtl_x, pressure_rig, vs_sim, population
    import root_search, fast_sim_x, fb, terms47
    import drmario.faithful_env, drmario.faithful_game
    # pressure_rig re-inserts qa-wt/tuck_v3 at import; restore intended order.
    _front_paths()
    nes = _load_nes_pills()
    loaded = {
        "fast_rtl_x": fast_rtl_x.__file__,
        "pressure_rig": pressure_rig.__file__,
        "vs_sim": vs_sim.__file__,
        "population": population.__file__,
        "root_search": root_search.__file__,
        "fast_sim_x": fast_sim_x.__file__,
        "nes_pills": nes.__file__,
        "fb": fb.__file__,
        "terms47": terms47.__file__,
        "drmario.faithful_env": drmario.faithful_env.__file__,
        "drmario.faithful_game": drmario.faithful_game.__file__,
    }
    bad = []
    for k, want in PINNED.items():
        got = os.path.realpath(loaded[k])
        if got != os.path.realpath(want):
            bad.append(f"{k}: got {got} want {want}")
    if bad:
        raise RuntimeError("import pin failed:\n  " + "\n  ".join(bad))
    if VENDORED:
        _assert_vendored_closure(loaded)
    return loaded


def _assert_vendored_closure(loaded):
    """Vendored mode: import EVERY module in VENDOR_MANIFEST.json now and assert each resolved from
    VENDOR_DIR -- several vendored modules insert their original absolute paths into sys.path at
    import, so on a machine that still has the originals a later lazy import could bind outside."""
    import json
    man = json.load(open(os.path.join(VENDOR_DIR, "VENDOR_MANIFEST.json")))
    bad = []
    for name in man:
        mod = importlib.import_module(name)
        f = os.path.realpath(mod.__file__)
        loaded[name] = f
        if not f.startswith(os.path.realpath(VENDOR_DIR) + os.sep):
            bad.append(f"{name}: {f}")
    _front_paths()
    if bad:
        raise RuntimeError("vendored closure leaked outside vendor/:\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    loaded = pin()
    for k, v in loaded.items():
        print(f"{k}: {v}")
    print("PIN_OK")
