// #47 CMD-8 stranded-scan unit gate: reads strand_cases.txt (per line: 128
// engine-encoded cells ((vir<<2)|col) + expected count), loads each board via
// the write port, issues CMD 8, compares the strand output. Also asserts the
// scan is read-only: a second CMD 8 on the same board must return the same
// count (bcell unperturbed).
#include "VLeafEval.h"
#include "verilated.h"
#include <cstdio>

static VLeafEval* t;
static void tick() { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }

static int run_cmd8() {
  t->cmd = 8; t->cmd_go = 1; tick(); t->cmd_go = 0;
  long cyc = 0;
  while (!t->done && cyc < 10000) { tick(); cyc++; }
  return t->done ? (int)t->strand : -1;
}

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  t = new VLeafEval;
  t->rst = 1; t->wr = 0; t->start = 0; t->cmd_go = 0; t->wslot = 0; tick(); tick();
  t->rst = 0; tick();

  FILE* f = fopen("strand_cases.txt", "r");
  if (!f) { printf("FAIL no strand_cases.txt\n"); return 1; }
  int n; if (fscanf(f, "%d", &n) != 1) return 1;
  int pass = 0;
  for (int k = 0; k < n; k++) {
    int exp, e[128];
    for (int i = 0; i < 128; i++) if (fscanf(f, "%d", &e[i]) != 1) return 1;
    if (fscanf(f, "%d", &exp) != 1) return 1;
    for (int i = 0; i < 128; i++) { t->wr = 1; t->waddr = i; t->wdata = e[i]; tick(); }
    t->wr = 0;
    int got = run_cmd8();
    int got2 = run_cmd8();               // read-only check: identical on re-run
    bool ok = (got == exp) && (got2 == exp);
    if (ok) pass++;
    else printf("case %d: got %d then %d, expected %d MISMATCH\n", k, got, got2, exp);
  }
  printf("STRAND %d/%d\n", pass, n);
  fclose(f);
  delete t;
  return pass == n ? 0 : 1;
}
