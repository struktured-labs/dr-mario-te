#!/usr/bin/env python3
"""Garbage-window compute BUDGET TABLE.

Currency is COPRO CLOCK CYCLES, because that is the one unit that survives the
clock-domain trap: the same decision costs the same number of cycles on MiSTer
and on Pocket, and only the frames-per-cycle conversion differs (1.57x).
See dr-mario-cosim-farm-turnbased: "store raw clocks, convert at analysis time".

INPUT (MEASURED): /mnt/data/drmario_cosim/results/prestart_pilot.jsonl
  1500 real per-decision copro-cycle costs from the Verilator co-sim farm running
  the real champion firmware (fw_md5 e970e9ab0208cdbce1d39ed33e2f51ee), 10 games,
  arm pilot_s20b_drop_bursty.  lat = [raw_clocks, entry_row, max_h, post_garbage, h_hit].

CITED constants:
  W(h) = 264 - 16h frames             ROM-derived, emulator-verified 8/8
                                      (dr-mario-garbage-window-mechanics)
  NTSC 60.0988 Hz
  Pocket copro tap 54.66935836 MHz    PLL IP confirmed, a0d5190f lineage
  MiSTer copro tap 85.909088 MHz      PLL IP confirmed at build commit 7f6ba69
"""
import json, sys

PILOT = "/mnt/data/drmario_cosim/results/prestart_pilot.jsonl"
NTSC = 60.0988
HZ = {"pocket": 54_669_358.36, "mister": 85_909_088.0}


def load():
    lat = []
    for line in open(PILOT):
        lat.extend(json.loads(line)["lat"])
    return lat


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))]


def main():
    lat = load()
    allc = sorted(t[0] for t in lat)
    pg = [t for t in lat if t[3] == 1]
    pgc = sorted(t[0] for t in pg)
    C50, C90 = pct(allc, 0.50), pct(allc, 0.90)

    print("## Champion decision cost, MEASURED (copro cycles)\n")
    print("| population | n | p10 | median | p90 | p99 | max |")
    print("|---|---|---|---|---|---|---|")
    for name, v in (("all decisions", allc), ("post-garbage only", pgc)):
        print("| %s | %d | %.1f M | **%.1f M** | %.1f M | %.1f M | %.1f M |" % (
            name, len(v), pct(v, .10)/1e6, pct(v, .50)/1e6,
            pct(v, .90)/1e6, pct(v, .99)/1e6, v[-1]/1e6))

    # empirical h_hit distribution of releases
    from collections import Counter
    hc = Counter(t[4] for t in pg)
    tot = sum(hc.values())

    for dom in ("pocket", "mister"):
        cpf = HZ[dom] / NTSC
        print("\n## Window budget at the %s copro tap (%.6f MHz, %.0f cycles/frame)\n"
              % (dom.upper(), HZ[dom]/1e6, cpf))
        print("| h | W (f) | W (cycles) | releases | budget @ median cost | "
              "budget @ p90 cost | EXTRA searches after the mandatory post-garbage one |")
        print("|---|---|---|---|---|---|---|")
        for h in list(range(0, 17)):
            wf = 264 - 16*h
            wc = wf * cpf
            n50, n90 = wc / C50, wc / C90
            share = "%.1f%%" % (100.0*hc.get(h, 0)/tot) if tot else "-"
            print("| %d | %d | %.1f M | %s | %.2f | %.2f | **%.2f** |"
                  % (h, wf, wc/1e6, share, n50, n90, max(0.0, n50 - 1.0)))

    print("\n(`releases` = share of the 208 MEASURED post-garbage decisions whose "
          "h_hit was that value; small-n, see caveats.)")

    # candidate-computation cost ladder
    print("\n## Cost of candidate computations, in the same currency\n")
    Cm = C50
    ladder = [
        ("(a) linear tail term, per-feature LUT in 6502 firmware "
         "(19 table reads + 19 adds x 32 candidates, ~12 cyc each)", 32*19*12, "DERIVED"),
        ("(a') same term in RTL beside LeafEval "
         "(Stage-2 precedent: 8 reads + 8 adds = 18 of 250 cycles)", 32*40, "DERIVED"),
        ("base post-garbage re-search (1 champion decision) -- MANDATORY", Cm, "MEASURED"),
        ("(b) 2-candidate x 1 extra ply (known next capsule, no sampling)", 2*Cm, "DERIVED"),
        ("(b+) the above PLUS the mandatory base search", 3*Cm, "DERIVED"),
        ("(c) top-4 x 1 extra ply + base", 5*Cm, "DERIVED"),
        ("(c') H12 as certified: topk 4 x fork_samples 5 x horizon 15", 300*Cm, "DERIVED"),
    ]
    cpf_p = HZ["pocket"] / NTSC
    print("| computation | cycles | Pocket frames | largest h that still fits | label |")
    print("|---|---|---|---|---|")
    for name, cyc, lab in ladder:
        f = cyc / cpf_p
        hmax = None
        for h in range(0, 17):
            if (264 - 16*h) >= f:
                hmax = h
        hs = ("h <= %d" % hmax) if hmax is not None else "**never** (exceeds even h=0)"
        print("| %s | %.3g | %.1f | %s | %s |" % (name, cyc, f, hs, lab))

    print("\nC_median = %.1f M cycles = %.1f Pocket frames = %.1f MiSTer frames"
          % (Cm/1e6, Cm/(HZ['pocket']/NTSC), Cm/(HZ['mister']/NTSC)))
    print("C_p90    = %.1f M cycles = %.1f Pocket frames" % (C90/1e6, C90/(HZ['pocket']/NTSC)))


if __name__ == "__main__":
    main()
