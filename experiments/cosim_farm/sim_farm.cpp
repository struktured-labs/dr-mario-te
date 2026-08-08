// Persistent co-sim SERVER: one verilated CoproDrMario instance, many decisions.
//
// The stock sim_mister.cpp reads a fixed hostdata.txt and exits. A full GAME needs the
// board to depend on the PREVIOUS decision, so the board cannot be known up front. This
// serves decisions over stdin/stdout instead, keeping ONE VCoproDrMario alive across the
// whole game -- which is also strictly more faithful than re-instantiating per board,
// because real silicon never re-instantiates either.
//
// The NES-side bus emulation (48 master clocks per CPU cycle, ce high on exactly one of
// them, address/data held across the cycle) is copied VERBATIM from sim_mister.cpp. It is
// not re-derived here: the agreement gate in gate_agree.py asserts this server reproduces
// the stock binary's decisions bit-for-bit on the same boards.
//
// PROTOCOL
//   stdin, one decision per line:  cA cB nA nB <128 hex board bytes>
//   stdout, one reply per line:    col orient tcol trow clocks
//   "BYE" on stdin, or EOF, exits.
// tcol==0xFF means "no tuck" (CoproDrMario.sv's own sentinel for $5087).
//
// The firmware image is $readmemh("copro_rom.hex", rom) -- resolved at RUNTIME, relative
// to the process CWD. Arm selection is therefore done by running this binary in a
// directory holding that arm's copro_rom.hex; the binary itself is arm-agnostic and is
// built exactly once. run_farm.py prints the md5 it launched under so the arm is never
// inferred from a filename.
#include "VCoproDrMario.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

static VCoproDrMario* t;
static long clocks = 0;

static void tick() {
  t->clk = 0; t->clk_cpu = 0; t->eval();
  t->clk = 1; t->clk_cpu = 1; t->eval();
  clocks++;
}

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

// Hard ceiling on one decision. The observed worst case in this project's own latency
// study is ~33M master clocks; 2G is ~60x that, so tripping it means the search wedged,
// not that it was slow. A wedge must be reported, never silently returned as a move.
static const long CLOCK_LIMIT = 2000000000L;

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  t = new VCoproDrMario;
  t->enable = 1; t->ce = 0; tick();

  setvbuf(stdout, nullptr, _IOLBF, 0);

  char* line = nullptr;
  size_t cap = 0;
  int b[128];

  while (true) {
    ssize_t n = getline(&line, &cap, stdin);
    if (n <= 0) break;
    if (!strncmp(line, "BYE", 3)) break;

    int cA, cB, nA, nB;
    char* p = line;
    char* end;
    cA = (int)strtol(p, &end, 10); if (end == p) continue; p = end;
    cB = (int)strtol(p, &end, 10); p = end;
    nA = (int)strtol(p, &end, 10); p = end;
    nB = (int)strtol(p, &end, 10); p = end;
    bool ok = true;
    for (int i = 0; i < 128; i++) {
      b[i] = (int)strtol(p, &end, 16);
      if (end == p) { ok = false; break; }
      p = end;
    }
    if (!ok) { printf("ERR badline\n"); continue; }

    for (int i = 0; i < 128; i++) nes_cycle(0x5000 + i, b[i], true);
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true);
    nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    nes_cycle(0x5084, 1, true);                        // GO

    long c0 = clocks;
    while (nes_read(0x5084) == 0 && clocks - c0 < CLOCK_LIMIT) { }
    long used = clocks - c0;
    if (used >= CLOCK_LIMIT) { printf("ERR timeout %ld\n", used); continue; }

    int rc = nes_read(0x5085), ro = nes_read(0x5086);
    int tc = nes_read(0x5087), tr = nes_read(0x5088);
    printf("%d %d %d %d %ld\n", rc, ro, tc, tr, used);
  }

  free(line);
  delete t;
  return 0;
}
