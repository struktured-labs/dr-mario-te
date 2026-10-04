// CHAINED publish-timeline co-sim: the REAL CoproDrMario RTL + firmware (copro_rom.hex in CWD), ONE process for a
// whole sequence of decisions, so every search starts on the copro state the previous one left behind -- the way the
// couch cart drives it -- instead of on a freshly-constructed model (tools/lateflip/sim_pubtrace.cpp, one process per
// decision). NES-side bus emulation and the mailbox poll are copied verbatim from sim_pubtrace.cpp.
//
// stdin, one decision per line:
//   <go_at> <abort> cA cB nA nB <128 hex board bytes>
//     go_at  = master clocks after the PREVIOUS decision's GO at which this decision's upload starts (first line: 0)
//     abort  = 1: start the upload at go_at even if the previous search has not DONE'd (the DRABORTSTALE cart: the
//                 stale search is torn down at the new-pill edge, and the upload + GO resets the copro mid-search)
//              0: today's driver: if the previous search is still running at go_at, keep polling until its DONE,
//                 then start the upload (at the next poll)
//   BYE ends the run.
// stdout, one reply per decision, AFTER the decision has ended (DONE, or aborted by the next upload):
//   PUB <n> {clk col orient}*n END <DONE|ABORT> <clk> <col> <orient> TUCK <tcol> <trow> UPL <upload_start_clk_rel_prev_go>
//   (clk = master clocks since this decision's GO; for ABORT the col/orient are the live mailbox at the abort)
// argv[1] = NES CPU cycles between polls (default 64), argv[2] = NES CPU cycles between board-byte writes (default 0 =
// back-to-back like sim_pubtrace; ~17 = the cart's upload loop), argv[3] = 1 -> write GO TWICE (GO, upload, GO).
#include "VCoproDrMario.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>

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
static void nes_idle(int ncyc) {
  t->prg_ain = 0x8000; t->prg_read = 0; t->prg_write = 0;
  for (int k = 0; k < ncyc; k++) for (int i = 0; i < 48; i++) { t->ce = (i == 24); tick(); }
  t->ce = 0;
}
static const long CLOCK_LIMIT = 2000000000L;

struct Run { long go = 0; int np = 0, lc = -1, lo = -1; bool done = false;
             std::vector<long> pc; std::vector<int> pcol, por; long upl = 0, done_clk = 0, abort_clk = 0;
             long end_clk() const { return done ? done_clk : abort_clk; } };

static void poll_once(Run& r) {      // exactly sim_pubtrace's poll body
  int o = nes_read(0x5086), c = nes_read(0x5085), o2 = nes_read(0x5086);
  int d = nes_read(0x5084);
  if (o == o2 && (o != r.lo || c != r.lc)) {
    r.pc.push_back(clocks - r.go); r.pcol.push_back(c); r.por.push_back(o); r.np++;
    r.lc = c; r.lo = o;
  }
  if (d) r.done = true;
}
static void report(Run& r, bool aborted) {
  int rc = nes_read(0x5085), ro = nes_read(0x5086), tc = nes_read(0x5087), tr = nes_read(0x5088);
  printf("PUB %d", r.np);
  for (int k = 0; k < r.np; k++) printf(" %ld %d %d", r.pc[k], r.pcol[k], r.por[k]);
  printf(" END %s %ld %d %d TUCK %d %d UPL %ld\n", aborted ? "ABORT" : "DONE", r.end_clk(), rc, ro, tc, tr, r.upl);
}

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  int POLL = argc > 1 ? atoi(argv[1]) : 64;
  int WGAP = argc > 2 ? atoi(argv[2]) : 0;
  int GO2 = argc > 3 ? atoi(argv[3]) : 0;
  t = new VCoproDrMario; t->enable = 1; t->ce = 0; tick();
  setvbuf(stdout, nullptr, _IOLBF, 0);
  char* line = nullptr; size_t cap = 0; int b[128];
  Run cur; bool have = false;
  while (true) {
    ssize_t n = getline(&line, &cap, stdin);
    if (n <= 0 || !strncmp(line, "BYE", 3)) break;
    long go_at; int abort_, cA, cB, nA, nB; char* p = line; char* end;
    go_at = strtol(p, &end, 10); if (end == p) continue; p = end;
    abort_ = (int)strtol(p, &end, 10); p = end;
    cA = (int)strtol(p, &end, 10); p = end; cB = (int)strtol(p, &end, 10); p = end;
    nA = (int)strtol(p, &end, 10); p = end; nB = (int)strtol(p, &end, 10); p = end;
    bool ok = true;
    for (int i = 0; i < 128; i++) { b[i] = (int)strtol(p, &end, 16); if (end == p) { ok = false; break; } p = end; }
    if (!ok) { printf("ERR badline\n"); continue; }
    // ---- run the previous decision forward until this upload starts
    bool aborted = false;
    if (have) {
      while (true) {
        long el = clocks - cur.go;
        if (el >= CLOCK_LIMIT) { printf("ERR timeout\n"); return 1; }
        if (cur.done && el >= go_at) break;                 // DONE'd and the upload time has come
        if (!cur.done && el >= go_at && abort_) { aborted = true; break; }   // stale search: abort it
        if (!cur.done) { poll_once(cur); if (cur.done) { cur.done_clk = clocks - cur.go; continue; } nes_idle(POLL); }
        else nes_idle(POLL);
      }
      cur.abort_clk = clocks - cur.go;
      report(cur, aborted);
    }
    long upl = have ? clocks - cur.go : 0;
    // ---- upload + GO (the dead search, if any, is still running during the upload)
    if (GO2) nes_cycle(0x5084, 1, true);
    for (int i = 0; i < 128; i++) { nes_cycle(0x5000 + i, b[i], true); if (WGAP) nes_idle(WGAP); }
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true); nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    nes_cycle(0x5084, 1, true);                        // GO
    cur = Run(); cur.go = clocks; cur.upl = upl; have = true;
  }
  if (have) {                                          // last decision: run to DONE
    while (!cur.done && clocks - cur.go < CLOCK_LIMIT) { poll_once(cur); if (cur.done) { cur.done_clk = clocks - cur.go; break; } nes_idle(POLL); }
    cur.abort_clk = clocks - cur.go;
    report(cur, false);
  }
  free(line); delete t; return 0;
}
