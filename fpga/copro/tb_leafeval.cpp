// LeafEval vs the python leaf_d3 golden: reads leafeval_cases.txt
// (per line: 128 hex cell bytes in NES encoding + expected sco (signed) + win),
// converts to the module's 3-bit encoding, runs, compares.
#include "VLeafEval.h"
#include "VLeafEval___024root.h"
#include "verilated.h"
#include <cstdio>

static VLeafEval* t;
static void tick() { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  t = new VLeafEval;
  t->rst = 1; t->wr = 0; t->start = 0; tick(); tick(); t->rst = 0; tick();

  FILE* f = fopen("leafeval_cases.txt", "r");
  if (!f) { printf("FAIL no leafeval_cases.txt\n"); return 1; }
  int n; if (fscanf(f, "%d", &n) != 1) return 1;
  int pass = 0;
  for (int k = 0; k < n; k++) {
    int exp_sco, exp_win, b[128];
    for (int i = 0; i < 128; i++) if (fscanf(f, "%x", &b[i]) != 1) return 1;
    if (fscanf(f, "%d %d", &exp_sco, &exp_win) != 2) return 1;

    for (int i = 0; i < 128; i++) {
      int enc = 0;
      if (b[i] != 0xFF) {
        int col = (b[i] & 0x0F) + 1;               // NES nibble 0..2 -> 1..3
        int vir = ((b[i] & 0xF0) == 0xD0) ? 1 : 0;
        enc = (vir << 2) | col;
      }
      t->wr = 1; t->waddr = i; t->wdata = enc; tick();
    }
    t->wr = 0;
    t->start = 1; tick(); t->start = 0;
    long cyc = 0;
    while (!t->done && cyc < 100000) { tick(); cyc++; }
    short got = (short)t->sco;
    bool ok = t->done && (int)t->win == exp_win && (exp_win || got == (short)exp_sco);
    if (ok) pass++;
    else if (k < 8 || pass + 8 > k)
      printf("case %d: got sco=%d win=%d (cyc=%ld) exp sco=%d win=%d MISMATCH rdy_ext=%d vrdy=%d\n",
             k, got, (int)t->win, cyc, exp_sco, exp_win,
             (int)t->rootp->LeafEval__DOT__rdy_ext, (int)t->rootp->LeafEval__DOT__vrdy),
      printf("   mh=%d ho=%d tr=%d spawn=%d setup=%d buried=%d pol=%d\n",
             (int)t->rootp->LeafEval__DOT__maxh, (int)t->rootp->LeafEval__DOT__holes,
             (int)t->rootp->LeafEval__DOT__toprisk, (int)t->rootp->LeafEval__DOT__spawn,
             (int)t->rootp->LeafEval__DOT__setup, (int)t->rootp->LeafEval__DOT__buried,
             (int)t->rootp->LeafEval__DOT__pollution);
    if (k == 0) printf("case 0 latency: %ld cycles\n", cyc);
  }
  printf("LEAFEVAL %d/%d\n", pass, n);
  fclose(f);

  // ---- phase 2: NODE command (land+place+targeted resolve+leaf) ----
  FILE* g = fopen("leafeval_node_cases.txt", "r");
  if (!g) { printf("no node cases\n"); delete t; return pass == n ? 0 : 1; }
  int nn; if (fscanf(g, "%d", &nn) != 1) return 1;
  int npass = 0;
  long worst = 0;
  for (int k = 0; k < nn; k++) {
    int b[128], nb[128], o4, col, ca, cb, legal, cells, vir, imm, sco, win;
    for (int i = 0; i < 128; i++) if (fscanf(g, "%x", &b[i]) != 1) return 1;
    if (fscanf(g, "%d %d %d %d %d %d %d %d %d %d", &o4, &col, &ca, &cb,
               &legal, &cells, &vir, &imm, &sco, &win) != 10) return 1;
    for (int i = 0; i < 128; i++) if (fscanf(g, "%x", &nb[i]) != 1) return 1;

    t->wslot = 0;
    for (int i = 0; i < 128; i++) {
      int enc = 0;
      if (b[i] != 0xFF)
        enc = ((((b[i] & 0xF0) == 0xD0) ? 1 : 0) << 2) | ((b[i] & 3) + 1);
      t->wr = 1; t->waddr = i; t->wdata = enc; tick();
    }
    t->wr = 0;
    t->a_o4 = o4; t->a_col = col; t->a_ca = ca + 1; t->a_cb = cb + 1;
    t->cmd = 4; t->cmd_go = 1; tick(); t->cmd_go = 0;
    long cyc = 0;
    while (!t->done && cyc < 100000) { tick(); cyc++; }
    if (cyc > worst) worst = cyc;
    bool ok = t->done && (int)t->legal == legal;
    if (legal) {
      ok = ok && (int)t->rv_cells == cells && (int)t->rv_vir == vir
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
    else if (npass + 6 > k)
      printf("node %d: legal=%d/%d cells=%d/%d vir=%d/%d imm=%d/%d sco=%d/%d win=%d/%d MISMATCH\n",
             k, (int)t->legal, legal, (int)t->rv_cells, cells, (int)t->rv_vir, vir,
             (int)t->imm, imm, (int)(short)t->sco, sco, (int)t->win, win);
  }
  printf("NODE %d/%d (worst latency %ld cyc)\n", npass, nn, worst);
  fclose(g); delete t;
  return (pass == n && npass == nn) ? 0 : 1;
}
