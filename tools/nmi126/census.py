#!/usr/bin/env python3
"""#126 NMI-hook cycle census, stage 2: static worst-case cycle bound.

Input: the IR JSON from capture_ir.py (ground-truth-gated against the emitter's
own assembled bytes). Output: a sound UPPER BOUND on the cycles one hook
invocation can consume, per entry point, plus the worst-case decomposition path.

Soundness rules (any violation is a HARD FAIL, never a warning):
  - every back-edge (loop) must have a declared iteration bound in LOOP_BOUNDS,
    keyed (config-agnostic) by the loop-head label; an undeclared loop kills
    the run and prints where it is;
  - every JSR/JMP target must resolve inside the captured units or be listed in
    EXTERNAL_COSTS with a declared worst-case cost;
  - any opcode outside the cycle table kills the run;
  - recursion (JSR cycles) kills the run.

Conservatisms (all one-directional, bound only gets LOOSER):
  - indexed absolute reads always charged the +1 page-cross penalty;
  - taken branches charged page-cross exactly (addresses are known);
  - branch direction is free choice: mutually-dependent predicates are not
    modeled, so infeasible path combinations may inflate the bound (never
    deflate it);
  - a loop's every iteration is charged its single worst iteration.

Usage:
  python3 tools/nmi126/census.py tmp/nmi126/v6e_ir.json
"""
import json
import sys
from collections import defaultdict

# Worst-case cycle table for the emitter's closed mnemonic set.
# Indexed absolute reads include the +1 page-cross penalty unconditionally.
CYC = {
    # imm
    "LDA_imm": 2, "LDX_imm": 2, "LDY_imm": 2, "CMP_imm": 2, "CPX_imm": 2,
    "CPY_imm": 2, "ADC_imm": 2, "SBC_imm": 2, "AND_imm": 2, "ORA_imm": 2,
    "EOR_imm": 2,
    # zp
    "LDA_zp": 3, "LDX_zp": 3, "LDY_zp": 3, "CMP_zp": 3, "CPX_zp": 3,
    "CPY_zp": 3, "ADC_zp": 3, "SBC_zp": 3, "AND_zp": 3, "ORA_zp": 3,
    "STA_zp": 3, "STX_zp": 3, "STY_zp": 3,
    "INC_zp": 5, "DEC_zp": 5,
    # abs
    "LDA_abs": 4, "LDX_abs": 4, "LDY_abs": 4, "CMP_abs": 4, "ADC_abs": 4,
    "SBC_abs": 4, "STA_abs": 4, "ORA_abs": 4, "AND_abs": 4, "EOR_abs": 4,
    "INC_abs": 6, "DEC_abs": 6,
    # indexed abs (reads +1 page-cross always; STA abs,X/Y is fixed 5)
    "LDA_absX": 5, "LDA_absY": 5, "CMP_absX": 5, "CMP_absY": 5,
    "STA_absX": 5, "STA_absY": 5,
    # implied / accumulator
    "ASL_A": 2, "LSR_A": 2, "ROR_A": 2, "CLC": 2, "SEC": 2, "NOP": 2,
    "TAY": 2, "TYA": 2, "TAX": 2, "TXA": 2, "INX": 2, "DEX": 2, "INY": 2,
    "DEY": 2,
    "PHA": 3, "PLA": 4,
}

# ---- Loop iteration bounds, keyed by loop-head label. -----------------------
# Every entry must carry a justification. The analyzer hard-fails on any
# back-edge whose head label is not listed here.
LOOP_BOUNDS = {
    # ================= driver main (unit-1) =================
    # pre_run 4-in-a-row scanner (DRPRESTART): walks PRE_MIN..PRE_MAX by
    # PRE_TMP. Emitted callers use (row: step 1, span 8) or (col: step 8,
    # span 16); worst = 16 iterations. Termination needs (MAX-MIN)%step==0,
    # which every emitted caller satisfies by construction.
    "pr_l": 16,
    # ================= v18 P1 AI ($9000) =================
    # land_col row scan: Y = col(0-7), +8 per iter, exits at Y>=0x80 -> <=16.
    "lc_scan": 16,
    # scan_run backward walk: Z_SOFF steps -Z_STEP until < Z_MIN / hits a
    # non-matching cell; axis length <= 16 (col, step 8) or 8 (row, step 1).
    "sr_back": 16,
    # scan_run forward walk: Z_SOFF steps +Z_STEP while <= Z_MAX; same axis
    # geometry -> <= 16 iterations.
    "sr_fwd": 16,
    # -------- DRPRESTART pre_tick (the known largest single-hook spike) -----
    # board copy $0500 -> PRE_BUF: X 0..127, CPX #128 -> exactly 128.
    "pt_cp": 128,
    # orphan guard: PRE_COL 0..7, exit at CMP #8 -> 8 head passes.
    "pt_og": 8,
    # settle column walk: PRE_COL 0..7 -> 8 head passes.
    "pt_col": 8,
    # settle fall: PRE_OFF walks down by +8 from row r, at most 16 rows.
    "pt_dn": 16,
    # match check: PRE_I 0..PRE_N with PRE_N <= 8 (one record per column);
    # head executes PRE_N+1 <= 9 times.
    "pt_mchk": 9,
    # NOTE: the DRPRESPIPE match drivers pp_m2.. are NOT declared here. Their
    # bound is the phase QUOTA, which is a build knob (DRPRESPIPE_Q), so it is
    # DERIVED FROM THE IR by detect_prespipe_bounds() -- a hand-written number
    # would silently keep the old bound after a re-split.
    # projection upload PRE_BUF -> $5x00 window: X 0..127 -> exactly 128.
    "pt_up": 128,
    # divide-by-3 of a reserve value 0..8: quotient <= 2 -> head passes <= 3.
    "pt_dv": 3,
    # STUDYCOUNTS level-display divide-by-10 (tags l1/l2): 8-bit value ->
    # quotient <= 25 -> head passes <= 26.
    "sc_l1": 26, "sc_l2": 26,
    # handle(2) _start board upload $0500 -> window: X 0..127 -> exactly 128.
    "h2_cp": 128,
    # DISTGATE fall scan: one row per pass, DG_N-capped, board is 16 rows.
    "dg_row": 16,
    # DISTGATE per-row cell walk: Y = DG_CSPAN <= 8 (span of a capsule +1).
    "dg_cell": 8,
    # -------- v18 P1 AI placement passes --------
    # vertical pass: Z_COL 0..7, exit at CMP #8 -> 8 head passes.
    "v_loop": 8,
    # horizontal pass: Z_COL 0..6, exit at CMP #7 -> 7 head passes.
    "h_loop": 7,
}

# JSR/JMP targets outside the captured units: {cpu_addr: (name, worst_cycles)}.
EXTERNAL_COSTS = {
}


def load(path):
    meta = json.load(open(path))
    return meta, load_from_meta(meta)


def load_from_meta(meta):
    # Global instruction map: cpu addr -> node
    nodes = {}
    unit_of = {}
    for uname, u in meta["units"].items():
        base = u["base"]
        labels = u["labels"]
        addr_label = {}
        for lname, off in labels.items():
            addr_label.setdefault(base + off, []).append(lname)
        recs = [r for r in u["records"] if r["k"] != "label"]
        for i, r in enumerate(recs):
            addr = base + r["off"]
            if r["k"] == "raw":
                continue  # data, never control-flow reachable (verified by traversal)
            if r["k"] == "ins":
                size = 1 + len(r["ops"])
                node = {"addr": addr, "m": r["m"], "size": size, "kind": "ins"}
            elif r["k"] == "br":
                node = {"addr": addr, "m": r["m"], "size": 2, "kind": "br",
                        "target": base + labels[r["target"]]}
            elif r["k"] in ("jmp", "jsr"):
                t = r["target"]
                dest = base + labels[t] if isinstance(t, str) else t
                node = {"addr": addr, "m": r["m"], "size": 3, "kind": r["k"],
                        "target": dest}
            node["labels"] = addr_label.get(addr, [])
            node["unit"] = uname
            nodes[addr] = node
            unit_of[addr] = uname
    return nodes


def instr_cost(node):
    k = node["kind"]
    if k == "ins":
        m = node["m"]
        if m == "RTS":
            return 6
        if m == "BRK":
            raise SystemExit(f"BRK reachable at ${node['addr']:04X}")
        assert m in CYC, f"no cycle entry for {m} at ${node['addr']:04X}"
        return CYC[m]
    if k == "br":
        return None  # edge-dependent
    if k == "jmp":
        return 3
    if k == "jsr":
        return 6
    raise AssertionError(k)


def successors(node, nodes):
    """Intra-routine successor (addr, edge_cycles) pairs. JSR falls through
    (call cost handled separately); RTS/RTI terminal."""
    a, k = node["addr"], node["kind"]
    if k == "ins" and node["m"] == "RTS":
        return []
    nxt = a + node["size"]
    if k == "br":
        t = node["target"]
        # taken: 3 + 1 if page cross of (pc_after_branch, target)
        taken = 3 + (1 if ((nxt & 0xFF00) != (t & 0xFF00)) else 0)
        return [(nxt, 2), (t, taken)]
    if k == "jmp":
        return [(node["target"], 3)]
    # plain ins or jsr: fall through with own cost
    return [(nxt, instr_cost(node))]


class Analyzer:
    def __init__(self, nodes, cuts=(), site_overrides=None, extra_bounds=None):
        """cuts: iterable of edge-cut specs applied to the whole graph:
          ('into', label)  -- remove EVERY edge whose destination is the label's
                              address (fall-through included): 'this path is not
                              taken this hook'.
          ('fallof', label) -- for branches TARGETING the label, remove their
                              fall-through edge: 'the branch to label is always
                              taken'.
        A label absent from the image is a hard error (a silently ignored cut
        would loosen nothing and quietly report the wrong scenario)."""
        self.nodes = nodes
        self.extra_bounds = dict(extra_bounds or {})
        self.routine_cost = {}   # (entry, overrides) -> (worst_cycles, witness)
        self.in_progress = set()
        self.site_overrides = site_overrides or {}
        self.cut_edges = set()
        label_addr = {}
        for a, n in nodes.items():
            for l in n.get("labels") or []:
                label_addr[l] = a
        for kind, lab in cuts:
            assert lab in label_addr, f"cut label {lab!r} not in image"
            t = label_addr[lab]
            if kind == "into":
                for a, n in nodes.items():
                    for sdst, _ in successors(n, nodes):
                        if sdst == t:
                            self.cut_edges.add((a, t))
            elif kind == "fallof":
                for a, n in nodes.items():
                    if n["kind"] == "br" and n["target"] == t:
                        self.cut_edges.add((a, a + 2))
            else:
                raise SystemExit(f"unknown cut kind {kind}")

    def succ(self, node):
        return [(sdst, ec) for sdst, ec in successors(node, self.nodes)
                if (node["addr"], sdst) not in self.cut_edges]

    def resolve(self, addr, ctx):
        if addr in self.nodes:
            return self.nodes[addr]
        raise SystemExit(
            f"UNRESOLVED target ${addr:04X} reached from {ctx} -- add to "
            f"EXTERNAL_COSTS or capture the unit")

    def worst(self, entry, overrides=frozenset()):
        key = (entry, overrides)
        if key in self.routine_cost:
            return self.routine_cost[key][0]
        if key in self.in_progress:
            raise SystemExit(f"RECURSION through ${entry:04X}")
        self.in_progress.add(key)
        bounds = dict(LOOP_BOUNDS)
        bounds.update(self.extra_bounds)
        bounds.update(dict(overrides))

        # 1. collect routine nodes (intra-routine traversal)
        seen = set()
        stack = [entry]
        while stack:
            a = stack.pop()
            if a in seen:
                continue
            seen.add(a)
            n = self.resolve(a, f"routine ${entry:04X}")
            for s, _ in self.succ(n):
                if s not in seen:
                    stack.append(s)
            if n["kind"] == "jsr":
                t = n["target"]
                if t in self.nodes:
                    self.worst(t, self.site_overrides.get(a, frozenset()))
                elif t not in EXTERNAL_COSTS:
                    raise SystemExit(
                        f"JSR ${t:04X} from ${a:04X} unresolved -- declare in "
                        f"EXTERNAL_COSTS or capture it")

        # 2. DFS back-edge detection
        color = {}
        back_edges = []
        order = []

        def dfs(a):
            color[a] = 1
            for s, _ in self.succ(self.nodes[a]):
                if color.get(s, 0) == 0:
                    dfs(s)
                elif color[s] == 1:
                    back_edges.append((a, s))
            color[a] = 2
            order.append(a)

        sys.setrecursionlimit(100000)
        dfs(entry)
        rpo = list(reversed(order))
        rpo_ix = {a: i for i, a in enumerate(rpo)}

        # 3. loops: group back-edges by head; natural loop = head + nodes that
        # reach a tail without passing head
        loops = defaultdict(list)
        for tail, head in back_edges:
            loops[head].append(tail)
        extra = defaultdict(int)     # head addr -> added cycles from loop collapse
        # innermost-first: compute loop node sets, sort by size
        loop_nodes = {}
        # build predecessor map (intra-routine)
        preds = defaultdict(list)
        for a in seen:
            for s, _ in self.succ(self.nodes[a]):
                preds[s].append(a)
        for head, tails in loops.items():
            body = {head}
            work = [t for t in tails]
            while work:
                x = work.pop()
                if x in body:
                    continue
                body.add(x)
                work.extend(p for p in preds[x] if p not in body)
            loop_nodes[head] = body

        def head_label(head):
            labs = self.nodes[head].get("labels") or []
            return labs[0] if labs else None

        missing = []
        for head in loops:
            lab = head_label(head)
            if lab is None or lab not in bounds:
                tails = ", ".join(f"${t:04X}" for t in loops[head])
                missing.append(f"  head ${head:04X} label={lab!r} unit="
                               f"{self.nodes[head]['unit']} back-edges from {tails}")
        if missing:
            raise SystemExit("UNDECLARED LOOPS (declare LOOP_BOUNDS):\n"
                             + "\n".join(missing))
        # innermost first = smallest body first
        for head in sorted(loops, key=lambda h: len(loop_nodes[h])):
            lab = head_label(head)
            bound = bounds[lab]
            # worst single iteration: longest acyclic path head->tail inside
            # the body (back-edges of THIS loop excluded) + the back-edge cost
            body = loop_nodes[head]
            best_iter = 0
            # longest path within body via DP over RPO restricted to body
            dist = {head: 0}
            for a in rpo:
                if a not in body or a not in dist:
                    continue
                d = dist[a]
                n = self.nodes[a]
                cost_here = extra.get(a, 0) if a != head else 0
                if n["kind"] == "jsr":
                    t = n["target"]
                    ck = (t, self.site_overrides.get(a, frozenset()))
                    call = (6 + self.routine_cost[ck][0]) if t in self.nodes else \
                           (6 + EXTERNAL_COSTS[t][1])
                else:
                    call = None
                for s, ec in self.succ(n):
                    if s not in body:
                        continue
                    if (a, s) in [(t, head) for t in loops[head]]:
                        continue  # back-edge itself excluded from DP graph
                    step = (call if call is not None else ec) + cost_here
                    if n["kind"] == "jsr":
                        step = call + cost_here
                    nd = d + step
                    if nd > dist.get(s, -1):
                        dist[s] = nd
            for tail in loops[head]:
                if tail not in dist:
                    continue
                n = self.nodes[tail]
                # back-edge cost: branch taken (or jmp)
                be_cost = 3
                if n["kind"] == "br":
                    nxt = tail + 2
                    be_cost = 3 + (1 if (nxt & 0xFF00) != (head & 0xFF00) else 0)
                it = dist[tail] + be_cost + extra.get(tail, 0)
                best_iter = max(best_iter, it)
            extra[head] += (bound - 1) * best_iter

        # 4. longest path entry -> terminal on the DAG (back-edges removed)
        be_set = set()
        for head, tails in loops.items():
            for t in tails:
                be_set.add((t, head))
        dist = {entry: 0}
        parent = {}
        worst_term = (0, entry)
        for a in rpo:
            if a not in dist:
                continue
            d = dist[a] + extra.get(a, 0)
            n = self.nodes[a]
            succs = [(s, ec) for s, ec in self.succ(n)
                     if (a, s) not in be_set]
            if n["kind"] == "ins" and n["m"] == "RTS":
                total = d + 6
                if total > worst_term[0]:
                    worst_term = (total, a)
                continue
            if n["kind"] == "jsr":
                t = n["target"]
                ck = (t, self.site_overrides.get(a, frozenset()))
                call = (6 + self.routine_cost[ck][0]) if t in self.nodes else \
                       (6 + EXTERNAL_COSTS[t][1])
                succs = [(s, call) for s, _ in succs]
            for s, ec in succs:
                nd = d + ec
                if nd > dist.get(s, -1):
                    dist[s] = nd
                    parent[s] = a
        # witness path (label trail)
        trail = []
        a = worst_term[1]
        while a in parent:
            labs = self.nodes[a].get("labels") or []
            if labs:
                trail.append(labs[0])
            a = parent[a]
        trail.reverse()
        self.in_progress.discard(key)
        self.routine_cost[key] = (worst_term[0], trail)
        return worst_term[0]


def detect_site_overrides(meta, nodes):
    """Call-context loop bounds, auto-derived from the IR itself:
    pre_run's pr_l walks PRE_MIN..PRE_MAX by PRE_TMP; the emitter sets
    PRE_TMP (LDA_imm v / STA_abs PRE_TMP) immediately before each JSR pre_run.
    step 1 = row scan (8 cells), step 8 = column scan (16 cells). A site whose
    step cannot be recovered keeps the global conservative bound (16)."""
    consts = meta.get("consts") or {}
    if "PRE_TMP" not in consts:
        return {}
    pre_tmp = consts["PRE_TMP"]
    u = meta["units"]["main"]
    base, labels = u["base"], u["labels"]
    if "pre_run" not in labels:
        return {}
    pre_run_addr = base + labels["pre_run"]
    overrides = {}
    last_imm = None
    step_at_jsr = None
    for r in u["records"]:
        if r["k"] == "ins" and r["m"] == "LDA_imm":
            last_imm = r["ops"][0]
        elif (r["k"] == "ins" and r["m"] == "STA_abs"
              and r["ops"] == [pre_tmp & 0xFF, (pre_tmp >> 8) & 0xFF]):
            step_at_jsr = last_imm
        elif r["k"] == "jsr":
            t = r["target"]
            dest = base + labels[t] if isinstance(t, str) else t
            if dest == pre_run_addr and step_at_jsr in (1, 8):
                overrides[base + r["off"]] = frozenset(
                    {("pr_l", 8 if step_at_jsr == 1 else 16)})
    return overrides


def detect_prespipe_bounds(meta):
    """Per-phase loop bounds for the DRPRESPIPE match drivers, read out of the
    IR's own quota compares -- the same discipline as detect_site_overrides.

    Each driver head pp_m<N> opens either
        LDA PRE_I / CMP_imm quota / BCS done   (a quota-bounded phase), or
        LDA PRE_I / CMP_abs PRE_N / BCS done   (the LAST phase, PRE_N-bounded).
    Records run are (quota - previous quota), and the head executes once more
    than that. A head that does not match this shape is a HARD FAIL: falling
    back to the loose 9 would still be sound but would quietly destroy the
    per-phase certificate the split exists to produce."""
    u = meta["units"].get("main")
    if not u:
        return {}
    labels = u["labels"]
    heads = sorted((l for l in labels if l.startswith("pp_m")
                    and l[4:].isdigit()), key=lambda l: int(l[4:]))
    if not heads:
        return {}
    recs = [r for r in u["records"] if r["k"] != "label"]
    by_off = {r["off"]: i for i, r in enumerate(recs)}
    out = {}
    prev_q = 0
    for i, h in enumerate(heads):
        j = by_off.get(labels[h])
        if j is None:
            raise SystemExit(f"prespipe: head {h} is not an instruction boundary")
        a0, a1 = recs[j], recs[j + 1]
        if not (a0["k"] == "ins" and a0["m"] == "LDA_abs"):
            raise SystemExit(f"prespipe: {h} does not open with LDA PRE_I")
        if a1["k"] == "ins" and a1["m"] == "CMP_imm":
            q = a1["ops"][0]
            if i == len(heads) - 1:
                raise SystemExit(f"prespipe: last phase {h} is quota-bounded; "
                                 "records above the final quota would never run")
        elif a1["k"] == "ins" and a1["m"] == "CMP_abs":
            if i != len(heads) - 1:
                raise SystemExit(f"prespipe: non-final phase {h} has no quota")
            q = 8                      # PRE_N <= 8 (one settle record per column)
        else:
            raise SystemExit(f"prespipe: {h} quota compare not recognised "
                             f"({a1.get('m')})")
        if q <= prev_q or q > 8:
            raise SystemExit(f"prespipe: {h} quota {q} not in ({prev_q}, 8]")
        out[h] = (q - prev_q) + 1
        prev_q = q
    if prev_q != 8:
        raise SystemExit(f"prespipe: phases cover only {prev_q} of 8 records")
    return out


SCENARIO_CUTS = {
    # Per-hook path classes. Every spike path is edge-triggered (fires at most
    # once per its trigger) and the cuts below EXCLUDE it from a scenario:
    #   pt_edge       DRPRESTART release-edge projection+upload (P2)
    #   h1_start/h2_start  spawn-edge board upload + GO (per player window)
    #   do_init       PRG-RAM cold init (power-on only)
    #   p1n search    DRP1NATIVE per-pill depth-1 search (fallof p1n_nosearch
    #                 = 'the skip branch is always taken' = no search)
    "steady_play": [("into", "pt_edge"), ("into", "h1_start"),
                     ("into", "h2_start"), ("into", "do_init"),
                     ("fallof", "p1n_nosearch")],
    "spawn_edge_p2": [("into", "pt_edge"), ("into", "h1_start"),
                       ("into", "do_init"), ("fallof", "p1n_nosearch")],
    "release_edge": [("into", "h1_start"), ("into", "h2_start"),
                      ("into", "do_init"), ("fallof", "p1n_nosearch")],
    "p1_search": [("into", "pt_edge"), ("into", "h1_start"),
                   ("into", "h2_start"), ("into", "do_init")],
    # ---- DRPRESPIPE per-phase classes (absent labels are skipped, so these
    # collapse onto the scenarios above on a non-pipelined image). Exactly one
    # phase runs per hook: PP_PH is read once at the top of pre_tick and each
    # phase either RTSes or reaches pt_bail, so cutting the other entries is a
    # statement about the DISPATCH, not an assumption about the workload.
    #
    # ⚠ The h2_cp cut is the load-bearing one and it is PROVEN, not assumed:
    # handle(2)'s `_start` opens `LDA PEND2 / BNE st1 / JMP h2_done`, so the
    # 128-byte spawn upload requires PEND2 != 0 -- and pp_disp ABORTS the whole
    # pipeline when PEND2 != 0 (and when ARMED2 != 0). A phase hook and a
    # spawn-edge upload are therefore mutually exclusive BY THE ABORT CHECKS.
    # Cutting `h2_cp` (the upload loop head) rather than `h2_start` keeps the
    # cheap guard path in the graph, so the cut removes only what the guard
    # provably removes. tests/test_prespipe.py M3 deletes the abort check and
    # must fail, which is what keeps this certificate honest.
}

# Common cuts for every DRPRESPIPE phase class: no spawn upload (proven above), no
# power-on init, no P1 search.
_PP_BASE = [("into", "h1_start"), ("into", "h2_cp"), ("into", "do_init"),
            ("fallof", "p1n_nosearch")]


def prespipe_scenarios(have):
    """Per-phase scenario cuts for a DRPRESPIPE image, derived from the labels the
    image actually carries (the phase COUNT is a build knob, DRPRESPIPE_Q), so a
    re-split cannot silently leave a phase uncertified. Returns {} on an image
    without the pipeline."""
    if "pp_disp" not in have:
        return {}
    match = sorted((l for l in have if l.startswith("pp_m")
                    and l[4:].isdigit()), key=lambda l: int(l[4:]))
    phases = ["pp_ph1"] + match           # dispatch entry label per phase, in order
    # ⚠ steady_play / spawn_edge_p2 are NOT usable as the "other hook" of a pair
    # on a pipelined image: they cut only pt_edge, so they still admit a PHASE
    # hook and pairing one with a phase double-counts the pipeline. These two
    # classes cut BOTH entries (no edge, no phase) and are the honest partners.
    #
    # COMBINED IMAGE (DRPRESPIPE + DRP1SLICE, #140): a hook can otherwise carry
    # BOTH a pp phase (~10.7k) and a p1 slice tick (~6k) -- the pairing NEITHER
    # lane's certificate covered, and the naive bound is 35.8k > 29,780, a real
    # OVER. The emitter's PP_RAN interlock makes the exclusion true BY GUARD:
    # pre_tick sets PP_RAN on every pipeline-work hook (edge family, phases,
    # bail, commit) and the slice dispatch branches to p1s_idle on it. So on a
    # combined image every pipeline-class scenario adds ("fallof","p1s_idle") --
    # "every branch to p1s_idle is taken", the exact analogue of the
    # p1n_nosearch cut -- and the slice tick is admitted ONLY in pp_idle /
    # pp_spawn, whose hooks the interlock leaves alone. The cut's premise is
    # verified from the IR by tests/test_combo_cart.py (guard present between
    # the slice dispatch and the JSR), whose mutants delete the guard and must
    # fail. On a slice-less pipelined image "p1s_idle" is absent and the cut is
    # dropped by the caller's have-filter as before.
    interlock = [("fallof", "p1s_idle")] if "p1s_ppguard" in have else []
    out = {"pp_edge": [("into", "pp_disp")] + interlock + _PP_BASE,
           "pp_idle": [("into", "pp_disp"), ("into", "pt_edge")] + _PP_BASE,
           "pp_spawn": [("into", "pp_disp"), ("into", "pt_edge"),
                        ("into", "h1_start"), ("into", "do_init"),
                        ("fallof", "p1n_nosearch")]}
    for i, entry in enumerate(phases):
        others = [("into", e) for e in phases if e != entry]
        out[f"pp_ph{i + 1}"] = [("into", "ppd_skip")] + others + interlock + _PP_BASE
    return out, ["pp_edge"] + [f"pp_ph{i + 1}" for i in range(len(phases))]



def main():
    path = sys.argv[1]
    meta, nodes = load(path)
    units = meta["units"]
    wrap_entry = units["wrapper"]["base"]
    main_entry = meta["main_cpu"]
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])

    print(f"config: {meta['manifest']}")
    results = {}
    so = detect_site_overrides(meta, nodes)
    eb = detect_prespipe_bounds(meta)
    an_all = Analyzer(nodes, site_overrides=so, extra_bounds=eb)
    results["ALL_PATHS"] = an_all.worst(wrap_entry)
    pp = prespipe_scenarios(have)
    pp_cuts, pp_order = pp if pp else ({}, [])
    scenarios = dict(SCENARIO_CUTS)
    scenarios.update(pp_cuts)
    for name, cuts in scenarios.items():
        cuts_here = [(k, l) for k, l in cuts if l in have]
        skipped = [l for k, l in cuts if l not in have]
        an = Analyzer(nodes, cuts_here, site_overrides=so, extra_bounds=eb)
        results[name] = an.worst(wrap_entry)
        note = f"  (absent labels skipped: {','.join(skipped)})" if skipped else ""
        print(f"  {name:16s} hook worst = {results[name] + 6:6d} cyc{note}")
    print(f"  {'ALL_PATHS':16s} hook worst = {results['ALL_PATHS'] + 6:6d} cyc")

    # same-frame pair bound: each spike class fires at most once per frame;
    # P2-side spikes exclude each other via ARMED2/PEND2, but a P1NATIVE
    # search (hook 1) can share a frame with a P2 spawn upload (hook 2).
    spikes = [k for k in ("release_edge", "spawn_edge_p2", "p1_search")
              if results.get(k) is not None]
    if "p1_search" in have and False:
        pass
    if meta.get("p1native"):
        pair = results["p1_search"] + results["spawn_edge_p2"] + 12
        note = "p1_search + spawn_edge_p2"
    else:
        pair = max(results[k] for k in spikes) + results["steady_play"] + 12
        note = f"max(spike) + steady_play"
    print(f"  SAME-FRAME PAIR (2 hooks) worst = {pair} cyc   [{note}]")
    print(f"  frame budget: 29780 CPU cycles minus the game NMI's own work")

    if pp_order:
        # ---- DRPRESPIPE admissible-pair certificate -------------------------
        # The generic pair line above is the WRONG MODEL for a pipelined image:
        # it pairs a spawn upload with a phase hook, which the abort checks make
        # impossible (see the h2_cp note in SCENARIO_CUTS). Admissible frames,
        # each an ORDERED pair of hooks 1 and 2 of one frame:
        #   (phase_i, phase_i+1)   the pipeline advancing across a frame boundary
        #   (edge, phase_1)        the edge hook and the first phase
        #   (spawn_edge_p2, edge)  a spawn upload, then a release edge next hook
        #   (X, steady_play)       any class followed by an ordinary hook
        # A phase can never share a frame with a spawn upload IN EITHER ORDER:
        # in the same hook the guard forbids it, and across the two hooks of a
        # frame PEND2/ARMED2 is still set at the second hook's dispatch, which
        # aborts the pipeline instead of running a phase.
        seq = [(pp_order[i], pp_order[i + 1]) for i in range(len(pp_order) - 1)]
        seq += [(a, "pp_idle") for a in pp_order]
        seq += [("pp_spawn", "pp_edge"), ("pp_idle", "pp_edge")]
        # #140: on a COMBINED image pp_idle/pp_spawn carry the p1 slice tick, so
        # ordinary frames with a tick in both hooks and spawn+tick frames are no
        # longer dominated by the (X, pp_idle) rows -- enumerate them explicitly.
        # (Harmless duplicates/orderings on a slice-less image: idle is cheap there.)
        seq += [("pp_idle", "pp_idle"), ("pp_spawn", "pp_idle"),
                ("pp_idle", "pp_spawn")]
        GAME_HEAD, EPS, FRAME = 2040, 300, 29780
        worst = max(seq, key=lambda ab: results[ab[0]] + results[ab[1]])
        wv = results[worst[0]] + results[worst[1]] + 12
        print("  DRPRESPIPE admissible frames (hook1 + hook2 + 12):")
        for a, b in sorted(seq, key=lambda ab: -(results[ab[0]] + results[ab[1]])):
            tot = results[a] + results[b] + 12 + GAME_HEAD + EPS
            print(f"    {a:10s} + {b:14s} = {results[a] + results[b] + 12:6d}"
                  f"  + head {GAME_HEAD} + eps {EPS} = {tot:6d}"
                  f"  {'OK' if tot < FRAME else 'OVER'}  margin {FRAME - tot:+6d}")
        tot = wv + GAME_HEAD + EPS
        print(f"  WORST ADMISSIBLE FRAME = {tot} of {FRAME} "
              f"({100.0 * tot / FRAME:.1f}%), margin {FRAME - tot} cyc "
              f"[{worst[0]} + {worst[1]}]")

    # per-routine detail from the uncut analysis
    print("  routines (ALL_PATHS):")
    for (e, ov), (c, tr) in sorted(an_all.routine_cost.items(),
                                    key=lambda kv: -kv[1][0]):
        labs = nodes[e].get("labels") or [f"${e:04X}"]
        tag = " [ctx]" if ov else ""
        print(f"    ${e:04X} {labs[0]:24s} {c:8d}{tag}")


if __name__ == "__main__":
    main()
