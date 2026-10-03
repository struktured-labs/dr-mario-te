// PUBLISH-TIMELINE co-sim: the REAL CoproDrMario RTL + firmware (copro_rom.hex in CWD), with the NES-side bus
// emulation copied verbatim from fpga/copro/sim_mister.cpp / experiments/cosim_farm/sim_farm.cpp.
// Difference: after GO it does NOT spin on DONE. It polls the live mailbox the way the cart driver does
// (orient $5x86, col $5x85, DONE $5x84) every POLL NES CPU cycles, idling the bus in between, and logs every
// CHANGE of the published (col, orient) with its master-clock stamp since GO. Port B reads are a dual-port RAM
// read (CoproDrMario.sv xlate/ram_b_q) and cannot perturb the copro.
// stdin, one decision per line: cA cB nA nB <128 hex board bytes>   (RAW bytes: seed / REACHTX / TAP nibbles included)
// stdout, one reply per line:   PUB <n> {clk col orient}*n DONE <clk> <col> <orient> TUCK <tcol> <trow>
// argv[1] = NES CPU cycles between polls (default 64). The firmware is $readmemh("copro_rom.hex") from the CWD.
#include "VCoproDrMario.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

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
  int v = t->prg_dout; t->ce = 0; t->prg_read = 0; return v;
}
static void nes_idle(int ncyc) {   // bus idle (game CPU running elsewhere)
  t->prg_ain = 0x8000; t->prg_read = 0; t->prg_write = 0;
  for (int k = 0; k < ncyc; k++) for (int i = 0; i < 48; i++) { t->ce = (i == 24); tick(); }
  t->ce = 0;
}
static const long CLOCK_LIMIT = 2000000000L;

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  int POLL = argc > 1 ? atoi(argv[1]) : 64;     // NES CPU cycles between polls
  t = new VCoproDrMario; t->enable = 1; t->ce = 0; tick();
  setvbuf(stdout, nullptr, _IOLBF, 0);
  char* line = nullptr; size_t cap = 0; int b[128];
  static long pc[4096]; static int pcol[4096], por[4096];
  while (true) {
    ssize_t n = getline(&line, &cap, stdin);
    if (n <= 0) break;
    if (!strncmp(line, "BYE", 3)) break;
    int cA, cB, nA, nB; char* p = line; char* end;
    cA = (int)strtol(p, &end, 10); if (end == p) continue; p = end;
    cB = (int)strtol(p, &end, 10); p = end; nA = (int)strtol(p, &end, 10); p = end; nB = (int)strtol(p, &end, 10); p = end;
    bool ok = true;
    for (int i = 0; i < 128; i++) { b[i] = (int)strtol(p, &end, 16); if (end == p) { ok = false; break; } p = end; }
    if (!ok) { printf("ERR badline\n"); continue; }
    for (int i = 0; i < 128; i++) nes_cycle(0x5000 + i, b[i], true);
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true); nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    nes_cycle(0x5084, 1, true);                        // GO
    long c0 = clocks; int np = 0, lc = -1, lo = -1, done = 0;
    while (clocks - c0 < CLOCK_LIMIT) {
      int o = nes_read(0x5086), c = nes_read(0x5085), o2 = nes_read(0x5086);
      done = nes_read(0x5084);
      if (o == o2 && (o != lo || c != lc)) {
        if (np < 4096) { pc[np] = clocks - c0; pcol[np] = c; por[np] = o; np++; }
        lc = c; lo = o;
      }
      if (done) break;
      nes_idle(POLL);
    }
    long used = clocks - c0;
    if (used >= CLOCK_LIMIT) { printf("ERR timeout %ld\n", used); continue; }
    int rc = nes_read(0x5085), ro = nes_read(0x5086), tc = nes_read(0x5087), tr = nes_read(0x5088);
    printf("PUB %d", np);
    for (int k = 0; k < np; k++) printf(" %ld %d %d", pc[k], pcol[k], por[k]);
    printf(" DONE %ld %d %d TUCK %d %d\n", used, rc, ro, tc, tr);
  }
  free(line); delete t; return 0;
}
