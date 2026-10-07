"""STEER14 analysis (PREREG_STEER14.md). Withholds every contrast of a part until all of that part's rows exist (R97).

  python analyze_steer14.py               -> steer14/analysis.txt (part R, then the main parts)
  python analyze_steer14.py --rederive    -> part R only (it runs first in the farm) -> steer14/analysis_R.txt
  python analyze_steer14.py --status      -> ROW COUNTS ONLY (blind; the only mode run while the farm is live)
  python analyze_steer14.py --selftest    -> killed-mutant check of every decision rule (no data read)

The descent model is the cart's DRSLAM gate (steer_model.execute(slam=...), Knob14), fw V11, MIN_THINK 6 f.
PART R  STEER13's V11-vs-1488 re-derived: C13_v116 - C13_14886 (both KOPEN 32) on STEER13's own seeds (LULU 1,600;
        owner race + gate b 600), 95 %, churn; beside STEER13's own contrast on the same seeds (+17.44) and the
        SURVIVAL ratio corrected / STEER13 (seed bootstrap).
PART M  2x2 {D4 = DIST gate vk 4 (today), D16 = A16} x {K32 = today's slam gate (KOPEN 32, KEND 255, VCEND 10), KC = the
        gate cut G* from the stage-1 screen (steer14_cal_read.py: a KOPEN, endgame KEND / VCEND, or uniform cut)}.
  PRIMARY  LULU race win at dr. lulu's measured M 167.5 (delta 2.65, sigma 0.15), n = 5,100 paired seeds, seed
           bootstrap, Bonferroni over K = 4 contrasts:
             (i)   D16 K32 - D4 K32           A16 at today's gate
             (ii)  D16 KC  - D4 KC            A16 at the gate cut
             (iii) D16 KC  - D4 K32           the COMBINED CANDIDATE vs today's FAIR2PLUS-equivalent
             (iv)  (ii) - (i), per seed       the interaction
           HELPS / HURTS iff the Bonferroni CI excludes 0; otherwise n.s. (never "no effect").
  GUARDS   gate-b tap-out (n = 1,000; harm = up), owner race at M 239.5 (n = 1,000; harm = down), for (i)-(iii);
           harm iff the Bonferroni CI over 2 guards x 3 contrasts = 6 excludes 0 on the bad side.
  VERDICTS (iii) CERTIFIED iff its Bonferroni lower > 0 AND no guard harm on (iii).
           (i), (ii) A16 ADDS VALUE iff Bonferroni lower > 0 AND no guard harm; A16 HURTS iff Bonferroni upper < 0 OR
           guard harm; otherwise A16 NOT ESTABLISHED.
           (iv) POSITIVE / NEGATIVE interaction iff its Bonferroni CI excludes 0; otherwise none established (+ MDE).
  ALSO     churn beside every net delta; absolute loss (slow / kill) per arm; activity (non-final commits, late,
           adoptions, refusals, landed on the final, tempo f/pill, disarmed pills, DOWN via DONE / stability / none, DIST
           target-on share); STALLS as STEER13 part A; LULU-race tap-out; gate-b tap<=100; reference D4 KC - D4 K32 (the
           gate cut alone); SENSITIVITY (iii) at q 2 % (n = 2,000, 95 %).
PART D  slam-gate dose-response (DIST4, LULU, the first 600 seeds; K32 / G* rows reused on those seeds): every screened
        configuration, delta vs K32 (95 %), tempo, GO->lock (all / endgame pills), landed on the final, disarmed. Descriptive.
Every arm's activity line carries GO->lock per pill and per ENDGAME pill (< 10 viruses) beside today's cart on the same
pills, and the SLAM_ARM disarm rate (arm and reference).
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer6r import boot, fmt, churn
from vs_race import evaluate
import steer12_stallcal as SC
import steer14_jobs as J

M_LULU, M_OWNER, DELTA, SIGMA = 167.5, 239.5, 2.65, 0.15
K_PRIM, K_GUARD = 4, 6
Pc = lambda K: (100 * 0.05 / K / 2, 100 - 100 * 0.05 / K / 2)
OUT = "steer14/analysis.txt"
OUT_R = "steer14/analysis_R.txt"
MAIN_DIR = "steer14/main"                 # steer14_kat.py points these at a synthetic known-answer bank
S13_DIR = "steer13/main"
RESULTS = {}                              # every contrast() by label (steer14_kat.py compares them to known answers)


def load(pattern, label, seeds):
    out = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label:
                out[r["seed"]] = r
    return {s: out[s] for s in seeds if s in out}


def win(r, M):
    return int(evaluate(r, M, SIGMA, DELTA)[0] == "win_race")


def ltype(r, M):
    o = evaluate(r, M, SIGMA, DELTA)[0]
    return {"win_race": "win", "loss_race": "slow", "loss_cap": "slow", "loss_kill": "kill"}[o]


# ------------------------------------------------------------------------------------------------- decision rules
def cls(ci):
    return "HELPS" if ci[1] > 0 else ("HURTS" if ci[2] < 0 else "n.s.")


def harm(tap_b, rc_b):
    """guard harm: gate-b tap-out UP (Bonferroni lower > 0) or owner race win DOWN (Bonferroni upper < 0)"""
    return tap_b[1] > 0 or rc_b[2] < 0


def verdict_iii(prim_b, tap_b, rc_b):
    return "CERTIFIED" if (prim_b[1] > 0 and not harm(tap_b, rc_b)) else "NOT CERTIFIED"


def verdict_a16(prim_b, tap_b, rc_b):
    if prim_b[2] < 0 or harm(tap_b, rc_b):
        return "A16 HURTS"
    return "A16 ADDS VALUE" if prim_b[1] > 0 else "A16 NOT ESTABLISHED"


def verdict_iv(iv_b):
    return "POSITIVE interaction" if iv_b[1] > 0 else ("NEGATIVE interaction" if iv_b[2] < 0 else "no interaction established")


# ------------------------------------------------------------------------------------------------- helpers
def m(D, S, f):
    return 100 * np.mean([f(D[s]) for s in S])


def contrast(lab, X, Y, S, f, K, out, bad_up=False):
    d = boot([f(X[s]) - f(Y[s]) for s in S]); db = boot([f(X[s]) - f(Y[s]) for s in S], *Pc(K))
    c = churn([Y[s] for s in S], [X[s] for s in S], (lambda r: f(r)) if bad_up else (lambda r: not f(r)))
    out(f"    {lab}: {m(Y, S, f):.2f}% -> {m(X, S, f):.2f}%  d {fmt(d)}  Bonferroni(K={K}) {fmt(db)}  churn fixed {c[0]} / new {c[1]}")
    RESULTS[lab] = dict(base=m(Y, S, f), new=m(X, S, f), d=d, db=db, churn=c, n=len(S))
    return d, db


def activity(L, SL):
    k = {kk: sum(L[s]["knob"].get(kk, 0) for s in SL) for kk in L[SL[0]]["knob"]}
    ru = {kk: sum(L[s]["rule"][kk] for s in SL) for kk in L[SL[0]]["rule"]}
    dec = max(k["dec"], 1)
    a = (f"miss {100 * k['miss'] / dec:.2f}%, non-final commits {100 * k['nonfinal_commit'] / dec:.1f}%, late "
         f"{k['late'] / dec:.3f}/pill, adopted {k['adopt'] / dec:.3f}, refused {k['refuse'] / dec:.3f}, landed on the final "
         f"{100 * k['landed_final'] / dec:.1f}%, tempo {k['tempo_f'] / dec:+.2f} f/pill")
    if "disarmed" in k:
        a += (f", disarmed {100 * k['disarmed'] / dec:.1f}% (today's-cart ref {100 * k['ref_disarmed'] / dec:.1f}%), DOWN via "
              f"DONE {100 * k['down_done'] / dec:.1f}% / stability {100 * k['down_stab'] / dec:.1f}% / none "
              f"{100 * k['no_down'] / dec:.1f}%")
    if "end_pills" in k:
        ep = max(k["end_pills"], 1)
        a += (f", GO->lock {k['golock_f'] / dec:.1f} f (today's cart {k['ref_golock_f'] / dec:.1f}); ENDGAME (< 10 viruses, "
              f"{100 * k['end_pills'] / dec:.1f}% of pills): GO->lock {k['end_golock_f'] / ep:.1f} f (today's cart on the same "
              f"pills {k['end_ref_golock_f'] / ep:.1f}), landed on the final {100 * k['end_landed_final'] / ep:.1f}%")
    return a + f", DIST target on {100 * ru['tgt_on'] / max(ru['dec'], 1):.1f}% of decisions"


def levels(lab, L, SL, R=None, G=None, SG=None, out=print):
    sl = 100 * np.mean([ltype(L[s], M_LULU) == "slow" for s in SL]); kl = 100 * np.mean([ltype(L[s], M_LULU) == "kill" for s in SL])
    w = boot([win(L[s], M_LULU) for s in SL])
    cs = [L[s] for s in SL if L[s]["how"] == "clear"]
    g = ""
    if R is not None:
        g = (f" | owner loss {100 - m(R, SG, lambda r: win(r, M_OWNER)):.2f}% | gate-b tap-out "
             f"{m(G, SG, lambda r: r['topout']):.2f}%")
    out(f"  {lab:18s} LULU loss {100 - w[0]:5.2f}% [{100 - w[2]:.2f}, {100 - w[1]:.2f}] (slow {sl:.2f} / kill {kl:.2f}){g} | "
        f"pills to clear (median) {np.median([r['pills'] for r in cs]) if cs else float('nan'):.0f}, t_clear "
        f"{np.median([r['t_end'] for r in cs]) if cs else float('nan'):.1f} s | {activity(L, SL)}")


def stall_rows(D, S):
    tr = [SC.metrics(SC.sim_runs(D[s], evaluate(D[s], M_LULU, SIGMA, DELTA)[1])) for s in S]
    un = [SC.metrics(SC.sim_runs(D[s])) for s in S]
    return tr, un


def arms():
    A, B, C, D = J.main_arms()
    return A, B, C, D, J.sens_arms(), J.dose_arms()


def rows_R():
    SL, SG = J.seeds(J.N13_LULU, J.LO13), J.seeds(J.N13_GUARD, J.LO13)
    L = {a: load(f"{MAIN_DIR}/lulu14_{a}_*.jsonl", f"{a}~steer", SL) for a in J.REDERIVE}
    R = {a: load(f"{MAIN_DIR}/rc14_{a}_*.jsonl", f"{a}~steer", SG) for a in J.REDERIVE}
    G = {a: load(f"{MAIN_DIR}/gb14_{a}_*.jsonl", f"{a}@owner202610", SG) for a in J.REDERIVE}
    short = [a for a in J.REDERIVE if len(L[a]) < len(SL) or len(R[a]) < len(SG) or len(G[a]) < len(SG)]
    return SL, SG, L, R, G, short


def rows_M():
    A, B, C, D, SENS, DOSE = arms()
    SL, SG, SS, SD = J.seeds(J.N_LULU), J.seeds(J.N_GUARD), J.seeds(J.N_SENS), J.seeds(J.N_DOSE)
    L = {a: load(f"{MAIN_DIR}/lulu14_{a}_*.jsonl", f"{a}~steer", SL) for a in (A, B, C, D)}
    L.update({a: load(f"{MAIN_DIR}/lulu14_{a}_*.jsonl", f"{a}~steer", SS) for a in SENS})
    L.update({a: load(f"{MAIN_DIR}/lulu14_{a}_*.jsonl", f"{a}~steer", SD) for a in DOSE})
    R = {a: load(f"{MAIN_DIR}/rc14_{a}_*.jsonl", f"{a}~steer", SG) for a in (A, B, C, D)}
    G = {a: load(f"{MAIN_DIR}/gb14_{a}_*.jsonl", f"{a}@owner202610", SG) for a in (A, B, C, D)}
    need = {a: (J.N_SENS if a in SENS else (J.N_DOSE if a in DOSE else J.N_LULU)) for a in L}
    short = [a for a in L if len(L[a]) < need[a]] + [a for a in (A, B, C, D) if len(R[a]) < J.N_GUARD or len(G[a]) < J.N_GUARD]
    return SL, SG, SS, SD, L, R, G, short


def status():
    """BLIND: row counts per cell only (R97a: no outcome tally, pooled or not, is ever printed)."""
    SL, SG, L, R, G, sh = rows_R()
    print("STEER14 part R rows (lulu / owner race / gate b): " + ", ".join(f"{a} {len(L[a])}/{len(R[a])}/{len(G[a])}" for a in L)
          + ("  complete" if not sh else ""))
    if J.GS is not None:
        SL, SG, SS, SD, L, R, G, sh = rows_M()
        print("STEER14 main rows: " + ", ".join(f"{a} {len(L[a])}" + (f"/{len(R[a])}/{len(G[a])}" if a in R else "") for a in L)
              + ("  complete" if not sh else f"  ({len(sh)} cells short)"))


def provenance(Ls, out):
    import steer14_run as RUN
    for L in Ls:
        for a in L:
            for s in L[a]:
                g = L[a][s]["rig"]["guard"]
                assert g["sha"] == RUN.GUARD_SHA and g["meta_bad"] == 0, (a, s, g)
    shas = {L[a][s]["rig"]["sha"] for L in Ls for a in L for s in L[a]}
    sms = {L[a][s]["rig"]["steer_model_sha"] for L in Ls for a in L for s in L[a]}
    gits = {L[a][s]["rig"]["git"] for L in Ls for a in L for s in L[a]}
    out(f"provenance: steer14_run sha {sorted(shas)}, steer_model sha {sorted(sms)}, git {sorted(gits)}; every row's jit guard == "
        f"{RUN.GUARD_SHA}")


# ------------------------------------------------------------------------------------------------- part R
def part_R(out):
    SL, SG, L, R, G, short = rows_R()
    out("=== PART R: STEER13's V11 vs 1488 (MIN_THINK 6 f) re-derived under the cart's slam gate (STEER13's own seeds) ===")
    out("rows (lulu / owner race / gate b): " + ", ".join(f"{a} {len(L[a])}/{len(R[a])}/{len(G[a])}" for a in L))
    if short:
        out(f"INCOMPLETE ({short}): part R is WITHHELD (R97)."); return None
    provenance([L, R, G], out)
    V, T = "C13_v116", "C13_14886"
    out(f"ABSOLUTE (LULU M {M_LULU} n={len(SL)}; owner M {M_OWNER} and gate b n={len(SG)}):")
    for a in (T, V):
        levels(a, L[a], SL, R[a], G[a], SG, out)
    wl = lambda r: win(r, M_LULU)
    out("  [V11 - 1488, corrected model]")
    p, pb = contrast("(R) LULU race", L[V], L[T], SL, wl, 1, out)
    contrast("(R) owner race", R[V], R[T], SG, lambda r: win(r, M_OWNER), 1, out)
    contrast("(R) gate-b tap-out", G[V], G[T], SG, lambda r: r["topout"], 1, out, bad_up=True)
    # STEER13's own contrast on the same seeds, and the survival ratio
    L13 = {a: load(f"{S13_DIR}/lulu13_{a}_*.jsonl", f"{a}~steer", SL) for a in ("B_v116_qb", "B_14886_qb")}
    assert all(len(v) == len(SL) for v in L13.values())
    out("  [the same contrast under STEER13's model, same seeds]")
    contrast("(R13) LULU race, STEER13 model", L13["B_v116_qb"], L13["B_14886_qb"], SL, wl, 1, out)
    dn = np.array([wl(L[V][s]) - wl(L[T][s]) for s in SL], float)
    do = np.array([wl(L13["B_v116_qb"][s]) - wl(L13["B_14886_qb"][s]) for s in SL], float)
    rng = np.random.default_rng(14); bs = []
    for _ in range(4000):
        i = rng.integers(0, len(SL), len(SL))
        bs.append(dn[i].mean() / do[i].mean() if do[i].mean() != 0 else np.nan)
    bs = np.array(bs)
    dd = boot(dn - do)
    out(f"  SURVIVAL of STEER13's +{100 * do.mean():.2f} pp: corrected {100 * dn.mean():+.2f} pp = {dn.mean() / do.mean():.2f} of it "
        f"[{np.nanpercentile(bs, 2.5):.2f}, {np.nanpercentile(bs, 97.5):.2f}] (seed bootstrap); corrected - STEER13 {fmt(dd)} pp")
    k13 = {a: {kk: sum(L13[a][s]["knob"][kk] for s in SL) for kk in ("dec", "tempo_f")} for a in L13}
    out(f"  tempo vs today's cart, STEER13 model: V11 {k13['B_v116_qb']['tempo_f'] / k13['B_v116_qb']['dec']:+.2f} f/pill; "
        f"corrected: V11 {sum(L[V][s]['knob']['tempo_f'] for s in SL) / sum(L[V][s]['knob']['dec'] for s in SL):+.2f} f/pill")
    return dict(d=p, ratio=dn.mean() / do.mean(), ratio_ci=(np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5)))


# ------------------------------------------------------------------------------------------------- part M + D
def part_M(out):
    A, B, C, D, SENS, DOSE = arms()
    SL, SG, SS, SD, L, R, G, short = rows_M()
    out(f"\n=== PART M: {{DIST4, A16}} x {{today's slam gate k32, the gate cut {J.GS}}} (V11, MIN_THINK 6 f) ===")
    out("rows (lulu / owner race / gate b): " + ", ".join(f"{a} {len(L[a])}" + (f"/{len(R[a])}/{len(G[a])}" if a in R else "")
                                                       for a in L))
    if short:
        out(f"INCOMPLETE ({short}): parts M and D are WITHHELD (R97)."); return None
    provenance([L, R, G], out)
    for a in (A, B, C, D):
        for s in L[a]:
            assert "stuck" in L[a][s], (a, s)
    wl = lambda r: win(r, M_LULU)
    out(f"\nABSOLUTE (LULU M {M_LULU} n={len(SL)}; owner M {M_OWNER} and gate b n={len(SG)}):")
    for a in (A, B, C, D):
        levels(a, L[a], SL, R[a], G[a], SG, out)
    out(f"\nPRIMARY CONTRASTS (LULU race win at M {M_LULU}; Bonferroni K = {K_PRIM}); GUARDS Bonferroni K = {K_GUARD}:")
    res = {}
    for key, lab, X, Y in (("i", f"(i) A16 at today's gate: {B} - {A}", B, A),
                           ("ii", f"(ii) A16 at the gate cut {J.GS}: {D} - {C}", D, C),
                           ("iii", f"(iii) COMBINED CANDIDATE: {D} - {A} (today's FAIR2PLUS-equivalent)", D, A)):
        out(f"\n  [{lab}]")
        p, pb = contrast(f"({key}) PRIMARY LULU race", L[X], L[Y], SL, wl, K_PRIM, out)
        t, tb = contrast(f"({key}) GUARD gate-b tap-out", G[X], G[Y], SG, lambda r: r["topout"], K_GUARD, out, bad_up=True)
        c, cb = contrast(f"({key}) GUARD owner race M{M_OWNER}", R[X], R[Y], SG, lambda r: win(r, M_OWNER), K_GUARD, out)
        contrast(f"({key}) LULU-race tap-out (how == topout)", L[X], L[Y], SL, lambda r: r["how"] == "topout", 1, out, bad_up=True)
        contrast(f"({key}) gate-b tap<=100", G[X], G[Y], SG, lambda r: int(r["topout"] and r["pills"] <= 100), 1, out, bad_up=True)
        for kk in ("slow", "kill"):
            a0 = [ltype(L[Y][s], M_LULU) == kk for s in SL]; a1 = [ltype(L[X][s], M_LULU) == kk for s in SL]
            out(f"    LULU loss type {kk}: {sum(a0)} -> {sum(a1)} (fixed {sum(x and not y for x, y in zip(a0, a1))} / new "
                f"{sum(y and not x for x, y in zip(a0, a1))})")
        v = verdict_iii(pb, tb, cb) if key == "iii" else verdict_a16(pb, tb, cb)
        out(f"    primary {cls(pb)}; guard harm {'YES' if harm(tb, cb) else 'no'}; VERDICT ({key}): {v}")
        res[key] = (p, pb, tb, cb, v)
    out(f"\n  [(iv) INTERACTION = (ii) - (i) per seed]")
    iv = [(wl(L[D][s]) - wl(L[C][s])) - (wl(L[B][s]) - wl(L[A][s])) for s in SL]
    ivd, ivb = boot(iv), boot(iv, *Pc(K_PRIM))
    hist = {x: sum(1 for y in iv if y == x) for x in (-2, -1, 0, 1, 2)}
    sd = float(np.std(iv, ddof=1))
    from scipy.stats import norm
    mde = 100 * (norm.ppf(1 - 0.05 / (2 * K_PRIM)) + norm.ppf(0.8)) * sd / np.sqrt(len(SL))
    out(f"    interaction {fmt(ivd)}  Bonferroni(K={K_PRIM}) {fmt(ivb)}  per-seed values {hist}  (sd {sd:.3f}; 80 % MDE "
        f"at this n {mde:.2f} pp)")
    out(f"    VERDICT (iv): {verdict_iv(ivb)}")
    res["iv"] = (ivd, ivb, verdict_iv(ivb))
    RESULTS["(iv)"] = dict(d=ivd, db=ivb, hist=hist, n=len(SL))
    out("\nREFERENCE (not a pre-registered contrast; 95 %):")
    contrast(f"(ref) the gate cut alone: {C} - {A}", L[C], L[A], SL, wl, 1, out)
    out("\nSTALLS (act-stall: >= 10 decisions with no legal placement of the actual pill clearing any virus), LULU per game, "
        "truncated at her finish | untruncated:")
    ST = {a: stall_rows(L[a], SL) for a in (A, B, C, D)}
    f_ = lambda ms, k: np.mean([x[k] for x in ms])
    for a in (A, B, C, D):
        tr, un = ST[a]
        out(f"    {a:12s} pills<=16 {f_(tr, 'pills16'):.1f} | {f_(un, 'pills16'):.1f}; pills<=12 {f_(tr, 'pills12'):.1f}; "
            f"pills<=8 {f_(tr, 'pills8'):.1f}; longest<=16 {f_(tr, 'long16'):.1f} s | {f_(un, 'long16'):.1f} s; "
            f"stall>=30 s {100 * f_(tr, 'ge30'):.1f}% | {100 * f_(un, 'ge30'):.1f}%")
    for lab, X, Y in (("(i)", B, A), ("(ii)", D, C), ("(iii)", D, A)):
        trX, _ = ST[X]; trY, _ = ST[Y]
        d = boot([(x["pills16"] - y["pills16"]) / 100 for x, y in zip(trX, trY)])
        dl = boot([(x["long16"] - y["long16"]) / 100 for x, y in zip(trX, trY)])
        d2 = boot([(x["ge30"] - y["ge30"]) for x, y in zip(trX, trY)])
        out(f"    {lab} {X} - {Y}: stall-pills<=16 (truncated) {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]; longest<=16 {dl[0]:+.2f} s "
            f"[{dl[1]:+.2f}, {dl[2]:+.2f}]; games with a stall >= 30 s {fmt(d2)} pp")
    q4, q16 = SENS
    out(f"\nSENSITIVITY: (iii) at q 2 % random-root misses (LULU, n={len(SS)}, 95 %):")
    for a in SENS:
        levels(a, L[a], SS, out=out)
    sp, spb = contrast(f"(iii) q 2 %: {q16} - {q4}", L[q16], L[q4], SS, wl, 1, out)
    contrast("(iii) q 0 on the same seeds (for comparison)", L[D], L[A], SS, wl, 1, out)
    out(f"    sensitivity {cls(sp)} at 95 %; same sign as the primary (iii): "
        f"{'yes' if np.sign(sp[0]) == np.sign(res['iii'][0][0]) else 'NO'}")
    # ---- part D
    out(f"\n=== PART D: slam-gate dose-response (DIST4, LULU, the first {len(SD)} seeds; descriptive, 95 %) ===")
    for g in J.GATE_NAMES:
        a = f"S14_d4_{g}"
        levels(a, L[a], SD, out=out)
        if g != "k32":
            contrast(f"(D) {g} - k32", L[a], L[A], SD, wl, 1, out)
    out("\nSUMMARY:")
    for key, nm in (("i", "(i) A16 @ today's gate"), ("ii", f"(ii) A16 @ gate cut {J.GS}"), ("iii", "(iii) combined")):
        p, pb, tb, cb, v = res[key]
        out(f"  {nm}: {fmt(p)} Bonferroni {fmt(pb)} -> {v}")
    out(f"  (iv) interaction: {fmt(res['iv'][0])} Bonferroni {fmt(res['iv'][1])} -> {res['iv'][2]}")
    out(f"  q 2 % sensitivity of (iii): {fmt(sp)} ({cls(sp)} at 95 %)")
    return res


def main(only_R=False):
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    r = part_R(out)
    if only_R:
        open(OUT_R, "w").write("\n".join(lines) + "\n")
        return r
    res = part_M(out)
    open(OUT, "w").write("\n".join(lines) + "\n")
    return res


def selftest():
    ok = True
    Z = (0, -1, 1)
    cases3 = [((+3, +0.5, +5.5), Z, Z, "CERTIFIED"), ((+3, +0.5, +5.5), (+2, +0.5, +3), Z, "NOT CERTIFIED"),
              ((+3, +0.5, +5.5), Z, (-3, -5, -0.5), "NOT CERTIFIED"), ((+2, -0.5, +4.5), Z, Z, "NOT CERTIFIED"),
              ((+3, +0.5, +5.5), (+0.5, -0.2, +1.5), (-0.5, -1.5, +0.3), "CERTIFIED"),
              ((-3, -5.5, -0.5), Z, Z, "NOT CERTIFIED")]
    for p, t, c, want in cases3:
        got = verdict_iii(p, t, c); ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} (iii) prim {p} tap {t} race {c} -> {got}")
    casesA = [((+3, +0.5, +5.5), Z, Z, "A16 ADDS VALUE"), ((+1, -1, +3), Z, Z, "A16 NOT ESTABLISHED"),
              ((-3, -5.5, -0.5), Z, Z, "A16 HURTS"), ((+3, +0.5, +5.5), (+2, +0.5, +3), Z, "A16 HURTS"),
              ((+1, -1, +3), Z, (-3, -5, -0.5), "A16 HURTS"), ((+3, +0.5, +5.5), (+0.5, -0.2, +1.5), (-0.5, -1.5, +0.3), "A16 ADDS VALUE"),
              ((-1, -3, +1), Z, Z, "A16 NOT ESTABLISHED")]
    for p, t, c, want in casesA:
        got = verdict_a16(p, t, c); ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} (ii) prim {p} tap {t} race {c} -> {got}")
    casesI = [((+3, +0.2, +6), "POSITIVE interaction"), ((-3, -6, -0.2), "NEGATIVE interaction"), ((+2, -1, +5), "no interaction established")]
    for ci, want in casesI:
        got = verdict_iv(ci); ok &= got == want
        print(f"  {'ok ' if got == want else 'BAD'} (iv) {ci} -> {got}")
    muts3 = {"primary on the mean": lambda p, t, c: p[0] > 0 and not (t[1] > 0 or c[2] < 0),
             "tap guard dropped": lambda p, t, c: p[1] > 0 and not c[2] < 0,
             "race guard dropped": lambda p, t, c: p[1] > 0 and not t[1] > 0,
             "race guard sign flipped": lambda p, t, c: p[1] > 0 and not (t[1] > 0 or c[1] > 0),
             "tap guard on its mean": lambda p, t, c: p[1] > 0 and not (t[0] > 0 or c[2] < 0)}
    for name, f in muts3.items():
        killed = any((("CERTIFIED" if f(p, t, c) else "NOT CERTIFIED") != want) for p, t, c, want in cases3)
        ok &= killed
        print(f"  (iii) mutant '{name}': {'KILLED' if killed else 'SURVIVED'}")
    mutsA = {"no HURTS branch on guards": lambda p, t, c: "A16 HURTS" if p[2] < 0 else ("A16 ADDS VALUE" if p[1] > 0 else "A16 NOT ESTABLISHED"),
             "HURTS on the mean": lambda p, t, c: "A16 HURTS" if (p[0] < 0 or t[1] > 0 or c[2] < 0) else ("A16 ADDS VALUE" if p[1] > 0 else "A16 NOT ESTABLISHED"),
             "ADDS on the mean": lambda p, t, c: "A16 HURTS" if (p[2] < 0 or t[1] > 0 or c[2] < 0) else ("A16 ADDS VALUE" if p[0] > 0 else "A16 NOT ESTABLISHED")}
    for name, f in mutsA.items():
        killed = any(f(p, t, c) != want for p, t, c, want in casesA)
        ok &= killed
        print(f"  (ii) mutant '{name}': {'KILLED' if killed else 'SURVIVED'}")
    mutsI = {"interaction on the mean": lambda ci: "POSITIVE interaction" if ci[0] > 0 else ("NEGATIVE interaction" if ci[0] < 0 else "no interaction established")}
    for name, f in mutsI.items():
        killed = any(f(ci) != want for ci, want in casesI)
        ok &= killed
        print(f"  (iv) mutant '{name}': {'KILLED' if killed else 'SURVIVED'}")
    ok &= Pc(4) == (0.625, 99.375) and Pc(6) == (100 * 0.05 / 12, 100 - 100 * 0.05 / 12)
    print(f"  Bonferroni percentiles K=4 {Pc(4)}, K=6 {tuple(round(x, 4) for x in Pc(6))}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    if "--status" in sys.argv:
        status(); sys.exit(0)
    main(only_R="--rederive" in sys.argv)
