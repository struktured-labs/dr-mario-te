// ============================================================================
// sim_orient_trace.cpp — MEASURE the pair-latch defect on the real RTL.
//
// Spec P0.1 says the cart commits ORIENT early (at MIN_THINK, ~5 frames of search) but
// COLUMN at DONE, so it plays a pair the depth-3 search never scored. The size of that
// effect depends on P — how converged the published orient already is at ~5 frames — and
// the spec is explicit that **P is INFERRED FROM A SOURCE COMMENT, NOT MEASURED**. That
// single unknown is what makes the whole champion claim model-dependent.
//
// This testbench measures it directly: pulse GO, then SAMPLE the published (col, orient)
// at every NES frame boundary while the search runs, and record the trajectory. From that
// we read off, per board:
//   * orient published at frame 5   (what the cart LATCHES, permanently)
//   * orient published at DONE      (what the search actually converged to)
//   * column at DONE                (what the cart uses)
// The orient-disagreement rate across boards IS P's complement, measured on silicon RTL
// rather than assumed.
//
// NOTE the anytime contract: reads of $5085/$5086 mid-search return best-so-far, which is
// exactly what the driver's act_p2 steers on. If the RTL instead parks them until DONE,
// this trace shows that too — and would REFUTE the premise, which is equally valuable.
//
// Build:  ./REBUILD_VSIM.sh sim_orient_trace.cpp VOrientTrace
// Run:    obj_mister/VOrientTrace   (reads hostdata.txt in cwd)
// ============================================================================
#include "VCoproDrMario.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>

static VCoproDrMario* t;
static long clocks = 0;

static void tick() { t->clk = 0; t->clk_cpu = 0; t->eval(); t->clk = 1; t->clk_cpu = 1; t->eval(); clocks++; }

static void nes_cycle(int addr, int data, bool we) {
  t->prg_ain = addr; t->prg_din = data; t->prg_write = we; t->prg_read = !we;
  for (int i = 0; i < 48; i++) { t->ce = (i == 24); tick(); }
  t->ce = 0; t->prg_write = 0; t->prg_read = 0;
}

static int nes_read(int addr) {
  t->prg_ain = addr; t->prg_read = 1; t->prg_write = 0;
  for (int i = 0; i < 48; i++) { t->ce = (i == 24); tick(); }
  int v = t->prg_dout;
  t->ce = 0; t->prg_read = 0;
  return v;
}

// 85.9 MHz master, ~60.1 Hz frames -> master clocks per NES frame
static const long CLK_PER_FRAME = 1429000L;
static const int  MIN_THINK_FRAMES = 5;      // spec: MIN_THINK 25 hooks ~ 5 frames
static int MAX_FRAMES = 240;   // override: argv[2]

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  t = new VCoproDrMario;
  t->enable = 1; t->ce = 0; tick();

  const char* path = (argc > 1) ? argv[1] : "hostdata.txt";
  if (argc > 2) MAX_FRAMES = atoi(argv[2]);
  FILE* f = fopen(path, "r");
  if (!f) { printf("FAIL cannot open %s\n", path); return 1; }
  printf("# %s  MAX_FRAMES=%d\n", path, MAX_FRAMES);
  int n; if (fscanf(f, "%d", &n) != 1) { printf("FAIL bad header\n"); return 1; }

  int disagree = 0, measured = 0, never_done = 0, parked = 0;
  printf("board,done_frame,orient_at5,orient_done,col_at5,col_done,orient_differs,col_differs\n");

  for (int k = 0; k < n; k++) {
    int cA, cB, nA, nB, ec, eo, b[128];
    if (fscanf(f, "%d %d %d %d %d %d", &cA, &cB, &nA, &nB, &ec, &eo) != 6) break;
    for (int i = 0; i < 128; i++) fscanf(f, "%x", &b[i]);

    for (int i = 0; i < 128; i++) nes_cycle(0x5000 + i, b[i], true);
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true);
    nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    nes_cycle(0x5084, 1, true);                        // GO

    int o_at5 = -1, c_at5 = -1, o_done = -1, c_done = -1, done_frame = -1;
    int distinct_o = 0, last_o = -999;
    long c0 = clocks;
    for (int fr = 1; fr <= MAX_FRAMES; fr++) {
      // idle-tick to the next frame boundary; polling via nes_read here would burn 48
      // clocks per poll (~30k reads/frame) and dominate runtime.
      while (clocks - c0 < (long)fr * CLK_PER_FRAME) tick();
      int d = nes_read(0x5084);
      int c = nes_read(0x5085), o = nes_read(0x5086);
      if (o != last_o) { distinct_o++; last_o = o; }
      if (fr == MIN_THINK_FRAMES) { o_at5 = o; c_at5 = c; }
      if (d != 0) { done_frame = fr; o_done = o; c_done = c; break; }
    }
    if (done_frame < 0) { never_done++; continue; }
    if (o_at5 < 0) { o_at5 = o_done; c_at5 = c_done; }   // converged before frame 5
    if (distinct_o <= 1) parked++;                        // never republished => no anytime orient

    measured++;
    int od = (o_at5 != o_done), cd = (c_at5 != c_done);
    disagree += od;
    printf("%d,%d,%d,%d,%d,%d,%d,%d\n", k, done_frame, o_at5, o_done, c_at5, c_done, od, cd);
    fflush(stdout);
  }

  printf("\n# MEASURED n=%d  never_done=%d\n", measured, never_done);
  if (measured) {
    printf("# ORIENT DISAGREEMENT (latched@5f vs converged@DONE): %d/%d = %.1f%%\n",
           disagree, measured, 100.0 * disagree / measured);
    printf("# boards where orient NEVER republished (parked till DONE): %d/%d\n", parked, measured);
    printf("# -> if parked==measured the RTL does NOT publish a running orient, and the\n"
           "#    'partial orient' premise is REFUTED for this core.\n");
  }
  fclose(f); delete t;
  return 0;
}
