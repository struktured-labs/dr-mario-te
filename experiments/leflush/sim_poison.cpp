// POISON co-sim for DRLEFLUSH: does ANY engine state that survives the copro GO reset change a search?
//
// The bus model, poll and reply format are sim_pubchain.cpp's (experiments/abortstale, itself = tools/lateflip
// sim_pubtrace.cpp's), so every reply is comparable with chain_cosim.py's fresh references bit for bit. Added:
//   POISON      at the reset RELEASE that follows a GO (the first clk_cpu edge with cpu_rst low again), overwrite
//               the selected engine registers with random values over their full width -- an arbitrary superset of
//               every state a preempted (mid-command) search can leave behind. Table + reasons: gen_poison.py.
//                 none (default) | all | allbut:a,b,.. | only:a,b,.. | set:a=V,b=V (exact values, scalars only)
//   POISON_RAM  1: also randomise the copro work RAM except what the HOST wrote for this decision (board $0500-$057F,
//               colours $6124-$6127, DONE $61FF) -- firmware-level leftovers, informational arm
//   POISON_SEED mt19937_64 seed (default 1)          POISON_GO   last (default) | every
//   DUMP=K      for the LAST decision: dump every table register at its first K engine command issues and DONEs
//   CLOCK_LIMIT master clocks after a GO before the run is declared hung (default 400M = ~280 frames)
// No wall-clock timeouts anywhere: a SIGSTOP (shared-box PAUSE switch) only delays the run.
// argv: POLL WGAP GO2 (as sim_pubchain).
#include "VCoproDrMario.h"
#include "VCoproDrMario___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>
#include <set>
#include "poison.inc"

static VCoproDrMario* t;
static long clocks = 0;
static bool armed = false, seen_rst = false, dumping = false;
static std::vector<int> psel; static bool pram = false; static unsigned long long pseed = 1;
static std::vector<std::pair<int, unsigned long long>> pset;
static int npoisoned = 0, dump_k = 0, dump_n = 0, lev_done_prev = 0; static long dump_go = 0;

static void dump_all(const char* ev, int cmd) {
  auto* r = t->rootp;
  printf("DUMP %s %ld %d", ev, clocks - dump_go, cmd);
  for (int k = 0; k < NPREG; k++) { printf(" %s=", PREG_NAME[k]); preg_dump(r, k); }
  printf("\n");
}
static void apply_poison() {
  auto* r = t->rootp;
  std::mt19937_64 g(pseed * 0x9E3779B97F4A7C15ULL + (unsigned long long)npoisoned);
  for (int k : psel) preg_poison(r, k, g);
  for (auto& kv : pset) if (!preg_set(r, kv.first, kv.second)) { printf("ERR set on non-scalar %s\n", PREG_NAME[kv.first]); exit(2); }
  if (pram)
    for (int a = 0; a < 4096; a++) {
      bool host = (a >= 0x500 && a < 0x580) || (a >= 0x824 && a < 0x828) || a == 0x8FF;
      unsigned v = (unsigned)g() & 0xFF;
      if (!host) r->CoproDrMario__DOT__wram__DOT__mem[a] = v;
    }
  printf("POISONED regs=%zu set=%zu ram=%d seed=%llu n=%d clk=%ld\n", psel.size(), pset.size(), pram ? 1 : 0, pseed, npoisoned, clocks);
  npoisoned++;
}
static void tick() {
  t->clk = 0; t->clk_cpu = 0; t->eval(); t->clk = 1; t->clk_cpu = 1; t->eval(); clocks++;
  auto* r = t->rootp;
  int rst = r->CoproDrMario__DOT__cpu_rst;
  if (armed) {
    if (rst) seen_rst = true;
    else if (seen_rst) { apply_poison(); armed = false; seen_rst = false; }
  }
  if (dumping && !rst && dump_n < dump_k) {
    int go = r->CoproDrMario__DOT__lev_cmd_go, st = r->CoproDrMario__DOT__lev_start, dn = r->CoproDrMario__DOT__lev_done;
    if (go || st) dump_all("go", go ? (int)(r->CoproDrMario__DOT__DO & 15) : 1);
    if (dn && !lev_done_prev) { dump_all("done", -1); dump_n++; }
    lev_done_prev = dn;
  }
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
static long CLOCK_LIMIT = 400000000L;

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

static int preg_index(const std::string& n) {
  for (int k = 0; k < NPREG; k++) if (n == PREG_NAME[k]) return k;
  fprintf(stderr, "unknown register %s\n", n.c_str()); exit(2);
}
static std::set<int> parse_names(const char* s) {
  std::set<int> out; std::string cur;
  for (const char* p = s;; p++) {
    if (*p == ',' || *p == 0) { if (!cur.empty()) out.insert(preg_index(cur)); cur.clear(); if (!*p) break; }
    else cur += *p;
  }
  return out;
}

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  int POLL = argc > 1 ? atoi(argv[1]) : 64;
  int WGAP = argc > 2 ? atoi(argv[2]) : 0;
  int GO2 = argc > 3 ? atoi(argv[3]) : 0;
  const char* ps = getenv("POISON"); std::string spec = ps ? ps : "none";
  if (spec == "all") { for (int k = 0; k < NPREG; k++) psel.push_back(k); }
  else if (spec.rfind("allbut:", 0) == 0) { auto ex = parse_names(spec.c_str() + 7); for (int k = 0; k < NPREG; k++) if (!ex.count(k)) psel.push_back(k); }
  else if (spec.rfind("only:", 0) == 0) { for (int k : parse_names(spec.c_str() + 5)) psel.push_back(k); }
  else if (spec.rfind("set:", 0) == 0) {
    std::string cur; std::string s2 = spec.substr(4) + ",";
    for (char ch : s2) {
      if (ch == ',') { if (!cur.empty()) { size_t e = cur.find('='); pset.push_back({preg_index(cur.substr(0, e)), strtoull(cur.substr(e + 1).c_str(), nullptr, 0)}); } cur.clear(); }
      else cur += ch;
    }
  }
  else if (spec != "none" && spec != "") { fprintf(stderr, "bad POISON %s\n", spec.c_str()); return 2; }
  pram = getenv("POISON_RAM") && atoi(getenv("POISON_RAM"));
  if (getenv("POISON_SEED")) pseed = strtoull(getenv("POISON_SEED"), nullptr, 10);
  bool every = getenv("POISON_GO") && !strcmp(getenv("POISON_GO"), "every");
  bool poison_on = !psel.empty() || !pset.empty() || pram;
  if (getenv("DUMP")) dump_k = atoi(getenv("DUMP"));
  if (getenv("CLOCK_LIMIT")) CLOCK_LIMIT = atol(getenv("CLOCK_LIMIT"));
  t = new VCoproDrMario; t->enable = 1; t->ce = 0; tick();
  setvbuf(stdout, nullptr, _IOLBF, 0);
  std::vector<std::string> lines; char* line = nullptr; size_t cap = 0;
  while (getline(&line, &cap, stdin) > 0) { if (!strncmp(line, "BYE", 3)) break; lines.push_back(line); }
  int b[128];
  Run cur; bool have = false;
  for (size_t li = 0; li < lines.size(); li++) {
    long go_at; int abort_, cA, cB, nA, nB; char* p = (char*)lines[li].c_str(); char* end;
    go_at = strtol(p, &end, 10); if (end == p) continue; p = end;
    abort_ = (int)strtol(p, &end, 10); p = end;
    cA = (int)strtol(p, &end, 10); p = end; cB = (int)strtol(p, &end, 10); p = end;
    nA = (int)strtol(p, &end, 10); p = end; nB = (int)strtol(p, &end, 10); p = end;
    bool ok = true;
    for (int i = 0; i < 128; i++) { b[i] = (int)strtol(p, &end, 16); if (end == p) { ok = false; break; } p = end; }
    if (!ok) { printf("ERR badline\n"); continue; }
    bool aborted = false;
    if (have) {
      while (true) {
        long el = clocks - cur.go;
        if (el >= CLOCK_LIMIT) { printf("ERR timeout\n"); return 1; }
        if (cur.done && el >= go_at) break;
        if (!cur.done && el >= go_at && abort_) { aborted = true; break; }
        if (!cur.done) { poll_once(cur); if (cur.done) { cur.done_clk = clocks - cur.go; continue; } nes_idle(POLL); }
        else nes_idle(POLL);
      }
      cur.abort_clk = clocks - cur.go;
      report(cur, aborted);
    }
    long upl = have ? clocks - cur.go : 0;
    bool last = li + 1 == lines.size();
    if (GO2) nes_cycle(0x5084, 1, true);
    for (int i = 0; i < 128; i++) { nes_cycle(0x5000 + i, b[i], true); if (WGAP) nes_idle(WGAP); }
    nes_cycle(0x5080, cA, true); nes_cycle(0x5081, cB, true); nes_cycle(0x5082, nA, true); nes_cycle(0x5083, nB, true);
    if (poison_on && (every || last)) { armed = true; seen_rst = false; }
    if (last && dump_k) { dumping = true; dump_n = 0; lev_done_prev = 1; }
    if (last) dump_go = clocks;
    nes_cycle(0x5084, 1, true);                        // GO
    cur = Run(); cur.go = clocks; cur.upl = upl; have = true;
  }
  if (have) {
    while (!cur.done) {
      if (clocks - cur.go >= CLOCK_LIMIT) { printf("ERR timeout\n"); return 1; }
      poll_once(cur); if (cur.done) { cur.done_clk = clocks - cur.go; break; } nes_idle(POLL);
    }
    cur.abort_clk = clocks - cur.go;
    report(cur, false);
  }
  if (poison_on && npoisoned == 0) { printf("ERR poison never applied\n"); return 1; }
  free(line); delete t; return 0;
}
