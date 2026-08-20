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
    return meta, nodes


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
    def __init__(self, nodes):
        self.nodes = nodes
        self.routine_cost = {}   # entry addr -> (worst_cycles, witness path summary)
        self.in_progress = set()

    def resolve(self, addr, ctx):
        if addr in self.nodes:
            return self.nodes[addr]
        raise SystemExit(
            f"UNRESOLVED target ${addr:04X} reached from {ctx} -- add to "
            f"EXTERNAL_COSTS or capture the unit")

    def worst(self, entry):
        if entry in self.routine_cost:
            return self.routine_cost[entry][0]
        if entry in self.in_progress:
            raise SystemExit(f"RECURSION through ${entry:04X}")
        self.in_progress.add(entry)

        # 1. collect routine nodes (intra-routine traversal)
        seen = set()
        stack = [entry]
        while stack:
            a = stack.pop()
            if a in seen:
                continue
            seen.add(a)
            n = self.resolve(a, f"routine ${entry:04X}")
            for s, _ in successors(n, self.nodes):
                if s not in seen:
                    stack.append(s)
            if n["kind"] == "jsr":
                t = n["target"]
                if t in self.nodes:
                    self.worst(t)  # recurse into callee now (cycle check)
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
            for s, _ in successors(self.nodes[a], self.nodes):
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
            for s, _ in successors(self.nodes[a], self.nodes):
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
            if lab is None or lab not in LOOP_BOUNDS:
                tails = ", ".join(f"${t:04X}" for t in loops[head])
                missing.append(f"  head ${head:04X} label={lab!r} unit="
                               f"{self.nodes[head]['unit']} back-edges from {tails}")
        if missing:
            raise SystemExit("UNDECLARED LOOPS (declare LOOP_BOUNDS):\n"
                             + "\n".join(missing))
        # innermost first = smallest body first
        for head in sorted(loops, key=lambda h: len(loop_nodes[h])):
            lab = head_label(head)
            bound = LOOP_BOUNDS[lab]
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
                    call = (6 + self.routine_cost[t][0]) if t in self.nodes else \
                           (6 + EXTERNAL_COSTS[t][1])
                else:
                    call = None
                for s, ec in successors(n, self.nodes):
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
            succs = [(s, ec) for s, ec in successors(n, self.nodes)
                     if (a, s) not in be_set]
            if n["kind"] == "ins" and n["m"] == "RTS":
                total = d + 6
                if total > worst_term[0]:
                    worst_term = (total, a)
                continue
            if n["kind"] == "jsr":
                t = n["target"]
                call = (6 + self.routine_cost[t][0]) if t in self.nodes else \
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
        self.in_progress.discard(entry)
        self.routine_cost[entry] = (worst_term[0], trail)
        return worst_term[0]


def main():
    path = sys.argv[1]
    meta, nodes = load(path)
    an = Analyzer(nodes)
    units = meta["units"]
    wrap_entry = units["wrapper"]["base"]
    w = an.worst(wrap_entry)
    main_entry = meta["main_cpu"]
    print(f"config: {meta['manifest']}")
    print(f"  W(main)    = {an.routine_cost[main_entry][0]:6d} cycles")
    if "p1ai" in units:
        se = units["p1ai"]["base"] + units["p1ai"]["labels"]["search_entry"]
        if se in an.routine_cost:
            print(f"  W(p1ai search) = {an.routine_cost[se][0]:6d} cycles")
    print(f"  W(wrapper) = {w:6d} cycles   (+6 blob head STA $F6/JMP = hook)")
    print(f"  HOOK WORST = {w + 6:6d} cycles")
    print(f"  witness: {' -> '.join(an.routine_cost[wrap_entry][1][:12])}")
    # per-routine table
    print("  routines:")
    for e, (c, tr) in sorted(an.routine_cost.items(), key=lambda kv: -kv[1][0]):
        labs = nodes[e].get("labels") or [f"${e:04X}"]
        print(f"    ${e:04X} {labs[0]:24s} {c:8d}")


if __name__ == "__main__":
    main()
