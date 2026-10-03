#!/usr/bin/env python3
"""Audit every store the EMITTED hook code (driver main + wrapper [+ P1 native AI]) makes into the game's own state.

Captures the IR of a cart config with tools/nmi126/capture_ir.py (ground-truth gated: the IR reassembles to the exact
bytes the emitter shipped), then lists every STA/STX/STY/INC/DEC whose operand lands in game-owned RAM:
  $0300-$032F P1 player RAM, $0380-$03AF P2 player RAM (gravity counter, X/Y/rotation, nextAction, ...),
  $0400-$047F / $0500-$057F the boards, zero page $80-$AF (currentP), $F5-$F8 (pads), $43 (frameCounter), $46 (mode).
Indexed stores (abs,X) are listed with their base. Each row carries the nearest preceding label, so every write can be
traced to its emitter site and its flag condition.
  audit_rom_writes.py <flags.json> <tag> [KEY=VAL ...]      (writes tmp/audit/<tag>_ir.json + prints the table)
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable
NAMES = {0x0381: "p2 capsule colour A", 0x0382: "p2 capsule colour B", 0x0385: "p2 X", 0x0386: "p2 Y (fallingPillY)",
         0x0388: "p2 pill size", 0x038A: "p2 speedUps", 0x038B: "p2 speed setting", 0x0392: "p2 SPEED COUNTER (gravity)",
         0x0393: "p2 horVelocity (DAS)", 0x0397: "p2 nextAction", 0x039A: "p2 preview A", 0x039B: "p2 preview B",
         0x03A5: "p2 rotation", 0x03A7: "p2 pillsCounter", 0x0312: "p1 SPEED COUNTER (gravity)", 0x0305: "p1 X",
         0x0306: "p1 Y", 0x0325: "p1 rotation", 0x0300: "p1 RAM +0 (row redraw)", 0x0380: "p2 RAM +0 (row redraw)",
         0x0316: "p1 level", 0x0396: "p2 level", 0x0318: "p1 attackSize", 0x0398: "p2 attackSize",
         0x00F5: "p1 pad (raw/pressed)", 0x00F6: "p2 pad pressed", 0x00F7: "p1 pad held", 0x00F8: "p2 pad held",
         0x0043: "frameCounter", 0x0046: "mode"}


def in_game(addr):
    return (0x0300 <= addr <= 0x03AF or 0x0400 <= addr <= 0x057F or 0x80 <= addr <= 0xAF or 0xF5 <= addr <= 0xF8
            or addr in (0x43, 0x46))


def main():
    flags, tag, overlays = sys.argv[1], sys.argv[2], sys.argv[3:]
    snap = json.load(open(flags))["flag_snapshot"]
    for kv in overlays:
        k, v = kv.split("=", 1); snap[k] = v
    os.makedirs(os.path.join(ROOT, "tmp", "audit"), exist_ok=True)
    man = os.path.join(ROOT, "tmp", "audit", f"{tag}.manifest.json")
    ir_path = os.path.join(ROOT, "tmp", "audit", f"{tag}_ir.json")
    json.dump({"flag_snapshot": snap}, open(man, "w"))
    r = subprocess.run([PY, os.path.join(ROOT, "tools", "nmi126", "capture_ir.py"), man, ir_path], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-3000:]); sys.exit(2)
    ir = json.load(open(ir_path))
    reach = reachable(ir)
    rows = []
    for uname, u in ir["units"].items():
        last_label = "?"
        for rec in u["records"]:
            if rec["k"] == "label":
                last_label = rec["name"]; continue
            if rec["k"] != "ins":
                continue
            m = rec["m"]
            if not m.split("_")[0] in ("STA", "STX", "STY", "INC", "DEC", "ASL", "LSR", "ROL", "ROR") or "_" not in m:
                continue
            mode = m.split("_", 1)[1]
            if mode == "A":
                continue
            ops = rec["ops"]
            addr = ops[0] | (ops[1] << 8) if mode.startswith("abs") else ops[0]
            if in_game(addr):
                pc = u["base"] + rec["off"]
                rows.append((uname, pc, m, addr, last_label, pc in reach))
    live = [r for r in rows if r[5]]
    print(f"== {tag}: {len(rows)} stores into game-owned state, {len(live)} REACHABLE from the hook entry "
          f"(units: {', '.join(ir['units'])})")
    for uname, pc, m, addr, lab, ok in rows:
        print(f"  {'LIVE' if ok else 'dead'} {uname:7s} ${pc:04X} {m:9s} ${addr:04X}  {NAMES.get(addr, ''):28s} after `{lab}`")


def reachable(ir):
    """CFG reachability from the wrapper entry over every captured unit (branches: both ways; JSR: target + return;
    JMP/RTS/RTI: no fallthrough). Raw data records are never entered by fallthrough."""
    nodes, nxt = {}, {}
    units = ir["units"]
    for uname, u in units.items():
        recs = [r for r in u["records"] if r["k"] != "label"]
        for i, r in enumerate(recs):
            pc = u["base"] + r["off"]
            fall = u["base"] + recs[i + 1]["off"] if i + 1 < len(recs) else None
            succ = []
            def lab(t):
                return u["base"] + u["labels"][t] if isinstance(t, str) else t
            if r["k"] == "raw":
                succ = []
            elif r["k"] == "br":
                succ = [lab(r["target"]), fall]
            elif r["k"] == "jmp":
                succ = [lab(r["target"])]
            elif r["k"] == "jsr":
                succ = [lab(r["target"]), fall]
            elif r["k"] == "ins" and r["m"] in ("RTS", "RTI"):
                succ = []
            else:
                succ = [fall]
            nodes[pc] = [s for s in succ if s is not None]
    entry = units["wrapper"]["base"]
    seen, stack = set(), [entry]
    while stack:
        pc = stack.pop()
        if pc in seen or pc not in nodes:
            continue
        seen.add(pc)
        stack.extend(nodes[pc])
    return seen


if __name__ == "__main__":
    main()
