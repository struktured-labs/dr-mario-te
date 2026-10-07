"""silfid: predict PUBLOG capture #2's tall-endgame coverage in the FAIR sim (no hardware).

  [PUMP_Q=q] pump_sim.py LEVEL LAM LO CNT STEP OUT.jsonl

FAIR = the STEER10/11/12 `s10_base` arm verbatim (steer10_run.make: the FAIR couch driver's decider + timing + unified
TAP-2 steering), played by stuck_probe.play_race to ITS OWN END (clear / top-out / cap) on the couch-calibrated clock
(steer11 clock_couch11.json, fitted on FAIR silicon), against a Poisson volley stream of LAM volleys/min with dr. lulu's
10/05 size mix (steer10 SIZES lulu202610b). This is the DRP1HOLD + DRGPUMP seat exactly: P1 never wins, garbage
arrives at LAM/min. LAM 0 = DRP1HOLD alone.
Each row: seed, level, lam, how, t_end, pills, vleft, sent/recv, and `trace` = [t_s, viruses, maxh] at every decision
(before the placement, i.e. at GO -- the same point the capture's upload and the couch cases are measured at).
PUMP_Q > 0 adds STEER12's silicon-like execution misses (steer12_run.Knob kind "miss": with probability q per pill the
steering model is handed a random other reachable root) -- sim FAIR otherwise executes almost perfectly, while the
silicon couch AI did not (18% of its 10/05 pills were not the brain's choice).
Truncations for the calibration anchors (CvC capture #1: P1 wins; couch: dr. lulu finishes) are applied post hoc by
pump_an.py. Seeds: the STEER10 LULU block (declared reuse -- a coverage prediction, not a confirmatory test)."""
import sys, os, json, hashlib
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0, CVX)
os.chdir(CVX)
import import_pin; import_pin.pin()
import steer10_run as S10
import steer11_run as S11
import stuck_probe as SP
import vs_race as V
from fb import FB
import root_search as RS

_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]


class CellProbe:
    """Records (t, viruses, maxh) at every decision; maxh = 16 - (top occupied row), the capture's definition."""
    def __init__(self):
        self.tr = []

    def pre_decision(self, board, cur, k, t, mask_fn):
        fb = FB.from_board(board); col, vir = RS.board_flat_from_fb(fb)
        h = 0
        for c in range(8):
            for r in range(16):
                if col[r * 8 + c] != 0:
                    h = max(h, 16 - r); break
        self.tr.append((round(t, 2), int(board.virus_count()), h))

    def post_own(self, board):
        pass

    def finish(self, how, n, t):
        return self.tr


def main():
    level, lam = int(sys.argv[1]), float(sys.argv[2])
    lo, cnt, step, outp = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    V.SIZES = S10.SIZES["lulu202610b"]
    V.CLOCK = S11.load_clock("couch11")
    steer, choose, dec = S10.make("s10_base")
    q = float(os.environ.get("PUMP_Q", "0"))
    if q > 0:                                  # STEER12's silicon-like execution misses: a random other reachable root
        import steer12_run as S12              # with probability q per pill (Knob wraps FAIR's Steer; V.CLOCK set above)
        steer = S12.Knob(steer, dict(kind="miss", q=q), race=True)
    zero = lambda: {k: 0 for k in dec.stats}
    with open(outp, "w") as fh:
        for i in range(cnt):
            dec.stats = zero()
            pr = CellProbe()
            r = SP.play_race(lo + i * step, "s10_base", lam, level=level, maxpills=900, steer=steer, probe=pr,
                             choose=choose)
            trace = r.pop("stuck")
            r.pop("steer", None)
            r.update(level=level, lam=lam, q=q, trace=trace, sha=_SHA, sizes="lulu202610b", clock="couch11")
            fh.write(json.dumps(r) + "\n"); fh.flush()


if __name__ == "__main__":
    main()
