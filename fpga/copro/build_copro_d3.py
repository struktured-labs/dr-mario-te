#!/usr/bin/env python3
"""Build the DEPTH-3 copro firmware (the 91.7% config on hardware): ply1 top-8 +
ply2 top-8 + integer expectimax over 8 pills, TARGETED capped resolve, ext+pollute+vrdy
leaf, WIN=30000. Same host handshake as full-d2 (NO SV/driver changes):
  host -> board@$0500 (LIVE), colors@$6124-27; GO=reset pulse ($BF80); firmware searches,
  writes col@$6134 orient@$6135, DONE($61FF)=1; host polls DONE.
SQ tables are read straight from ROM @$B000 (copro RAM is only $0000-$0FFF + $6100-$61FF);
the stub copies the 8-pill table ROM $B030 -> RAM $09C0. Search logic byte-identical to
tests/test_search_d3.py (30/30 vs decide_d3). Emits copro_rom.hex ($8000-$BFFF slice) and
validates in py65: direct search call + full $BF80 reset->DONE flow vs decide_d3."""
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, ROOT)

# ---- IMPORT-ORDER GUARD (root-caused 2026-08-05, task #17) -----------------------
# test_vrdy.py and test_readiness_ext.py each unconditionally `sys.path.insert(0, ...)`
# a HARDCODED sibling worktree ("/home/struktured/projects/dr-mario-mods"), not
# gated on "already present" the way this file's own inserts are effectively gated
# by running first. If anything below imports them (directly or transitively)
# BEFORE `import test_search_d3`, that worktree's copy -- which can be on a
# different branch and genuinely stale -- silently wins the name resolution instead
# of THIS tree's tests/test_search_d3.py, because Python only resolves a module by
# path on its FIRST import; whichever sys.path entry is first at that moment wins,
# silently, with no error. Traced via a `Asm6502.label` call-sequence diff between a
# working and a broken import order: identical up to one line, where the broken run
# silently skips emitting the "eh_terms_scan" label (added on this tree's branch,
# absent from dr-mario-mods' study-pause-branch copy) -- confirmed by printing
# `test_search_d3.__file__` in the broken scenario: it resolved to dr-mario-mods,
# not this file's own tests/. See TUCK_BFS_PORT_REPORT.md for the day's fuller
# investigation log (the original bug report + workaround before this fix).
#
# FIX: force-register the CORRECT test_search_d3 (this tree's own tests/) into
# sys.modules before anything else has a chance to import it under a polluted
# path -- the same force-preload dbg_build.py already uses for its own (deliberate,
# delta-emitter) override, just moved into the library so every entry point
# inherits the protection instead of needing to know about this trap.
#
# Guard condition is "absent OR specifically the known-stale sibling", not just
# "absent" -- a plain "not in sys.modules" only protects THIS file's own internal
# import order (test_vrdy/test_readiness_ext are imported below, by this file,
# AFTER this guard runs, so a bare presence check would suffice for that). But the
# same trap can also be sprung by code OUTSIDE this file that imports test_vrdy/
# test_readiness_ext (or anything else that pollutes sys.path the same way) before
# ever importing build_copro_d3 -- in that case "test_search_d3" is ALREADY in
# sys.modules by the time this guard runs, just pointing at the wrong file, and a
# bare presence check would wrongly treat that as "already claimed, leave it
# alone". Detecting the SPECIFIC known-bad path and re-registering over it handles
# both cases while still never touching a genuinely different, deliberate override
# (dbg_build.py's own incr-delta emitter has a different __file__ entirely, so it
# never matches this condition and is left untouched).
#
# LIMIT: this can only fix module-registry resolution from this point forward. A
# caller that already did its own `import test_search_d3 as D3` (or `from
# test_search_d3 import X`) before ever importing build_copro_d3 has already bound
# ITS OWN name to whatever was cached at that moment -- re-registering the sys.
# modules entry here cannot retroactively fix a reference the caller already holds.
# That is a different, narrower failure mode than the one this guard closes (this
# file's own internal resolution, and any OTHER code's later resolution of the
# name), and is inherent to how Python's import cache works, not fixable from a
# library's own import block.
_bad_cached = ("test_search_d3" in sys.modules
               and "dr-mario-mods/" in getattr(sys.modules["test_search_d3"], "__file__", ""))
if "test_search_d3" not in sys.modules or _bad_cached:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
    _mod = _ilu.module_from_spec(_spec)
    sys.modules["test_search_d3"] = _mod
    _spec.loader.exec_module(_mod)
    del _ilu, _spec, _mod
del _bad_cached

import patch_vs_cpu
patch_vs_cpu.OPS.setdefault("SEI", 0x78)
patch_vs_cpu.OPS.setdefault("TXS", 0x9A)
from patch_vs_cpu import Asm6502
from py65_harness import Cpu
import test_vrdy, test_readiness_ext
import test_search_d3 as D3
assert "dr-mario-mods/" not in D3.__file__, (
    f"test_search_d3 resolved to the known-stale sibling worktree: {D3.__file__} "
    "-- the import-order guard above should have prevented this; see its comment")
from test_search_d3 import (THIRD, PILLA, PILLB, D_BC, D_BO, make_fewlegal)
from test_depth2 import S_CA, S_CB, S_NA, S_NB, S_BEST_C, S_BEST_O
import primitives as P
import nes_d3_golden as G3

EMPTY = 0xFF
STUB = 0xBF80            # MiSTer mapper hardcodes the copro reset to $BF80 (in-ROM)
DONE = 0x61FF
# DRCOPRO_TUCK=1: emit the 6502 tuck enumerator and call it after the search, so the copro
# publishes a real tuck descriptor at $6139/$613A (cart $5087/$5088 once CoproDrMario's
# xlate maps them). Default OFF keeps this builder's output byte-identical.
EMIT_TUCK = os.environ.get("DRCOPRO_TUCK", "0") == "1"
TUCK_ROM = 0xA800            # free: search ends ~$88E1, SQ tables start $B000
TUCK_COL, TUCK_ROW = 0x6139, 0x613A
# DRCOPRO_TUCKV3=1: task #17 stage-2 firmware integration -- generalised root-action tucks
# (multi-candidate/both-orientation enumeration, full depth-3 scoring via slot-0 injection,
# theta=150 gate, EH_PLY1 required). Alternative to v1's EMIT_TUCK (same TUCK_COL/TUCK_ROW
# mailbox, same driver-side executor consumes either), not simultaneous -- asserted below.
# Default OFF keeps this builder's output byte-identical (including with EMIT_TUCK=1 --
# v3 being off must not perturb v1's existing wiring at all).
EMIT_TUCK_V3 = os.environ.get("DRCOPRO_TUCKV3", "0") == "1"
assert not (EMIT_TUCK and EMIT_TUCK_V3), "EMIT_TUCK (v1) and EMIT_TUCK_V3 are alternatives"
TUCK_V3_ROM = 0x9000          # well clear of search-end (~$88E1) and v1's TUCK_ROM ($A800)
# DRCOPRO_TUCKBFS=1: task #17 stage 4 -- the TE-free BFS enumerator (tests/tuck_bfs_6502.py,
# bit-exact 200/200 vs tuck_enum.py's motion-truth reachable set) + its CANDLIST translation
# (tests/tuck_bfs_translate_6502.py) feeding tuck_v3.py's UNCHANGED scoring/gating functions
# (tuck_cell_prep/tuck_ply2_score/tuck_root_extension) in place of tuck_v3's own tuck_scan_v3
# enumerator. Alternative to EMIT_TUCK_V3 (same CANDLIST/TS_CNT/TS_DROP/TUCK_COL/TUCK_ROW
# mailbox, same driver-side executor), not simultaneous -- asserted below. Shares
# TUCK_V3_ROM's address (never co-resident, so no collision) rather than claiming a 4th ROM
# region. Default OFF keeps this builder's output byte-identical.
EMIT_TUCK_BFS = os.environ.get("DRCOPRO_TUCKBFS", "0") == "1"
assert not (EMIT_TUCK and EMIT_TUCK_BFS), "EMIT_TUCK (v1) and EMIT_TUCK_BFS are alternatives"
assert not (EMIT_TUCK_V3 and EMIT_TUCK_BFS), \
    "EMIT_TUCK_V3 and EMIT_TUCK_BFS are alternative enumerators for the same tuck_v3 scoring"
TUCK_BFS_ROM = TUCK_V3_ROM
# DRCOPRO_TUCKBFS_TIER3=1: tier-3 mission (2026-08-05) -- widens tuck_bfs's CANDLIST
# translation (tests/tuck_bfs_translate_6502.py, tier 1: target+/-1 approach columns) to
# tests/tuck_bfs_tier3_6502.py's tier-3 vocabulary (any approach column, mono-reachable-
# verified) as a FALLBACK tried only when tier 1 finds nothing for a candidate -- see
# tuck_bfs_tier3_6502.py's own module docstring for the driver investigation that makes
# this safe (mv_p2's steering was already general over all 8 columns; only the search's
# own translation was narrow). ADDITIVE on top of EMIT_TUCK_BFS, not an alternative to it
# (asserted below) -- swaps ONE call (tr_translate -> tr_translate_tier3) in the tuck_bfs_v3
# entry point; tuck_bfs_6502.py and tuck_bfs_translate_6502.py are never modified, so
# DRCOPRO_TUCKBFS=1 alone (this knob off) keeps its existing byte-for-byte behaviour.
EMIT_TUCK_BFS_TIER3 = os.environ.get("DRCOPRO_TUCKBFS_TIER3", "0") == "1"
assert not (EMIT_TUCK_BFS_TIER3 and not EMIT_TUCK_BFS), \
    "DRCOPRO_TUCKBFS_TIER3 requires DRCOPRO_TUCKBFS=1 (tier 3 is a translation upgrade, " \
    "not a standalone enumerator)"
SQ_ROM, PILL_ROM = 0xB000, 0xB030
MAX_STEPS = 3_000_000_000


def build_image(board, cA, cB, nA, nB):
    assert (D3.NPILLS, D3.SHIFT) == (4, 2), "deploy config is 4 pills / >>2 (isoD 24/24)"
    D3.USE_ENGINE = True         # full BoardEngine: land/resolve/leaf/copies in RTL
    D3.DISC = True               # temporal discount d=0.5 (dual-end fix, +14% solo efficiency)
    D3.EH_PLY1 = True            # ply-1 excav+hang firmware add-on (eh_terms -> D_AD)
    # #47 stranded-half root cost (env DRSTRAND, default 0 = byte-identical firmware;
    # dose 20 = the mirror+VS-gated config, see eval47/SILICON_PLAN.md).
    D3.DRSTRAND = int(os.environ.get("DRSTRAND", "0"))
    # #123 double-capsule orient canonicalisation. Default 0 = emits NOTHING, so
    # copro_rom.hex stays byte-identical to the pre-#123 build (the hex drift guard
    # depends on that). NOT "DRCANON" -- that name is already in use as a path to
    # the canonical worktree in four files, and setting it to 1 would break them.
    D3.DBLCANON = int(os.environ.get("DRDBLCANON", "0"))
    import nes_d3_golden as _G
    _G.DISC_SHIFT = 1            # golden must match for the py65 gate
    _G.EXCAV_HANG_PLY1 = True    # golden must match for the py65 gate
    _G.BURIED_COLOR_AWARE = True # R1: color-aware g_buried (matches patched LeafEval.sv RTL)
    _G.W_VRDY = 12               # R3->r47b5: vrdy 24->12 (lockstep w/ LeafEval.sv S_DONE; leaf runs in RTL so no hex change)
    _G.W_EXCAV = 24              # R2: eh_terms excav weight -> emitted into copro_rom.hex
    _G.HANG_DEPTH_PROP = True     # R4: depth-proportional hang credit  (eh_terms -> copro_rom.hex)
    _G.W_HANG_GAP = 20            # R4
    _G.HANG_VIRUS_COL_ONLY = True # R4: credit hangs only in virus columns
    _G.MATCHED_COVER_SETUP = True # R6: matched-cover setup credit (matches patched LeafEval.sv)
    _G.W_MATCHED_COVER = 60       # R6
    _G.BURIED_NEAREST2_CAP = True # R7b: buried capped at 2 topmost viruses/col (matches RTL)
    _G.READINESS_EXT_CAP = 0      # R7a: no-op on resolved boards (run^2<=9)
    # copro RAM is ONLY $0000-$0FFF + $6100-$61FF (CoproDrMario.sv): the SQ tables must be
    # read straight from ROM @$B000 (there is no RAM at the py65 tests' $7A00 location).
    # test_vrdy/test_readiness_ext capture the addresses at import -> override those too.
    P.SQ_LO_ADDR, P.SQ_HI_ADDR = SQ_ROM, SQ_ROM + 17
    test_vrdy.SQ_LO, test_vrdy.SQ_HI = SQ_ROM, SQ_ROM + 17
    test_readiness_ext.SQ_LO, test_readiness_ext.SQ_HI = SQ_ROM, SQ_ROM + 17
    code, labels = D3.build()
    assert len(code) <= SQ_ROM - 0x8000, f"search overruns ROM tables ({len(code)}B)"
    search_ep = 0x8000 + labels["search"]

    tuck_code = b""
    if EMIT_TUCK:
        from tuck_scan import emit_tuck_scan
        ta = Asm6502(TUCK_ROM)
        emit_tuck_scan(ta, live=0x0500)          # self-contained: owns its first-occ scan
        tuck_code = ta.assemble()
        assert TUCK_ROM + len(tuck_code) <= SQ_ROM, "tuck_scan overruns the SQ tables"
        assert 0x8000 + len(code) <= TUCK_ROM, "search overruns tuck_scan"

    tuck_v3_code = b""
    tuck_v3_ep = None
    if EMIT_TUCK_V3:
        import tuck_v3 as TV
        resolve_capped_addr = 0x8000 + labels["resolve_capped"]
        expectimax_addr = 0x8000 + labels["expectimax"]
        eh_terms_scan_addr = 0x8000 + labels["eh_terms_scan"]
        cp_live_cur_addr = 0x8000 + labels["cp_live_cur"]
        tv = Asm6502(TUCK_V3_ROM)
        TV.emit_tuck_scan_v3(tv, live=0x0500)
        TV.emit_land_place_at(tv, board=TV.CUR)
        TV.emit_tuck_cell_prep(tv, s_ca=S_CA, s_cb=S_CB)
        TV.emit_tuck_imm1(tv)
        TV.emit_tuck_slot0_inject(tv, eh_terms_scan_addr, D3.D_L1L, D3.D_L1H, board=TV.CUR)
        TV.emit_tuck_ply2_score(
            tv, D_C2=D3.D_C2, D_O2=D3.D_O2, D_TKC=D3.D_TKC, D_J=D3.D_J,
            D_MKL=D3.D_MKL, D_MKH=D3.D_MKH, D_MI=D3.D_MI, D_B2L=D3.D_B2L, D_B2H=D3.D_B2H,
            D_I1L=D3.D_I1L, D_I1H=D3.D_I1H, D_I2L=D3.D_I2L, D_I2H=D3.D_I2H,
            D_L1L=D3.D_L1L, D_L1H=D3.D_L1H, D_V1L=D3.D_V1L, D_V1H=D3.D_V1H,
            D_V3L=D3.D_V3L, D_V3H=D3.D_V3H, D_EL=D3.D_EL, D_EH=D3.D_EH,
            D_ADL=D3.D_ADL, D_ADH=D3.D_ADH, S_NA=S_NA, S_NB=S_NB,
            TK_KL=D3.TK_KL, TK_KH=D3.TK_KH, TK_O=D3.TK_O, TK_C=D3.TK_C,
            TK_IL=D3.TK_IL, TK_IH=D3.TK_IH, WIN=D3.WIN, DISC=D3.DISC,
            expectimax_addr=expectimax_addr,
        )
        TV.emit_tuck_root_extension(
            tv, D_BVL=D3.D_BVL, D_BVH=D3.D_BVH, D_BC=D_BC, D_BO=D_BO,
            S_BEST_C=S_BEST_C, S_BEST_O=S_BEST_O,
            D_V1L=D3.D_V1L, D_V1H=D3.D_V1H, D_I1L=D3.D_I1L, D_I1H=D3.D_I1H,
            resolve_capped_addr=resolve_capped_addr,
            cp_live_cur_addr=cp_live_cur_addr,
        )
        tv.label("tuck_v3")
        tv.jsr("tuck_scan_v3")
        tv.jsr("tuck_root_extension")
        tv.ins("RTS")
        tuck_v3_code = tv.assemble()
        tuck_v3_ep = TUCK_V3_ROM + tv.labels["tuck_v3"]
        assert TUCK_V3_ROM + len(tuck_v3_code) <= 0xA800, \
            f"tuck_v3 overruns the free ROM window before $A800 ({len(tuck_v3_code)}B)"
        assert 0x8000 + len(code) <= TUCK_V3_ROM, "search overruns tuck_v3"

    tuck_bfs_code = b""
    tuck_bfs_ep = None
    if EMIT_TUCK_BFS:
        import tuck_bfs_6502 as TB
        import tuck_bfs_translate_6502 as TRB
        import tuck_v3 as TV
        resolve_capped_addr = 0x8000 + labels["resolve_capped"]
        expectimax_addr = 0x8000 + labels["expectimax"]
        eh_terms_scan_addr = 0x8000 + labels["eh_terms_scan"]
        cp_live_cur_addr = 0x8000 + labels["cp_live_cur"]
        tvb = Asm6502(TUCK_BFS_ROM)
        TB.emit_tuck_bfs(tvb)                    # enumerator: "tuck_bfs" label
        TRB.emit_translate(tvb)                  # translation: "tr_translate" label,
                                                   # writes tuck_v3.py's own CANDLIST/TS_CNT/
                                                   # TS_DROP -- same bytes tuck_scan_v3 would
        translate_entry = "tr_translate"
        if EMIT_TUCK_BFS_TIER3:
            import tuck_bfs_tier3_6502 as T3
            T3.emit_tier3(tvb)                   # adds tr_derive_cascade/tr_translate_tier3
            translate_entry = "tr_translate_tier3"  # tier1-then-tier3, same CANDLIST bytes
        TV.emit_land_place_at(tvb, board=TV.CUR)
        TV.emit_tuck_cell_prep(tvb, s_ca=S_CA, s_cb=S_CB)
        TV.emit_tuck_imm1(tvb)
        TV.emit_tuck_slot0_inject(tvb, eh_terms_scan_addr, D3.D_L1L, D3.D_L1H, board=TV.CUR)
        TV.emit_tuck_ply2_score(
            tvb, D_C2=D3.D_C2, D_O2=D3.D_O2, D_TKC=D3.D_TKC, D_J=D3.D_J,
            D_MKL=D3.D_MKL, D_MKH=D3.D_MKH, D_MI=D3.D_MI, D_B2L=D3.D_B2L, D_B2H=D3.D_B2H,
            D_I1L=D3.D_I1L, D_I1H=D3.D_I1H, D_I2L=D3.D_I2L, D_I2H=D3.D_I2H,
            D_L1L=D3.D_L1L, D_L1H=D3.D_L1H, D_V1L=D3.D_V1L, D_V1H=D3.D_V1H,
            D_V3L=D3.D_V3L, D_V3H=D3.D_V3H, D_EL=D3.D_EL, D_EH=D3.D_EH,
            D_ADL=D3.D_ADL, D_ADH=D3.D_ADH, S_NA=S_NA, S_NB=S_NB,
            TK_KL=D3.TK_KL, TK_KH=D3.TK_KH, TK_O=D3.TK_O, TK_C=D3.TK_C,
            TK_IL=D3.TK_IL, TK_IH=D3.TK_IH, WIN=D3.WIN, DISC=D3.DISC,
            expectimax_addr=expectimax_addr,
        )
        TV.emit_tuck_root_extension(
            tvb, D_BVL=D3.D_BVL, D_BVH=D3.D_BVH, D_BC=D_BC, D_BO=D_BO,
            S_BEST_C=S_BEST_C, S_BEST_O=S_BEST_O,
            D_V1L=D3.D_V1L, D_V1H=D3.D_V1H, D_I1L=D3.D_I1L, D_I1H=D3.D_I1H,
            resolve_capped_addr=resolve_capped_addr,
            cp_live_cur_addr=cp_live_cur_addr,
        )
        tvb.label("tuck_bfs_v3")
        # tuck_bfs's own contract (module docstring): PILL_A/PILL_B must hold the two pill
        # colours before calling. Unused downstream in THIS integration (tuck_cell_prep
        # re-derives colour from S_CA/S_CB directly, not from tuck_bfs's OUT_CA/OUT_CB --
        # CANDLIST carries no colour field at all), but set correctly anyway so tuck_bfs
        # never reads uninitialised zero page and its documented contract holds regardless
        # of which downstream consumer is wired to it.
        tvb.ins16("LDA_abs", S_CA); tvb.ins("STA_zp", TB.PILL_A)
        tvb.ins16("LDA_abs", S_CB); tvb.ins("STA_zp", TB.PILL_B)
        tvb.jsr("tuck_bfs")
        tvb.jsr(translate_entry)
        tvb.jsr("tuck_root_extension")
        tvb.ins("RTS")
        tuck_bfs_code = tvb.assemble()
        tuck_bfs_ep = TUCK_BFS_ROM + tvb.labels["tuck_bfs_v3"]
        assert TUCK_BFS_ROM + len(tuck_bfs_code) <= 0xA800, \
            f"tuck_bfs overruns the free ROM window before $A800 ({len(tuck_bfs_code)}B)"
        assert 0x8000 + len(code) <= TUCK_BFS_ROM, "search overruns tuck_bfs"

    stub = Asm6502(STUB)
    stub.ins("SEI"); stub.ins("CLD")
    stub.ins("LDX_imm", 0xFF); stub.ins("TXS")
    stub.ins("LDX_imm", 15)                     # PILLA[8]+PILLB[8] ROM -> $09C0 RAM
    stub.label("cp2")
    stub.ins16("LDA_absX", PILL_ROM); stub.ins16("STA_absX", PILLA)
    stub.ins("DEX"); stub.br("BPL", "cp2")
    if EMIT_TUCK or EMIT_TUCK_V3 or EMIT_TUCK_BFS:
        # descriptor defaults BEFORE the search: wiring $5087/$5088 in CoproDrMario turned
        # them from a scratch alias into real copro RAM, so an uninitialised pair would make
        # a DRTUCK=1 driver steer to a random column. Gated so the SHIPPED firmware stays
        # byte-identical -- an unconditional write here moved c87e60a1 to 44a7b37e.
        stub.ins("LDA_imm", 0xFF)
        stub.ins16("STA_abs", TUCK_COL); stub.ins16("STA_abs", TUCK_ROW)
    stub.jsr(search_ep)
    if EMIT_TUCK:
        stub.jsr(TUCK_ROM)
    if EMIT_TUCK_V3:
        stub.jsr(tuck_v3_ep)
    if EMIT_TUCK_BFS:
        stub.jsr(tuck_bfs_ep)
    stub.ins("LDA_zp", D_BC); stub.ins16("STA_abs", S_BEST_C)
    stub.ins("LDA_zp", D_BO); stub.ins16("STA_abs", S_BEST_O)
    stub.ins("LDA_imm", 1); stub.ins16("STA_abs", DONE)
    stub.label("spin"); stub.jmp("spin")
    stub_code = stub.assemble()
    assert STUB + len(stub_code) <= 0xC000, f"stub overruns ROM ({len(stub_code)}B)"

    img = bytearray(0x10000)
    img[0x8000:0x8000 + len(code)] = code
    if tuck_code:
        img[TUCK_ROM:TUCK_ROM + len(tuck_code)] = tuck_code
    if tuck_v3_code:
        img[TUCK_V3_ROM:TUCK_V3_ROM + len(tuck_v3_code)] = tuck_v3_code
    if tuck_bfs_code:
        img[TUCK_BFS_ROM:TUCK_BFS_ROM + len(tuck_bfs_code)] = tuck_bfs_code
    for i in range(17):
        img[SQ_ROM + i] = (i * i) & 0xFF
        img[SQ_ROM + 17 + i] = (i * i) >> 8
    for i in range(len(THIRD)):
        img[PILL_ROM + i] = THIRD[i][0]
        img[PILL_ROM + 8 + i] = THIRD[i][1]
    img[STUB:STUB + len(stub_code)] = stub_code
    for i, b in enumerate(board):
        img[0x0500 + i] = b & 0xFF
    img[S_CA] = cA; img[S_CB] = cB; img[S_NA] = nA; img[S_NB] = nB
    img[DONE] = 0
    img[0xFFFC] = STUB & 0xFF; img[0xFFFD] = (STUB >> 8) & 0xFF   # py65 only; mapper hardcodes
    return img, len(code), len(stub_code)


def main():
    sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")
    sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/tmp")
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes

    img, clen, slen = build_image([EMPTY] * 128, 0, 0, 0, 0)
    for i in range(128):
        img[0x0500 + i] = EMPTY
    rom = img[0x8000:0xC000]
    # main() builds + py65-validates the BASE search firmware (the cell-exact reference for the search
    # LOGIC vs decide_d3). The SHIPPED firmware is the co-sim-validated DELTA build (CMD-6/7 engine),
    # md5 c87e60a1, produced by `dbg_build.py all 0` and committed as copro_rom.hex. py65 cannot run
    # the RTL delta engine (attach_engine_emu has no CMD-6/7), so we MUST NOT overwrite the ship hex
    # here -- write a clearly-named reference and report the ship hex instead. See FIRMWARE.md.
    import hashlib
    base_txt = "\n".join("%02x" % x for x in rom) + "\n"
    with open(os.path.join(HERE, "copro_rom.base.hex"), "w") as f:
        f.write(base_txt)
    if not D3.__file__.startswith(ROOT):
        print(f"  WARN: built with the main-repo SHADOW emitter ({D3.__file__}) -- that is the "
              f"PRE-DELTA base emitter; the shipped delta build only comes from dbg_build.py.")
    print(f"copro_rom.base.hex written (py65 BASE reference, NOT the ship hex): d3 search={clen}B "
          f"stub={slen}B rom={len(rom)}B (topk1={D3.TOPK1} topk2=8 pills={D3.NPILLS} "
          f"resolve={D3.RESOLVE_LBL} WIN={D3.WIN})")
    ship = os.path.join(HERE, "copro_rom.hex")
    if os.path.exists(ship):
        smd5 = hashlib.md5(open(ship, "rb").read()).hexdigest()
        rel = "DELTA (shipped)" if smd5 != hashlib.md5(base_txt.encode()).hexdigest() else \
              "== this BASE reference (delta not built in this tree; run dbg_build.py all 0)"
        print(f"  ship firmware copro_rom.hex md5={smd5[:8]} [{rel}]; reproduce/validate the shipped "
              f"delta via 'dbg_build.py all 0' + './run_gate.sh' (FIRMWARE.md).")

    _code, labels = D3.build()
    search_ep = 0x8000 + labels["search"]
    rng = random.Random(2026)

    def problem():
        fb = make_fewlegal(rng, FaithfulBoard)
        ca, cb = rng.randint(1, 3), rng.randint(1, 3)
        na, nb_ = rng.randint(1, 3), rng.randint(1, 3)
        return list(faithful_to_nes(fb)), ca - 1, cb - 1, na - 1, nb_ - 1

    def _expect(b, cA, cB, nA, nB):
        """The golden's answer, with #123's publish-time canonicalisation applied.

        DRDBLCANON rewrites only the WINNING orient, so the gate applies the same
        rewrite to the golden's winner rather than re-deriving the search. With the
        flag off `canon_o4` is the identity and this is the pre-#123 comparison
        unchanged. `canon_o4` comes from D3 (this tree, force-registered) because
        `nes_d3_golden` resolves to a sibling worktree -- see the import guard above.
        """
        exp = G3.decide_d3(b, cA, cB, nA, nB, topk1=D3.TOPK1, topk2=8, third=THIRD)
        if D3.DBLCANON and exp is not None:
            exp = (exp[0], D3.canon_o4(exp[1], cA, cB))
        return exp

    fails = 0

    # ---- (1) direct search-entry call vs decide_d3 ----
    b, cA, cB, nA, nB = problem()
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    for i in range(16):                          # direct call skips the stub: load pill table
        cpu.mem[PILLA + i] = img[PILL_ROM + i]
    cpu.set_board(b)
    D3.attach_engine_emu(cpu)
    cpu.mem[S_CA] = cA; cpu.mem[S_CB] = cB; cpu.mem[S_NA] = nA; cpu.mem[S_NB] = nB
    cpu.call(search_ep, max_steps=MAX_STEPS)
    got = (cpu.mem[D_BC], cpu.mem[D_BO]) if cpu.mem[D_BO] != 0xFF else None
    exp = _expect(b, cA, cB, nA, nB)
    ok = got == exp
    fails += 0 if ok else 1
    print(f"  direct-call: got={got} exp={exp}  {'OK' if ok else 'FAIL'}")

    # ---- (2) hardware path: reset @$BF80 -> stub copies tables -> search -> DONE ----
    b, cA, cB, nA, nB = problem()
    cpu2 = Cpu()
    for a, v in enumerate(img):
        cpu2.mem[a] = v
    cpu2.set_board(b)
    D3.attach_engine_emu(cpu2)
    cpu2.mem[S_CA] = cA; cpu2.mem[S_CB] = cB; cpu2.mem[S_NA] = nA; cpu2.mem[S_NB] = nB
    cpu2.mem[DONE] = 0
    m = cpu2.mpu
    m.pc = STUB; m.sp = 0xFF
    steps = 0; reached = False
    while steps < MAX_STEPS:
        m.step(); steps += 1
        if cpu2.mem[DONE] == 1:
            reached = True; break
    got2 = (cpu2.mem[S_BEST_C], cpu2.mem[S_BEST_O])
    exp2 = _expect(b, cA, cB, nA, nB)
    tables_ok = all(cpu2.mem[PILLA + i] == img[PILL_ROM + i] for i in range(16))
    ok2 = reached and tables_ok and exp2 is not None and got2 == exp2
    fails += 0 if ok2 else 1
    est = steps * 3 / 85_900_000
    print(f"  stub-flow: DONE={reached} tables={tables_ok} got={got2} exp={exp2} "
          f"steps={steps/1e6:.0f}M (~{est:.1f}s @85.9MHz)  {'OK' if ok2 else 'FAIL'}")

    print(f"build_copro_d3 validation: {'PASS' if not fails else 'FAIL'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
