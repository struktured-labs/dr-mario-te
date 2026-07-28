#!/usr/bin/env python3
"""planner_bridge.py — serve the py65 depth-3 planner (nes_d3_golden.decide_d3, DEPLOY config)
to the Mesen copro harness over a tiny file protocol, so the emulated copro answers with the
ACTUAL brain's move instead of the dumb default. Turns the harness into a real end-to-end
integration test of cart + driver + brain (task #47 stretch, team-lead GO).

DEPLOY config (mirrors build_copro_d3.build_image + the 'how to apply' in the
golden-is-weekend-era memory): topk1=32 (full ply1), topk2=8, third=THIRD (4-pill stratified),
DISC_SHIFT=1, EXCAV_HANG_PLY1=True, W_EXCAV=24, imm=180*vir+10*cells, WIN=30000.

*** LEAF FIDELITY: RTL-EXACT (leaf_r47) ***  decide_d3's own leaf_d3 is WEEKEND-ERA (12*vrdy,
flat buried, no matched60; it does NOT read the R47 flags). So at startup we MONKEYPATCH
nes_d3_golden.leaf_d3 -> the RTL-faithful leaf in fpga/copro/leaf_r47.py, which is validated
536/536 cell-exact vs the pinned Verilator corpus (real LeafEval.sv output) and 5036/5036 vs the
live RTL. The whole depth-3 chain is now ship-faithful: leaf == RTL == FPGA, search == decide_d3
== the shipped 6502 emit_search_d3. --w-vrdy selects the arm: 24 = the eval on the CURRENTLY
SHIPPED cart; 12 = the r47b5_c11_pad build in flight (task #48, "vrdy 24->12"). Only the vrdy
coefficient differs between arms; all other R47 leaf refinements (R1 same-color burial exemption,
R7b nearest-2 cap, R6 matched-cover) stay at their shipped-default values. eh_terms (W_EXCAV
g_excav/g_hang) is a decide_d3 ply-1 ROOT add-on, NOT part of LeafEval, so it stays layered on top
exactly as the shipped 6502 engine path does it.

Protocol (line-based text, atomic via os.replace), in --dir:
  req.txt : seq\n  pA pB nA nB\n  <128 space-separated board bytes>\n
  resp.txt: seq\n  col o4 compute_ms\n
Board bytes are RAW NES playfield ($00 already normalized to $FF by the harness): $FF empty,
virus = high nibble $D, color = low nibble; row-major 8x16 (offset = row*8 + col). col in 0..7,
o4 in 0..3 (copro-space: 0=V A-top,1=V B-top,2=H A-left,3=H B-left) — the driver maps o4 to game
orient {0:3,1:1,2:0,3:2}.
"""
import os, sys, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
# planner lives in the repo tests/; use the canonical incr-delta worktree
REPO = "/home/struktured/projects/dr-mario-mods.wt/incr-delta"
sys.path.insert(0, os.path.join(REPO, "tests"))
sys.path.insert(0, os.path.join(REPO, "fpga", "copro"))

import test_search_d3 as D3
import nes_d3_golden as G
import leaf_r47 as LR


def install_r47_leaf(w_vrdy):
    """Replace nes_d3_golden's weekend-era leaf_d3 with the RTL-exact leaf_r47.

    decide_d3 looks up the module global `leaf_d3` at call time, so rebinding
    G.leaf_d3 makes the ENTIRE depth-3 search evaluate every leaf with the shipped
    LeafEval.sv S_DONE2 combine (leaf_r47.leaf_sco, 536/536 cell-exact vs the pinned
    RTL corpus). The WIN sentinel (virus_count==0 -> G.WIN) is preserved so the search's
    win logic is byte-for-byte unchanged. w_vrdy is the only per-arm knob: 24 = shipped
    cart, 12 = the r47b5 build in flight; the remaining R47 leaf refinements keep
    leaf_r47's shipped defaults (buried_color_aware / buried_nearest2_cap / matched_cover).
    """
    def leaf_r47_d3(b):
        if G._virus_count(b) == 0:
            return G.WIN
        sco, _win = LR.leaf_sco(b, w_vrdy=w_vrdy)
        return sco
    leaf_r47_d3.w_vrdy = w_vrdy
    G.leaf_d3 = leaf_r47_d3
    return leaf_r47_d3


def apply_deploy_config():
    """Set nes_d3_golden module state to the shipped DEPLOY search config.

    NOTE: the G.* leaf flags below (BURIED_COLOR_AWARE, W_VRDY, ...) are read only by the
    weekend leaf_d3; once install_r47_leaf() rebinds leaf_d3 they are inert. They are kept
    set for anyone who inspects G, but the leaf's real config lives in leaf_r47's flags.
    The SEARCH-shaping settings (DISC_SHIFT, EXCAV_HANG_PLY1, W_EXCAV, hang params) DO matter
    -- decide_d3 reads them directly for the blend and the ply-1 eh_terms root add-on."""
    G.DISC_SHIFT = 1
    G.EXCAV_HANG_PLY1 = True
    G.W_EXCAV = 24              # build_copro_d3 override (default 12)
    # leaf/eh flags (no-ops on the weekend leaf, set for faithfulness where read)
    G.BURIED_COLOR_AWARE = True
    G.W_VRDY = 24
    G.HANG_DEPTH_PROP = True
    G.W_HANG_GAP = 20
    G.HANG_VIRUS_COL_ONLY = True
    G.MATCHED_COVER_SETUP = True
    G.W_MATCHED_COVER = 60
    G.BURIED_NEAREST2_CAP = True
    G.READINESS_EXT_CAP = 0


def decide(board, pA, pB, nA, nB):
    """One deploy-config depth-3 decision. Returns (col, o4, ms)."""
    t0 = time.time()
    mv = G.decide_d3(list(board), pA, pB, nA, nB,
                     topk1=32, topk2=8, third=D3.THIRD, seed=0)
    ms = int((time.time() - t0) * 1000)
    if mv is None:
        return (0, 0, ms)           # no legal placement (topout imminent) -> harmless default
    col, o4 = mv
    return (int(col) & 7, int(o4) & 3, ms)


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def _read_req(path):
    """Parse req.txt -> (seq, pA,pB,nA,nB, board[128]) or None if malformed/partial."""
    try:
        with open(path) as f:
            lines = f.read().splitlines()
        seq = int(lines[0])
        pA, pB, nA, nB = (int(x) for x in lines[1].split())
        board = [int(x) for x in lines[2].split()]
        if len(board) != 128:
            return None
        return (seq, pA, pB, nA, nB, board)
    except Exception:
        return None


def serve(d, w_vrdy=24, verbose=True):
    apply_deploy_config()
    install_r47_leaf(w_vrdy)
    req_path = os.path.join(d, "req.txt")
    resp_path = os.path.join(d, "resp.txt")
    os.makedirs(d, exist_ok=True)
    # clear any stale files
    for p in (req_path, resp_path):
        try: os.remove(p)
        except FileNotFoundError: pass
    last_seq = -1
    arm = "SHIPPED cart" if w_vrdy == 24 else ("r47b5 in-flight" if w_vrdy == 12 else "custom")
    print(f"[bridge] serving decide_d3 (DEPLOY d3, RTL-exact leaf_r47 w_vrdy={w_vrdy} [{arm}]) "
          f"in {d}; waiting for req.txt (Ctrl-C to stop)", flush=True)
    while True:
        r = _read_req(req_path)
        if r is not None and r[0] != last_seq:
            seq, pA, pB, nA, nB, board = r
            last_seq = seq
            col, o4, ms = decide(board, pA, pB, nA, nB)
            _atomic_write(resp_path, f"{seq}\n{col} {o4} {ms}\n")
            if verbose:
                vir = sum(1 for c in board if (c & 0xF0) == 0xD0)
                print(f"[bridge] seq={seq} pill=({pA},{pB}) next=({nA},{nB}) vir={vir} -> col={col} o4={o4} ({ms}ms)", flush=True)
        time.sleep(0.01)


def selftest(w_vrdy=24):
    import random
    apply_deploy_config()
    leaf = install_r47_leaf(w_vrdy)
    # prove the swap took: the installed leaf must be the RTL mirror, not the weekend one
    assert G.leaf_d3 is leaf and getattr(G.leaf_d3, "w_vrdy", None) == w_vrdy, "leaf swap failed"
    # spot-check a virus-bearing board scores identically through G.leaf_d3 and leaf_r47.leaf_sco
    _probe = [0xFF] * 128
    _probe[8 * 8 + 3] = 0xD0; _probe[9 * 8 + 3] = 0x00  # a virus + a cell
    assert G.leaf_d3(_probe) == LR.leaf_sco(_probe, w_vrdy=w_vrdy)[0], "leaf score mismatch"
    print(f"[selftest] leaf swap OK: G.leaf_d3 is RTL leaf_r47 (w_vrdy={w_vrdy})")
    random.seed(11)
    b = [0xFF] * 128
    placed = 0
    while placed < 48:
        r = random.randint(6, 15); c = random.randint(0, 7); off = r * 8 + c
        if b[off] == 0xFF:
            b[off] = 0xD0 | random.randint(0, 2); placed += 1
    print(f"[selftest] synthetic board with {placed} viruses")
    for _ in range(3):
        col, o4, ms = decide(b, 0, 1, 1, 2)
        print(f"[selftest] decide -> col={col} o4={o4} ({ms}ms)")
    # round-trip via files
    d = os.path.join(HERE, "bridge")
    os.makedirs(d, exist_ok=True)
    _atomic_write(os.path.join(d, "req.txt"),
                  "7\n0 1 1 2\n" + " ".join(str(x) for x in b) + "\n")
    r = _read_req(os.path.join(d, "req.txt"))
    assert r is not None and r[0] == 7 and len(r[5]) == 128, "req round-trip failed"
    print(f"[selftest] req round-trip OK (seq={r[0]}, {sum(1 for c in r[5] if (c&0xF0)==0xD0)} viruses parsed)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(HERE, "bridge"))
    ap.add_argument("--w-vrdy", type=int, default=24,
                    help="leaf_r47 vrdy coefficient: 24 = shipped cart, 12 = r47b5 in-flight (task #48)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(a.w_vrdy)
    else:
        serve(a.dir, a.w_vrdy)
