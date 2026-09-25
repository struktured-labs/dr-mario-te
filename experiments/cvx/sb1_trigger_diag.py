"""SB1 trigger diagnostic: replay every fw540 gate-(b) tap-out through StallBreakerDecider with ZERO dig
effect (dig_chain=540, dig_sp=0, dig_nv=0 -> must be byte-identical to the banked fw540 row) and log
whether the dig condition (stall>=8 AND spawn lane>=11) held in the last 12 pills. Also paired fix/new
tap-out counts per dig arm. Writes sb1_trigger_diag.json next to this file."""
import sys, os, json, glob
CVX = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CVX)
import import_pin; import_pin.pin()
import gate_b as G, vs_race as V, bursty_model as BM, cascade_dig_x as DG, fast_rtl_x as FX, cascade_chain_x as C
os.chdir(CVX)
C.warmup_chain(topk2=8)
m = BM.fit_struktured_20260804()
base = {}
for f in glob.glob("gateb/fw540_*.jsonl"):
    for l in open(f): r = json.loads(l); base[r["seed"]] = r
def arm_rows(a):
    d = {}
    for f in glob.glob(f"gateb/{a}_*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == a: d[r["seed"]] = r          # sb_all_* glob also matches sb_all_early
    return d
seeds = sorted(s for s, r in base.items() if r["topout"])
print("fw540 tap-out seeds:", len(seeds))
for arm in ("sb_chain0", "sb_spawn", "sb_virus", "sb_all", "sb_all_early"):
    d = arm_rows(arm)
    fixed = [s for s in seeds if s in d and not d[s]["topout"]]
    new = [s for s, r in d.items() if r["topout"] and s in base and not base[s]["topout"]]
    print(f"  {arm}: fixes {len(fixed)} of {len(seeds)} fw540 tap-outs, introduces {len(new)} new")
w, fl = FX.variant("winner")
out = []
for s in seeds:
    dec = DG.StallBreakerDecider(w, fl, w_chain=540, ws=20, S=8, H=11, dig_chain=540, dig_sp=0, dig_nv=0)
    trace = []
    def choose(env, col, vir, ctx, dec=dec, trace=trace):
        a = dec.choose(env.board, env.cur, env.nxt)
        trace.append((dec.stall, int(DG._spawn_h(DG.board_flat(env.board)[0])), int(env.board.virus_count())))
        return a
    r = G.play(s, None, m, choose=choose)
    r.update({"arm": "fw540", "model": "owner", "trate": 0.0})
    same = json.dumps(r, sort_keys=True) == json.dumps(base[s], sort_keys=True)
    last = trace[-12:]
    dig_last = [st >= 8 and h >= 11 for st, h, v in last]
    out.append(dict(seed=s, identical=same, pills=len(trace), vleft=r["vleft"], dig_any_last12=any(dig_last),
                    dig_pills_total=sum(st >= 8 and h >= 11 for st, h, v in trace),
                    max_stall_last12=max(st for st, h, v in last), spawn_h_last12=[h for st, h, v in last]))
    print(json.dumps(out[-1]))
print("identical to banked fw540:", sum(o["identical"] for o in out), "/", len(out))
print("dig condition true in last 12 pills:", sum(o["dig_any_last12"] for o in out), "/", len(out))
json.dump(out, open(os.path.join(CVX, "sb1_trigger_diag.json"), "w"), indent=1)
