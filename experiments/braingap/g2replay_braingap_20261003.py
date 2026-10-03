#!/usr/bin/env python3
"""Re-run the 10/03 G2 counterfactuals (couch_forensics/g2_counterfactual_dist60_20261003.py) with the SILICON-FAITHFUL
brain (Leaf6FwDecider, every firmware switch on) next to the python sim brain it replaced:
  (1) brain-only replay: observed capsules + observed garbage, perfect execution, from P0
  (2) the steering-model replay (steer_model, 20 latency seeds) from P0, if --steer
The 9/25-style conclusion "the brain alone clears the board, so the death was execution" was drawn with the python
brain; this asks whether silicon's own brain clears it too.
Usage: g2replay_braingap_20261003.py OUT.txt [--steer N_SEEDS] [p0 ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlengine_braingap_20261003 as E  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as F  # noqa: E402

CF = E.H16 + "/experiments/couch_forensics"
sys.path.insert(0, CF)
os.chdir(CF)
import g2_counterfactual_dist60_20261003 as GC  # noqa: E402
import json  # noqa: E402


def main():
    out = os.path.join(HERE, os.path.basename(sys.argv[1])) if not os.path.isabs(sys.argv[1]) else sys.argv[1]
    args = sys.argv[2:]
    nseed = 0
    if "--steer" in args:
        i = args.index("--steer"); nseed = int(args[i + 1]); del args[i:i + 2]
    p0s = [int(x) for x in args] or [0, 31, 59, 90]
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)
    brains = {"python": F.Leaf6FwDecider(w, fl, sw=dict(veto=0, hang=0, ehb1=0, ehnp=0, wrap=0, order=0), **kw),
              "silicon": F.Leaf6FwDecider(w, fl, sw=None, **kw),
              "eh_fix_only": F.Leaf6FwDecider(w, fl, sw=dict(veto=0, hang=1, ehb1=1, ehnp=1, wrap=0, order=0), **kw)}
    keep = os.environ.get("BRAINS")
    if keep:
        brains = {k: v for k, v in brains.items() if k in keep.split(",")}
    Q = [json.loads(l) for l in open(GC.CASES)]
    idx = {q["p"]: i for i, q in enumerate(Q)}
    with open(out, "w") as fh:
        def say(s):
            print(s, flush=True); fh.write(s + "\n"); fh.flush()
        say("=== brain-only replay (observed capsules + observed garbage, perfect execution) ===")
        for p0 in ([] if os.environ.get("STEER_ONLY") else p0s):
            for name, dec in brains.items():
                R = GC.replay(Q, dec, idx[p0])
                last = R[-1]
                vir = [v for (_p, _s, v, _h) in R]
                say(f"from p{p0:3d} {name:12s}: {len(R):3d} pills -> {last[1]:6s} at p{last[0]} viruses {last[2]} "
                    f"maxh {max(last[3])} | viruses at p+10/20/40: "
                    + " ".join(str(vir[j]) if j < len(vir) else "-" for j in (10, 20, 40)))
        if nseed:
            say(f"=== steering-model replay ({nseed} latency seeds) ===")
            for p0 in p0s:
                for name, dec in brains.items():
                    res = [GC.steer_replay(Q, dec, idx[p0], s) for s in range(nseed)]
                    outc = {}
                    for r in res:
                        outc[r[1]] = outc.get(r[1], 0) + 1
                    say(f"from p{p0:3d} {name:12s}: outcomes {outc}; viruses at end {sorted(r[2] for r in res)}; "
                        f"top-out pills {sorted(r[0] for r in res if r[1] == 'TOPOUT')}")


if __name__ == "__main__":
    main()
