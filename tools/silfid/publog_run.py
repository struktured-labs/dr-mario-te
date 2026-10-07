#!/usr/bin/env python3
"""Incremental, prioritised driver for `ss_cosim.py --publog` on a large capture.

  publog_run.py PILLS.json OUT.jsonl [-j 6] [--cell-first]
PILLS.json = tools/silfid/publog.py --json output (merged over all save-states). Every FINAL pill is co-simulated on the
Verilator copro (vsim_pub2, fw 1488e158) exactly as ss_cosim.py --publog does, and its verdict record is APPENDED to
OUT.jsonl as soon as it completes (restart-safe: pills already in OUT.jsonl are skipped). Order: prestart pills, then
the endgame (<= 20 viruses left), then tall boards (max column height >= 12), then the rest -- so a partial run already
covers the regimes the 10/05 couch residual lives in.
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publog as PL
import ss_cosim as SC

TOL, HPF = 1.0, 2.0


def bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


def maxh(board_hex):
    b = bytes.fromhex(board_hex); h = 0
    for c in range(8):
        for r in range(16):
            if b[r * 8 + c] != 0xFF:
                h = max(h, 16 - r); break
    return h


def judge_pill(p, pubs, done, tuck):
    live = [e for e in p["events"] if e["type"] == "live"]
    dn = [e for e in p["events"] if e["type"] == "done"]
    reads = [dict(t=round(e["hooks"] / HPF, 2), f=e["frames"], col=e["a"], o4=e["b"],
                  status=SC.judge(pubs, done, e["hooks"] / HPF, e["a"], e["b"], TOL)) for e in live]
    seen = {(r["col"], r["o4"]) for r in reads}
    seq = list(pubs) + [(done[0], done[1], done[2])]
    t_end = (dn[0]["hooks"] / HPF) if dn else 1e9
    missed = [(round(tt, 2), c, o) for i, (tt, c, o) in enumerate(pubs)
              if min(seq[i + 1][0], t_end) - tt >= 1.5 and (c, o) not in seen]
    rec = dict(seq=p["seq"], kind=p["kind"], viruses=bcd(p["viruses_bcd"]), maxh=maxh(p["board"]),
               upload=PL.upload_line(p), reads=reads, missed=missed,
               cosim_pubs=[(round(tt, 2), c, o) for tt, c, o in pubs],
               cosim_done=(round(done[0], 2), done[1], done[2]), cosim_tuck=tuck,
               events=p["events"], src=p["src"])
    rec["tuck"] = bool(tuck and tuck[0] != 0xFF) or any(e["type"] == "done" and (e["c"] >> 4) != 0x0F for e in dn)
    if not dn:
        rec["verdict"] = "NO_DONE"
        return rec
    d = dn[0]
    rec["done"] = dict(t=round(d["hooks"] / HPF, 2), col=d["a"], o4=d["b"], tuck=d["c"])
    rec["final_ok"] = (d["a"], d["b"]) == (done[1], done[2])
    tk = (((tuck[0] & 0x0F) << 4) | (tuck[1] & 0x0F)) if tuck else None
    rec["done_tuck_ok"] = tk is None or d["c"] == tk
    rec["done_dt"] = round(d["hooks"] / HPF - done[0], 2)          # silicon DONE read time - co-sim DONE time
    st = {r["status"] for r in reads}
    if not rec["final_ok"] or not rec["done_tuck_ok"] or st & {"MISMATCH_IN_SEQ", "MISMATCH_NEW"} or missed:
        rec["verdict"] = "DIVERGED"
    elif "AMBIGUOUS" in st:
        rec["verdict"] = "AMBIGUOUS"
    else:
        rec["verdict"] = "EXACT"
    return rec


def main():
    pills_path, out = sys.argv[1], sys.argv[2]
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 6
    pills = [p for p in json.load(open(pills_path)) if p["final"]]
    done_seqs = set()
    if os.path.exists(out):
        done_seqs = {json.loads(l)["seq"] for l in open(out) if l.strip()}
    cell_first = "--cell-first" in sys.argv          # capture #2: the tall-endgame cell (<= 20 viruses, height 14-16) first
    def prio(p):
        v = bcd(p["viruses_bcd"]); h = maxh(p["board"])
        if cell_first and v <= 20 and h >= 14:
            return (-1, p["seq"])
        return (0 if p["kind"] == 1 else 1 if v <= 20 else 2 if h >= 12 else 3, p["seq"])
    todo = sorted((p for p in pills if p["seq"] not in done_seqs), key=prio)
    print(f"{len(pills)} final pills, {len(done_seqs)} already done, {len(todo)} to run", flush=True)
    with ThreadPoolExecutor(j) as ex, open(out, "a") as f:
        futs = {ex.submit(SC.cosim_full, PL.upload_line(p)): p for p in todo}
        n = 0
        for fu in as_completed(futs):
            p = futs[fu]
            pubs, done, tuck = fu.result()
            rec = judge_pill(p, pubs, done, tuck)
            f.write(json.dumps(rec) + "\n"); f.flush()
            n += 1
            if n % 50 == 0:
                print(f"{n}/{len(todo)}", flush=True)
    print("PUBLOG_RUN DONE", flush=True)


if __name__ == "__main__":
    main()
