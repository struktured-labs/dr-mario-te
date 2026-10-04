#!/usr/bin/env python3
"""DRLEFLUSH firmware gates: static identity + py65 whole-decision identity (finals unchanged when nothing preempts).

  STATIC  build_fw.py recipes through build_copro_d3 (shipped-style DELTA hexes):
            flag off, V1 recipe (TR RO TL)   == fw a1ef31c8 byte for byte   (negative control)
            flag off, DIST60 recipe          == fw 1488e158 byte for byte   (negative control)
            flag on  differs from its flag-off twin ONLY inside the reset stub $BF80-$BFFF, and the stub is the
            flag-off stub with exactly the flush inserted (issue after SEI/CLD, poll after the pill-table copy)
  PY65    the WHOLE decision from the reset stub (stub -> search -> tuck extension -> DONE) on the NON-delta build of
          the same flags, golden-leaf engine emulator (test_search_d3.attach_engine_emu, which models the flush's
          illegal CMD 7 exactly and refuses a legal one), flag on vs flag off, per board:
            final (col, o4), tuck descriptor, tuck commits, the live-mailbox publish VALUE sequence, the reach state
            at the tuck entry -> identical; RAM write set ($0000-$0FFF) identical (the flush stores only to $70xx);
            6502 cycles on - off == 22 exactly (the flush's instructions; its poll exits on the first read)
          corpora: the fw-tuckreach lane's 62 py65 gate boards (tmp/py65/couch_ab.jsonl there, as the cart uploads
          them; their banked flag-off 'ship' rows must reproduce too) + the gate-(b) game corpus every --step'th board
Usage: gate_py65_flush.py [--step 7] [--workers 4] [--out ROWS.jsonl]"""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "experiments", "tuckreach"))
COUCH = "/home/struktured/projects/dr-mario-fwtuckreach-wt/tmp/py65/couch_ab.jsonl"
PY = sys.executable
_IMG = {}


def build_hex(args):
    out = os.path.join(HERE, "_gate_tmp.hex")
    r = subprocess.run([PY, os.path.join(ROOT, "experiments", "reach", "build_fw.py"), "540", out] + args,
                       capture_output=True, text=True, check=True)
    b = [int(x, 16) for x in open(out).read().split()]
    os.remove(out)
    return r.stdout.split("md5=")[1].split()[0], b


def static():
    ok = True
    v1_off, A = build_hex(["1", "1", "1", "1", "1", "1", "19", "8", "0"])
    d60_off, D = build_hex(["1", "1", "1"])
    v1_on, B = build_hex(["1", "1", "1", "1", "1", "1", "19", "8", "1"])
    d60_on, E = build_hex(["1", "1", "1", "0", "0", "0", "19", "8", "1"])
    print(f"IDENTITY flag off, V1 recipe     md5 {v1_off} == a1ef31c8: {'PASS' if v1_off.startswith('a1ef31c8') else 'FAIL'}")
    print(f"IDENTITY flag off, DIST60 recipe md5 {d60_off} == 1488e158: {'PASS' if d60_off.startswith('1488e158') else 'FAIL'}")
    ok &= v1_off.startswith("a1ef31c8") and d60_off.startswith("1488e158")
    issue = [0xA9, 0x02, 0x8D, 0xE0, 0x70, 0xA9, 0x07, 0x8D, 0xE1, 0x70, 0x8D, 0xF4, 0x70]
    poll = [0xAD, 0xF8, 0x70, 0xF0, 0xFB]
    for name, off, on, md5 in (("V1", A, B, v1_on), ("DIST60", D, E, d60_on)):
        d = [i for i in range(len(off)) if off[i] != on[i]]
        in_stub = all(0x3F80 <= i < 0x4000 for i in d)
        so, sn = off[0x3F80:0x4000], on[0x3F80:0x4000]
        # flag-off stub = SEI CLD | LDX #$FF TXS LDX #15 | cp2: LDA $B030,X STA $09C0,X DEX BPL cp2 | rest (JSR/JMP retargeted)
        exp = so[:2] + issue + so[2:16] + poll
        body_ok = sn[:len(exp)] == exp
        # the rest of the stub: same instructions, the JMP spin operand moved by the 18 inserted bytes
        rest_o, rest_n = so[16:], sn[len(exp):]
        jmp_o = max(i for i in range(len(rest_o) - 2) if rest_o[i] == 0x4C)
        tail_ok = rest_n[:jmp_o] == rest_o[:jmp_o] and rest_n[jmp_o] == 0x4C and \
            (rest_n[jmp_o + 1] | rest_n[jmp_o + 2] << 8) == (rest_o[jmp_o + 1] | rest_o[jmp_o + 2] << 8) + 18
        print(f"STUB {name} flag on md5 {md5}: {len(d)} bytes differ, all inside $BF80-$BFFF: {in_stub}; "
              f"flush inserted as specified: {body_ok}; remaining stub identical (spin JMP +18): {tail_ok}")
        ok &= in_stub and body_ok and tail_ok
    return ok


def init():
    import fwlib as F
    for k, fl in (("off", 0), ("on", 1)):
        _IMG[k] = F.image(1, 1, DRTUCKLIVE=1, DRLEFLUSH=fl)


def task(bd):
    import fwlib as F
    row = dict(id=bd["id"])
    for k in ("off", "on"):
        r = F.run(_IMG[k], bd["nes"], *bd["go"], ramscan=True)
        ent = dict(r["entry"]) if r["entry"] else None
        if ent:
            ent.pop("n", None)
        row[k] = dict(final=list(r["final"]), tuck=list(r["tuck"]), commits=[{x: c[x] for x in c if x != "n"} for c in r["commits"]],
                      pubs=[p[1:] for p in r["pubs"]], entry=ent, cycles=r["cycles"], steps=r["steps"],
                      ram=sorted(r["ram"]))
    return row


def boards(step):
    import fwlib as F
    out = []
    for l in open(COUCH):
        q = json.loads(l)
        out.append(dict(id=q["id"], nes=q["nes"], go=q["go"], banked=q.get("ship")))
    for d in F.load_corpus(step=step):
        p = [x - 1 for x in d["pills"]]
        out.append(dict(id=f"game{d['level']}_{d['seed']}_{d['k']}", nes=d["nes"],
                        go=F.transport(*p, d["speed"], d["speedups"]), banked=None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=7)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "tmp", "leflush_py65_rows.jsonl"))
    ap.add_argument("--static-only", action="store_true")
    a = ap.parse_args()
    ok = static()
    print("GATE_STATIC", "PASS" if ok else "FAIL")
    if a.static_only:
        sys.exit(0 if ok else 1)
    B = boards(a.step)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = {}
    if os.path.exists(a.out):
        done = {json.loads(l)["id"]: json.loads(l) for l in open(a.out)}
    todo = [b for b in B if b["id"] not in done]
    print(f"py65: {len(B)} boards ({sum(1 for b in B if b['banked'])} fw-lane gate boards + game corpus step {a.step}), "
          f"{len(done)} banked, running {len(todo)}", flush=True)
    with mp.get_context("fork").Pool(a.workers, initializer=init) as pool, open(a.out, "a") as fh:
        for i, row in enumerate(pool.imap_unordered(task, todo, chunksize=1)):
            fh.write(json.dumps(row) + "\n"); fh.flush(); done[row["id"]] = json.loads(json.dumps(row))
            if i % 20 == 0:
                print(f"  {i + 1}/{len(todo)}", flush=True)
    n = same = ram_same = cyc_ok = 0
    bank_n = bank_same = 0
    diffs = []
    for b in B:
        r = done[b["id"]]
        n += 1
        f, o = r["off"], r["on"]
        keys = ("final", "tuck", "commits", "pubs", "entry")
        s = all(f[k] == o[k] for k in keys)
        same += s
        ram_same += f["ram"] == o["ram"]
        cyc_ok += o["cycles"] - f["cycles"] == 22
        if not s:
            diffs.append((b["id"], [k for k in keys if f[k] != o[k]]))
        if b["banked"]:
            bank_n += 1
            bk = b["banked"]
            bank_same += (list(bk["final"]) == f["final"] and list(bk["tuck"]) == f["tuck"]
                          and [p[1:] for p in bk["pubs"]] == f["pubs"])
    print(f"REPRO flag off == the fw lane's banked 'ship' rows (final, tuck, publish values): {bank_same}/{bank_n}")
    print(f"IDENTITY flag on == flag off (final, tuck, commits, publish values, tuck-entry reach state): {same}/{n}")
    print(f"RAM write set identical: {ram_same}/{n};  6502 cycles on - off == 22: {cyc_ok}/{n}")
    for d in diffs[:20]:
        print("  DIFF", d)
    ok2 = same == n and ram_same == n and cyc_ok == n and bank_same == bank_n and n > 0
    print("GATE_PY65_FLUSH", "PASS" if ok2 else "FAIL")
    sys.exit(0 if ok and ok2 else 1)


if __name__ == "__main__":
    main()
