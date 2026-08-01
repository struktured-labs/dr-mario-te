// bitexact_gate testbench for LeafEval.sv (adapted from qa-wt tb_leafeval.cpp).
//   argv[1] = leaf cases file    (n; per case: 128 hex NES cells + exp_sco + exp_win)
//   argv[2] = node cases file    (n; per case: 128 hex + o4 col ca cb legal cells vir
//                                 imm sco win + 128 hex child)  -- optional
//   argv[3] = "delta"            enable phase 3 (CMD6 BASE + CMD7 DELTA vs the same
//                                 full-recompute oracle; needs -DHAS_DELTA build)
// Prints machine-greppable PHASE lines; exit 0 iff every phase is clean.
#include "VLeafEval.h"
#include "VLeafEval___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>

static VLeafEval* t;
static void tick() { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }

static void write_board(const int* b) {
  t->wslot = 0;
  for (int i = 0; i < 128; i++) {
    int enc = 0;
    if (b[i] != 0xFF)
      enc = ((((b[i] & 0xF0) == 0xD0) ? 1 : 0) << 2) | ((b[i] & 3) + 1);
    t->wr = 1; t->waddr = i; t->wdata = enc; tick();
  }
  t->wr = 0;
}

static long wait_done() {
  long cyc = 0;
  while (!t->done && cyc < 200000) { tick(); cyc++; }
  return cyc;
}

static int read_board_case(FILE* f, int* b) {
  for (int i = 0; i < 128; i++) if (fscanf(f, "%x", &b[i]) != 1) return 0;
  return 1;
}

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  t = new VLeafEval;
  t->rst = 1; t->wr = 0; t->start = 0; t->cmd_go = 0; tick(); tick();
  t->rst = 0; tick();

  int fails = 0;
  const int MAXPRINT = 20;

  // ---------------- phase 1: LEAF ----------------
  {
    FILE* f = fopen(argc > 1 ? argv[1] : "leafeval_cases.txt", "r");
    if (!f) { printf("PHASE1 FAIL no leaf cases file\n"); return 1; }
    int n; if (fscanf(f, "%d", &n) != 1) return 1;
    int pass = 0, b[128];
    for (int k = 0; k < n; k++) {
      int exp_sco, exp_win;
      if (!read_board_case(f, b)) return 1;
      if (fscanf(f, "%d %d", &exp_sco, &exp_win) != 2) return 1;
      write_board(b);
      t->start = 1; tick(); t->start = 0;
      long cyc = wait_done();
      short got = (short)t->sco;
      bool ok = t->done && (int)t->win == exp_win && (exp_win || got == (short)exp_sco);
      if (ok) pass++;
      else if (fails < MAXPRINT)
        printf("LEAF case %d: got sco=%d win=%d (cyc=%ld) exp sco=%d win=%d MISMATCH\n",
               k, got, (int)t->win, cyc, exp_sco, exp_win);
      if (!ok) fails++;
    }
    printf("PHASE1 LEAF %d/%d\n", pass, n);
    fclose(f);
  }

  // ---------------- phase 2: NODE (land+place+resolve+leaf) ----------------
  int nn = 0;
  if (argc > 2) {
    FILE* g = fopen(argv[2], "r");
    if (!g) { printf("PHASE2 FAIL no node cases file\n"); return 1; }
    if (fscanf(g, "%d", &nn) != 1) return 1;
    int npass = 0, b[128], nb[128];
    long worst = 0;
    for (int k = 0; k < nn; k++) {
      int o4, colu, ca, cb, legal, cells, vir, imm, sco, win;
      if (!read_board_case(g, b)) return 1;
      if (fscanf(g, "%d %d %d %d %d %d %d %d %d %d", &o4, &colu, &ca, &cb,
                 &legal, &cells, &vir, &imm, &sco, &win) != 10) return 1;
      if (!read_board_case(g, nb)) return 1;

      write_board(b);
      t->a_o4 = o4; t->a_col = colu; t->a_ca = ca + 1; t->a_cb = cb + 1;
      t->cmd = 4; t->cmd_go = 1; tick(); t->cmd_go = 0;
      long cyc = wait_done();
      if (cyc > worst) worst = cyc;
      bool ok = t->done && (int)t->legal == legal;
      if (legal && ok) {
        ok = (int)t->rv_cells == cells && (int)t->rv_vir == vir
          && (int)t->imm == imm && (int)t->win == win
          && (win || (short)t->sco == (short)sco);
        for (int i = 0; ok && i < 128; i++) {
          int enc = 0;
          if (nb[i] != 0xFF)
            enc = ((((nb[i] & 0xF0) == 0xD0) ? 1 : 0) << 2) | ((nb[i] & 3) + 1);
          if ((int)t->rootp->LeafEval__DOT__bcell[i] != enc) ok = false;
        }
      }
      if (ok) npass++;
      else {
        if (fails < MAXPRINT)
          printf("NODE case %d: legal=%d/%d cells=%d/%d vir=%d/%d imm=%d/%d "
                 "sco=%d/%d win=%d/%d MISMATCH\n",
                 k, (int)t->legal, legal, (int)t->rv_cells, cells, (int)t->rv_vir,
                 vir, (int)t->imm, imm, (int)(short)t->sco, sco, (int)t->win, win);
        fails++;
      }
    }
    printf("PHASE2 NODE %d/%d (worst latency %ld cyc)\n", npass, nn, worst);
    fclose(g);
  }

  // ---------------- phase 3: CMD6 BASE + CMD7 DELTA vs the same oracle ----------
  if (argc > 3 && strcmp(argv[3], "delta") == 0) {
#ifndef HAS_DELTA
    printf("PHASE3 SKIP (built without -DHAS_DELTA)\n");
#else
    FILE* g = fopen(argv[2], "r");
    int n3; if (fscanf(g, "%d", &n3) != 1) return 1;
    int dpass = 0, dfall = 0, b[128], nb[128];
    for (int k = 0; k < n3; k++) {
      int o4, colu, ca, cb, legal, cells, vir, imm, sco, win;
      if (!read_board_case(g, b)) return 1;
      if (fscanf(g, "%d %d %d %d %d %d %d %d %d %d", &o4, &colu, &ca, &cb,
                 &legal, &cells, &vir, &imm, &sco, &win) != 10) return 1;
      if (!read_board_case(g, nb)) return 1;

      write_board(b);
      t->cmd = 6; t->cmd_go = 1; tick(); t->cmd_go = 0;   // BASE latch
      wait_done();
      t->a_o4 = o4; t->a_col = colu; t->a_ca = ca + 1; t->a_cb = cb + 1;
      t->cmd = 7; t->cmd_go = 1; tick(); t->cmd_go = 0;   // DELTA child
      wait_done();
      bool ok;
      if (!legal) ok = (int)t->legal == 0;
      else if (cells > 0 || vir > 0) {                    // clears: must fall back
        ok = (int)t->dv_fallback == 1; if (ok) dfall++;
      } else {
        ok = (int)t->legal == 1 && (int)t->dv_fallback == 0
          && (int)t->win == win && (win || (short)t->sco == (short)sco);
      }
      if (ok) dpass++;
      else if (fails < MAXPRINT)
        printf("DELTA case %d: legal=%d/%d fb=%d sco=%d/%d win=%d/%d MISMATCH\n",
               k, (int)t->legal, legal, (int)t->dv_fallback,
               (int)(short)t->sco, sco, (int)t->win, win);
      if (!ok) fails++;
    }
    printf("PHASE3 DELTA %d/%d (%d clear-fallbacks verified)\n", dpass, n3, dfall);
    fclose(g);
#endif
  }

  delete t;
  return fails == 0 ? 0 : 1;
}
