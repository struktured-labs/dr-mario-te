#!/usr/bin/env python3
"""Static enumeration of every LeafEval / engine-argument register that SURVIVES the copro GO reset (RTL NES_MiSTer
claude/dist-leaf 3b164c7, DIST60 defines), by when it is written relative to when it is read. Checked for COVERAGE
against gen_poison.py's table (the RTL's own `reg` list intersected with the Verilator build): every surviving register
must be classified exactly once, or this script fails.

  LIVE-IN   read before it is written by a command the search issues -> its stale value reaches a result
  DETOUR    read only on the path a nonzero `dphase` opens INSIDE a LEAF/NODE/BASE walk (S_VSPAN_D -> S_DRVFIN ->
            S_DADV -> S_DSETH/S_DSETV -> S_DUNPL/S_DBUR -> S_DCOMB -> S_DONE): dead once dphase == 0
  PIPE      loaded on EVERY clock (no enable): the stale value is gone 1-2 clocks after the reset release
  BOARD     CUR board planes: rewritten whole (128 cells + 128 links) by the search's first CMD 2 (slot 1 -> CUR)
  SLOT      snapshot RAM: slot 1 rewritten by the 128-byte window upload every search; slots 2/3 by a CMD 3 before every
            CMD 2 that reads them; slot 0 never read (FIXSLOT)
  BASEL     CMD 6 latches: written by every BASE before any CMD 7 of the same pass reads them
  RESULT    result registers: the firmware reads them only after the command that writes them
  ARG       engine argument / select registers (CoproDrMario): stored by the firmware before every use
  SCRATCH   initialised at its command's entry, or written before it is read on every path of that command
  DEAD      written, never read
Usage: enumerate_regs.py POISON.inc"""
import re
import sys

C = {}


def put(cat, names, where):
    for n in names.split():
        assert n not in C, f"{n} classified twice"
        C[n] = (cat, where)


put("LIVE-IN", "dphase",
    "read by S_VSPAN_D (LeafEval.sv:1045) on EVERY per-virus walk of CMD 1 / 4 / 6; written only by CMD 7 entry (:624), "
    "S_DBUR (:1261) and S_DADV (:1297). A completed search leaves 0; a GO mid CMD 7 leaves 1 or 2")
put("PIPE", "bl_rq vn_hit sq_h_in sq_v_in h_waddr h_wdata h_wlnk h_wslot dw_col dw_vir dw_v dw_r dw_c dt_fin "
    "slotram.q_a slotram.q_b lev_q", "unconditional nonblocking load every clk_cpu edge")
put("BOARD", "bcell blink", "CMD 2 S_CP_R: all 128 cells (+ the link funnel's S_CP_R arm); the flush CMD 7 only reads "
    "column 7's occupancy for its own <= 17-clock walk")
put("SLOT", "slotram.mem", "slot 1: 128 window stores (cell + link) per search; slots 2/3: CMD 3 (search :749, :1002; "
    "tuck_slot0_inject dest 2) before every CMD 2 from them")
put("BASEL", "base_maxh base_holes base_toprisk base_spawn base_setup base_pol base_buried base_matched base_rdy "
    "base_vrdy base_anyvir colh b_row b_colv b_top b_tvir b_tcol",
    "CMD 6: colh zeroed at entry + walk, base_* at S_DONE, b_* at dt_fin && base_mode; every pass issues its CMD 6 "
    "before its CMD 7s (also read by the DETOUR's S_DCOMB)")
put("RESULT", "sco win legal rv_cells rv_vir imm chain strand", "S_DONE/S_DONE2 (sco, win), NODE/DELTA entry + resolve "
    "(legal, rv_*, imm, chain), CMD 8 (strand)")
put("ARG", "lev_wslot lev_a_o4 lev_a_sl lev_a_ca lev_a_cb lev_a_col lev_a_fix lev_a_chw",
    "stores before use: wslot around the upload, a_sl before each CMD 2/3, o4/col/ca/cb before each CMD 4/7 (the CMD 4 "
    "after a CMD 7 fallback reuses that CMD 7's), fix/chw at search entry")
put("DETOUR", "od_bur nd_bur od_rdy nd_rdy od_vrdy nd_vrdy od_set nd_set dd_matched dd_pol dd_holes dsoff dscnt dstep "
    "dcol drow dbur_new dcolstep dlmask dws dwhi dwrow dwsecond pca pcb",
    "CMD 7 scratch (entry zeroes od_/nd_/dd_; S_DNEW/S_DPOL/S_DBUR/S_DADV set the cursors) -- and read by the stale "
    "dphase detour (S_DUNPL even WRITES bcell at stale off_a/off_b)")
put("SCRATCH", "cmd_l sr_addr cpw_p", "CMD 2/3 entry / S_COPY")
put("SCRATCH", "node_leaf fwp fo1 off_a off_b markb anyclear chain_bonus fullscan",
    "CMD 4 / 7 entry, S_FO1/S_FO2 (off_a/off_b also on the DETOUR)")
put("SCRATCH", "li soff sstep scnt srun smcol srstart fli", "S_PLACE / S_FPREP / S_EOL (srstart set when a run starts; "
    "li also on the DETOUR)")
put("SCRATCH", "fwp2 bl_ra ap_m ap_vir ap_lk ap_i ap_unl ap_pixr", "S_EOL / S_APPLY / S_APPLY_P")
put("SCRATCH", "gr gc gmoved gk1 g_do g_has ga_isrep ga_occ ga_vir ga_blk0 g_k0 g_k1 g_cell g_lnk",
    "S_APPLY2 end / S_GRAV / S_GRAV_D / S_GRAV_M")
put("SCRATCH", "wc wr_ maxh holes toprisk spawn setup pollution buried matched60 rdy_ext vrdy anyvir seen fillcnt curcol "
    "curlen vseen", "CMD 1 / 6 entry, S_RESDONE (node leaf)")
put("SCRATCH", "vo p run_h run_v span_lo span_hi vspan_lo vspan_hi", "end of S_COLWALK / S_VNEXT / the run states")
put("SCRATCH", "maxh_p holes_p toprisk_p spawn_p setup_p pollution_p buried_p rdy_ext_p vrdy_p matched60_p",
    "S_DONE before S_DONE2")
put("SCRATCH", "str_i rs_c rs_u rs_d rs_l rs_r rs_p", "CMD 8 entry / S_STR_R")
put("SCRATCH", "dt_row dt_colv dt_top dt_tvir dt_tcol dq dh_v dh_i dv_v dv_i dsw dbest dt_pen",
    "DRDIST D-FSM: every latch rewritten by the full walk's cell pipeline (or copied from b_* at S_DNEW); dq / dt_pen "
    "restarted at dt_fin / S_DNEW (~20-clock D-FSM), final before S_DONE reads dt_pen (Verilator witness dt_late)")
put("DEAD", "fo2 daff affbit", "never read")

RESET = {"st": "rst arm (:575)", "done": "rst arm", "sl_cpw": "rst arm", "base_mode": "rst arm (:576)",
         "delta_mode": "rst arm", "dv_fallback": "rst arm", "h_wr": "h_wr <= rst ? 0 : wr",
         "lev_a_tgt": "CoproDrMario: if (cpu_rst) lev_a_tgt <= 0"}


def main():
    inc = open(sys.argv[1]).read()
    names = re.search(r"PREG_NAME\[NPREG\] = \{(.*?)\};", inc).group(1)
    table = [x.strip().strip('"') for x in names.split(",")]
    missing = [n for n in table if n not in C]
    extra = [n for n in C if n not in table]
    if missing or extra:
        raise SystemExit(f"COVERAGE FAIL: unclassified {missing}, classified but not in the build {extra}")
    from collections import Counter
    cnt = Counter(v[0] for v in C.values())
    print(f"registers surviving the GO reset: {len(table)} (LeafEval {len(table) - 9}, CoproDrMario engine args 9); "
          f"cleared by the reset (not counted): {', '.join(RESET)}")
    print("by class: " + ", ".join(f"{k} {cnt[k]}" for k in ("LIVE-IN", "DETOUR", "PIPE", "BOARD", "SLOT", "BASEL",
                                                             "RESULT", "ARG", "SCRATCH", "DEAD")))
    for cat in ("LIVE-IN", "DETOUR", "PIPE", "BOARD", "SLOT", "BASEL", "RESULT", "ARG", "SCRATCH", "DEAD"):
        groups = {}
        for n in table:
            if C[n][0] == cat:
                groups.setdefault(C[n][1], []).append(n)
        for where, ns in groups.items():
            print(f"  {cat:8s} {' '.join(ns)}\n           -> {where}")
    print("COVERAGE PASS: every surviving register classified exactly once")


if __name__ == "__main__":
    main()
