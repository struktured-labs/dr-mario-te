"""silfid lane: load silicon trajectories (video tracker) + Mesen FAIR replay T-traces per pill, aligned on spawn."""
import json, re, os, collections
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
RUNS = "/home/struktured/projects/dr_mario_rl/tmp/lulu_20261005/fx/execfid/runs"
GAMES = ["m1g1", "m1g2", "m1g4", "m2g2", "m2g3"]
TRE = re.compile(r"^T p(\d+) f=(-?\d+) y=(\d+) x=(\d+) rot=(\d+) na=(\d+) grav=(\d+) \| tgt=(\d+),(\d+) rd2=(\d+) arm=(\d+) pend=(\d+) dly=(\d+) eff=(\d+) bud=(\d+) fall=(\d+) proph=(\w+) lg=(\d+),(\d+) \| pad=(\w+) held=(\w+) \| mb=(-?\d+),(-?\d+),(-?\d+) k=(-?\d+) sa=(\d+) st=(\d+) pa=(\d+) hv=(\d+) f8=(\w+) lpc=(\d+)")
LRE = re.compile(r"^LAND p(\d+) f=(\d+) x=(\d+) y=(\d+) rot=(\d+) action=(\d+)")
KEYS = "p f y x rot na grav tc to rd2 arm pend dly eff bud fall proph lgc lgl pad held mbc mbo mbd k sa st pa hv f8 lpc".split()

def mesen(game, arm="D", tag=None):
    tag = tag or f"lulu1005_{game}_{arm}_chain_garb"
    path = os.path.join(RUNS, tag, f"lateflip_{tag}.log")
    T = collections.defaultdict(list); land = {}; inject = {}
    for ln in open(path, errors="replace"):
        if ln.startswith("T p"):
            m = TRE.match(ln)
            if not m:
                continue
            v = m.groups(); d = {}
            for k, s in zip(KEYS, v):
                d[k] = int(s, 16) if k in ("proph", "pad", "held", "f8") else int(s)
            T[d["p"]].append(d)
        elif ln.startswith("LAND p"):
            m = LRE.match(ln); p = int(m.group(1))
            land[p] = dict(f=int(m.group(2)), x=int(m.group(3)), y=int(m.group(4)), rot=int(m.group(5)), a=int(m.group(6)))
        elif ln.startswith("INJECT p"):
            p = int(ln.split()[1][1:]); inject[p] = ln.strip()
    return T, land, inject

def cases(game):
    return {q["p"]: q for q in map(json.loads, open(os.path.join(CF, f"cases_ai_{game}_lulu_20261005.jsonl")))}

def fidelity():
    return {(f["game"], f["p"]): f for f in map(json.loads, open(os.path.join(CF, "cases_ai_fidelity_lulu_20261005.jsonl")))}

def misses():
    return {(f["game"], f["p"]): f for f in map(json.loads, open(os.path.join(CF, "cases_ai_misses_lulu_20261005.jsonl")))}

def pubtrace(game):
    return {r["p"]: r for r in map(json.loads, open(os.path.join(CF, f"pubtrace_{game}_lulu_20261005.jsonl")))}

def sil_frames(q):
    """silicon per-frame poses: {frame_since_spawn: (HV, row, col, colours)}"""
    out = {}
    for t, hv, row, col, cols in q["traj"]:
        f = round((t - q["t_spawn"]) * 60)
        out[f] = (hv, row, col, tuple(cols))
    return out

def mpose(d, cur):
    """Mesen T row -> silicon-comparable pose (HV, row, col, colours)"""
    rot = d["rot"]; row = 15 - d["y"]
    a, b = cur
    if rot == 0: return ("H", row, d["x"], (a, b))
    if rot == 2: return ("H", row, d["x"], (b, a))
    if rot == 3: return ("V", row - 1, d["x"], (a, b))
    return ("V", row - 1, d["x"], (b, a))

def spose(s, cur):
    hv, row, col, cols = s
    if cur[0] == cur[1]: cols = (cur[0], cur[1])
    return (hv, row, col, cols)
