#!/usr/bin/env python3
"""COMBINED-CART gate (#140): DRPRESPIPE(Q=3) + DRP1SLICE on the hardened class.

THE DEFECT UNDER TEST is a certification hole, not a slow routine: each lane
certified its own state machine with the other one assumed absent (every
prespipe phase scenario carried the no-P1-search cut; the p1slice pair bound
was computed on a class with no prestart at all). On the combined image one
hook can carry BOTH a pp phase (~10.7k) and a slice tick (~6k): the sound
admissible-frame bound is 35.8k > 29,780 -- OVER by ~6k, a real hazard neither
green sheet covered. The fix is the emitter's PP_RAN interlock (pre_tick sets
the latch on every pipeline-work hook; the slice dispatch skips the tick on it
and clears the latch each hook), which makes the phase/slice exclusion a
GUARD-PROVEN census cut, the same shape as h2_cp.

GATES
  C1 BYTE-IDENTITY / PROVENANCE:
     a. DRP1SLICE=0 on the combined snapshot differs from the certified
        prespipe-hardened-q3 cart (7e73d4a3) in EXACTLY the 3 FC_STAB operand
        low bytes ($61BB -> $61C4, the #140 relocation) -- nothing else.
     b. tcvc-p1slice (010f4ffe) still rebuilds byte-exact (no STARTGUARD, no
        PRESPIPE on that class: relocation and interlock both invisible).
     c. the shipped combo cart rebuilds deterministically from its manifest.
  C2 INTERLOCK PREMISE, from the IR: the guard (LDA PP_RAN / BNE p1s_idle)
     sits between the slice dispatch and JSR p1s_tick; PP_RAN has exactly the
     five expected writers (2 set sites -- pt_edge head and the pp dispatch
     path -- 1 per-hook clear at p1s_idle, 2 init sites); the census cut
     ("fallof","p1s_idle") is therefore a statement about emitted code.
  C3 ADMISSIBLE-FRAME CERTIFICATE, both machines: every admissible ordered
     hook pair (phase advance, edge, idle/spawn WITH slice ticks, the pairs a
     slice-less image never needed) fits 29,780 including the measured game
     NMI head (2,040) and tail eps (300).
  C4 NOT-INERT: the interlock cut must BIND -- the pp_idle-class bound with
     the tick admitted exceeds the phase-class bound with the tick cut by at
     least 4,000 cycles (an unreachable tick would make C3 vacuously green).
  C5 KILLED MUTANTS:
     M1 guard deleted from the IR             -> C2 premise check must FAIL
     M2 pt_edge set-site deleted              -> C2 premise check must FAIL
     M3 the RETIRED per-lane certification: prespipe-only green + p1slice-only
        green while the combined NAIVE model (no interlock cut) is OVER the
        frame -- proving separate-green does not imply combined-green. This is
        the process defect that created #140, kept as a named mutant.

Run with the dr-mario-mods venv python:
  /home/struktured/projects/dr-mario-mods/.venv/bin/python tests/test_combo_cart.py
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "nmi126"))
import census  # noqa: E402

PY = sys.executable
MAN_Q3 = "roms/manifests/prespipe-hardened-q3.json"
Q3_MD5 = "7e73d4a3b381bf315b628327807faf1c"
TCVC_SL_MAN = "roms/manifests/tcvc-p1slice.json"
TCVC_SL_MD5 = "010f4ffe350df3b57561f8ce3bc4320b"
COMBO = "roms/combo-hardened-pp3sl-20260820.nes"
TMP = "tmp/combo"
GAME_HEAD, EPS, FRAME = 2040, 300, 29780

ok = True


def check(label, cond, detail=""):
    global ok
    print(f"  {label:64s} {'PASS' if cond else 'FAIL'}{('  ' + detail) if detail else ''}")
    ok &= bool(cond)


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def build(out, snap, overlay):
    env = dict(os.environ)
    env.update({k: str(v) for k, v in snap.items()})
    env.update(overlay)
    env["DRBUILDID"] = "0"
    r = subprocess.run([PY, "tools/romgen.py", "build", "--out", out,
                        "--base", "drmario_v28cs.nes", "--tag", "combo-gate-CHECKONLY"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return open(out, "rb").read()


def capture(out, *overlay):
    subprocess.run([PY, "tools/nmi126/capture_ir.py", MAN_Q3, out, *overlay],
                   check=True, capture_output=True)
    return json.load(open(out))


# --------------------------------------------------------------- C1: bytes --
def c1():
    os.makedirs(TMP, exist_ok=True)
    snap = json.load(open(MAN_Q3))["flag_snapshot"]
    ref = open("roms/prespipe-hardened-q3.nes", "rb").read()
    assert hashlib.md5(ref).hexdigest() == Q3_MD5, "reference cart is not 7e73d4a3 -- stop"

    a = build(f"{TMP}/c1_offslice.nes", snap, {})
    diffs = [i for i in range(len(a)) if a[i] != ref[i]]
    sites = [i for i in diffs
             if ref[i] == 0xBB and a[i] == 0xC4 and ref[i + 1] == 0x61 == a[i + 1]]

    # Bind the diff set to an INDEPENDENTLY DERIVED reference set (team-lead
    # ruling, DRVERFIX style): enumerate every emitted instruction whose 16-bit
    # operand is FC_STAB in the flags-off IR, translate those operand offsets
    # to file offsets, and assert SET EQUALITY with the observed diffs -- not
    # a hardcoded count. The CPU->file delta is derived from the first match
    # and must be consistent for all (one contiguous bank).
    meta_off = capture(f"{TMP}/c1_off_ir.json")
    fc = meta_off["consts"]["FC_STAB"]
    fc_ops = [fc & 0xFF, fc >> 8]
    u = meta_off["units"]["main"]
    op_offs = [u["base"] + r["off"] + 1 for r in u["records"]
               if r["k"] == "ins" and r.get("ops") == fc_ops and r["m"].endswith("_abs")]
    ok_ref = len(op_offs) > 0 and len(op_offs) == len(sites)
    if ok_ref and sites:
        delta = sorted(sites)[0] - sorted(op_offs)[0]
        ok_ref = sorted(sites) == [o + delta for o in sorted(op_offs)]
    check("C1a DRP1SLICE=0 vs 7e73d4a3: diff set == IR-derived FC_STAB operand set",
          len(diffs) == len(sites) and ok_ref,
          f"diffs={len(diffs)} fc_sites={len(sites)} ir_refs={len(op_offs)}")

    snap_t = json.load(open(TCVC_SL_MAN))["flag_snapshot"]
    b = build(f"{TMP}/c1_tcvc.nes", snap_t, {})
    check("C1b tcvc-p1slice rebuilds byte-exact (010f4ffe)",
          hashlib.md5(b).hexdigest() == TCVC_SL_MD5, hashlib.md5(b).hexdigest())

    c = build(f"{TMP}/c1_combo.nes", snap, {"DRP1SLICE": "1"})
    check("C1c combo cart deterministic rebuild == shipped bytes",
          os.path.exists(COMBO) and hashlib.md5(c).hexdigest() == md5(COMBO),
          hashlib.md5(c).hexdigest())
    for f in ("c1_offslice.nes", "c1_tcvc.nes", "c1_combo.nes"):
        os.remove(f"{TMP}/{f}")
    if os.path.exists("roms/manifests/combo-gate-CHECKONLY.json"):
        os.remove("roms/manifests/combo-gate-CHECKONLY.json")


# ------------------------------------------------- C2: interlock premise ----
def premise(meta):
    """True iff the emitted code carries the full PP_RAN interlock."""
    u = meta["units"]["main"]
    labels, base = u["labels"], u["base"]
    consts = meta["consts"]
    ppran = [consts["PP_RAN"] & 0xFF, consts["PP_RAN"] >> 8]
    recs = [r for r in u["records"] if r["k"] != "label"]
    if not {"p1s_ppguard", "p1s_idle", "p1s_tick", "pt_edge", "pp_disp"} <= set(labels):
        return False
    by_off = {r["off"]: i for i, r in enumerate(recs)}

    # guard: LDA_abs PP_RAN at p1s_ppguard, then BNE p1s_idle, then JSR p1s_tick
    gi = by_off.get(labels["p1s_ppguard"])
    if gi is None:
        return False
    g0, g1, g2 = recs[gi], recs[gi + 1], recs[gi + 2]
    if not (g0["k"] == "ins" and g0["m"] == "LDA_abs" and g0["ops"] == ppran):
        return False
    if not (g1["k"] == "br" and g1["target"] == "p1s_idle"):
        return False
    if not (g2["k"] == "jsr"):
        return False

    # writers: LDA_imm 1 + STA_abs PP_RAN at pt_edge head and on the dispatch path;
    # LDA_imm 0 + STA_abs PP_RAN right after p1s_idle; 2 init writers elsewhere.
    stores = [i for i, r in enumerate(recs)
              if r["k"] == "ins" and r["m"] == "STA_abs" and r["ops"] == ppran]
    if len(stores) != 5:
        return False
    ei = by_off.get(labels["pt_edge"])
    edge_set = any(recs[i - 1]["m"] == "LDA_imm" and recs[i - 1]["ops"] == [1]
                   and abs(i - ei) <= 2 for i in stores)
    ii = by_off.get(labels["p1s_idle"])
    idle_clr = any(recs[i - 1]["m"] == "LDA_imm" and recs[i - 1]["ops"] == [0]
                   and 0 <= i - ii <= 2 for i in stores)
    disp_set = any(recs[i - 1]["m"] == "LDA_imm" and recs[i - 1]["ops"] == [1]
                   and recs[i + 1]["k"] == "jmp" and recs[i + 1]["target"] == "pp_disp"
                   for i in stores)
    return bool(edge_set and idle_clr and disp_set)


# ------------------------------------------------ C3/C4: the certificate ----
def certificate(meta, interlock=True):
    """(worst_total, table) over the admissible ordered pairs, slice included."""
    nodes = census.load_from_meta(meta)
    so = census.detect_site_overrides(meta, nodes)
    eb = census.detect_prespipe_bounds(meta)
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])
    pp_cuts, pp_order = census.prespipe_scenarios(have)
    if not interlock:
        pp_cuts = {k: [c for c in v if c != ("fallof", "p1s_idle")]
                   for k, v in pp_cuts.items()}
    res = {}
    wrap = meta["units"]["wrapper"]["base"]
    for name, cuts in pp_cuts.items():
        cuts_here = [(k, l) for k, l in cuts if l in have]
        res[name] = census.Analyzer(nodes, cuts_here, site_overrides=so,
                                    extra_bounds=eb).worst(wrap)
    seq = [(pp_order[i], pp_order[i + 1]) for i in range(len(pp_order) - 1)]
    seq += [(a, "pp_idle") for a in pp_order]
    seq += [("pp_spawn", "pp_edge"), ("pp_idle", "pp_edge"),
            ("pp_idle", "pp_idle"), ("pp_spawn", "pp_idle"),
            ("pp_idle", "pp_spawn")]
    table = [(a, b, res[a] + res[b] + 12 + GAME_HEAD + EPS) for a, b in seq]
    return max(t for _, _, t in table), table, res


def main():
    print("=" * 84)
    print("COMBINED-CART GATE (#140): DRPRESPIPE(Q=3) + DRP1SLICE, hardened class")
    print("=" * 84)

    c1()

    meta = capture(f"{TMP}/gate_combo_ir.json", "DRP1SLICE=1")
    check("C2 interlock premise verified from the IR", premise(meta))

    worst, table, res = certificate(meta, interlock=True)
    for a, b, t in sorted(table, key=lambda x: -x[2])[:3]:
        print(f"       {a:10s} + {b:10s} = {t} of {FRAME}  margin {FRAME - t:+d}")
    check("C3 every admissible frame fits (incl. slice-bearing pairs)",
          worst < FRAME, f"worst {worst}, margin {FRAME - worst:+d}")

    # C4: the cut must bind -- the SAME pp_idle scenario with the tick cut must
    # drop by roughly the tick bound (~6k). If cutting the tick changes nothing,
    # the tick was never reachable and C3 is vacuously green.
    nodes = census.load_from_meta(meta)
    so = census.detect_site_overrides(meta, nodes)
    eb = census.detect_prespipe_bounds(meta)
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])
    pp_cuts, _ = census.prespipe_scenarios(have)
    idle_cut = [(k, l) for k, l in pp_cuts["pp_idle"] + [("fallof", "p1s_idle")]
                if l in have]
    wrap = meta["units"]["wrapper"]["base"]
    idle_nocut = res["pp_idle"]
    idle_cutv = census.Analyzer(nodes, idle_cut, site_overrides=so,
                                extra_bounds=eb).worst(wrap)
    gap = idle_nocut - idle_cutv
    check("C4 interlock cut binds (tick reachable where admitted)",
          gap >= 4000, f"gap {gap} (idle {idle_nocut} vs tick-cut {idle_cutv})")

    # ---- C5 mutants ----
    import copy
    m1 = copy.deepcopy(meta)
    u = m1["units"]["main"]
    goff = u["labels"]["p1s_ppguard"]
    u["records"] = [r for r in u["records"]
                    if not (r["k"] != "label" and goff <= r["off"] < goff + 5)]
    del u["labels"]["p1s_ppguard"]
    check("C5 M1 guard deleted -> premise FAILS (mutant killed)", not premise(m1))

    m2 = copy.deepcopy(meta)
    u2 = m2["units"]["main"]
    consts = meta["consts"]; ppran = [consts["PP_RAN"] & 0xFF, consts["PP_RAN"] >> 8]
    eoff = u2["units" if False else "labels"]["pt_edge"]
    recs2 = u2["records"]
    kill = None
    for i, r in enumerate(recs2):
        if (r["k"] == "ins" and r["m"] == "STA_abs" and r["ops"] == ppran
                and abs(r["off"] - eoff) <= 6):
            kill = i
            break
    assert kill is not None
    del recs2[kill]
    check("C5 M2 pt_edge set-site deleted -> premise FAILS (mutant killed)",
          not premise(m2))

    # M3: the retired per-lane process. prespipe-only green, p1slice-only green
    # (test_p1slice's own sheet), combined-naive OVER.
    meta_pp = capture(f"{TMP}/gate_pp_only_ir.json")
    worst_pp, _, _ = certificate(meta_pp, interlock=True)
    worst_naive, _, _ = certificate(meta, interlock=False)
    check("C5 M3 retired per-lane certification -> combined naive model is OVER",
          worst_pp < FRAME and worst_naive > FRAME,
          f"pp-only {worst_pp} < {FRAME} but naive combined {worst_naive} OVER")

    print()
    print("test_combo_cart: " + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
