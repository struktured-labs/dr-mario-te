#!/usr/bin/env python3
"""HUMAN-CHALLENGE CART gate (#148): DRHUMAN on the #140 hardened+pipelined class.

RULE 13 IS WHY THIS FILE EXISTS. The certificates already on the shelf --
GATE_HARDENED (#129/#133/#134/#114), test_prespipe (#126 enforcement 2),
test_p1slice, GATE_COMBO (#140) -- are all certificates for CvC images, where
BOTH sides are the driver. Putting a person on P1 produces a NEW OBJECT whose
emitted program is not any of those programs, so none of those sheets transfer.
This gate certifies the human image on its own bytes.

WHAT IS ACTUALLY DIFFERENT, and therefore what has to be re-proven:
  * P1's whole machine is GONE. `DRP1NATIVE=1 with DRHUMAN=1 is refused` and
    `DRP1SLICE=1 without DRP1NATIVE=1 is refused` are emitter asserts, so the
    P1 native search AND its #140 slice are not representable on this image.
    Everything #140 certified -- the PP_RAN phase/slice interlock, the
    slice-bearing admissible pairs -- is about a machine this cart does not
    contain. Its sheet cannot be inherited; the frame model must be rebuilt on
    the labels this image actually emits (H5, M2).
  * The cart must never press the person's buttons. On a CvC cart writing $F5
    is the executor's whole job; here it is the one thing that must never
    happen. That is a NEW safety property with no predecessor sheet at all, so
    it gets a gate and a killed mutant (H4, M1).
  * DRUNPAUSE (#133) and DRNAVESC are compiled OUT under DRHUMAN
    (`if UNPAUSE and not HUMAN_P1`, `if NAVESC and not HUMAN_P1`). We assert
    that as BYTE-IDENTITY rather than repeating the claim in prose (H2b): #133's
    unpausable-cart hazard is answered here by construction, not by its fix.
  * DRPRESTART/DRPRESPIPE remain fully live and are, if anything, MORE
    load-bearing: prestart triggers on P2's INCOMING volley, and on this cart
    the attacker is the human (H2a, H6).

GATES
  H1 PROVENANCE   a. deterministic rebuild == the shipped image
                  b. inverting ONLY the human deltas reproduces the certified
                     #140 combo cart (2b806db8) byte-exact -- binding this
                     image to the certified one by construction
  H2 FLAG LIVENESS (byte-identity per flag OFF)
                  a. each hardening flag OFF must CHANGE the bytes (live here)
                  b. each DRHUMAN-neutralised flag OFF must leave the bytes
                     IDENTICAL (compiled out -- measured, not assumed)
  H3 REFUSALS     DRP1SLICE / DRP1NATIVE / DRP1WIGGLE with DRHUMAN must all be
                  refused by the emitter
  H4 HUMAN-INPUT SAFETY  zero writes to $F5/$F7/GRAV_P1 anywhere in the emitted
                  hook code
  H5 ADMISSIBLE-FRAME CERTIFICATE  every admissible ordered hook pair fits the
                  29,780-cycle frame, on THIS image's scenario set
  H6 NOT-INERT    the unpipelined arm (DRPRESPIPE=0) is still OVER the frame on
                  the human image, so H5 is not vacuously green
  H7 KILLED MUTANTS
     M1 inject one STA $F5 into the IR      -> H4 must FAIL
     M2 sheet-inheritance (the Rule 13 defect itself): the #140 combo scenario
        set is NOT this image's scenario set -- reusing it is detectable
     M3 drop a prespipe phase cut           -> H5 must go OVER

Run with the dr-mario-mods venv python:
  /home/struktured/projects/dr-mario-mods/.venv/bin/python tests/test_human_cart.py
"""
import copy
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
MAN = "roms/manifests/human-hardened-pp3-20260823.json"
HUMAN_ROM = "roms/human-hardened-pp3-20260823.nes"
COMBO_ROM = "roms/combo-hardened-pp3sl-20260820.nes"
COMBO_MD5 = "2b806db8792ba525d77014f4260b84e1"
TMP = "tmp/human"
GAME_HEAD, EPS, FRAME = 2040, 300, 29780

# $F5/$F7 are P1's raw controller latch and derived-buttons byte; GRAV_P1 is P1's
# gravity counter (pinning it is how the driver freezes its own capsule mid-search).
P1_INPUT_ZP = (0xF5, 0xF7)
GRAV_P1 = 0x0312

ok = True


def check(label, cond, detail=""):
    global ok
    print(f"  {label:66s} {'PASS' if cond else 'FAIL'}{('  ' + detail) if detail else ''}")
    ok &= bool(cond)


def snapshot():
    return dict(json.load(open(MAN))["flag_snapshot"])


def build(out, overlay):
    """Build with the human snapshot + overlay. Returns bytes, or None if the
    emitter REFUSED the configuration (which is a result, not an error)."""
    env = dict(os.environ)
    env.update({k: str(v) for k, v in snapshot().items()})
    env.update({k: str(v) for k, v in overlay.items()})
    r = subprocess.run([PY, "tools/romgen.py", "build", "--out", out,
                        "--base", "drmario_v28cs.nes", "--tag", "human-gate-CHECKONLY"],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stdout + r.stderr)
    return open(out, "rb").read(), ""


def capture(out, *overlay):
    subprocess.run([PY, "tools/nmi126/capture_ir.py", MAN, out, *overlay],
                   check=True, capture_output=True)
    return json.load(open(out))


def scenarios(meta, drop_cut=None):
    """(worst admissible frame, table, per-scenario bounds) for an image.

    Scenario set is census.SCENARIO_CUTS merged with whatever prespipe phases
    THIS image emits -- derived from the IR's own labels, never inherited.
    """
    nodes = census.load_from_meta(meta)
    so = census.detect_site_overrides(meta, nodes)
    eb = census.detect_prespipe_bounds(meta)
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])
    pp_cuts, pp_order = census.prespipe_scenarios(have)
    scen = dict(census.SCENARIO_CUTS)
    scen.update(pp_cuts)
    res = {}
    for name, cuts in scen.items():
        cuts_here = [(k, l) for k, l in cuts if l in have and (k, l) != drop_cut]
        res[name] = census.Analyzer(nodes, cuts_here, site_overrides=so,
                                    extra_bounds=eb).worst(meta["units"]["wrapper"]["base"])
    pairs = [(pp_order[i], pp_order[i + 1]) for i in range(len(pp_order) - 1)]
    pairs += [(a, "pp_idle") for a in pp_order]
    pairs += [("pp_spawn", "pp_edge"), ("pp_idle", "pp_edge")]
    pairs = [(a, b) for a, b in pairs if a in res and b in res]
    table = [(a, b, res[a] + res[b] + 12 + GAME_HEAD + EPS) for a, b in pairs]
    return max(t for _, _, t in table), table, res, have


def reachable(nodes, entry):
    """Every CPU address the hook can actually execute, from `entry`.

    census.successors() gives intra-routine edges (a JSR falls THROUGH but does
    not descend); for reachability we must also follow the call target, so the
    body of every called routine counts as executable. Anything not in this set
    is emitted-but-dead code.
    """
    seen, work = set(), [entry]
    while work:
        a = work.pop()
        if a in seen or a not in nodes:
            continue
        seen.add(a)
        n = nodes[a]
        for s_, _ in census.successors(n, nodes):
            work.append(s_)
        if n["kind"] == "jsr":
            work.append(n["target"])
    return seen


def input_writes(meta, reachable_only=True):
    """Emitted stores that could touch the person's input or gravity.

    Returns (reachable_hits, dead_hits). A CvC cart writes $F5 constantly -- it
    is the executor's output. On a human cart the P1 executor block is still
    ASSEMBLED (the emitter jumps over it rather than omitting it: `act_p1:
    JMP act_done` under DRHUMAN), so a naive "count the STA $F5 opcodes" gate
    reports 8 hits on a cart that is in fact never able to reach one. The
    property that actually matters is REACHABILITY from the hook entry, so
    that is what we measure.
    """
    nodes = census.load_from_meta(meta)
    live = reachable(nodes, meta["units"]["wrapper"]["base"]) if reachable_only else set(nodes)
    hot, dead = [], []
    # operands live in the raw records, so walk those and map offset -> addr
    for uname, u in meta["units"].items():
        base = u["base"]
        for r in u["records"]:
            if r["k"] != "ins":
                continue
            ops = r.get("ops") or []
            is_hit = (r["m"] in ("STA_zp", "STX_zp", "STY_zp", "INC_zp", "DEC_zp")
                      and len(ops) == 1 and ops[0] in P1_INPUT_ZP)
            is_hit = is_hit or (r["m"] in ("STA_abs", "INC_abs", "DEC_abs")
                                and len(ops) == 2 and (ops[0] | ops[1] << 8) == GRAV_P1)
            if not is_hit:
                continue
            entry = (uname, r["off"], r["m"], ops)
            (hot if (base + r["off"]) in live else dead).append(entry)
    return hot, dead


# ------------------------------------------------------------------ H1 -----
def h1():
    os.makedirs(TMP, exist_ok=True)
    shipped = hashlib.md5(open(HUMAN_ROM, "rb").read()).hexdigest()
    a, err = build(f"{TMP}/h1_rebuild.nes", {})
    check("H1a deterministic rebuild == shipped human image", a is not None
          and hashlib.md5(a).hexdigest() == shipped,
          shipped if a is not None else err[-200:])

    # Invert ONLY the human deltas -> must land exactly on the certified #140 cart.
    b, err = build(f"{TMP}/h1_cvc.nes", {"DRHUMAN": "0", "DRP1NATIVE": "1",
                                         "DRP1SLICE": "1", "DRBUILDID_TAG": "PRES"})
    got = hashlib.md5(b).hexdigest() if b is not None else err[-200:]
    check("H1b inverting the human deltas == certified combo 2b806db8",
          b is not None and got == COMBO_MD5, got)
    return shipped


# ------------------------------------------------------------------ H2 -----
# LIVE: these change the emitted program on a HUMAN image, so the hardening they
# carry is really present here and not silently compiled out with P1's machine.
# Each entry is (label, overlay, baseline-overlay): DRPRESTART cannot be turned
# off alone (`DRPRESPIPE=1 without DRPRESTART=1 is refused`), so its arm is
# measured against the pipeline-off image rather than against the shipped one --
# otherwise "REFUSED" would masquerade as a failure of the flag to be live.
LIVE_ARMS = [
    ("DRVERFIX",    {"DRVERFIX": "0"},                          None),
    ("DRSTARTGUARD", {"DRSTARTGUARD": "0"},                     None),
    ("DRROTDIR",    {"DRROTDIR": "0"},                          None),
    ("DRPRESPIPE",  {"DRPRESPIPE": "0"},                        None),
    ("DRPRESTART",  {"DRPRESTART": "0", "DRPRESPIPE": "0"},     {"DRPRESPIPE": "0"}),
    ("DRTUCK",      {"DRTUCK": "0"},                            None),
]
# NEUTRALISED: gated `and not HUMAN_P1` in the emitter. Byte-identity is the
# measurement that turns "we believe it is compiled out" into a fact.
NEUTRALISED_FLAGS = ["DRUNPAUSE", "DRNAVESC"]
# SUBSUMED: byte-inert on THIS flag set, but not because of DRHUMAN -- every site
# NO_FREEZE guards is `NO_FREEZE or X` for an X that is already on here
# (`COLDINIT or not NO_FREEZE`, `NO_FREEZE or ROTFIX`, `NO_FREEZE or COLGATE`,
# and the RECOMMIT gate is opened by DRRECOMMIT_NOFREEZE=1). Recorded as a
# measured fact so nobody later reads DRNOFREEZE as a live knob on this class.
SUBSUMED_FLAGS = ["DRNOFREEZE"]


def h2(shipped):
    for name, overlay, base_overlay in LIVE_ARMS:
        b, err = build(f"{TMP}/h2_{name}.nes", overlay)
        got = hashlib.md5(b).hexdigest() if b is not None else "REFUSED: " + err[-90:]
        if base_overlay is None:
            ref = shipped
        else:
            rb, rerr = build(f"{TMP}/h2_{name}_ref.nes", base_overlay)
            ref = hashlib.md5(rb).hexdigest() if rb is not None else "BUILD-FAILED"
        check(f"H2a {name} OFF changes the bytes (flag is LIVE on the human image)",
              b is not None and got != ref, got)
    for f in NEUTRALISED_FLAGS:
        b, err = build(f"{TMP}/h2_{f}.nes", {f: "0"})
        got = hashlib.md5(b).hexdigest() if b is not None else "REFUSED"
        check(f"H2b {f}=0 is BYTE-IDENTICAL (compiled out under DRHUMAN)",
              b is not None and got == shipped, got)
    for f in SUBSUMED_FLAGS:
        b, err = build(f"{TMP}/h2_{f}.nes", {f: "0"})
        got = hashlib.md5(b).hexdigest() if b is not None else "REFUSED"
        check(f"H2c {f}=0 is BYTE-IDENTICAL (SUBSUMED, not a DRHUMAN effect)",
              b is not None and got == shipped, got)


# ------------------------------------------------------------------ H3 -----
def h3():
    for flag in ("DRP1SLICE", "DRP1NATIVE", "DRP1WIGGLE"):
        b, err = build(f"{TMP}/h3_{flag}.nes", {flag: "1"})
        refused = b is None and "refused" in err.lower()
        check(f"H3 {flag}=1 with DRHUMAN=1 is REFUSED by the emitter", refused,
              "" if refused else (err[-160:] if b is None else "BUILT -- assert missing"))


# ------------------------------------------------------------------ H4 -----
def h4(meta):
    hot, dead = input_writes(meta)
    check("H4a no REACHABLE write to $F5/$F7/GRAV_P1 (never presses the human)",
          len(hot) == 0, f"{len(hot)} reachable" + (f" {hot[:4]}" if hot else ""))
    # Reported, not failed: the P1 executor block IS assembled on this image and
    # IS unreachable. Stating the number keeps the H4a PASS honest -- it is a
    # reachability result, not an absence-of-opcodes result.
    print(f"       (P1 executor emitted but UNREACHABLE: {len(dead)} dead "
          f"$F5/$F7/GRAV_P1 stores behind `act_p1: JMP act_done`)")
    check("H4b the dead P1 executor is really present (H4a is a reachability claim)",
          len(dead) > 0, f"{len(dead)} dead stores")
    return hot, dead


# ------------------------------------------------------------------ main ---
def main():
    print("=" * 92)
    print("HUMAN-CHALLENGE CART GATE (#148): DRHUMAN on the #140 hardened+pipelined class")
    print("=" * 92)

    shipped = h1()
    h2(shipped)
    h3()

    meta = capture(f"{TMP}/gate_human_ir.json")
    h4(meta)

    worst, table, res, have = scenarios(meta)
    for a, b, t in sorted(table, key=lambda x: -x[2])[:3]:
        print(f"       {a:12s} + {b:12s} = {t} of {FRAME}  margin {FRAME - t:+d}")
    check("H5 every admissible frame fits on this image's own scenario set",
          worst < FRAME, f"worst {worst}, margin {FRAME - worst:+d}")

    # H6 NOT-INERT: same image with the pipeline off must still be OVER, i.e. the
    # #126 hazard is present on a HUMAN cart too and DRPRESPIPE is load-bearing here.
    meta_off = capture(f"{TMP}/gate_human_nopp_ir.json", "DRPRESPIPE=0")
    nodes_off = census.load_from_meta(meta_off)
    so_off = census.detect_site_overrides(meta_off, nodes_off)
    have_off = set()
    for n in nodes_off.values():
        have_off.update(n.get("labels") or [])
    off_rel = census.Analyzer(
        nodes_off, [(k, l) for k, l in census.SCENARIO_CUTS["release_edge"] if l in have_off],
        site_overrides=so_off).worst(meta_off["units"]["wrapper"]["base"])
    off_frame = off_rel + res["pp_idle"] + 12 + GAME_HEAD + EPS
    check("H6 NOT-INERT: unpipelined arm still OVER the frame on the human image",
          off_frame >= FRAME, f"unpipelined {off_frame} vs {FRAME}")

    # ---- H7 mutants ----
    # M1: the PLAUSIBLE regression, not a synthetic one. The human passthrough is
    # a single `JMP act_done` that jumps OVER the still-assembled P1 executor. Point
    # that jump at the executor instead (exactly what reordering the emitter's
    # if/elif chain would do) and the reachability gate must go red.
    m1 = copy.deepcopy(meta)
    u = m1["units"]["main"]
    tgt = next(r for r in u["records"]
               if r["k"] == "jmp" and r["off"] == u["labels"]["act_p1"])
    tgt["target"] = "act_p1_go"
    hot_m1, _ = input_writes(m1)
    check("H7 M1 act_p1 passthrough re-pointed at the executor -> H4a FAILS",
          len(hot_m1) > 0, f"{len(hot_m1)} reachable stores after mutation")

    # M2: the Rule 13 defect itself. The #140 sheet's scenario set is built on
    # slice labels; this image has none, so a sheet reused wholesale is a sheet
    # written about a different program -- and that is mechanically detectable.
    combo_meta = json.load(open("tmp/combo/gate_combo_ir.json")) \
        if os.path.exists("tmp/combo/gate_combo_ir.json") else None
    if combo_meta is None:
        subprocess.run([PY, "tools/nmi126/capture_ir.py",
                        "roms/manifests/combo-hardened-pp3sl-20260820.json",
                        f"{TMP}/m2_combo_ir.json"], check=True, capture_output=True)
        combo_meta = json.load(open(f"{TMP}/m2_combo_ir.json"))
    combo_have = set()
    for n in census.load_from_meta(combo_meta).values():
        combo_have.update(n.get("labels") or [])
    slice_labels = {"p1s_ppguard", "p1s_tick", "p1s_idle"}
    check("H7 M2 sheet-inheritance detectable: #140 slice labels absent here",
          (slice_labels & combo_have) and not (slice_labels & have),
          f"combo has {sorted(slice_labels & combo_have)}, human has "
          f"{sorted(slice_labels & have) or 'none'}")

    # M3: the census cuts must BIND. Drop each declared cut in turn; at least one
    # must make the certificate worse, or H5 is green because nothing was cut.
    binding = []
    for name, cuts in census.prespipe_scenarios(have)[0].items():
        for cut in cuts:
            if cut[1] not in have:
                continue
            w_drop, _, _, _ = scenarios(meta, drop_cut=cut)
            if w_drop > worst:
                binding.append((name, cut, w_drop))
    check("H7 M3 at least one prespipe cut BINDS (H5 is not green by vacuity)",
          len(binding) > 0,
          f"{len(binding)} binding; worst example {max(binding, key=lambda x: x[2])[1]} "
          f"{worst} -> {max(binding, key=lambda x: x[2])[2]}" if binding else "none bind")

    for f in os.listdir(TMP):
        if f.endswith(".nes"):
            os.remove(os.path.join(TMP, f))
    if os.path.exists("roms/manifests/human-gate-CHECKONLY.json"):
        os.remove("roms/manifests/human-gate-CHECKONLY.json")

    print()
    print("test_human_cart: " + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
