// DIAGNOSTIC co-sim (not a gate): which copro state carries over a GO-reset into the next search?
// Same RTL/bus as sim_pubchain.cpp, built with --public-flat-rw. Input lines as sim_pubchain (go_at abort cA cB nA nB
// board). For the LAST decision only: dumps the 4 KB work RAM at GO, then logs, per RAM address, the FIRST copro access
// after the reset is released (R or W) and the clock; prints "RAM <hex 4096 bytes>" and "FIRST <addr> <R|W> <clk>"
// lines for every address whose first access is a READ (a read-before-write: leftover state the search consumes),
// plus the usual PUB/END line. argv: POLL WGAP
#include "VCoproDrMario.h"
#include "VCoproDrMario___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "dump_lev.inc"   // generated: every LeafEval register (experiments/abortstale, diagnostic only)

static VCoproDrMario* t;
static long clocks = 0;
static bool track = false; static long track_go = 0;
static int firstk[4096]; static long firstc[4096];
static int levn = 0, lev_done_prev = 0;
static void tick() {
  t->clk = 0; t->clk_cpu = 0; t->eval();
  if (track) {
    auto* r = t->rootp;
    int rst = r->CoproDrMario__DOT__cpu_rst;
    int ab = r->CoproDrMario__DOT__AB, we = r->CoproDrMario__DOT__WE;
    bool lo = (ab >> 12) == 0, st = (ab >> 8) == 0x61;
    if (!rst && levn < 400) {
      int go = r->CoproDrMario__DOT__lev_cmd_go, stt = r->CoproDrMario__DOT__lev_start, dn = r->CoproDrMario__DOT__lev_done;
      if (go || stt) {
        printf("LEV %ld go %s cmd=%d slot=%d\n", clocks - track_go, go ? "cmd" : "leaf", (int)(r->CoproDrMario__DOT__DO & 15), (int)r->CoproDrMario__DOT__lev_a_sl); levn++;
        if (levn < 12) {      // engine state at the first commands: CUR cells + links, and the 4 slots
          printf("ENG %ld cur ", clocks - track_go);
          for (int i = 0; i < 128; i++) printf("%d%d", (int)r->CoproDrMario__DOT__leafeval__DOT__bcell[i], (int)r->CoproDrMario__DOT__leafeval__DOT__blink[i]);
          printf(" slots ");
          for (int i = 0; i < 512; i++) printf("%02x", (int)r->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem[i]);
          printf("\n");
          printf("REG %ld", clocks - track_go); dump_lev(r);
        }
      }
      if (dn && !lev_done_prev) { printf("LEV %ld done\n", clocks - track_go); levn++; }
      lev_done_prev = dn;
    }
    if (!rst && (lo || st)) {
      int a = st ? (0x800 | (ab & 0xFF)) : (ab & 0xFFF);
      if (!firstk[a]) { firstk[a] = we ? 2 : 1; firstc[a] = clocks - track_go; }
    }
  }
  t->clk = 1; t->clk_cpu = 1; t->eval(); clocks++;
}
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
static void nes_idle(int ncyc) {
  t->prg_ain = 0x8000; t->prg_read = 0; t->prg_write = 0;
  for (int k = 0; k < ncyc; k++) for (int i = 0; i < 48; i++) { t->ce = (i == 24); tick(); }
  t->ce = 0;
}
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  int POLL = argc > 1 ? atoi(argv[1]) : 64, WGAP = argc > 2 ? atoi(argv[2]) : 0;
  t = new VCoproDrMario; t->enable = 1; t->ce = 0; tick();
  std::vector<std::vector<long>> L; char* line = nullptr; size_t cap = 0;
  std::vector<std::string> lines;
  while (getline(&line, &cap, stdin) > 0) { if (!strncmp(line, "BYE", 3)) break; lines.push_back(line); }
  long go = 0; bool have = false, done = false;
  for (size_t li = 0; li < lines.size(); li++) {
    char* p = (char*)lines[li].c_str(); char* end; int b[128];
    long go_at = strtol(p, &end, 10); p = end; int ab = (int)strtol(p, &end, 10); p = end;
    int cA = (int)strtol(p, &end, 10); p = end; int cB = (int)strtol(p, &end, 10); p = end;
    int nA = (int)strtol(p, &end, 10); p = end; int nB = (int)strtol(p, &end, 10); p = end;
    for (int i = 0; i < 128; i++) { b[i] = (int)strtol(p, &end, 16); p = end; }
    if (have) {
      while (true) {
        long el = clocks - go;
        if (done && el >= go_at) break;
        if (!done && el >= go_at && ab) break;
        if (!done) { if (nes_read(0x5084)) { done = true; continue; } nes_idle(POLL); } else nes_idle(POLL);
      }
    }
    bool last = li + 1 == lines.size();
    for (int i = 0; i < 128; i++) { nes_cycle(0x5000 + i, b[i], true); if (WGAP) nes_idle(WGAP); }
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true); nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    if (last) {
      auto* r = t->rootp;
      printf("RAM ");
      for (int a = 0; a < 4096; a++) printf("%02x", (int)r->CoproDrMario__DOT__wram__DOT__mem[a]);
      printf("\n");
      memset(firstk, 0, sizeof firstk); track = true;
    }
    nes_cycle(0x5084, 1, true);
    go = clocks; track_go = clocks; have = true; done = false;
  }
  while (!done) { if (nes_read(0x5084)) done = true; else nes_idle(POLL); }
  printf("END %ld\n", clocks - go);
  for (int a = 0; a < 4096; a++) if (firstk[a]) printf("FIRST %03x %c %ld\n", a, firstk[a] == 1 ? 'R' : 'W', firstc[a]);
  return 0;
}
