#!/usr/bin/env python3
"""G3 TIER-1 margin assembler -- the Sept-3 GO/NO-GO numbers.

Inputs (all MEASURED unless tagged):
  run_s*/out.txt          first-valid-pub + DONE clocks per scenario (real RTL,
                          ship hex a2b2e4ac, Verilator lockstep)
  rom_measurements*.json  gravity law W=EU[base+ups]+1, DAS 2/16/6, press
                          deadline W-2, edge-burn, P2 ywrite head start ~1f
  rom_geometry.json       one-edge un-ledge truth per board class
Clock domains ([[dr-mario-cosim-farm-turnbased]]): copro cycles are the
invariant; silicon tap 54.669 MHz -> 909652.11 clk/frame (BINDING); the sim's
48x-NES lockstep (85.909 MHz -> 1429468 clk/frame) is reported for reference.

Driver pipeline (MEASURED from patch_cartridge_copro.py + the 2-hooks/frame
audit at :97-115): detect <=1 hook after Y-write; DELAY2=15 hooks settle
(:1578-1580) = 7.5f; upload+GO on the 16th hook = ~8f; adopt <=0.5f (hook
poll); press->edge +1..2f (measured E2/E3).  P2 Y-write precedes the slide
window by ~1f (E6), so T_go ~ 7.5f +/- 1 after window open.
"""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SIL_CLK_F = 54.669e6 / 60.0988          # 909652.11
SIM_CLK_F = 48 * 1789773 / 60.0988      # 1429468.5

T_GO = 7.5          # frames after slide-window open (+-1)
T_ADOPT = 0.5
PRESS_DEADLINE_OFF = 2                  # press must land by W-2 (E3)
FIXB_SPEC_PRESS = T_GO + 1.0            # spec waits PEND2==0 (post-GO) + invalidate + hook
FIXB_AMEND_PRESS = 1.5                  # fire from first hook after detect (settle window)

REGIMES = [("fresh MED ups0", 20), ("mid MED ups5", 15), ("owner-endgame ups10", 10),
           ("late ups15", 8), ("floor ups20+", 6)]

def parse_runs():
    out = {}
    for f in glob.glob(os.path.join(HERE, "run_s*/out.txt")):
        for line in open(f):
            m = re.match(r"CASE (\S+) final=(-?\d+),(-?\d+) done=(\d+) b4zero=\d+ "
                         r"b4one=\d+ cmd4viol=\d+ pubs=(\S+) clocks=(\d+) "
                         r"doneclk=(-?\d+) timeout=(\d+)", line)
            if not m: continue
            name = m.group(1)
            pubs = []
            if m.group(5) != "-":
                for p in m.group(5).rstrip(";").split(";"):
                    c, o, v, ph, clk = p.split(":")
                    pubs.append((int(c), int(o), int(v), ph, int(clk)))
            spubs = [p for p in pubs if p[3] == "s"]
            first = spubs[0] if spubs else (pubs[0] if pubs else None)
            out[name] = dict(final=(int(m.group(2)), int(m.group(3))),
                             firstpub_clk=first[4] if first else None,
                             firstpub_col=first[0] if first else None,
                             done_clk=int(m.group(7)), timeout=int(m.group(8)))
    return out

def board_of(name):
    """fo profile per scenario, from the generator's definitions."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("g", os.path.join(HERE, "gen_g3_cases.py"))
    return None  # fo comes from the case files instead

def fo_from_case_files():
    fos = {}
    for f in glob.glob(os.path.join(HERE, "g3cases_*.txt")):
        lines = open(f).read().split("\n")
        i = 1
        while i + 1 < len(lines) and lines[i].strip():
            name = lines[i].split()[0]
            b = [int(x, 16) for x in lines[i + 1].split()]
            fo = [min([r for r in range(16) if b[r * 8 + c] != 0xFF], default=16)
                  for c in range(8)]
            fos[name] = fo
            i += 2
    return fos

def geometry(fo):
    """rest row + one-edge escape per side, mirror of the verified rom_geometry runs."""
    r = min(fo[3], fo[4]) - 1
    if r < 0: r = 0
    def side(a, b):        # capsule cells after one edge -> cols (a,b)
        if fo[a] <= r or fo[b] <= r: return False          # move blocked
        return fo[a] > r + 1 and fo[b] > r + 1             # falls after the edge
    return dict(rest_row=r, one_edge_L=side(2, 3), one_edge_R=side(4, 5),
                spawn_rest=min(fo[3], fo[4]) <= 2)

def classify(pub_f, geo, W):
    press_deadline = W - PRESS_DEADLINE_OFF
    steer_press = T_GO + pub_f + T_ADOPT
    one_edge = geo["one_edge_L"] or geo["one_edge_R"]
    tier1 = steer_press <= press_deadline                      # (i) answer beats window
    fixb_spec = one_edge and FIXB_SPEC_PRESS <= press_deadline
    fixb_amend = one_edge and FIXB_AMEND_PRESS <= press_deadline
    return tier1, fixb_spec, fixb_amend

def main():
    runs = parse_runs()
    fos = fo_from_case_files()
    rows = []
    for name, r in sorted(runs.items()):
        if r["firstpub_clk"] is None: continue
        pub_f = r["firstpub_clk"] / SIL_CLK_F
        pub_f_sim = r["firstpub_clk"] / SIM_CLK_F
        done_f = r["done_clk"] / SIL_CLK_F
        geo = geometry(fos[name])
        rows.append(dict(name=name, pub_f=round(pub_f, 2), pub_f_sim=round(pub_f_sim, 2),
                         done_f=round(done_f, 1), firstpub_col=r["firstpub_col"],
                         final_col=r["final"][0], agree=r["firstpub_col"] == r["final"][0],
                         **geo))
    print(f"{'scenario':22s} {'pub_f(sil)':>10s} {'done_f':>7s} {'1edgeL/R':>9s} "
          f"{'agree':>5s}")
    for w in rows:
        print(f"{w['name']:22s} {w['pub_f']:10.2f} {w['done_f']:7.1f} "
              f"{str(w['one_edge_L'])[0]}/{str(w['one_edge_R'])[0]:>7s} "
              f"{str(w['agree'])[0]:>5s}")
    print()
    table = {}
    for label, W in REGIMES:
        n = len(rows)
        t1 = sum(classify(w["pub_f"], w, W)[0] for w in rows)
        fs = sum(classify(w["pub_f"], w, W)[1] and not classify(w["pub_f"], w, W)[0]
                 for w in rows)
        fa = sum(classify(w["pub_f"], w, W)[2] and not classify(w["pub_f"], w, W)[0]
                 for w in rows)
        none_a = n - t1 - fa
        table[label] = dict(W=W, n=n, i_answer=t1, ii_fixb_spec=fs, ii_fixb_amend=fa,
                            iii_nothing_amend=none_a)
        print(f"{label:22s} W={W:2d}: (i) answer-in-time {t1}/{n}  "
              f"(ii) FixB-spec +{fs}  FixB-amended +{fa}  (iii) left {none_a}")
    json.dump(dict(rows=rows, table=table), open(os.path.join(HERE, "margins.json"), "w"),
              indent=1, default=lambda o: bool(o))
    print("\nwrote margins.json")

if __name__ == "__main__":
    main()
