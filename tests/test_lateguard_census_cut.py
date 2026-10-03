#!/usr/bin/env python3
"""GATE: the NMI census's per-phase CUTS on a DRPRESPIPE image are TRUE of the emitted driver, and they FAIL when
their premise breaks (PR #30 review, DRLATEGUARD).

tools/nmi126/census.py prespipe_scenarios() certifies the worst frame by cutting code it claims a phase hook can never
run:
  * every phase hook ................ ("into", "h2_cp")                       spawn upload (premise: pp_disp's PEND2 abort)
  * every NON-committing phase ...... ("into", "lg_live"), ("into", "lg_done") the DRLATEGUARD gate (premise: pp_disp's
                                       ARMED2/PEND2 aborts + a non-committing phase never writes ARMED2)
Without the lg cut the couch DRLATEGUARD image's worst admissible frame is 29,306 (margin +474 on a MEASURED game
head) instead of 27,704 (+2,076), so the premise is load-bearing for the margin. The census comment says
`tests/test_prespipe.py M3` keeps it honest; that file exists only on the unmerged prestart-pipeline-138 lineage (not
on main, not on claude/late-flip), and even there its mutant M3 deletes only the PEND2 abort (G5 exercises the ARMED2
abort behaviourally, no mutant targets it) and nothing covers "a non-committing phase never writes ARMED2". On this
branch nothing ran at all. This gate does, by REPRODUCING THE DEFECT, not by looking for the guard:

  1. Capture the couch DRLATEGUARD image (experiments/lateflip/couch_c960dd49_flags.json + DRLATEGUARD=1) with
     tools/nmi126/capture_ir.py (ground-truth-gated against the emitter's own bytes).
  2. Run ONE real driver hook (`main`, py65, flat memory) per state over a grid of P2 search/pipeline states:
     PP_PH x ARMED2 x PEND2 x DELAY2 x lock edge x PRE_ACT2 x incoming volley x DRSTALLWD firing x mailbox.
     The mailbox is ADVERSARIAL (reads of $5284-$5288 return the grid's values whatever the driver wrote, GO
     included), because the census does not model the copro either: a cut must hold for any answer timing.
  3. Classify each hook by the phase entry it DISPATCHED to (pp_ph1 / pp_m2 / ...), and for every class whose census
     scenario cuts a label, require that label (and, for the lg cut, lg_gate's entry) never executed in that hook.
  4. Mutants, each built from a mutated COPY of the emitter (the tree is never touched), must be KILLED:
       M_armed  pp_disp's ARMED2 abort is dead (LDA #0)            -> lg_gate runs in a non-committing phase hook
       M_pend   pp_disp's PEND2 abort is dead                       -> spawn upload h2_cp runs in a phase hook
       M_write  phase 1's exit (pp_s_done) writes ARMED2 := 1       -> lg_gate runs in a non-committing phase hook
       M_early  a non-last match phase (pp_m3) commits + GOes       -> lg_gate runs in a hook the census cut
     A mutation anchor that is not found EXACTLY once is a FAIL, never a skip.
  5. Positive controls (the witness is alive): every class is populated; lg_gate and h2_cp ARE executed in the
     same grid (aborted / idle hooks); the last (committing) phase reaches lg_gate, which is why the census keeps it.
  6. Census-model checks: (a) the census applies each cut scenario-wide, so pp_disp's ABORTED hooks (ARMED2/PEND2
     set, where lg_gate and the spawn upload DO run) are charged at the cut bound; require the independently computed
     aborted-hook bound to be <= every phase scenario's bound (dominated) -- else the certificate is unsound;
     (b) every measured hook's py65 cycles <= the census bound of its class; (c) LOOP_BOUNDS["lg_row"] >= the
     ROWCAP immediates the IR actually carries before `lg_nk` (the census hand-declares 2; the emitter's `assert
     ROWCAP <= 2` vanishes under `python -O`, which mutant M_rowcap reproduces and this check must kill).

Usage: python tests/test_lateguard_census_cut.py      (needs py65; only the emitter runs, no base ROM). ~15 s.
       Exit 0 = PASS. Wired into tools/gate/run_cart_gates.sh.
"""
import itertools
import json
import os
import shutil
import subprocess
import sys

from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "nmi126"))
import census as C  # noqa: E402

FLAGS = os.path.join(ROOT, "experiments", "lateflip", "couch_c960dd49_flags.json")
CAPTURE = os.path.join(ROOT, "tools", "nmi126", "capture_ir.py")
EMITTER = os.path.join(ROOT, "patch_cartridge_copro.py")
WORK = os.path.join(ROOT, "tmp", "lgcut_gate")
SENT = 0x3000
LG_CUT = [("into", "lg_live"), ("into", "lg_done")]

# (name, [(anchor, replacement)], what the mutation breaks)
MUTANTS = [
    ("M_armed", [('a.ins16("LDA_abs", ARMED2); a.br("BEQ", "pp_d3")',
                  'a.ins("LDA_imm", 0); a.br("BEQ", "pp_d3")')],
     "pp_disp ARMED2 abort dead"),
    ("M_pend", [('a.ins16("LDA_abs", PEND2); a.br("BEQ", "pp_d2")',
                 'a.ins("LDA_imm", 0); a.br("BEQ", "pp_d2")')],
     "pp_disp PEND2 abort dead"),
    ("M_write", [('a.label("pp_s_done")\n',
                  'a.label("pp_s_done")\n            a.ins("LDA_imm", 1); a.ins16("STA_abs", ARMED2)\n')],
     "non-committing phase 1 writes ARMED2 := 1"),
    ("M_early", [('                if last:\n                    a.jmp("pt_commit")',
                  '                if last or k == PP_NM - 2:\n                    a.jmp("pt_commit")')],
     "non-last match phase commits (GO, ARMED2 := 1)"),
]


def snapshot(overlay):
    snap = json.load(open(FLAGS))["flag_snapshot"]
    snap.update(overlay)
    return snap


def capture(tag, overlay, emitter_src=None, optimize=False):
    """IR JSON for the couch flags + overlay. emitter_src: mutated emitter source (built in its own dir)."""
    d = os.path.join(WORK, tag)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    man, out = os.path.join(d, "manifest.json"), os.path.join(d, "ir.json")
    json.dump({"flag_snapshot": snapshot(overlay)}, open(man, "w"))
    cwd = ROOT
    if emitter_src is not None:
        cwd = d
        open(os.path.join(d, "patch_cartridge_copro.py"), "w").write(emitter_src)
        for dep in ("patch_vs_cpu.py", "expand_prg.py"):
            os.symlink(os.path.join(ROOT, dep), os.path.join(d, dep))
    env = {k: v for k, v in os.environ.items() if not k.startswith("DR")}
    cmd = [sys.executable] + (["-O"] if optimize else []) + [CAPTURE, man, out]
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: capture {tag} rc={r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    if "GROUND-TRUTH OK" not in r.stdout:
        raise SystemExit(f"FAIL: capture {tag}: no GROUND-TRUTH OK line")
    return json.load(open(out))


def ram_map():
    """RAM addresses from the emitter itself (imported under the couch flags), so a relocation cannot desync us."""
    for k, v in snapshot({"DRLATEGUARD": "1"}).items():
        os.environ[k] = str(v)
    sys.path.insert(0, ROOT)
    import patch_cartridge_copro as P
    names = ["PP_PH", "ARMED2", "PEND2", "DELAY2", "LASTY2", "NAV_MAGIC", "MATCH_ACTIVE", "PRE_ATK2", "PRE_LAST2",
             "PRE_ACT2", "PRE_BUF", "SWD_S0", "SWD_S1", "SWD_S2", "SWD_CTL", "SWD_CTH", "STALLWD_N", "VCOUNT_P2",
             "TGT_C2", "TGT_O2", "LG_CMT2", "LG_LOCK2", "W2_BASE", "PP_SWAL"]
    return {n: getattr(P, n) for n in names}


class Image:
    def __init__(self, ir):
        self.ir = ir
        self.flat = [0] * 0x10000
        for u in ir["units"].values():
            b = bytes.fromhex(u["bytes"])
            self.flat[u["base"]:u["base"] + len(b)] = list(b)
        self.L = {k: u["base"] + o for u in ir["units"].values() for k, o in u["labels"].items()}
        self.have = set(self.L)
        m = sorted((l for l in self.have if l.startswith("pp_m") and l[4:].isdigit()), key=lambda l: int(l[4:]))
        self.phases = ["pp_ph1"] + m                     # census order: scenario pp_ph{i+1} dispatches phases[i]


def run_hook(img, R, st):
    """One driver hook from `main` under state st; returns (executed-address set, main cycles)."""
    W = R["W2_BASE"]
    mbox = {W + 0x84: st["done"], W + 0x85: 6, W + 0x86: st["orient"], W + 0x87: 0xFF, W + 0x88: 0}
    mem = ObservableMemory(subject=list(img.flat))
    mem.subscribe_to_read(range(W + 0x84, W + 0x89), lambda a: mbox[a])
    for a in range(0x0500, 0x0580):
        mem[a] = 0xFF
    for c in range(8):                                   # a floor row so the gate's fall scan has something to see
        mem[0x0500 + 15 * 8 + c] = 0xD1 if c % 3 else 0xFF
    for a in range(R["PRE_BUF"], R["PRE_BUF"] + 128):
        mem[a] = 0xFF
    mem[0x46], mem[0x04], mem[0x0727] = 4, 1, 2
    mem[R["NAV_MAGIC"]], mem[R["MATCH_ACTIVE"]] = 0xA5, 1
    x, y, rot = 3, 12, 0
    mem[0x0385], mem[0x0386], mem[0x03A5] = x, y, rot
    mem[R["VCOUNT_P2"]] = 0x20
    mem[R["LASTY2"]] = 2 if st["edge"] else y                # $0386 > LASTY2 -> the P2 lock/new-pill edge fires
    mem[R["PRE_ACT2"]] = st["preact"]
    atk_cur, atk_last = st["atk"]
    mem[R["PRE_ATK2"]], mem[R["PRE_LAST2"]] = atk_cur, atk_last
    if st["swd"]:                                        # DRSTALLWD fires THIS hook (pose static, counter at N-1)
        mem[R["SWD_S0"]], mem[R["SWD_S1"]], mem[R["SWD_S2"]] = x, y, rot
        n = R["STALLWD_N"] - 1
        mem[R["SWD_CTL"]], mem[R["SWD_CTH"]] = n & 0xFF, n >> 8
    mem[R["PP_PH"]] = st["pp"]
    mem[R["ARMED2"]], mem[R["PEND2"]], mem[R["DELAY2"]] = st["armed"], st["pend"], st["delay"]
    mem[R["TGT_C2"]], mem[R["TGT_O2"]] = 0, 3              # differs from the mailbox (6, 1) -> gate's full path
    mem[R["LG_CMT2"]], mem[R["LG_LOCK2"]] = 1, 0
    mem[0x01FE], mem[0x01FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
    m = MPU(memory=mem)
    m.sp, m.pc = 0xFD, img.L["main"]
    hits, n = set(), 0
    while m.pc != SENT:
        hits.add(m.pc)
        m.step()
        n += 1
        if n > 200000:
            raise SystemExit(f"FAIL: runaway hook pc=${m.pc:04X} state={st}")
    return hits, m.processorCycles


def grid(nphases):
    dims = dict(pp=range(0, nphases + 1), armed=(0, 1), pend=(0, 1), delay=(0, 3), edge=(0, 1), preact=(0, 1),
                atk=((0, 0), (2, 2), (0, 2)), swd=(0, 1), done=(0, 1), orient=(0xFF, 1))
    keys = list(dims)
    for vals in itertools.product(*(dims[k] for k in keys)):
        yield dict(zip(keys, vals))


def census_bounds(img):
    """Census per-scenario bounds (hook worst incl. wrapper) + the cut map, from census.py itself."""
    meta = img.ir
    nodes = C.load_from_meta(meta)
    so = C.detect_site_overrides(meta, nodes)
    eb = C.detect_prespipe_bounds(meta)
    wrap = meta["units"]["wrapper"]["base"]
    have = set()
    for nd in nodes.values():
        have.update(nd.get("labels") or [])

    def worst(cuts):
        cuts = [(k, l) for k, l in cuts if l in have]
        return C.Analyzer(nodes, cuts, site_overrides=so, extra_bounds=eb).worst(wrap) + 6

    pp = C.prespipe_scenarios(have)
    assert pp, "image has no DRPRESPIPE pipeline -- this gate is vacuous on it"
    cuts, order = pp
    B = {name: worst(c) for name, c in cuts.items()}
    abort = ([("into", "ppd_skip")] + [("into", e) for e in img.phases]
             + [("into", "h1_start"), ("into", "do_init"), ("fallof", "p1n_nosearch")])
    B["pp_abort"] = worst(abort)                        # aborted hook: no phase, NO h2_cp/lg cut (both reachable)
    return B, cuts


def check_image(img, R, cuts, stop_at_first=False, bounds=None):
    """Returns (violations, stats). A violation = a census-cut label executed in a hook of a class that cuts it."""
    L = img.L
    phase_addr = {L[p]: i for i, p in enumerate(img.phases)}
    cut_of = {}                                          # phase index -> set of cut label names
    for i in range(len(img.phases)):
        cut_of[i] = {l for k, l in cuts[f"pp_ph{i + 1}"] if k == "into" and l in ("h2_cp", "lg_live", "lg_done")}
    lg_entry = L["lg_gate"]
    viol, over = [], []
    stats = dict(hooks=0, cls={i: 0 for i in range(len(img.phases))}, lg_seen=0, h2cp_seen=0, aborted=0,
                 last_lg=0, lg_in_abort=0)
    for st in grid(len(img.phases)):
        hits, cyc = run_hook(img, R, st)
        stats["hooks"] += 1
        entered = sorted({phase_addr[a] for a in hits if a in phase_addr})
        lg_ran = lg_entry in hits
        stats["lg_seen"] += lg_ran
        stats["h2cp_seen"] += L["h2_cp"] in hits
        if len(entered) > 1:
            viol.append((st, f"two phases dispatched in one hook: {entered}"))
        if not entered:
            if st["pp"] and L["pp_disp"] in hits:
                stats["aborted"] += 1
                stats["lg_in_abort"] += lg_ran
            klass = None
        else:
            i = entered[0]
            stats["cls"][i] += 1
            if i == len(img.phases) - 1:
                stats["last_lg"] += lg_ran
            for lab in cut_of[i]:
                if L[lab] in hits:
                    viol.append((st, f"{img.phases[i]} hook executed census-cut label {lab}"))
            if ("lg_live" in cut_of[i] or "lg_done" in cut_of[i]) and lg_ran:
                viol.append((st, f"{img.phases[i]} hook entered lg_gate (census cut lg_live/lg_done)"))
            klass = f"pp_ph{i + 1}"
        if bounds is not None:
            if klass is None:                            # the census lumps an aborted hook into pp_ph{PP_PH}
                klass = f"pp_ph{st['pp']}" if st["pp"] else ("pp_edge" if L["pt_edge"] in hits else
                                                              "pp_spawn" if L["h2_cp"] in hits else "pp_idle")
            if cyc > bounds[klass]:
                over.append((st, klass, cyc, bounds[klass]))
        if viol and stop_at_first:
            break
    return viol, over, stats


def rowcap_imms(ir):
    u = ir["units"]["main"]
    recs = [r for r in u["records"] if r["k"] != "label"]
    off = u["labels"]["lg_nk"]
    j = [i for i, r in enumerate(recs) if r["off"] == off]
    assert len(j) == 1, "lg_nk not an instruction boundary"
    seq = recs[j[0] - 3:j[0]]                            # CMP_imm ROWCAP / BCC lg_nk / LDA_imm ROWCAP
    shape = [(r["k"], r["m"]) for r in seq]
    assert shape == [("ins", "CMP_imm"), ("br", "BCC"), ("ins", "LDA_imm")], f"lg_nk preamble changed: {shape}"
    return seq[0]["ops"][0], seq[2]["ops"][0]


def main():
    ok = True
    res = []

    def verdict(name, good, detail):
        nonlocal ok
        ok &= good
        res.append(name)
        print(f"  [{'PASS' if good else 'FAIL'}] {name}: {detail}")

    R = ram_map()
    print("== real image: couch flags + DRLATEGUARD=1")
    real = Image(capture("real", {"DRLATEGUARD": "1"}))
    B, cuts = census_bounds(real)
    lg_phases = [p for p in cuts if p.startswith("pp_ph") and all(c in cuts[p] for c in LG_CUT)]
    verdict("census cut map", len(lg_phases) == len(real.phases) - 1 and f"pp_ph{len(real.phases)}" not in lg_phases,
            f"lg cut on {lg_phases}; last phase pp_ph{len(real.phases)} ({real.phases[-1]}) keeps lg")
    viol, over, s = check_image(real, R, cuts, bounds=B)
    verdict("real: no census-cut label runs in its class", not viol,
            f"{s['hooks']} hooks, per-phase {s['cls']}, aborted {s['aborted']}; violations {len(viol)} {viol[:2]}")
    verdict("PC: every phase class populated", all(v > 0 for v in s["cls"].values()), str(s["cls"]))
    verdict("PC: lg_gate witness alive (aborted/idle hooks)", s["lg_seen"] > 0 and s["lg_in_abort"] > 0,
            f"lg_gate entered in {s['lg_seen']} hooks, {s['lg_in_abort']} of them aborted phase hooks")
    verdict("PC: spawn-upload witness alive", s["h2cp_seen"] > 0, f"h2_cp in {s['h2cp_seen']} hooks")
    verdict("PC: committing phase reaches lg_gate (why census keeps it)", s["last_lg"] > 0,
            f"{real.phases[-1]} hooks with lg_gate: {s['last_lg']}")
    verdict("measured py65 cycles <= census bound of the hook's class", not over, f"{len(over)} over {over[:2]}")
    ph = {k: v for k, v in B.items() if k.startswith("pp_ph")}
    verdict("aborted-hook bound dominated by every phase scenario", all(B["pp_abort"] <= v for v in ph.values()),
            f"pp_abort {B['pp_abort']} vs phase bounds {ph}")
    cmp_i, lda_i = rowcap_imms(real.ir)
    verdict("lg_row bound covers the IR's ROWCAP", max(cmp_i, lda_i) <= C.LOOP_BOUNDS["lg_row"],
            f"IR ROWCAP CMP#{cmp_i} LDA#{lda_i} vs LOOP_BOUNDS lg_row {C.LOOP_BOUNDS['lg_row']}")

    src = open(EMITTER).read()
    print("== mutants (each must be KILLED)")
    for name, edits, what in MUTANTS:
        msrc = src
        for anchor, repl in edits:
            n = msrc.count(anchor)
            if n != 1:
                verdict(f"{name} applied", False, f"anchor found {n}x (must be exactly 1): {anchor!r}")
                break
            msrc = msrc.replace(anchor, repl)
        else:
            mimg = Image(capture(name, {"DRLATEGUARD": "1"}, emitter_src=msrc))
            if mimg.flat == real.flat:
                verdict(f"{name} applied", False, "mutant image is byte-identical to the real one")
                continue
            _, mcuts = census_bounds(mimg)
            mv, _, ms = check_image(mimg, R, mcuts, stop_at_first=True)
            verdict(f"{name} KILLED ({what})", bool(mv), (mv[0][1] + f" @ {mv[0][0]}") if mv else
                    f"SURVIVED over {ms['hooks']} hooks")
    print("== mutant M_rowcap: python -O strips the emitter's ROWCAP assert")
    try:
        rimg = capture("M_rowcap", {"DRLATEGUARD": "1", "DRLATEGUARD_ROWCAP": "3"}, optimize=True)
        cmp_i, lda_i = rowcap_imms(rimg)
        verdict("M_rowcap KILLED (IR ROWCAP > census lg_row)", max(cmp_i, lda_i) > C.LOOP_BOUNDS["lg_row"],
                f"IR ROWCAP {cmp_i}/{lda_i} vs lg_row {C.LOOP_BOUNDS['lg_row']}")
    except SystemExit as e:
        verdict("M_rowcap built", False, str(e)[:300])
    print("GATE_LGCUT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
