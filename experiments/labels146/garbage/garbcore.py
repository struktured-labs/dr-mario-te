"""garbcore.py — garbage-board labeling campaign (PREREG_GARBAGE.md).

Strata A/B: import the champion's (P2) pre-death board from a MiSTer
save-state, gate it (mode / counter / settle / links / pills), and label every
dedup'd candidate with N=8 CRN forks to H=25 under the L20 lulu home regime.
Per-sample future = capsule stream swap (autopsy A1.1) + injection, both keyed
by dist_seed(source_key, 0, s) — candidate-independent, so CRN holds.

Stratum C: labelcore's replay-gated walk + label_state, unchanged, at the
mid-game window end-k, k in {30, 40, 50}.

Everything decision-making is the sealed champion-145 oracle lineage, imported.
"""
import base64
import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))            # labelcore
sys.path.insert(0, os.path.expanduser(
    "~/projects/dr-mario-sileval-wt/experiments/sileval"))  # e1_winner

import numpy as np  # noqa: E402
import labelcore as LC  # noqa: E402  (also wires the oracle sys.path)
import oracle_arm  # noqa: E402,F401  (its import block wires EV/QA/faithful-sim paths)

LEVEL = 20
H = 25
N_SAMPLES = 8
PILLS_PLACED_INIT = 60      # >= GARBAGE_MIN_PILLS=25: pressure live (PREREG §4)
MAX_PILLS = PILLS_PLACED_INIT + 400

# NES RAM offsets relative to the save-state's internal-RAM base (P2 = champion)
MODE = 0x46
P2_BOARD = 0x500
P2_VIRUS_BCD = 0x3A4
P2_CUR_A, P2_CUR_B = 0x381, 0x382
P2_NXT_A, P2_NXT_B = 0x39A, 0x39B

STRATUM_ID = {"A": 1, "B": 2}

# tile high-nibble -> link direction names (transfer_check.nes_to_board mapping)
_LINK_OF_HI = {0x4: "down", 0x5: "up", 0x6: "right", 0x7: "left"}
_DELTA = {"down": (1, 0), "up": (-1, 0), "right": (0, 1), "left": (0, -1)}
_RECIP = {"down": "up", "up": "down", "right": "left", "left": "right"}


class ImportVoid(Exception):
    """The save-state failed an import gate; .cls names the VOID class."""
    def __init__(self, cls, detail=None):
        super().__init__(cls, detail)
        self.cls = cls
        self.detail = detail


def _bcd(x):
    return (x >> 4) * 10 + (x & 0x0F)


def read_state(path, hint=None):
    """Decode one save-state -> dict(nes[128], cur, nxt, mode, v2, base).

    Raises ImportVoid on gates G-I1 (mode), G-I2 (counter), G-I5 (pills).
    The base offset is re-verified per file (find_base anchors on magics).
    """
    import e1_winner as E
    blob = open(path, "rb").read()
    try:
        base = E.find_base(blob, hint)
    except BaseException as ex:            # find_base may SystemExit
        raise ImportVoid("nobase", repr(ex))
    mode = blob[base + MODE]
    if mode != 4:                          # G-I1
        raise ImportVoid("mode", mode)
    nes = list(blob[base + P2_BOARD: base + P2_BOARD + 128])
    nvir = sum(1 for v in nes if (v >> 4) == 0xD)
    v2 = _bcd(blob[base + P2_VIRUS_BCD])
    if nvir != v2:                         # G-I2
        raise ImportVoid("counter", (nvir, v2))
    cur = (blob[base + P2_CUR_A], blob[base + P2_CUR_B])
    nxt = (blob[base + P2_NXT_A], blob[base + P2_NXT_B])
    if not all(0 <= c <= 2 for c in cur + nxt):   # G-I5
        raise ImportVoid("pills", (cur, nxt))
    return {"nes": nes, "cur": cur, "nxt": nxt, "mode": mode, "v2": v2,
            "base": base}


def decode_planes(nes):
    """128 NES bytes -> (color, is_virus, link) 16x8 planes, gated.

    G-I4: every half-link must have a reciprocal partner (bail, don't model).
    Link plane holds direction names (matched to FaithfulBoard's encoding by
    build_env, which translates through the vendored constants).
    """
    color = np.zeros((16, 8), dtype=np.int8)
    virus = np.zeros((16, 8), dtype=bool)
    link = np.empty((16, 8), dtype=object)
    link[:, :] = None
    for i, v in enumerate(nes):
        if v in (0xFF, 0x00):
            continue
        r, c = divmod(i, 8)
        hi = (v >> 4) & 0xF
        color[r, c] = (v & 0x3) + 1
        if hi == 0xD:
            virus[r, c] = True
        elif hi in _LINK_OF_HI:
            link[r, c] = _LINK_OF_HI[hi]
        elif hi != 0x8:                    # 0x8x = orphan single, linkless
            raise ImportVoid("tile", (r, c, hex(v)))
    for r in range(16):
        for c in range(8):
            d = link[r, c]
            if d is None:
                continue
            dr, dc = _DELTA[d]
            rr, cc = r + dr, c + dc
            if not (0 <= rr < 16 and 0 <= cc < 8) or link[rr, cc] != _RECIP[d]:
                raise ImportVoid("links", (r, c, d))   # G-I4
    return color, virus, link


def build_env(color, virus, link, cur, nxt, stream_seed):
    """A FaithfulDrMarioEnv holding the imported board, cur/nxt from RAM.

    G-I3 (settle): _apply_gravity on the imported board must be a NO-OP.
    """
    from drmario.faithful_env import FaithfulDrMarioEnv, Pill
    from drmario.faithful_game import LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT
    import oracle_arm as OA
    from nes_pills import NesPillSource
    lcode = {"up": LINK_UP, "down": LINK_DOWN,
             "left": LINK_LEFT, "right": LINK_RIGHT}
    env = FaithfulDrMarioEnv(level=LEVEL, seed=int(stream_seed) & 0xFFFF,
                             max_pills=MAX_PILLS)
    env.reset()
    b = env.board
    b.color[:, :] = color
    b.is_virus[:, :] = virus
    b.link[:, :] = 0
    for r in range(16):
        for c in range(8):
            if link[r, c] is not None:
                b.link[r, c] = lcode[link[r, c]]
    before = (b.color.copy(), b.is_virus.copy(), b.link.copy())
    b._apply_gravity()
    moved = not (np.array_equal(before[0], b.color)
                 and np.array_equal(before[1], b.is_virus)
                 and np.array_equal(before[2], b.link))
    if moved:                              # G-I3
        raise ImportVoid("settle")
    env._rand_pill = OA.PillDraw(NesPillSource(seed=int(stream_seed) & 0xFFFF))
    env.cur = Pill(cur[0] + 1, cur[1] + 1)     # nes 0-based -> lab 1-based
    env.nxt = Pill(nxt[0] + 1, nxt[1] + 1)
    env.pills_placed = PILLS_PLACED_INIT
    return env


def source_key(stratum, seed, pre_idx):
    """Injective fseed base (PREREG §4): (id<<24) | (seed<<8) | pre_idx."""
    sid = STRATUM_ID[stratum]
    assert 0 <= seed < 0x10000 and 0 <= pre_idx < 0x100
    return (sid << 24) | (seed << 8) | pre_idx


def _swap_stream(e, fseed):
    """Autopsy A1.1 — resample the UNSEEN future (cur/nxt stay: visible)."""
    import oracle_arm as OA
    from nes_pills import NesPillSource
    e._rand_pill = OA.PillDraw(NesPillSource(seed=int(fseed) & 0xFFFF))


def label_import_state(env, C, bmodel, skey, n_samples=N_SAMPLES, horizon=H):
    """Label every unique candidate of an IMPORTED state (strata A/B).

    Sample s: one deepcopy of env, stream swapped by fseed, then every
    candidate forked from that same copy (fseed also keys injection) — the
    future is candidate-independent, so CRN holds across candidates.
    """
    import oracle_arm as OA
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    ents = LC.enumerate_candidates(env)
    for e in ents:
        e["surv"], e["prog"] = [], []
    for s in range(n_samples):
        fseed = OA.dist_seed(skey, 0, s)
        env_s = copy.deepcopy(env)
        _swap_stream(env_s, fseed)
        for e in ents:
            surv, prog = OA._fork_label(env_s, e["rep_slot"], C, fseed, bmodel,
                                        w, fl, wt, ws, horizon)
            e["surv"].append(int(surv))
            e["prog"].append(int(prog))
    return ents


def champ_pick(env, C):
    """(vals, action) by the lab champion (the silicon champion's MIRROR)."""
    import oracle_arm as OA
    vals = LC.compute_vals(env, C["w"], C["fl"], C["wt"], C["ws"])
    return vals, OA._champ_action(vals, OA.CHAMP_ORDER)


# ------------------------------------------------------------- source lists
def load_sources_A():
    out = []
    root = os.path.expanduser(
        "~/projects/dr-mario-sileval-wt/experiments/sileval/out/artifacts")
    for ln in open(os.path.join(HERE, "sources_A.txt")):
        row, samp = ln.split()
        out.append({"stratum": "A", "row": row, "seed": int(row.split("_")[0]),
                    "sample": samp, "pre_idx": int(samp[1:4]),
                    "path": os.path.join(root, row, samp)})
    assert len(out) == 45, len(out)
    return out


def load_sources_B():
    out = []
    for ln in open(os.path.join(HERE, "sources_B.txt")):
        toks = ln.split()
        box, row, bracket, art = toks[0], toks[1], toks[2], toks[-1]
        for samp in toks[3:-1]:
            out.append({"stratum": "B", "row": row, "box": box,
                        "seed": int(row.split("_")[0]), "bracket": bracket,
                        "sample": samp, "pre_idx": int(samp[1:4]),
                        "path": os.path.join(art, samp)})
    assert len({(s["row"], s["bracket"]) for s in out}) == 17
    return out


def state_id(src):
    """Stable per-state id (dedup key for resume + fseed pre_idx)."""
    tag = src.get("bracket", "")
    return f"{src['stratum']}_{src['row']}{('_' + tag) if tag else ''}_{src['sample']}".replace(".ss", "")


# ------------------------------------------------------------- claim rule
def claims_from_row(rowd, n_samples=N_SAMPLES):
    """PREREG §5: max_c surv - surv_champ >= 3 with surv_champ <= 5."""
    ents = rowd["cands"]
    champ = None
    for e in ents:
        if rowd["champ_slot"] in e["slots"]:
            champ = e
            break
    assert champ is not None, rowd.get("id", rowd.get("seed"))
    sc = sum(champ["surv"])
    best = max(ents, key=lambda e: sum(e["surv"]))
    if sum(best["surv"]) - sc >= 3 and sc <= 5:
        return {"champ_surv": sc, "best_surv": sum(best["surv"]),
                "best_key": best["key"], "best_slot": best["rep_slot"]}
    return None
