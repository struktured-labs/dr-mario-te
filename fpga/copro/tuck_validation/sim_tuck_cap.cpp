// TUCK co-sim: stream boards through the REAL CoproDrMario.sv, poll DONE, then read the
// tuck descriptor back out through the HOST BRIDGE at cart $5087/$5088 (not copro RAM).
// Reports clocks GO->DONE so baseline vs tuck firmware gives the added latency directly.
//
// input file: N, then per case "cA cB nA nB" followed by 128 hex board bytes.
#include "VCoproDrMario.h"
#include "verilated.h"
#include <cstdio>

static VCoproDrMario* t;
static long clocks = 0;

static void tick() { t->clk = 0; t->clk_cpu = 0; t->eval(); t->clk = 1; t->clk_cpu = 1; t->eval(); clocks++; }

// one NES CPU cycle = 48 master clocks, ce high on exactly one of them
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

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  const char* path = (argc > 1 && argv[1][0] != '+') ? argv[1] : "hostdata.txt";
  t = new VCoproDrMario;
  t->enable = 1; t->ce = 0; tick();

  FILE* f = fopen(path, "r");
  if (!f) { printf("FAIL no %s\n", path); return 1; }
  int n; if (fscanf(f, "%d", &n) != 1) { printf("FAIL bad header\n"); return 1; }
  printf("case,cA,cB,nA,nB,best_col,best_orient,tuck_col,tuck_row,clocks\n");
  for (int k = 0; k < n; k++) {
    int cA, cB, nA, nB, b[128];
    if (fscanf(f, "%d %d %d %d", &cA, &cB, &nA, &nB) != 4) { printf("FAIL case %d\n", k); return 1; }
    for (int i = 0; i < 128; i++) fscanf(f, "%x", &b[i]);

    for (int i = 0; i < 128; i++) nes_cycle(0x5000 + i, b[i], true);
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true);
    nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    nes_cycle(0x5084, 1, true);                       // GO

    long c0 = clocks;
    while (nes_read(0x5084) == 0 && clocks - c0 < 400000000L) {}
    long used = clocks - c0;
    int rc = nes_read(0x5085), ro = nes_read(0x5086);
    int tc = nes_read(0x5087), tr = nes_read(0x5088);
    printf("%d,%d,%d,%d,%d,%d,%d,%d,%d,%ld\n", k, cA, cB, nA, nB, rc, ro, tc, tr, used);
    fflush(stdout);
  }
  fclose(f); delete t;
  return 0;
}
