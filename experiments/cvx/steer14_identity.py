"""STEER14 identity gate (PREREG_STEER14.md sec. 2); reads only steer14/gate/ and STEER13's banked rows.
  IDENTITY     S14_id_v116 (slam gate OFF) == STEER13 B_v116_qb (lulu 50, owner race 25, gate b 25 seeds) on EVERY key
               except the stamps ("arm", "rig").
  CONSISTENCY  C13_14886 (fw 1488, KOPEN 32) IS the tempo reference: tempo charged 0 on every pill.
  DETERMINISM  S14_d4_k32 run twice on the same seeds: identical rows (rule 30).
  POSITIVE     S14_d16_k32 rows differ from S14_d4_k32 rows on >= 1 seed (prints a COUNT only, no outcome).
  SMOKES       every slam arm active: DOWN via DONE > 0 and via stability > 0 (summed over the file's rows), anytime
               (non-final commits or late publishes) > 0; q 2 % arms: misses > 0; A16 arms: target on > 0; endgame cuts:
               stability slams below 10 viruses > 0; race rows: the garbage-drop wrap fired (> 0). Every row:
               LULU rows carry the probe with ndec in {dec, dec + 1} (R100); a passing jit guard with the pre-registered sha.
Exit 0 = PASS. Writes steer14/gate/identity.txt.
"""
import json, glob, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import steer14_run as R

lines = []


def out(s):
    print(s); lines.append(s)


def load(pat, lab=None):
    d = {}
    for f in glob.glob(pat):
        for l in open(f):
            r = json.loads(l)
            if lab is None or r.get("arm") == lab:
                d[r["seed"]] = r
    return d


ok = True
for cell, gp, bp, sfx, n_need in (("lulu", "id_lulu", "lulu13", "~steer", 50), ("rc", "id_rc", "rc13", "~steer", 25),
                                  ("gb", "id_gb", "gb13", "@owner202610", 25)):
    G = load(f"steer14/gate/{gp}_S14_id_v116.jsonl", "S14_id_v116" + sfx)
    B = load(f"steer13/main/{bp}_B_v116_qb_*.jsonl", "B_v116_qb" + sfx)
    both = sorted(s for s in G if s in B)
    bad = [(s, [k for k in set(B[s]) | set(G[s]) if k not in ("arm", "rig") and G[s].get(k) != B[s].get(k)]) for s in both]
    bad = [x for x in bad if x[1]]
    good = len(both) == n_need and not bad
    ok &= good
    out(f"IDENTITY S14_id_v116 (slam off) == STEER13 B_v116_qb ({cell}): {len(both) - len(bad)}/{len(both)} identical "
        f"(need {n_need})" + (f"  DIFF {bad[:2]}" if bad else "") + f" -> {'ok' if good else 'FAIL'}")
C = load("steer14/gate/cons_lulu_C13_14886.jsonl")
cons = len(C) == 10 and all(r["knob"]["tempo_f"] == 0 for r in C.values())
ok &= cons
out(f"CONSISTENCY C13_14886 tempo charged {[r['knob']['tempo_f'] for r in C.values()]} (all must be 0) -> {'ok' if cons else 'FAIL'}")
A1, A2 = load("steer14/gate/det1_lulu_S14_d4_k32.jsonl"), load("steer14/gate/det2_lulu_S14_d4_k32.jsonl")
det = len(A1) == 10 and all({k: v for k, v in A1[s].items() if k != "rig"} == {k: v for k, v in A2[s].items() if k != "rig"}
                            for s in A1)
ok &= det
out(f"DETERMINISM S14_d4_k32 twice on 10 seeds: {'identical' if det else 'DIFFERENT -> FAIL'}")
P = load("steer14/gate/pc_lulu_S14_d16_k32.jsonl")
both = sorted(s for s in P if s in A1)
nd = sum(1 for s in both if any(P[s].get(k) != A1[s].get(k) for k in A1[s] if k not in ("arm", "rig", "rule")))
tg = (sum(P[s]["rule"]["tgt_on"] for s in both), sum(A1[s]["rule"]["tgt_on"] for s in both))
ok &= nd > 0 and len(both) == 10
out(f"POSITIVE CONTROL S14_d16_k32 vs S14_d4_k32 (must differ): {nd}/{len(both)} rows differ; target-on decisions "
    f"{tg[0]} vs {tg[1]}")
for f in sorted(glob.glob("steer14/gate/*.jsonl")):
    rows = [json.loads(l) for l in open(f)]
    for r in rows:
        g = r["rig"]["guard"]
        gok = g["sha"] == R.GUARD_SHA and g["meta_bad"] == 0 and g["out_diff"] == 0 and g["mid_diff"] > 0
        if r["rig"].get("probe"):
            pok = "stuck" in r and r["stuck"]["ndec"] in (r["knob"]["dec"], r["knob"]["dec"] + 1)
        else:
            pok = "stuck" not in r
        ok &= gok and pok
        if not (gok and pok):
            out(f"ROW CHECK FAIL {os.path.basename(f)} seed {r['seed']}: guard {gok} probe {pok}")
    spec = rows[0]["rig"]["knob"]
    if not spec.get("slam"):
        continue
    k = {kk: sum(r["knob"][kk] for r in rows) for kk in rows[0]["knob"]}
    acts = {"down via DONE": k["down_done"] > 0, "down via stability": k["down_stab"] > 0,
            "anytime": k["nonfinal_commit"] > 0 or k["late"] > 0}
    if spec["q"] > 0:
        acts["miss"] = k["miss"] > 0
    if spec["rule"] == "s10_A16":
        acts["A16 tgt_on"] = sum(r["rule"]["tgt_on"] for r in rows) > 0
    if spec["kend"] < 255 or spec["vcend"] < 10:              # an ENDGAME cut: stability slams below 10 viruses
        acts["endgame stability slams"] = k["end_down_stab"] > 0
    if f.endswith("_rc_S14_d16_e16.jsonl") or "_lulu_" in f:
        acts["garbage wrap live"] = k["garb_events"] > 0
    act = all(acts.values())
    ok &= act
    out(f"SMOKE {os.path.basename(f)} ({len(rows)} rows): disarmed {k['disarmed']} (ref {k['ref_disarmed']}), DOWN via DONE "
        f"{k['down_done']} / stability {k['down_stab']} / none {k['no_down']}, endgame pills {k['end_pills']} (stability slams "
        f"{k['end_down_stab']}), garbage events {k['garb_events']}, checks {acts} -> {'active' if act else 'FAIL'}")
out(f"guard sha in every gate row == GUARD_SHA {R.GUARD_SHA}")
out("STEER14 IDENTITY GATE " + ("PASS" if ok else "FAIL"))
open("steer14/gate/identity.txt", "w").write("\n".join(lines) + "\n")
sys.exit(0 if ok else 1)
