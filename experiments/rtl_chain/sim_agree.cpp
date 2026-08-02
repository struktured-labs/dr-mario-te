// AGREEMENT-vs-K: when during a search does the copro's published move stop changing?
//
// WHY THIS EXISTS. The Pocket runs the copro at 54.669 MHz against the same ~80-frame pill
// budget, so a decision that fits on MiSTer can be truncated there. Truncation is only
// harmful if the move the driver would commit EARLY differs from the move the search
// finally returns. The firmware live-publishes its running best (test_search_d3.py: "ANYTIME
// live-publish running best", fired on strict improvement, with orient=0xFF written at search
// start as a "no candidate yet" sentinel), so the early-commit move is observable directly.
//
// This rig records every publish transition with its clock offset. From that trace the
// agreement at ANY truncation point K is computable analytically -- one pass per board
// instead of one run per K.
//
// MEASUREMENT HYGIENE. Sampling is a direct read of the dpram array, NOT a host bus cycle:
//   - the mailbox is a true dual-port RAM (port A copro, port B host), so host reads cannot
//     stall the search -- but reading zero times is a stronger guarantee than reasoning that
//     reading is free;
//   - the poll loop in sim_mister.cpp quantises DONE to a 48-clock CPU cycle, so this rig's
//     T is expected to be SMALLER by up to ~150 clocks. That is quantisation, not drift.
// The control is dist69.log: per-board DONE clocks must reproduce within that tolerance.
// A perturbing instrument would move them by percent, not by microscopic constants.
#include "VCoproDrMario.h"
#include "VCoproDrMario___024root.h"
#include "verilated.h"
#include <cstdio>

static VCoproDrMario* t;
static long clocks = 0;

// $61FF DONE / $6134 best_col / $6135 best_orient, via CoproDrMario's xlate() map
static const int I_DONE = 0x8FF, I_COL = 0x834, I_ORI = 0x835;
#define WRAM(i) (t->rootp->CoproDrMario__DOT__wram__DOT__mem[(i)])

static void tick() { t->clk = 0; t->clk_cpu = 0; t->eval(); t->clk = 1; t->clk_cpu = 1; t->eval(); clocks++; }

// one NES CPU cycle = 48 master clocks, ce high on exactly one of them
static void nes_cycle(int addr, int data, bool we) {
  t->prg_ain = addr; t->prg_din = data; t->prg_write = we; t->prg_read = !we;
  for (int i = 0; i < 48; i++) { t->ce = (i == 24); tick(); }
  t->ce = 0; t->prg_write = 0; t->prg_read = 0;
}

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  t = new VCoproDrMario;
  t->enable = 1; t->ce = 0; tick();

  FILE* f = fopen("hostdata.txt", "r");
  if (!f) { printf("FAIL no hostdata.txt\n"); return 1; }
  int n; if (fscanf(f, "%d", &n) != 1) { printf("FAIL bad hostdata header\n"); return 1; }
  printf("# boards %d\n", n);

  for (int k = 0; k < n; k++) {
    int cA, cB, nA, nB, ec, eo, b[128];
    if (fscanf(f, "%d %d %d %d %d %d", &cA, &cB, &nA, &nB, &ec, &eo) != 6) {
      printf("FAIL truncated record %d\n", k); return 1;
    }
    for (int i = 0; i < 128; i++) fscanf(f, "%x", &b[i]);

    for (int i = 0; i < 128; i++) nes_cycle(0x5000 + i, b[i], true);
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true);
    nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    nes_cycle(0x5084, 1, true);                       // GO

    // GO must have cleared DONE, or "time to DONE" would measure the PREVIOUS decision.
    if (WRAM(I_DONE) != 0) { printf("FAIL board %d: GO did not clear DONE\n", k); return 2; }

    long c0 = clocks;
    // The mailbox is NOT cleared by GO: col keeps the previous decision's value until the
    // first candidate publishes. That carry-over is real hardware behaviour and is what the
    // driver's 0xFF-orient sentinel exists to reject, so record it rather than hide it.
    int lc = WRAM(I_COL), lo = WRAM(I_ORI);
    printf("BOARD %d carry %d %d\n", k, lc, lo);

    long t_sent = -1, t_first = -1, t_settle = -1;
    int ntrans = 0;
    while (WRAM(I_DONE) == 0 && clocks - c0 < 16000000000L) {
      tick();
      int c = WRAM(I_COL), o = WRAM(I_ORI);
      if (c != lc || o != lo) {
        long dt = clocks - c0;
        printf("PUB %d %ld %d %d\n", k, dt, c, o);
        ntrans++;
        if (o == 0xFF) { if (t_sent < 0) t_sent = dt; }
        else { if (t_first < 0) t_first = dt; t_settle = dt; }
        lc = c; lo = o;
      }
    }
    long T = clocks - c0;
    printf("DONEB %d T %ld sent %ld first %ld settle %ld ntrans %d final %d %d\n",
           k, T, t_sent, t_first, t_settle, ntrans, lc, lo);
    fflush(stdout);
  }
  fclose(f); delete t;
  return 0;
}
