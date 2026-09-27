// G1 (minimal): delta-path co-sim gate for DRVETO Fix A -- drives the REAL mapper
// RTL (CoproDrMario + LeafEval + copro6502) with the firmware hex in ./copro_rom.hex
// and OBSERVES, per s_loop iteration and per mailbox store:
//   - the zp $B4 (D_VETO) write executes (count b4zero/b4one);
//   - at every $B4 write, the LAST COMPLETED LeafEval command is CMD-4 and the
//     live lev_rvc/lev_win equal the values latched at that CMD-4's done edge
//     (the C1 freshness invariant; the M2 o_cand mutant must trip it);
//   - the full S_BEST_C/O store trajectory ($6134/$6135) with the shadowed $B4
//     flag and the search/post phase (post = after the first fetch into the tuck
//     ROM window [$9000,$A800), where $B4 is stale by construction);
//   - the final published answer + DONE.
// Output: one "CASE <name> ..." line per case; the runner (run_g1.py) applies the
// assertion matrix across hexes (fixa_delta / fixa_base / m2_delta / veto1).
#include "VCoproDrMario.h"
#include "VCoproDrMario___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static VCoproDrMario* t;
static long clocks = 0;

// ---- per-case observer state
struct Pub { int c, o, veto; bool search_phase; long clk; };
static std::vector<Pub> pubs;
static long b4zero, b4one, cmd4viol;
static int shadow_c, shadow_b4;
static bool tuck_started, done_seen;
static int pending_cmd, last_done_cmd;
static long done_clk;
static int snap_rvc, snap_win;
static int prev_done;

static void obs_reset() {
  pubs.clear(); b4zero = b4one = cmd4viol = 0;
  shadow_c = -1; shadow_b4 = 0; tuck_started = false; done_seen = false;
  pending_cmd = -1; last_done_cmd = -1; snap_rvc = -1; snap_win = -1; prev_done = 0;
  done_clk = -1;
}

static void observe() {
  auto* r = t->rootp;
  int AB = r->CoproDrMario__DOT__AB;
  int DO = r->CoproDrMario__DOT__DO;
  int WE = r->CoproDrMario__DOT__WE;
  int done = r->CoproDrMario__DOT__lev_done;
  int rvc = r->CoproDrMario__DOT__lev_rvc;
  int win = r->CoproDrMario__DOT__lev_win;
  if (done && !prev_done) {           // LeafEval done edge: latch what completed
    last_done_cmd = pending_cmd;
    snap_rvc = rvc; snap_win = win;
  }
  prev_done = done;
  if (!WE && AB >= 0x9000 && AB < 0xA800) tuck_started = true;
  if (WE) {
    if (AB == 0x70F4) pending_cmd = DO & 0xF;
    else if (AB == 0x00B4) {
      if ((DO & 0xFF) == 0) b4zero++; else b4one++;
      shadow_b4 = DO & 0xFF;
      if (last_done_cmd != 4 || rvc != snap_rvc || win != snap_win) cmd4viol++;
    } else if (AB == 0x6134) shadow_c = DO & 0xFF;
    else if (AB == 0x6135) {
      if ((DO & 0xFF) != 0xFF)
        pubs.push_back({shadow_c, DO & 0xFF, shadow_b4, !tuck_started, clocks});
    } else if (AB == 0x61FF && (DO & 0xFF) == 1) { done_seen = true; if (done_clk < 0) done_clk = clocks; }
  }
}

static void tick() {
  t->clk = 0; t->clk_cpu = 0; t->eval();
  t->clk = 1; t->clk_cpu = 1; t->eval();
  observe();
  clocks++;
}

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
  const char* casefile = argc > 1 ? argv[1] : "g3cases.txt";
  const long MAXCLK = 3000000000L;         // ~35 s of copro time @85.9MHz
  t = new VCoproDrMario;
  t->enable = 1; t->ce = 0;
  { t->clk = 0; t->clk_cpu = 0; t->eval(); t->clk = 1; t->clk_cpu = 1; t->eval(); }

  FILE* f = fopen(casefile, "r");
  if (!f) { printf("FAIL no %s\n", casefile); return 1; }
  int n; if (fscanf(f, "%d", &n) != 1) { printf("FAIL bad header\n"); return 1; }
  for (int k = 0; k < n; k++) {
    char name[128];
    int cA, cB, nA, nB, nf, unv;
    fscanf(f, "%127s %d %d %d %d %d", name, &cA, &cB, &nA, &nB, &nf);
    std::vector<int> fired;                     // post-canon (col,o4) pairs
    for (int i = 0; i < nf; i++) { int c, o; fscanf(f, "%d %d", &c, &o); fired.push_back(c * 16 + o); }
    fscanf(f, "%d", &unv);
    int b[128];
    for (int i = 0; i < 128; i++) fscanf(f, "%x", &b[i]);

    for (int i = 0; i < 128; i++) nes_cycle(0x5000 + i, b[i], true);
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true);
    nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    obs_reset();
    nes_cycle(0x5084, 1, true);                       // GO (reset pulse, clears DONE)

    long c0 = clocks;
    while (!done_seen && clocks - c0 < MAXCLK) {
      // idle host cycles; the observer runs inside tick()
      for (int i = 0; i < 480; i++) tick();
    }
    long used = clocks - c0;
    int rdone = nes_read(0x5084);
    int rc = nes_read(0x5085), ro = nes_read(0x5086);
    bool timeout = !done_seen;

    // serialize pubs
    std::string ps;
    char buf[64];
    for (auto& p : pubs) {
      snprintf(buf, sizeof buf, "%d:%d:%d:%s:%ld;", p.c, p.o, p.veto,
               p.search_phase ? "s" : "p", p.clk - c0);
      ps += buf;
    }
    printf("CASE %s final=%d,%d done=%d b4zero=%ld b4one=%ld cmd4viol=%ld "
           "pubs=%s clocks=%ld doneclk=%ld timeout=%d\n",
           name, rc, ro, rdone, b4zero, b4one, cmd4viol,
           ps.empty() ? "-" : ps.c_str(), used, done_clk < 0 ? -1 : done_clk - c0, timeout ? 1 : 0);
    fflush(stdout);
  }
  fclose(f);
  delete t;
  return 0;
}
