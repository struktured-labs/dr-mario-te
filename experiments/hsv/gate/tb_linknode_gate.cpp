// LeafEval CMD-4 (NODE) co-sim for the LINK-AWARE engine.
//
// Compares the RTL against cascade_chain_x/_leafv_ship on real self-play placements:
// colour plane, VIRUS plane, LINK plane, cells, viruses, CHAIN DEPTH, imm, sco, win.
// Both arms: fix=0 (cap-1, the lnk1 payload) and fix=1 (fixpoint, the chain payload).
//
// The NES-byte -> (cell, link) decode below MIRRORS CoproDrMario's lev_enc / lev_lnk. It
// is a mirror, not a test, of the wrapper -- the wrapper decode is exercised at the
// CoproDrMario level by the firmware co-sim.
//
// Also reports DONE latency, separately per arm, because fixpoint lengthens the resolve
// and the search has a falling-piece deadline to meet.
#include "VLeafEval.h"
#include "VLeafEval___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>

static VLeafEval* t;
static void tick() { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }

// NES playfield byte -> 3-bit engine cell (mirrors lev_enc)
static int enc_of(int b) {
  if (b == 0xFF) return 0;
  int colenc = ((b & 3) == 0) ? 1 : ((b & 3) == 1) ? 2 : 3;
  return (((b & 0xF0) == 0xD0) ? 4 : 0) | colenc;
}
// NES playfield byte -> 3-bit link code (mirrors lev_lnk)
static int lnk_of(int b) {
  switch (b & 0xF0) {
    case 0x40: return 2;   // top of a vertical pair    -> partner DOWN
    case 0x50: return 1;   // bottom of a vertical pair -> partner UP
    case 0x60: return 4;   // left of a horizontal pair -> partner RIGHT
    case 0x70: return 3;   // right of a horizontal pair-> partner LEFT
    default:   return 0;   // $8x orphan, $Dx virus, $FF empty
  }
}

int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  const char* path = (argc > 1) ? argv[1] : "chain_cases.txt";
  // optional DRCHAIN dose/4. Non-zero re-checks imm against the reference's _imm_chain
  // rule: only chain > 1 pays, and it pays w_chain*(chain-1). The corpus itself is always
  // generated at dose 0, so this also proves dose 0 is the identity.
  const int chw = (argc > 2) ? atoi(argv[2]) : 0;
  FILE* g = fopen(path, "r");
  if (!g) { printf("FAIL: no %s\n", path); return 2; }

  t = new VLeafEval;
  t->rst = 1; t->wr = 0; t->start = 0; t->cmd_go = 0; t->wslot = 0;
  tick(); tick(); t->rst = 0; tick();

  int n; if (fscanf(g, "%d", &n) != 1) return 2;
  int pass = 0, checked = 0;
  int bad_legal = 0, bad_cells = 0, bad_vir = 0, bad_chain = 0,
      bad_imm = 0, bad_sco = 0, bad_win = 0, bad_col = 0, bad_link = 0;
  long worst[2] = {0, 0}, tot[2] = {0, 0}, cnt[2] = {0, 0};
  int shown = 0, n_chained = 0;

  for (int k = 0; k < n; k++) {
    int b[128], nb[128], o4, col, ca, cb, fix, legal, cells, vir, ch, imm, sco, win;
    for (int i = 0; i < 128; i++) if (fscanf(g, "%x", &b[i]) != 1) return 2;
    if (fscanf(g, "%d %d %d %d %d", &o4, &col, &ca, &cb, &fix) != 5) return 2;
    if (fscanf(g, "%d %d %d %d %d %d %d", &legal, &cells, &vir, &ch, &imm, &sco, &win) != 7) return 2;
    for (int i = 0; i < 128; i++) if (fscanf(g, "%x", &nb[i]) != 1) return 2;

    t->wslot = 0;
    for (int i = 0; i < 128; i++) {
      t->wr = 1; t->waddr = i; t->wdata = enc_of(b[i]); t->wlnk = lnk_of(b[i]); tick();
    }
    t->wr = 0;
    t->a_o4 = o4; t->a_col = col; t->a_ca = ca + 1; t->a_cb = cb + 1; t->a_fix = fix;
    t->a_chw = chw;
    if (ch > 1) { n_chained++; if (chw) imm += chw * 4 * (ch - 1); }
    t->cmd = 4; t->cmd_go = 1; tick(); t->cmd_go = 0;
    long cyc = 0;
    while (!t->done && cyc < 2000000) { tick(); cyc++; }
    if (cyc > worst[fix]) worst[fix] = cyc;
    tot[fix] += cyc; cnt[fix]++;

    bool ok = t->done && (int)t->legal == legal;
    if (!ok) bad_legal++;
    if (ok && legal) {
      checked++;
      if ((int)t->rv_cells != cells) { bad_cells++; ok = false; }
      if ((int)t->rv_vir != vir)     { bad_vir++;   ok = false; }
      if ((int)t->chain != ch)       { bad_chain++; ok = false; }
      if ((int)t->imm != imm)        { bad_imm++;   ok = false; }
      if ((int)t->win != win)        { bad_win++;   ok = false; }
      if (!win && (unsigned short)t->sco != (unsigned short)sco) { bad_sco++; ok = false; }
      bool cbad = false, lbad = false;
      for (int i = 0; i < 128; i++) {
        if ((int)t->rootp->LeafEval__DOT__bcell[i] != enc_of(nb[i])) cbad = true;
        if ((int)t->rootp->LeafEval__DOT__blink[i] != lnk_of(nb[i])) lbad = true;
      }
      if (cbad) { bad_col++;  ok = false; }
      if (lbad) { bad_link++; ok = false; }
    }
    if (ok) pass++;
    else if (shown < 8) {
      shown++;
      printf("case %d MISMATCH fix=%d o4=%d col=%d: legal %d/%d cells %d/%d vir %d/%d "
             "chain %d/%d imm %d/%d sco %d/%d win %d/%d\n",
             k, fix, o4, col, (int)t->legal, legal, (int)t->rv_cells, cells,
             (int)t->rv_vir, vir, (int)t->chain, ch, (int)t->imm, imm,
             (int)(unsigned short)t->sco, sco, (int)t->win, win);
    }
  }
  fclose(g);

  printf("\n=========== LINK/CHAIN NODE CO-SIM ===========\n");
  printf("cases            : %d   (legal+checked %d)   DRCHAIN dose %d\n",
         n, checked, chw * 4);
  printf("PASS             : %d/%d\n", pass, n);
  printf("  legal mismatch : %d\n", bad_legal);
  printf("  cells          : %d\n", bad_cells);
  printf("  viruses        : %d\n", bad_vir);
  printf("  CHAIN depth    : %d\n", bad_chain);
  printf("  imm            : %d\n", bad_imm);
  printf("  sco            : %d\n", bad_sco);
  printf("  win            : %d\n", bad_win);
  printf("  COLOUR plane   : %d\n", bad_col);
  printf("  LINK plane     : %d\n", bad_link);
  for (int f = 0; f < 2; f++)
    if (cnt[f])
      printf("latency %s : mean %ld  worst %ld cycles  (n=%ld)\n",
             f ? "fixpoint" : "cap-1   ", tot[f] / cnt[f], worst[f], cnt[f]);
  printf("cases with chain > 1 : %d\n", n_chained);
  // Invariant witness for the link-RAM write-forward bypass. The collision FIRES often;
  // what must stay zero is the number a consumer actually latches -- if that moves, a
  // read-latency bubble was removed and the bypass became load-bearing.
  {
    unsigned fired = (unsigned)t->rootp->LeafEval__DOT__byp_fire;
    unsigned used  = (unsigned)t->rootp->LeafEval__DOT__byp_used;
    printf("bypass collisions    : %u fired, %u latched by a consumer%s\n",
           fired, used, used ? "   <-- BYPASS IS NOW LOAD-BEARING" : "");
    if (used) { printf("\nOVERALL: FAIL (bypass invariant broken)\n"); delete t; return 1; }
  }
  // A dose run over a corpus with no cascades checks nothing: the reward term is only
  // live when chain > 1, so it would pass whether the RTL implemented it or not.
  if (chw && n_chained == 0) {
    printf("\nOVERALL: FAIL (VACUOUS -- dose %d checked against a corpus containing no "
           "chains; the reward term was never exercised)\n", chw * 4);
    delete t;
    return 1;
  }
  printf("\nOVERALL: %s\n", pass == n ? "PASS" : "FAIL");
  delete t;
  return pass == n ? 0 : 1;
}
