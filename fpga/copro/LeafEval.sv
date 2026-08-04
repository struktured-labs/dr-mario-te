// Dr. Mario depth-3 LEAF EVAL accelerator. Computes the full endgame leaf
// (shape + spawn + setup + buried + readiness_ext + vrdy + pollution + combine)
// over a 128-bcell board in ~1.5-4k clocks -- replaces ~50k cycles of 6502 walks.
//
// Cell encoding (written by the host/copro): 0 = empty, else {vir, color[1:0]}
// with color 1..3 (NES low nibble + 1). Interface:
//   write board[i]  : wr=1, waddr=i (0..127), wdata[2:0], wlnk[2:0]
//   start           : pulse start=1 (loads nothing; board regs already written)
//   done            : high when finished; sco[15:0] (signed) & win valid
//
// LINK PLANE (`blink`, this revision).  The NES playfield byte is high-nibble = link
// direction, low-nibble = colour; the wrapper used to decode only the $D virus test and
// discard the link.  `blink` carries it so gravity drops LINKED BODIES -- a capsule half
// falls with its partner until that partner is cleared -- instead of dropping every cell
// independently.  Compact per-cell gravity over-predicts cascade viruses 3.2x, which is
// what made a cascade reward unmeasurable.
//
// The link plane is a SEPARATE 3-bit array rather than a widening of `bcell`, because NO
// EVAL TERM READS LINKS: every walk below (colwalk, per-virus run/span, pollution, setup,
// and the whole CMD6/7 delta engine) reads only colour, occupancy and virus-ness through
// col_of/occ_of/vir_of.  Holding bcell at 3 bits leaves all of those 128:1 muxes
// byte-identical, so the link plane costs muxes only where links are actually read:
// S_APPLY (partner un-linking) and the gravity sweep.
//
// Link codes match the offline reference kernel (cascade_link_x.py):
//   0 NONE   1 UP   2 DOWN   3 LEFT   4 RIGHT   -- "which way the partner lies".
//
// GRAVITY ORDER.  The reference enumerates bodies row-major then STABLE-SORTS them
// lowest-first before dropping each one row, repeating to fixpoint.  A 128-entry stable
// sort is not affordable here, and it is also not necessary: body gravity is confluent
// (bodies only ever move DOWN), so any drop order reaches the same settled board.
// MEASURED, not assumed -- a plain bottom-up sweep matched the sorted reference on the
// colour, virus AND link planes plus cells/viruses/chain over 96,540 real placements
// (L11 6 games + L17 8 games, cap-1 and fixpoint):
// dr_mario_rl/tmp/rtl_chain/gravity_order_test.py.
// Bit-exact contract (validated vs the python goldens in tb_leafeval):
//   sco = 5000 - 12*maxh - 20*holes - 90*toprisk - 150*spawn + 32*setup
//         - 48*buried + 8*rdy_ext + 8*vrdy - 6*pollution + matched60   (16-bit wrap; buried color-aware + nearest-2 cap, R6 matched-cover pre-scaled @48; r47b5: vrdy 24->12; eval-winner (coef-opt2): setup 60->32, buried 30->48, rdy_ext 12->8, vrdy 12->8, matched-cover 60->48 -- held-out -12.5 / TEST -11.0 paired-median pills vs vrdy12, RTL cost 21 vs 30 bits)
//   win = (no virus on board)
module LeafEval(
	input             clk,
	input             rst,
	input             wr,          // board-window write into slot `wslot`
	input       [6:0] waddr,
	input       [2:0] wdata,
	input       [2:0] wlnk,        // link code for the written cell (0 = none)
	input       [1:0] wslot,       // 0=CUR 1=LIVE 2=WORK1 3=WORK2
	input             start,       // legacy: LEAF on CUR
	input       [3:0] cmd,         // 1=LEAF 2=CUR<-slot(a_sl) 3=slot(a_sl)<-CUR
	                               // 4=NODE(land+place+resolve+leaf) 5=LAND_RESOLVE (no leaf)
	input             cmd_go,
	input       [1:0] a_sl,        // slot argument for copies
	input       [1:0] a_o4,        // orient4 (0..3)
	input       [2:0] a_col,       // column 0..7
	input       [1:0] a_ca,        // colors, ENGINE encoding 1..3 handled by wrapper (pass nibble+1)
	input       [1:0] a_cb,
	input             a_fix,       // 0 = stop after one clear round (lnk1 arm)
	                               // 1 = resolve to fixpoint, counting rounds (chain arm)
	input       [7:0] a_chw,       // DRCHAIN dose / 4. imm gains a_chw*4*(chain-1) when
	                               // chain > 1, mirroring cascade_chain_x._imm_chain.
	                               // 0 reproduces the no-reward arms EXACTLY (the term
	                               // vanishes), which is what makes one bitstream serve
	                               // lnk1, fixpoint+0 and fixpoint+dose. Scaling by 4 puts
	                               // the measured doses (60/180/360, knee above 360) in a
	                               // single patchable byte at 4-point granularity.
	output reg        done,
	output reg [15:0] sco,
	output reg        win,
	output reg        legal,
	output reg  [6:0] rv_cells,    // widened for fixpoint: a cascade can clear > 63 cells
	output reg  [5:0] rv_vir,      // widened for fixpoint: a cascade can clear > 15 viruses
	output reg [15:0] imm,
	output reg  [3:0] chain,       // clear ROUNDS performed (1 = plain clear, >1 = cascade)
	output reg        dv_fallback,  // CMD 7 (DELTA): placement clears -> host must re-issue as full NODE
	output reg  [6:0] strand       // CMD 8 (#47): stranded-half count of the current bcell board
);

// CUR as registers (the eval/scan walks index it combinationally); the 3 snapshot
// slots in ONE inferred BRAM (sequential access only: window writes + 130-cyc copies)
// -- 3 register files didn't fit the device (fitter: 4246/4191 LABs).
reg [2:0] bcell [0:127] /*verilator public_flat_rd*/;
// link plane, same geometry. Only gravity and the clear-apply sweep read it.
reg [2:0] blink [0:127] /*verilator public_flat_rd*/;
// ONE read address, ONE read mux, for the WHOLE link plane.
//
// Four independent `blink[<expr>]` reads meant four independent 128:1 mux trees, and that
// -- not the write decoders -- is where the area went. MEASURED: merging the link into a
// 6-bit bcell, which shares the write decoders, changed the standalone cost by exactly 0
// ALMs (8,674 either way). Sharing the READ port is the lever that actually moves.
//
// Every consumer already captures the value into a register on the next cycle (see the
// timing split below), so each one simply drives bl_ra one state early and reads bl_rq.
// That is also exactly the shape a BRAM wants, if the plane ever has to move into one.
reg  [6:0] bl_ra;
reg  [2:0] bl_rq;
// SYNCHRONOUS read + ONE write port == the shape Quartus infers as a RAM, which is the
// whole point: it moves 128x3 bits out of ALMs and takes the 128-way read mux and write
// decode with them.
// WRITE-FORWARD BYPASS, and exactly how far it is load-bearing -- MEASURED, because an
// untested guard is false assurance.
// The hazard is real and frequent: S_APPLY_U un-links a SURVIVING partner, and that
// partner can be the cell the sweep reads next (partner at fwp2+1 under LK_RIGHT). The
// collision condition fires **37,284 times** across the 53,568-placement corpus.
// But **0 of those are ever latched by a consumer**: every consumed read is latched at the
// end of a BUBBLE state (S_APPLY_W / S_GRAV_W / S_GRAV2_W / S_CP_W*), and no bubble state
// drives bl_we. The read-latency bubbles that the RAM needed already serialise the hazard
// away. Proven three ways: deleting the bypass passes the corpus, POISONING it with an
// illegal link code passes the corpus, and the counters below report 37,284 / 0.
// It is kept as defence-in-depth -- delete a bubble state and it becomes load-bearing
// immediately -- and the assertion below is what tells you that has happened.
always @(posedge clk)
	bl_rq <= (bl_we && bl_wa == bl_ra) ? bl_wd : blink[bl_ra];
`ifdef VERILATOR
// Simulation-only invariant witness: costs nothing in silicon, and turns the bypass from
// an untested guard into a documented one. byp_used must stay 0; if it ever moves, a
// bubble state was removed and the bypass is now the only thing keeping the read correct.
reg [31:0] byp_fire /*verilator public_flat_rd*/;
reg [31:0] byp_used /*verilator public_flat_rd*/;
always @(posedge clk) begin
	if (rst) begin byp_fire <= 0; byp_used <= 0; end
	else if (bl_we && bl_wa == bl_ra) begin
		byp_fire <= byp_fire + 1;
		if (st == S_APPLY_W || st == S_GRAV_W || st == S_GRAV2_W
		    || st == S_CP_W || st == S_CP_W_P) byp_used <= byp_used + 1;
	end
end
`endif

// ---- link-plane WRITE PORTS -------------------------------------------------------
// Ten separate `blink[<expr>] <=` statements give every one of the 128 registers a
// ten-way enable and a ten-way data mux. Funnelling the FSM's writes through TWO explicit
// ports leaves each register a 2-way enable and a 2:1 mux, with one shared address select
// in front -- the same trick as bl_ra, applied to the write side. No state writes the same
// address twice, so collapsing them loses no ordering.
// (The host-window write keeps its own statement: it fires while the FSM is idle, and
// leaving it separate preserves the original last-write-wins ordering for free.)
wire       ap_phas = (ap_lk == LK_UP    && ap_i[6:3] != 4'd0)
                  || (ap_lk == LK_DOWN  && ap_i[6:3] != 4'd15)
                  || (ap_lk == LK_LEFT  && ap_i[2:0] != 3'd0)
                  || (ap_lk == LK_RIGHT && ap_i[2:0] != 3'd7);
wire [6:0] ap_pix  = (ap_lk == LK_UP)   ? ap_i - 7'd8
                   : (ap_lk == LK_DOWN) ? ap_i + 7'd8
                   : (ap_lk == LK_LEFT) ? ap_i - 7'd1
                   :                      ap_i + 7'd1;
reg  [6:0] bl_wa;
reg  [2:0] bl_wd;
reg        bl_we;
always @* begin
	bl_we = 1'b0; bl_wa = 7'd0; bl_wd = LK_NONE;
	// The host window write only ever fires while the FSM is idle, so priority between
	// the two is moot; giving it first refusal keeps the arms below mutually exclusive.
	if (wr && wslot == 2'd0) begin
		bl_we = 1'b1; bl_wa = waddr; bl_wd = wlnk;
	end else case (st)
	S_CP_R:     begin bl_we = 1'b1; bl_wa = fwp2;  bl_wd = sl_qb[5:3]; end
	S_PLACE:    begin bl_we = 1'b1; bl_wa = off_a; bl_wd = a_o4[1] ? LK_RIGHT : LK_DOWN; end
	S_PLACE_B:  begin bl_we = 1'b1; bl_wa = off_b; bl_wd = a_o4[1] ? LK_LEFT  : LK_UP;  end
	S_APPLY_U:  if (ap_m && ap_unl) begin bl_we = 1'b1; bl_wa = ap_pixr; bl_wd = LK_NONE; end
	S_APPLY2:   if (ap_m)           begin bl_we = 1'b1; bl_wa = ap_i;    bl_wd = LK_NONE; end
	S_GRAV_MA:  if (g_do) begin bl_we = 1'b1; bl_wa = g_k0;        bl_wd = LK_NONE; end
	S_GRAV_M:   if (g_do) begin bl_we = 1'b1; bl_wa = g_k0 + 7'd8; bl_wd = g_lnk;   end
	S_GRAV2MA:  begin bl_we = 1'b1; bl_wa = gk1;         bl_wd = LK_NONE; end
	S_GRAV2M:   begin bl_we = 1'b1; bl_wa = gk1 + 7'd8;  bl_wd = g_lnk;   end
	S_DUNPL:    begin bl_we = 1'b1; bl_wa = off_a; bl_wd = LK_NONE; end
	S_DUNPL_B:  begin bl_we = 1'b1; bl_wa = off_b; bl_wd = LK_NONE; end
	default: ;
	endcase
end
// snapshot slots in an EXPLICIT dpram (behavioral arrays fail BRAM inference in
// Quartus Std -> got synthesized as 1.5k registers and blew the LAB budget).
// port A = writes (host window / copy-out walk), port B = registered reads (copy-in).
// The slot words were already 8 bits wide with only 3 used, so the link plane rides
// along in bits [5:3] for FREE -- no extra BRAM, no second RAM, no wider address.
reg  [8:0] sr_addr;
reg  [6:0] cpw_p;
wire [8:0] sr_waddr = {wslot, waddr};
wire       sl_we    = (wr && wslot != 2'd0) || sl_cpw;
reg        sl_cpw;                    // S_CP_W write strobe
wire [8:0] sl_wa    = sl_cpw ? {a_sl, cpw_p} : sr_waddr;
wire [7:0] sl_wd    = sl_cpw ? {2'd0, bl_rq, bcell[cpw_p]} : {2'd0, wlnk, wdata};
wire [7:0] sl_qb;
wire [2:0] slotq = sl_qb[2:0];
dpram #(.widthad_a(9), .width_a(8)) slotram (
	.clock_a  (clk),
	.address_a(sl_wa),
	.data_a   (sl_wd),
	.wren_a   (sl_we),
	.q_a      (),
	.clock_b  (clk),
	.address_b(sr_addr),
	.data_b   (8'd0),
	.wren_b   (1'b0),
	.q_b      (sl_qb)
);

wire [1:0] col_of  [0:127];
wire       occ_of  [0:127];
wire       vir_of  [0:127];
genvar gi;
generate for (gi = 0; gi < 128; gi = gi + 1) begin : g
	assign col_of[gi] = bcell[gi][1:0];
	assign occ_of[gi] = bcell[gi][1:0] != 2'd0;
	assign vir_of[gi] = bcell[gi][2] && bcell[gi][1:0] != 2'd0;
end endgenerate

// squares 0..16
function [8:0] sq(input [4:0] n);
	sq = n * n;
endfunction

// ------------------------------------------------------------------ FSM
localparam S_IDLE=0, S_COLWALK=1, S_VNEXT=2, S_HRUN_L=3, S_HSPAN_L=4, S_HRUN_R=5,
           S_HSPAN_R=6, S_VRUN_U=7, S_VSPAN_U=8, S_VRUN_D=9, S_VSPAN_D=10,
           S_POLROW=11, S_POLCOL=12, S_VFIN=13, S_SETUP_H=14, S_SETUP_V=15, S_DONE=16,
           S_COPY=17, S_FO1=18, S_FO2=19, S_PLACE=20, S_SCAN=21, S_EOL=22,
           S_APPLY=23, S_GRAV=24, S_RESDONE=25, S_CP_R=26, S_CP_W=27, S_CP_P=28, S_DONE2=29;
// incremental-delta states (CMD 6 = BASE latch, CMD 7 = DELTA child)
localparam S_DPOL=31, S_DNEW=32, S_DBUR=33, S_DADV=34, S_DRV=35,
           S_DRVFIN=36, S_DSETH=37, S_DUNPL=38, S_DSETV=39, S_DCOMB=40;
// body gravity + fixpoint re-scan. S_GRAV keeps its number: it is now the bottom-up
// body sweep instead of the old per-column compaction.
localparam S_GRAV2=41,          // second cell of a two-cell body: READ
           S_FPREP=42,          // clear the mark plane, arm the 24-line full scan
// TIMING SPLIT. `blink` is a 128-entry register file, so a blink READ is a 128:1 mux and a
// blink WRITE is a 128-way decode. Doing both in one cycle put mux -> decision logic ->
// decode on a single path: MEASURED 14.16 ns against an 11.64 ns requirement on the copro
// clock (worst setup paths were literally blink[92] -> blink[88]), turning the baseline's
// +0.118 ns margin into -3.241. Each sweep is therefore split into a READ/DECIDE cycle
// that ends at a register and a WRITE cycle whose operands are all registers. Costs 2x
// cycles in the apply and gravity sweeps -- both clearing-path only.
           S_APPLY_P=46,        // apply sweep: RESOLVE the partner (markb lookup)
           S_GRAV_D=47,         // gravity: DECIDE (the k1-indexed blocker lookup)
// SINGLE-WRITE-PORT serialisation. A RAM has one write port, so the five states that
// wrote two link words now spread them over two cycles. Each extra state does ONLY the
// second write, leaving the original state's branch logic untouched -- the alternative,
// moving branch logic into a new tail state, is where this kind of refactor goes wrong.
           S_APPLY_U=48,        // apply: un-link the surviving partner
           S_GRAV_MA=49,        // gravity: vacate the source cell's link
           S_GRAV2MA=50,        // gravity: vacate the partner's link
           S_PLACE_B=51,        // place: second half's link
           S_DUNPL_B=52,        // delta un-place: second cell's link
// RAM READ LATENCY bubbles. A synchronous read presents its address one cycle and returns
// data the next, so a consumer needs its address set TWO states earlier, not one. Each
// consumer gets an explicit idle cycle rather than duplicating the FSM's address
// arithmetic into a combinational next-address block -- which is exactly where an
// off-by-one would hide.
           S_APPLY_W=53,        // wait for blink[fwp2]
           S_GRAV_W=54,         // wait for blink[cursor]
           S_GRAV2_W=55,        // wait for blink[gk1]
           S_CP_W_P=56,         // prime the copy-out walk
           S_APPLY2=43,         // apply sweep: WRITE
           S_GRAV_M=44,         // gravity: WRITE first cell
           S_GRAV2M=45;         // gravity: WRITE partner cell
// CMD 8 stranded scan (#47): READ/DECIDE split per the blink timing lesson above --
// the 128:1 col_of muxes land in registers in S_STR_R, the compare+count runs on
// registers only in S_STR_D.
localparam S_STR_R=57, S_STR_D=58;
// link codes -- "which way the partner lies" (cascade_link_x.py)
localparam [2:0] LK_NONE=3'd0, LK_UP=3'd1, LK_DOWN=3'd2, LK_LEFT=3'd3, LK_RIGHT=3'd4;
reg [3:0] cmd_l;
reg [5:0] st;
reg       node_leaf;           // CMD_NODE: run the leaf after resolve
// land/resolve working regs
reg [4:0]   fo1, fo2, fwp;     // first-occ results + walk pointer
reg [6:0]   off_a, off_b;      // placed cell offsets
reg [127:0] markb;             // targeted-clear mark bits
// ---- CMD 8 stranded scan (#47) working regs ----
reg [6:0]   str_i;             // cell cursor 0..127
reg [1:0]   rs_c, rs_u, rs_d, rs_l, rs_r;   // registered self + 4 neighbour colours
reg         rs_p;              // self is an occupied NON-virus (pill) cell
reg [1:0]   li;                // scan line index 0..3
reg [7:0]   soff;              // scan offset
reg [3:0]   sstep;             // scan step (1 or 8)
reg [4:0]   scnt;              // cells left in line
reg [4:0]   srun;              // current run length
reg [1:0]   smcol;             // current run color (0 = none)
reg [7:0]   srstart;           // run start offset
reg [6:0]   fwp2;              // apply sweep pointer 0..127
reg         anyclear;
// ---- body-gravity sweep (replaces the old per-cell compaction) ----
reg [3:0]   gr;                // sweep row 14..0 (row 15 can never fall)
reg [2:0]   gc;                // sweep col 0..7
reg         gmoved;            // a body moved this pass -> another pass is due
reg [6:0]   gk1;               // partner cell queued for its own move cycle
// READ/DECIDE -> WRITE pipeline registers (see the S_GRAV_M / S_APPLY2 timing note)
reg         g_do, g_has;       // this body falls / it has a second cell
// Stage-A captures for the fall decision. The chain was blink mux -> k1 -> bcell mux ->
// dofall: TWO 128:1 muxes in series feeding one register, and after the apply sweep was
// fixed it became the worst path on the copro clock (-0.113 ns). Splitting it puts the
// k0-indexed lookups (k0 is cursor-derived, so register-driven) in stage A and the single
// k1-indexed blocker lookup in stage B, one mux deep each.
reg         ga_isrep, ga_occ, ga_vir, ga_blk0;
// DRCHAIN reward as an ACCUMULATOR, not a multiply. The multiplier form put a DSP's
// clock-enable at the end of a bcell-indexed FSM branch (worst path was
// bcell[64] -> Mult7~8|ENA_DFF0, +0.026 ns), and chain depth is small enough that
// w_chain*(chain-1) is just "add w_chain on every round after the first". Costs an adder,
// refunds a DSP, and takes the multiply off the critical path entirely.
// Saturation: chain stops at 15, so the bonus stops with it -- the reward cannot run away
// on a pathological board. Real boards top out at chain 3.
reg [15:0]  chain_bonus;
reg [6:0]   g_k0, g_k1;
reg [2:0]   g_cell, g_lnk;     // the cell being moved, captured before it is cleared
reg         ap_m, ap_vir;      // apply sweep: marked / was a virus
reg [2:0]   ap_lk;
reg [6:0]   ap_i;
// Partner resolved in its OWN stage. `markb[ap_pix]` is a second 128:1 mux, and letting it
// feed the blink write enable in the same cycle left the copro clock at -0.312 ns with
// every failing path reading markb[..] -> blink[..]. Registering the lookup splits that
// into (registers -> pix arith -> markb mux -> register) and (registers -> write decode).
reg         ap_unl;            // partner survives and must be un-linked
reg [6:0]   ap_pixr;           // its index
// ---- full-board re-scan (chain rounds 2+) ----
// Round 1 needs only the 4 lines through the placed cells: a settled parent has no run
// >= 4 anywhere else. After gravity the surviving cells have moved arbitrarily, so
// rounds 2+ must scan all 16 rows and all 8 columns.
reg         fullscan;
reg [4:0]   fli;               // full-scan line: 0..15 = rows, 16..23 = cols

reg  [3:0] wc, wr_;            // column/row walk indices
reg  [4:0] maxh /*verilator public_flat_rd*/;
reg  [7:0] holes /*verilator public_flat_rd*/, toprisk /*verilator public_flat_rd*/, spawn /*verilator public_flat_rd*/, setup /*verilator public_flat_rd*/;
reg [10:0] pollution /*verilator public_flat_rd*/;   // up to 48 viruses x 22 cells = 1056
reg  [9:0] buried /*verilator public_flat_rd*/;   // up to 48 x 15 = 720
reg [12:0] matched60 /*verilator public_flat_rd*/; // R6 matched-cover pre-scaled: +48 per virus w/ same-color cover directly on top (name historical; was +60)
reg [15:0] rdy_ext /*verilator public_flat_rd*/, vrdy /*verilator public_flat_rd*/;
reg        anyvir;
reg        seen;               // column walk: first-occupied seen
reg  [4:0] fillcnt;            // filled-so-far in this column (for buried)
reg  [1:0] curcol;            // R1 color-aware buried: color of the contiguous same-color
reg  [4:0] curlen;            // non-virus cover run ending at the previous cell (0 = none)
reg  [4:0] vseen;             // R7b: viruses seen so far this column (buried charge caps at 2)
// combine-pipeline: registered multiplier inputs (S_DONE stage1) -> combine in S_DONE2
reg  [4:0] maxh_p; reg [7:0] holes_p, toprisk_p, spawn_p, setup_p;
reg [10:0] pollution_p; reg [9:0] buried_p; reg [15:0] rdy_ext_p, vrdy_p; reg [12:0] matched60_p;

// ---- incremental delta engine (CMD 6 = BASE latch, CMD 7 = DELTA child) ----
reg        base_mode;                 // CMD 6: latch base_* instead of driving sco
reg        delta_mode;                // CMD 7 active
reg  [4:0] colh [0:7] /*verilator public_flat_rd*/;  // per-column height (16 - top occ row); 0 = empty
reg  [4:0] base_maxh /*verilator public_flat_rd*/;
reg  [7:0] base_holes /*verilator public_flat_rd*/, base_toprisk, base_spawn, base_setup;
reg [10:0] base_pol;
reg  [9:0] base_buried;
reg [12:0] base_matched;
reg [15:0] base_rdy, base_vrdy;
reg        base_anyvir;
// delta accumulators: new_total = base - old_local + new_local
reg  [9:0] od_bur, nd_bur;
reg [15:0] od_rdy, nd_rdy, od_vrdy, nd_vrdy;
reg  [7:0] od_set, nd_set;
reg [12:0] dd_matched;                // matched60 delta (closed form: +48 per new same-color cover)
reg [10:0] dd_pol;                    // pollution delta (closed form)
reg  [7:0] dd_holes;                  // holes delta (closed form from colh)
reg  [1:0] pca, pcb;                  // placed colors landed at off_a / off_b (post o4-swap)
reg  [6:0] dsoff; reg [4:0] dscnt; reg [3:0] dstep;  // delta row/col scan cursor
reg  [1:0] dphase;                    // rdy/vrdy rescore phase: 1=new(child) 2=old(parent)
reg  [6:0] daff;                      // affected-virus iterator (0..127)
reg [127:0] affbit;                   // affected viruses to rescore for rdy_ext/vrdy
reg  [2:0] dcol; reg [4:0] drow;      // delta mini-colwalk cursor
reg        dbur_new;                  // buried mini-colwalk phase (1=child/new 0=parent/old)
reg  [1:0] dcolstep;                  // which placed column (0 = col_a, 1 = col_b)
reg  [3:0] dlmask;                    // rdy/vrdy rescore: which of the 4 placed lines to scan (dedup)
reg  [3:0] dws, dwhi, dwrow;          // setup-window cursor: start, hi bound, row(H)/col(V)
reg        dwsecond;                  // setup scan: processing the second placed row/col

reg  [6:0] vo;                 // current virus bcell offset
wire [3:0] v_r = vo[6:3];
wire [2:0] v_c = vo[2:0];
wire [1:0] v_col = col_of[vo];

reg  [4:0] run_h, run_v;       // same-color runs through the virus
reg  [4:0] p;                  // walk pointer (row 0..15 or col 0..7 as needed)
reg  [4:0] span_lo, span_hi;   // span bounds (exclusive), horizontal: -1..8 as 5-bit signed-ish
reg  [4:0] vspan_lo, vspan_hi;

wire signed [17:0] rdy_h_sq = (span_hi - span_lo - 1 >= 4) ? sq(run_h) : 9'd0;
// (assigned in-state below; wire above only for readability of the gate)

integer i;

always @(posedge clk) begin
	if (rst) begin
		st <= S_IDLE; done <= 1'b0; sl_cpw <= 1'b0;
		base_mode <= 1'b0; delta_mode <= 1'b0; dv_fallback <= 1'b0;
	end else begin
		if (wr && wslot == 2'd0) begin                    // slot writes go via the dpram port
			bcell[waddr] <= wdata;   // its link goes through the write port below
		end
		if (bl_we) blink[bl_wa] <= bl_wd;      // THE link-plane write port (see funnel above)
		case (st)
		S_IDLE: if (start || cmd_go) begin
			done <= 1'b0;
			if (start || cmd == 4'd1) begin                      // LEAF on CUR
				delta_mode <= 1'b0; base_mode <= 1'b0;           // FIX: a fresh LEAF must not inherit a stale mode
				maxh <= 0; holes <= 0; toprisk <= 0; spawn <= 0; setup <= 0;
				pollution <= 0; buried <= 0; rdy_ext <= 0; vrdy <= 0; anyvir <= 0; matched60 <= 13'd0;
				wc <= 0; wr_ <= 0; seen <= 0; fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
				st <= S_COLWALK;
			end else if (cmd == 4'd2 || cmd == 4'd3) begin       // slot copies
				cmd_l <= cmd; st <= S_COPY;
			end
			else if (cmd == 4'd4) begin                          // NODE: land+place+resolve+leaf
				node_leaf <= 1'b1;
				delta_mode <= 1'b0; base_mode <= 1'b0;           // FIX: a fresh NODE must not inherit a stale mode
				legal <= 1'b0; rv_cells <= 0; rv_vir <= 0; imm <= 0;
				markb <= 128'd0; anyclear <= 1'b0;
				chain <= 4'd0; chain_bonus <= 16'd0; fullscan <= 1'b0;
				fwp <= 0;
				st <= S_FO1;
			end
			else if (cmd == 4'd6) begin                          // BASE: full scan, latch base_* + colh
				base_mode <= 1'b1; node_leaf <= 1'b0; delta_mode <= 1'b0;   // FIX: no stale delta_mode into a BASE scan
				maxh <= 0; holes <= 0; toprisk <= 0; spawn <= 0; setup <= 0;
				pollution <= 0; buried <= 0; rdy_ext <= 0; vrdy <= 0; anyvir <= 0; matched60 <= 13'd0;
				wc <= 0; wr_ <= 0; seen <= 0; fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
				colh[0]<=0; colh[1]<=0; colh[2]<=0; colh[3]<=0; colh[4]<=0; colh[5]<=0; colh[6]<=0; colh[7]<=0;
				st <= S_COLWALK;
			end
			else if (cmd == 4'd7) begin                          // DELTA: land+place, child leaf via base +/- local
				delta_mode <= 1'b1; node_leaf <= 1'b0; dv_fallback <= 1'b0;
				legal <= 1'b0; rv_cells <= 0; rv_vir <= 0; imm <= 0;
				markb <= 128'd0; anyclear <= 1'b0; fwp <= 0;
				chain <= 4'd0; chain_bonus <= 16'd0; fullscan <= 1'b0;
				od_bur <= 0; nd_bur <= 0; od_rdy <= 0; nd_rdy <= 0; od_vrdy <= 0; nd_vrdy <= 0;
				od_set <= 0; nd_set <= 0; dd_matched <= 13'd0; dd_pol <= 0; dd_holes <= 0; affbit <= 128'd0;
				dphase <= 2'd0;
				st <= S_FO1;
			end
			else if (cmd == 4'd8) begin                          // STRANDED count of bcell (#47)
				// Read-only over bcell; deliberately touches NO leaf/delta/base mode
				// state, so it can run between a root NODE/DELTA eval and the next
				// command without perturbing the search flow.
				strand <= 7'd0; str_i <= 7'd0;
				st <= S_STR_R;
			end
		end

		// copy CUR <- slot: pipelined BRAM read (addr set cycle N, data cycle N+1)
		S_COPY: begin
			fwp2 <= 0; cpw_p <= 0; bl_ra <= 7'd0;   // bl_ra tracks cpw_p through the walk
			sr_addr <= {a_sl, 7'd0};
			if (cmd_l == 4'd2) st <= S_CP_P;
			else begin sl_cpw <= 1'b1; st <= S_CP_W_P; end
		end
		S_CP_P: begin                             // prime: cell 0 lands in slotq next cycle
			sr_addr <= sr_addr + 1'b1;
			st <= S_CP_R;
		end
		S_CP_R: begin
			bcell[fwp2] <= slotq;                 // slotq = cell fwp2
			sr_addr <= sr_addr + 1'b1;
			if (fwp2 == 7'd127) begin done <= 1'b1; st <= S_IDLE; end
			else fwp2 <= fwp2 + 1'b1;
		end
		// copy slot <- CUR: drive the dpram write port, 128 cycles
		S_CP_W: begin
			if (cpw_p == 7'd127) begin sl_cpw <= 1'b0; done <= 1'b1; st <= S_IDLE; end
			else begin cpw_p <= cpw_p + 1'b1; bl_ra <= cpw_p + 7'd2; end
		end

		// ---- landing: first_occ walks (col, then col+1 for horizontal) ----
		S_FO1: begin
			if (fwp == 5'd16 || occ_of[{fwp[3:0], a_col}]) begin
				fo1 <= fwp; fwp <= 0;
				if (a_o4[1]) begin                               // horizontal
					if (a_col == 3'd7) begin done <= 1'b1; st <= S_IDLE; end  // illegal (legal=0)
					else st <= S_FO2;
				end else begin                                   // vertical: legal iff fo>=2
					if (fwp >= 5'd2) begin
						off_b <= {fwp[3:0] - 4'd1, a_col};
						off_a <= {fwp[3:0] - 4'd2, a_col};
						legal <= 1'b1; st <= S_PLACE;
					end else begin done <= 1'b1; st <= S_IDLE; end
				end
			end else
				fwp <= fwp + 1'b1;
		end
		S_FO2: begin
			if (fwp == 5'd16 || occ_of[{fwp[3:0], a_col + 3'd1}]) begin : fo2b
				reg [4:0] fom;
				fom = (fo1 < fwp) ? fo1 : fwp;
				if (fom >= 5'd1) begin
					off_a <= {fom[3:0] - 4'd1, a_col};
					off_b <= {fom[3:0] - 4'd1, a_col + 3'd1};
					legal <= 1'b1; st <= S_PLACE;
				end else begin done <= 1'b1; st <= S_IDLE; end
			end else
				fwp <= fwp + 1'b1;
		end
		S_PLACE: begin
			// orient4 odd = color swap (B goes to offa/top/left)
			bcell[off_a] <= {1'b0, a_o4[0] ? a_cb : a_ca};
			bcell[off_b] <= {1'b0, a_o4[0] ? a_ca : a_cb};
			// the two halves are LINKED: they fall as one body until one of them clears.
			// S_FO1/S_FO2 always give off_a = LEFT (horizontal) or TOP (vertical).
			// a_o4[1] selects horizontal, matching the landing walks above.
			pca <= a_o4[0] ? a_cb : a_ca; pcb <= a_o4[0] ? a_ca : a_cb;   // placed colors (delta)
			li <= 0; st <= S_PLACE_B;
			// initialize line 0 (row of off_a)
			soff <= {1'b0, off_a[6:3], 3'd0}; sstep <= 4'd1; scnt <= 5'd8;
			srun <= 0; smcol <= 0;
		end

		// ---- targeted find-clears: 4 lines (rowA, colA, rowB, colB) ----
		// One cell per cycle; a completed run >= 4 marks its cells COMBINATIONALLY
		// (16 conditional bit-sets along the stride) -- no flush sub-state, no re-scan.
		S_SCAN: begin : scan
			reg brk;      // run break at this cell (empty or color change)
			reg [1:0] c_;
			c_  = col_of[soff[6:0]];
			brk = (c_ == 2'd0) || (c_ != smcol);
			if (brk && srun >= 5'd4)
				for (i = 0; i < 16; i = i + 1)
					if (i < srun) markb[srstart[6:0] + i * sstep] <= 1'b1;
			if (c_ == 2'd0) begin
				srun <= 0; smcol <= 0;
			end else if (c_ != smcol) begin
				smcol <= c_; srstart <= soff; srun <= 5'd1;
			end else
				srun <= srun + 1'b1;
			if (scnt == 5'd1)
				st <= S_EOL;
			else begin
				soff <= soff + {4'd0, sstep};
				scnt <= scnt - 1'b1;
			end
		end
		S_EOL: begin
			if (srun >= 5'd4)
				for (i = 0; i < 16; i = i + 1)
					if (i < srun) markb[srstart[6:0] + i * sstep] <= 1'b1;
			srun <= 0; smcol <= 0;
			if (fullscan) begin : feol
				// 24 lines: 0..15 = rows (stride 1, 8 cells), 16..23 = cols (stride 8, 16 cells)
				reg [4:0] nx;
				nx = fli + 5'd1;
				if (fli == 5'd23) begin fwp2 <= 0; bl_ra <= 7'd0; st <= S_APPLY_W; end
				else begin
					fli <= nx;
					if (nx < 5'd16) begin soff <= {nx[3:0], 3'd0}; sstep <= 4'd1; scnt <= 5'd8; end
					else            begin soff <= {5'd0, nx[2:0]}; sstep <= 4'd8; scnt <= 5'd16; end
					st <= S_SCAN;
				end
			end else
			case (li)
				2'd0: begin soff <= {5'd0, off_a[2:0]}; sstep <= 4'd8; scnt <= 5'd16; li <= 2'd1; st <= S_SCAN; end
				2'd1: begin soff <= {1'b0, off_b[6:3], 3'd0}; sstep <= 4'd1; scnt <= 5'd8; li <= 2'd2; st <= S_SCAN; end
				2'd2: begin soff <= {5'd0, off_b[2:0]}; sstep <= 4'd8; scnt <= 5'd16; li <= 2'd3; st <= S_SCAN; end
				default: begin fwp2 <= 0; bl_ra <= 7'd0; st <= S_APPLY_W; end
			endcase
		end

		// apply sweep, stage 1: READ ONLY. The blink read mux ends at a register here so
		// that it never feeds the blink write decode in the same cycle.
		S_APPLY: begin
			ap_m   <= markb[fwp2];
			ap_lk  <= bl_rq;                  // == blink[fwp2]
			ap_vir <= vir_of[fwp2];
			ap_i   <= fwp2;
			st <= S_APPLY_P;
		end
		// apply sweep, stage 2: RESOLVE the partner. One 128:1 mux (markb), ending at a
		// register, so it shares a cycle with nothing else.
		S_APPLY_P: begin
			ap_pixr <= ap_pix;
			ap_unl  <= ap_phas && !markb[ap_pix];
			st <= S_APPLY_U;
		end
		S_APPLY_W:  st <= S_APPLY;   // RAM read latency
		S_GRAV_W:   st <= S_GRAV;    // RAM read latency
		S_GRAV2_W:  st <= S_GRAV2;   // RAM read latency
		S_CP_W_P:   begin bl_ra <= 7'd1; st <= S_CP_W; end   // prime the copy-out read
		S_PLACE_B:  st <= S_SCAN;    // second half's link (write port arm above)
		S_APPLY_U:  st <= S_APPLY2;  // partner un-link  (write port arm above)
		S_GRAV_MA:  st <= S_GRAV_M;  // vacate source    (write port arm above)
		S_GRAV2MA:  st <= S_GRAV2M;  // vacate partner   (write port arm above)
		// apply sweep, stage 4: WRITE, operands all registered.
		// Clearing a cell also BREAKS THE LINK of a surviving partner: that partner
		// becomes a loose single and falls on its own. If both halves are marked no
		// unlink is needed -- they are both about to be blanked.
		S_APPLY2: begin : apl
			if (ap_m) begin
				rv_cells <= rv_cells + 1'b1;
				if (ap_vir) rv_vir <= rv_vir + 1'b1;
				bcell[ap_i] <= 3'd0;      // blink[ap_i] and the partner un-link: write funnel
				anyclear <= 1'b1;
			end
			if (ap_i == 7'd127) begin
				gr <= 4'd14; gc <= 3'd0; gmoved <= 1'b0; bl_ra <= {4'd14, 3'd0};  // arm the sweep
				if (delta_mode) begin
					if (anyclear || ap_m) begin               // clearing placement -> host does full NODE
						dv_fallback <= 1'b1; done <= 1'b1; delta_mode <= 1'b0; st <= S_IDLE;
					end else st <= S_DNEW;                     // non-clearing: child in CUR, run delta scans
				end else if (anyclear || ap_m) begin
					if (chain != 4'd15) begin
						chain <= chain + 1'b1;
						// every round AFTER the first pays w_chain: total = w_chain*(chain-1)
						if (chain >= 4'd1) chain_bonus <= chain_bonus + {6'd0, a_chw, 2'b00};
					end
					st <= S_GRAV_W;
				end else
					st <= S_RESDONE;                           // rescan found nothing: settled
			end else begin
				fwp2 <= fwp2 + 1'b1; bl_ra <= fwp2 + 1'b1;
				st <= S_APPLY_W;
			end
		end

		// ---- BODY gravity: bottom-up sweep, repeated until a pass moves nothing ----
		// The old code compacted each column independently, which drops a capsule half
		// even when its partner is still supported -- that is the 3.2x cascade
		// over-prediction. Here a linked pair falls only if BOTH halves are clear to move.
		//
		// Representative rule (removes the need for any `seen` bitmap): a vertical body is
		// handled at its BOTTOM cell, a horizontal body at its LEFT cell. The sweep runs
		// rows 14->0 and cols 0->7, so a body's partner is always a cell this pass has not
		// reached yet, and nothing is processed twice. A link pointing off-board or at an
		// empty cell is DANGLING and falls as a single, matching the reference kernel.
		S_GRAV: begin : grv
			reg [2:0] lk;
			reg       isrep, haspt, blk, dofall;
			reg [6:0] k0, k1;
			k0 = {gr, gc};
			lk = bl_rq;                       // == blink[k0]: bl_ra tracks the cursor (invariant)
			haspt = 1'b0; k1 = 7'd0; isrep = 1'b1;
			case (lk)
				LK_UP:    if (gr != 4'd0 && occ_of[k0 - 7'd8]) begin haspt = 1'b1; k1 = k0 - 7'd8; end
				LK_RIGHT: if (gc != 3'd7 && occ_of[k0 + 7'd1]) begin haspt = 1'b1; k1 = k0 + 7'd1; end
				LK_DOWN:  if (gr != 4'd15 && occ_of[k0 + 7'd8]) isrep = 1'b0;  // partner below represents us
				LK_LEFT:  if (gc != 3'd0 && occ_of[k0 - 7'd1]) isrep = 1'b0;   // partner to the left does
				default: ;
			endcase
			// blocked if any body cell has an occupied cell beneath that is not body itself.
			// gr <= 14 so k0+8 is on-board; k1's row is <= 14 for every representative case.
			blk = occ_of[k0 + 7'd8];
			if (haspt && occ_of[k1 + 7'd8] && (k1 + 7'd8) != k0) blk = 1'b1;
			// stage A is READ ONLY -- capture the cell, the body shape, and every
			// k0-indexed lookup. `blk` needs a k1-indexed one, so it waits for stage B.
			g_has <= haspt; g_k0 <= k0; g_k1 <= k1;
			g_cell <= bcell[k0]; g_lnk <= lk;
			ga_isrep <= isrep; ga_occ <= occ_of[k0]; ga_vir <= vir_of[k0];
			ga_blk0  <= occ_of[k0 + 7'd8];
			st <= S_GRAV_D;
		end
		// gravity stage B: the one lookup that needed k1, now indexed by a REGISTER.
		// A body falls only if every cell of it has an empty cell beneath that is not the
		// body itself; g_k1 + 8 == g_k0 is the vertical pair resting on its own lower half.
		S_GRAV_D: begin : grvd
			reg blk;
			blk = ga_blk0;
			if (g_has && occ_of[g_k1 + 7'd8] && (g_k1 + 7'd8) != g_k0) blk = 1'b1;
			g_do <= ga_occ && !ga_vir && ga_isrep && !blk;
			st <= S_GRAV_MA;
		end
		// gravity stage 2: move the representative cell down one row, from registers.
		S_GRAV_M: begin
			if (g_do) begin
				bcell[g_k0 + 7'd8] <= g_cell;   // link half handled by the write funnel
				bcell[g_k0]        <= 3'd0;
				gmoved <= 1'b1;
			end
			if (g_do && g_has) begin
				gk1 <= g_k1; bl_ra <= g_k1; st <= S_GRAV2_W;  // partner next: point at its link
			end else begin
				// cursor advance + end-of-pass (mirrored in S_GRAV2M). bl_ra follows the
				// cursor so the next S_GRAV already has its link word waiting.
				// st is assigned FIRST so the terminal arm below can override it -- the
				// other order makes the last nonblocking write win and the sweep never ends.
				st <= S_GRAV_W;
				if (gc == 3'd7) begin
					gc <= 3'd0;
					if (gr == 4'd0) begin
						if (gmoved || g_do) begin
							gr <= 4'd14; gmoved <= 1'b0; bl_ra <= {4'd14, 3'd0};
						end else st <= a_fix ? S_FPREP : S_RESDONE;
					end else begin gr <= gr - 1'b1; bl_ra <= {gr - 4'd1, 3'd0}; end
				end else begin gc <= gc + 1'b1; bl_ra <= {gr, gc + 3'd1}; end
			end
		end
		// second cell of a two-cell body. For a vertical pair gk1 + 8 == the cell S_GRAV_M
		// just vacated, so it must follow that write, not share the cycle. Read then write,
		// same reason as above.
		S_GRAV2: begin
			g_cell <= bcell[gk1]; g_lnk <= bl_rq;   // S_GRAV_M pointed bl_ra at gk1
			st <= S_GRAV2MA;
		end
		S_GRAV2M: begin
			bcell[gk1 + 7'd8] <= g_cell;    // link half handled by the write funnel
			bcell[gk1]        <= 3'd0;
			// cursor advance + end-of-pass (gmoved is already 1 from S_GRAV_M)
			if (gc == 3'd7) begin
				gc <= 3'd0;
				if (gr == 4'd0) begin gr <= 4'd14; gmoved <= 1'b0; bl_ra <= {4'd14, 3'd0}; end
				else begin gr <= gr - 1'b1; bl_ra <= {gr - 4'd1, 3'd0}; end
			end else begin gc <= gc + 1'b1; bl_ra <= {gr, gc + 3'd1}; end
			st <= S_GRAV_W;
		end
		// settled with a_fix set: blank the mark plane and re-scan the WHOLE board for a
		// follow-on clear. Round 1's 4-line targeted scan is not valid here because the
		// survivors have moved.
		S_FPREP: begin
			markb <= 128'd0; anyclear <= 1'b0;
			fullscan <= 1'b1; fli <= 5'd0;
			soff <= 8'd0; sstep <= 4'd1; scnt <= 5'd8;
			srun <= 0; smcol <= 0;
			st <= S_SCAN;
		end

		S_RESDONE: begin
			// chain reward: only a real CASCADE pays, never a plain clear (chain == 1),
			// so the term is gated on chain > 1 exactly as _imm_chain gates on ch > 1.
			imm <= 16'd180 * rv_vir + 16'd10 * rv_cells + chain_bonus;
			if (node_leaf) begin
				maxh <= 0; holes <= 0; toprisk <= 0; spawn <= 0; setup <= 0;
				pollution <= 0; buried <= 0; rdy_ext <= 0; vrdy <= 0; anyvir <= 0; matched60 <= 13'd0;
				wc <= 0; wr_ <= 0; seen <= 0; fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
				st <= S_COLWALK;
			end else begin
				done <= 1'b1; st <= S_IDLE;
			end
		end

		// ---- one bcell per cycle, column-major: shape + buried + toprisk + spawn + anyvir
		S_COLWALK: begin
			if (occ_of[{wr_[3:0], wc[2:0]}]) begin
				if (!seen) begin
					seen <= 1'b1;
					if (5'd16 - wr_ > maxh) maxh <= 5'd16 - wr_;
					if (base_mode) colh[wc] <= 5'd16 - wr_;   // per-column height for delta holes
				end
				if (vir_of[{wr_[3:0], wc[2:0]}]) begin
					anyvir <= 1'b1;
					// R6 matched-cover setup: a same-color non-virus cell resting directly on the virus
					// (== the R1 exemption condition) counts a started vertical clear.
					if (curcol == col_of[{wr_[3:0], wc[2:0]}]) matched60 <= matched60 + 13'd48;
					// R1 color-aware buried; R7b: charge only the 2 topmost viruses in the column.
					if (vseen < 5'd2)
						buried <= buried + fillcnt - ((curcol == col_of[{wr_[3:0], wc[2:0]}]) ? curlen : 5'd0);
					vseen <= vseen + 1'b1;
					curcol <= 2'd0; curlen <= 5'd0;                 // virus breaks the cover run
				end else begin                                     // occupied non-virus: extend/restart run
					if (curcol == col_of[{wr_[3:0], wc[2:0]}])
						curlen <= curlen + 1'b1;
					else begin
						curcol <= col_of[{wr_[3:0], wc[2:0]}]; curlen <= 5'd1;
					end
				end
				fillcnt <= fillcnt + 1'b1;
				if (wr_ < 3) toprisk <= toprisk + 1'b1;
				if (wr_ < 4 && (wc == 3 || wc == 4)) spawn <= spawn + 1'b1;
			end else begin
				if (seen) holes <= holes + 1'b1;
				curcol <= 2'd0; curlen <= 5'd0;                    // empty cell breaks the cover run
			end
			// advance row-major within the column
			if (wr_ == 4'd15) begin
				wr_ <= 0; seen <= 0; fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
				if (wc == 3'd7) begin
					vo <= 0; st <= S_VNEXT;
				end else
					wc <= wc + 1'b1;
			end else
				wr_ <= wr_ + 1'b1;
		end

		// ---- per-virus terms: iterate all cells, process viruses
		S_VNEXT: begin
			if (vir_of[vo]) begin
				run_h <= 1; run_v <= 1;
				p <= {2'b0, v_c};      // horizontal left walk from c-1
				st <= S_HRUN_L;
			end else if (vo == 7'd127) begin
				wc <= 0; wr_ <= 0; st <= S_SETUP_H;
			end else
				vo <= vo + 1'b1;
		end

		// horizontal: same-color run leftwards, then span leftwards
		S_HRUN_L: begin
			if (p != 0 && col_of[{v_r, p[2:0] - 3'd1}] == v_col && occ_of[{v_r, p[2:0]-3'd1}]) begin
				run_h <= run_h + 1'b1; p <= p - 1'b1;
			end else begin
				span_lo <= p; st <= S_HSPAN_L;    // continue span from p-1 downward
			end
		end
		S_HSPAN_L: begin
			if (span_lo != 0 &&
			    (!occ_of[{v_r, span_lo[2:0] - 3'd1}] || col_of[{v_r, span_lo[2:0] - 3'd1}] == v_col))
				span_lo <= span_lo - 1'b1;
			else begin
				p <= {2'b0, v_c}; st <= S_HRUN_R;
			end
		end
		S_HRUN_R: begin
			if (p != 5'd7 && occ_of[{v_r, p[2:0] + 3'd1}] && col_of[{v_r, p[2:0] + 3'd1}] == v_col) begin
				run_h <= run_h + 1'b1; p <= p + 1'b1;
			end else begin
				span_hi <= p; st <= S_HSPAN_R;
			end
		end
		S_HSPAN_R: begin
			if (span_hi != 5'd7 &&
			    (!occ_of[{v_r, span_hi[2:0] + 3'd1}] || col_of[{v_r, span_hi[2:0] + 3'd1}] == v_col))
				span_hi <= span_hi + 1'b1;
			else begin
				p <= {1'b0, v_r}; st <= S_VRUN_U;
			end
		end

		// vertical: run up, span up, run down, span down
		S_VRUN_U: begin
			if (p != 0 && occ_of[{p[3:0] - 4'd1, v_c}] && col_of[{p[3:0] - 4'd1, v_c}] == v_col) begin
				run_v <= run_v + 1'b1; p <= p - 1'b1;
			end else begin
				vspan_lo <= p; st <= S_VSPAN_U;
			end
		end
		S_VSPAN_U: begin
			if (vspan_lo != 0 &&
			    (!occ_of[{vspan_lo[3:0] - 4'd1, v_c}] || col_of[{vspan_lo[3:0] - 4'd1, v_c}] == v_col))
				vspan_lo <= vspan_lo - 1'b1;
			else begin
				p <= {1'b0, v_r}; st <= S_VRUN_D;
			end
		end
		S_VRUN_D: begin
			if (p != 5'd15 && occ_of[{p[3:0] + 4'd1, v_c}] && col_of[{p[3:0] + 4'd1, v_c}] == v_col) begin
				run_v <= run_v + 1'b1; p <= p + 1'b1;
			end else begin
				vspan_hi <= p; st <= S_VSPAN_D;
			end
		end
		S_VSPAN_D: begin
			if (vspan_hi != 5'd15 &&
			    (!occ_of[{vspan_hi[3:0] + 4'd1, v_c}] || col_of[{vspan_hi[3:0] + 4'd1, v_c}] == v_col))
				vspan_hi <= vspan_hi + 1'b1;
			else if (dphase != 2'd0) st <= S_DRVFIN;   // delta rescore: skip pollution, go accumulate
			else begin
				p <= 0; st <= S_POLROW;
			end
		end

		// pollution: differently-colored NON-virus occupied cells in row then column
		S_POLROW: begin
			if (p[2:0] != v_c && occ_of[{v_r, p[2:0]}] && !vir_of[{v_r, p[2:0]}]
			    && col_of[{v_r, p[2:0]}] != v_col)
				pollution <= pollution + 1'b1;
			if (p == 5'd7) begin p <= 0; st <= S_POLCOL; end
			else p <= p + 1'b1;
		end
		S_POLCOL: begin
			if (p[3:0] != v_r && occ_of[{p[3:0], v_c}] && !vir_of[{p[3:0], v_c}]
			    && col_of[{p[3:0], v_c}] != v_col)
				pollution <= pollution + 1'b1;
			if (p == 5'd15) st <= S_VFIN;
			else p <= p + 1'b1;
		end

		S_VFIN: begin
			// readiness_ext: max(run^2 per direction, gated on span >= 4)
			begin : fin
				reg [8:0] hq, vq, mx;
				// python gates on (hi - lo - 1) >= 4 with EXCLUSIVE blocker endpoints;
				// span_lo/hi here are INCLUSIVE span cells -> width = hi - lo + 1.
				hq = ((span_hi  - span_lo  + 5'd1) >= 5'd4) ? sq(run_h) : 9'd0;
				vq = ((vspan_hi - vspan_lo + 5'd1) >= 5'd4) ? sq(run_v) : 9'd0;
				mx = (hq > vq) ? hq : vq;
				rdy_ext <= rdy_ext + mx;
				vrdy    <= vrdy + sq(run_v);
			end
			if (vo == 7'd127) begin
				wc <= 0; wr_ <= 0; st <= S_SETUP_H;
			end else begin
				vo <= vo + 1'b1; st <= S_VNEXT;
			end
		end

		// ---- setup: 3-in-a-row same color touching a same-color virus (win extendable)
		// horizontal windows: rows 0..15, i 0..5 ; vertical: cols 0..7, i 0..13
		S_SETUP_H: begin : suh
			reg [1:0] c0;
			reg t;
			c0 = col_of[{wr_[3:0], wc[2:0]}];
			if (c0 != 0 && col_of[{wr_[3:0], wc[2:0] + 3'd1}] == c0
			            && col_of[{wr_[3:0], wc[2:0] + 3'd2}] == c0) begin
				t = (vir_of[{wr_[3:0], wc[2:0]}]        && col_of[{wr_[3:0], wc[2:0]}] == c0)
				  || (vir_of[{wr_[3:0], wc[2:0] + 3'd1}] && col_of[{wr_[3:0], wc[2:0] + 3'd1}] == c0)
				  || (vir_of[{wr_[3:0], wc[2:0] + 3'd2}] && col_of[{wr_[3:0], wc[2:0] + 3'd2}] == c0);
				if (!t && wc != 0)
					t = vir_of[{wr_[3:0], wc[2:0] - 3'd1}] && col_of[{wr_[3:0], wc[2:0] - 3'd1}] == c0;
				if (!t && wc < 3'd5)
					t = vir_of[{wr_[3:0], wc[2:0] + 3'd3}] && col_of[{wr_[3:0], wc[2:0] + 3'd3}] == c0;
				if (t) setup <= setup + 1'b1;
			end
			if (wc == 3'd5) begin
				wc <= 0;
				if (wr_ == 4'd15) begin wr_ <= 0; st <= S_SETUP_V; end
				else wr_ <= wr_ + 1'b1;
			end else
				wc <= wc + 1'b1;
		end
		S_SETUP_V: begin : suv
			reg [1:0] c0;
			reg t;
			c0 = col_of[{wr_[3:0], wc[2:0]}];
			if (c0 != 0 && col_of[{wr_[3:0] + 4'd1, wc[2:0]}] == c0
			            && col_of[{wr_[3:0] + 4'd2, wc[2:0]}] == c0) begin
				t = (vir_of[{wr_[3:0], wc[2:0]}]         && col_of[{wr_[3:0], wc[2:0]}] == c0)
				  || (vir_of[{wr_[3:0] + 4'd1, wc[2:0]}] && col_of[{wr_[3:0] + 4'd1, wc[2:0]}] == c0)
				  || (vir_of[{wr_[3:0] + 4'd2, wc[2:0]}] && col_of[{wr_[3:0] + 4'd2, wc[2:0]}] == c0);
				if (!t && wr_ != 0)
					t = vir_of[{wr_[3:0] - 4'd1, wc[2:0]}] && col_of[{wr_[3:0] - 4'd1, wc[2:0]}] == c0;
				if (!t && wr_ < 4'd13)
					t = vir_of[{wr_[3:0] + 4'd3, wc[2:0]}] && col_of[{wr_[3:0] + 4'd3, wc[2:0]}] == c0;
				if (t) setup <= setup + 1'b1;
			end
			if (wr_ == 4'd13) begin
				wr_ <= 0;
				if (wc == 3'd7) st <= S_DONE;
				else wc <= wc + 1'b1;
			end else
				wr_ <= wr_ + 1'b1;
		end

		S_DONE: begin       // stage 1: register combine (multiplier) inputs near the DSPs
			if (base_mode) begin   // CMD 6: latch base_* totals, no sco
				base_maxh <= maxh; base_holes <= holes; base_toprisk <= toprisk; base_spawn <= spawn;
				base_setup <= setup; base_pol <= pollution; base_buried <= buried; base_matched <= matched60;
				base_rdy <= rdy_ext; base_vrdy <= vrdy; base_anyvir <= anyvir;
				win <= !anyvir; done <= 1'b1; base_mode <= 1'b0; st <= S_IDLE;
			end else begin
				maxh_p <= maxh; holes_p <= holes; toprisk_p <= toprisk; spawn_p <= spawn; setup_p <= setup;
				pollution_p <= pollution; buried_p <= buried; rdy_ext_p <= rdy_ext; vrdy_p <= vrdy; matched60_p <= matched60;
				win  <= !anyvir;
				st <= S_DONE2;
			end
		end
		S_DONE2: begin      // stage 2: combine from registered inputs (same sco, +1 leaf cycle)
			sco <= 16'd5000
			     - 16'd12  * maxh_p
			     - 16'd20  * holes_p
			     - 16'd90  * toprisk_p
			     - 16'd150 * spawn_p
			     + 16'd32  * setup_p
			     + matched60_p
			     - 16'd48  * buried_p
			     + 16'd8   * rdy_ext_p
			     + 16'd8   * vrdy_p
			     - 16'd6   * pollution_p;
			done <= 1'b1;
			st <= S_IDLE;
		end

		// ================= incremental DELTA child (CMD 7) =================
		// entered from S_APPLY with the non-clearing CHILD board in bcell; base_* valid.
		S_DNEW: begin : dnew
			reg [7:0] ga, gb;
			// holes delta: horizontal pill can hover a half over a shorter column; vertical lands contiguous -> 0
			ga = 8'd15 - {3'd0, colh[off_a[2:0]]} - {4'd0, off_a[6:3]};
			gb = 8'd15 - {3'd0, colh[off_b[2:0]]} - {4'd0, off_b[6:3]};
			dd_holes <= a_o4[1] ? (ga + gb) : 8'd0;
			// matched60 delta: a placed cell resting directly on a same-color virus adds a cover (+48)
			dd_matched <= ((off_a[6:3] != 4'd15 && vir_of[off_a + 7'd8] && col_of[off_a + 7'd8] == pca) ? 13'd48 : 13'd0)
			            + ((off_b[6:3] != 4'd15 && vir_of[off_b + 7'd8] && col_of[off_b + 7'd8] == pcb) ? 13'd48 : 13'd0);
			// pollution delta: scan the 2 placed cells' rows+cols for differently-colored viruses
			dsoff <= {off_a[6:3], 3'd0}; dstep <= 4'd1; dscnt <= 5'd8; li <= 2'd0;
			st <= S_DPOL;
		end
		S_DPOL: begin
			if (vir_of[dsoff] && col_of[dsoff] != (li[1] ? pcb : pca))
				dd_pol <= dd_pol + 1'b1;
			if (dscnt == 5'd1) begin
				case (li)
					2'd0: begin dsoff <= {5'd0, off_a[2:0]}; dstep <= 4'd8; dscnt <= 5'd16; li <= 2'd1; end  // colA
					2'd1: begin dsoff <= {off_b[6:3], 3'd0}; dstep <= 4'd1; dscnt <= 5'd8;  li <= 2'd2; end  // rowB
					2'd2: begin dsoff <= {5'd0, off_b[2:0]}; dstep <= 4'd8; dscnt <= 5'd16; li <= 2'd3; end  // colB
					default: begin   // -> buried mini-colwalk (new phase, child board)
						dbur_new <= 1'b1; dcolstep <= 2'd0; dcol <= off_a[2:0]; drow <= 5'd0;
						fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
						st <= S_DBUR;
					end
				endcase
			end else begin
				dsoff <= dsoff + {3'd0, dstep};
				dscnt <= dscnt - 1'b1;
			end
		end
		S_DCOMB: begin : dcomb
			reg [4:0] hha, hhb, hmax;
			hha = 5'd16 - off_a[6:3]; hhb = 5'd16 - off_b[6:3]; hmax = base_maxh;
			if (hha > hmax) hmax = hha;
			if (hhb > hmax) hmax = hhb;
			maxh     <= hmax;
			holes    <= base_holes + dd_holes;
			toprisk  <= base_toprisk + {7'd0, (off_a[6:3] < 4'd3)} + {7'd0, (off_b[6:3] < 4'd3)};
			spawn    <= base_spawn
			          + {7'd0, (off_a[6:3] < 4'd4 && (off_a[2:0] == 3'd3 || off_a[2:0] == 3'd4))}
			          + {7'd0, (off_b[6:3] < 4'd4 && (off_b[2:0] == 3'd3 || off_b[2:0] == 3'd4))};
			setup    <= base_setup - od_set + nd_set;
			pollution<= base_pol + {5'd0, dd_pol};
			buried   <= base_buried - od_bur + nd_bur;
			rdy_ext  <= base_rdy - od_rdy + nd_rdy;
			vrdy     <= base_vrdy - od_vrdy + nd_vrdy;
			matched60<= base_matched + dd_matched;
			anyvir   <= base_anyvir;
			delta_mode <= 1'b0;
			st <= S_DONE;
		end

		// buried mini-colwalk over the 1-2 placed columns (R1 color-aware + R7b nearest-2 cap),
		// new phase on child then old phase on parent; new_buried = base - od_bur + nd_bur.
		S_DBUR: begin : dbur
			reg [4:0] excess;
			if (occ_of[{drow[3:0], dcol}]) begin
				if (vir_of[{drow[3:0], dcol}]) begin
					if (vseen < 5'd2) begin
						excess = fillcnt - ((curcol == col_of[{drow[3:0], dcol}]) ? curlen : 5'd0);
						if (dbur_new) nd_bur <= nd_bur + {5'd0, excess};
						else          od_bur <= od_bur + {5'd0, excess};
					end
					vseen <= vseen + 1'b1; curcol <= 2'd0; curlen <= 5'd0;
				end else begin
					if (curcol == col_of[{drow[3:0], dcol}]) curlen <= curlen + 1'b1;
					else begin curcol <= col_of[{drow[3:0], dcol}]; curlen <= 5'd1; end
				end
				fillcnt <= fillcnt + 1'b1;
			end else begin
				curcol <= 2'd0; curlen <= 5'd0;
			end
			if (drow == 5'd15) begin
				if (dcolstep == 2'd0 && a_o4[1] && off_b[2:0] != off_a[2:0]) begin
					dcolstep <= 2'd1; dcol <= off_b[2:0]; drow <= 5'd0;
					fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
				end else begin
					// buried done -> rdy_ext/vrdy rescore of same-color viruses in the placed lines
					dphase <= dbur_new ? 2'd1 : 2'd2;
					dlmask <= {a_o4[1], ~a_o4[1], 1'b1, 1'b1};   // {col_b(horiz), row_b(vert), col_a, row_a}
					dsoff <= {off_a[6:3], 3'd0}; dstep <= 4'd1; dscnt <= 5'd8; li <= 2'd0;
					st <= S_DRV;
				end
			end else drow <= drow + 1'b1;
		end
		S_DUNPL: begin
			// placed cells were empty on the settled parent; the funnel clears their links too
			bcell[off_a] <= 3'd0; bcell[off_b] <= 3'd0;
			dbur_new <= 1'b0; dcolstep <= 2'd0; dcol <= off_a[2:0]; drow <= 5'd0;
			fillcnt <= 0; curcol <= 2'd0; curlen <= 5'd0; vseen <= 5'd0;
			st <= S_DUNPL_B;
		end
		S_DUNPL_B: st <= S_DBUR;   // second cell's link (write port arm above)

		// rdy_ext/vrdy rescore: walk the placed cells' rows+cols, and for each same-color virus
		// re-run the per-virus run/span machinery (reused) to get its old/new contribution.
		S_DRV: begin
			// rescore EVERY virus in a placed line: a diff-color placed cell can bound a virus's
			// span (rdy_ext gate), not only extend a same-color run. Unaffected viruses net od==nd.
			if (vir_of[dsoff]) begin
				vo <= dsoff; run_h <= 5'd1; run_v <= 5'd1; p <= {2'b0, dsoff[2:0]};
				st <= S_HRUN_L;                              // -> ... -> S_VSPAN_D -> S_DRVFIN (dphase!=0)
			end else st <= S_DADV;
		end
		S_DADV: begin
			if (dscnt != 5'd1) begin
				dsoff <= dsoff + {3'd0, dstep}; dscnt <= dscnt - 1'b1; st <= S_DRV;
			end else if (li == 2'd0) begin                  // -> col_a
				dsoff <= {5'd0, off_a[2:0]}; dstep <= 4'd8; dscnt <= 5'd16; li <= 2'd1; st <= S_DRV;
			end else if (li == 2'd1 && dlmask[2]) begin      // -> row_b
				dsoff <= {off_b[6:3], 3'd0}; dstep <= 4'd1; dscnt <= 5'd8; li <= 2'd2; st <= S_DRV;
			end else if (li != 2'd3 && dlmask[3]) begin      // -> col_b
				dsoff <= {5'd0, off_b[2:0]}; dstep <= 4'd8; dscnt <= 5'd16; li <= 2'd3; st <= S_DRV;
			end else begin                                   // rescore done -> setup windows (horizontal first)
				dphase <= 2'd0;
				dwrow <= {1'b0, off_a[6:3]};
				dws   <= (off_a[2:0] >= 3'd2) ? {1'b0, off_a[2:0] - 3'd2} : 4'd0;
				dwhi  <= a_o4[1] ? ((off_b[2:0] <= 3'd5) ? {1'b0, off_b[2:0]} : 4'd5)
				                 : ((off_a[2:0] <= 3'd5) ? {1'b0, off_a[2:0]} : 4'd5);
				dwsecond <= 1'b0;
				st <= S_DSETH;
			end
		end
		S_DRVFIN: begin : drvfin
			reg [8:0] hq, vq, mx;
			hq = ((span_hi  - span_lo  + 5'd1) >= 5'd4) ? sq(run_h) : 9'd0;
			vq = ((vspan_hi - vspan_lo + 5'd1) >= 5'd4) ? sq(run_v) : 9'd0;
			mx = (hq > vq) ? hq : vq;
			if (dphase == 2'd1) begin nd_rdy <= nd_rdy + {7'd0, mx}; nd_vrdy <= nd_vrdy + {7'd0, sq(run_v)}; end
			else                begin od_rdy <= od_rdy + {7'd0, mx}; od_vrdy <= od_vrdy + {7'd0, sq(run_v)}; end
			st <= S_DADV;
		end

		// setup delta: re-evaluate only the 3-in-a-row windows that contain a placed cell,
		// horizontal windows (over placed rows) then vertical (over placed cols); dbur_new picks nd/od.
		S_DSETH: begin : dseth
			reg [1:0] c0; reg tt;
			c0 = col_of[{dwrow[3:0], dws[2:0]}]; tt = 1'b0;
			if (c0 != 2'd0 && col_of[{dwrow[3:0], dws[2:0] + 3'd1}] == c0
			              && col_of[{dwrow[3:0], dws[2:0] + 3'd2}] == c0) begin
				tt = (vir_of[{dwrow[3:0], dws[2:0]}]         && col_of[{dwrow[3:0], dws[2:0]}] == c0)
				  || (vir_of[{dwrow[3:0], dws[2:0] + 3'd1}]  && col_of[{dwrow[3:0], dws[2:0] + 3'd1}] == c0)
				  || (vir_of[{dwrow[3:0], dws[2:0] + 3'd2}]  && col_of[{dwrow[3:0], dws[2:0] + 3'd2}] == c0);
				if (!tt && dws[2:0] != 3'd0) tt = vir_of[{dwrow[3:0], dws[2:0] - 3'd1}] && col_of[{dwrow[3:0], dws[2:0] - 3'd1}] == c0;
				if (!tt && dws[2:0] < 3'd5)  tt = vir_of[{dwrow[3:0], dws[2:0] + 3'd3}] && col_of[{dwrow[3:0], dws[2:0] + 3'd3}] == c0;
				if (tt) begin if (dbur_new) nd_set <= nd_set + 1'b1; else od_set <= od_set + 1'b1; end
			end
			if (dws >= dwhi) begin
				if (!a_o4[1] && !dwsecond) begin                 // vertical pill: second placed row
					dwrow <= {1'b0, off_b[6:3]}; dwsecond <= 1'b1;
					dws <= (off_a[2:0] >= 3'd2) ? {1'b0, off_a[2:0] - 3'd2} : 4'd0;
				end else begin                                    // -> vertical windows
					dwrow <= {1'b0, off_a[2:0]};
					dws  <= (off_a[6:3] >= 4'd2) ? (off_a[6:3] - 4'd2) : 4'd0;
					dwhi <= (!a_o4[1]) ? ((off_b[6:3] <= 4'd13) ? off_b[6:3] : 4'd13)
					                   : ((off_a[6:3] <= 4'd13) ? off_a[6:3] : 4'd13);
					dwsecond <= 1'b0; st <= S_DSETV;
				end
			end else dws <= dws + 1'b1;
		end
		S_DSETV: begin : dsetv
			reg [1:0] c0; reg tt;
			c0 = col_of[{dws[3:0], dwrow[2:0]}]; tt = 1'b0;
			if (c0 != 2'd0 && col_of[{dws[3:0] + 4'd1, dwrow[2:0]}] == c0
			              && col_of[{dws[3:0] + 4'd2, dwrow[2:0]}] == c0) begin
				tt = (vir_of[{dws[3:0], dwrow[2:0]}]         && col_of[{dws[3:0], dwrow[2:0]}] == c0)
				  || (vir_of[{dws[3:0] + 4'd1, dwrow[2:0]}]  && col_of[{dws[3:0] + 4'd1, dwrow[2:0]}] == c0)
				  || (vir_of[{dws[3:0] + 4'd2, dwrow[2:0]}]  && col_of[{dws[3:0] + 4'd2, dwrow[2:0]}] == c0);
				if (!tt && dws != 4'd0)  tt = vir_of[{dws[3:0] - 4'd1, dwrow[2:0]}] && col_of[{dws[3:0] - 4'd1, dwrow[2:0]}] == c0;
				if (!tt && dws < 4'd13)  tt = vir_of[{dws[3:0] + 4'd3, dwrow[2:0]}] && col_of[{dws[3:0] + 4'd3, dwrow[2:0]}] == c0;
				if (tt) begin if (dbur_new) nd_set <= nd_set + 1'b1; else od_set <= od_set + 1'b1; end
			end
			if (dws >= dwhi) begin
				if (a_o4[1] && !dwsecond) begin                  // horizontal pill: second placed col
					dwrow <= {1'b0, off_b[2:0]}; dwsecond <= 1'b1;
					dws <= (off_a[6:3] >= 4'd2) ? (off_a[6:3] - 4'd2) : 4'd0;
				end else st <= dbur_new ? S_DUNPL : S_DCOMB;      // setup done -> unplace / combine
			end else dws <= dws + 1'b1;
		end
		// ================= CMD 8: stranded-half scan (#47) =================
		// A pill cell with NO same-colour orthogonal neighbour can never match
		// without excavation (terms47.g_stranded / cascade_stranded_x, both
		// offline gates green). Read-only over bcell; runs after a NODE/DELTA
		// left the child board in bcell. 2 cycles/cell = 256 cycles ~ 5us.
		S_STR_R: begin         // READ: register the 128:1 muxed colours
			rs_c <= col_of[str_i];
			rs_p <= occ_of[str_i] && !vir_of[str_i];
			rs_u <= (str_i >= 7'd8)      ? col_of[str_i - 7'd8] : 2'd0;
			rs_d <= (str_i <= 7'd119)    ? col_of[str_i + 7'd8] : 2'd0;
			rs_l <= (str_i[2:0] != 3'd0) ? col_of[str_i - 7'd1] : 2'd0;
			rs_r <= (str_i[2:0] != 3'd7) ? col_of[str_i + 7'd1] : 2'd0;
			st <= S_STR_D;
		end
		S_STR_D: begin         // DECIDE: compare on registers only
			if (rs_p && rs_c != rs_u && rs_c != rs_d && rs_c != rs_l && rs_c != rs_r)
				strand <= strand + 7'd1;
			if (str_i == 7'd127) begin done <= 1'b1; st <= S_IDLE; end
			else begin str_i <= str_i + 7'd1; st <= S_STR_R; end
		end
		default: st <= S_IDLE;
		endcase
	end
end

endmodule
