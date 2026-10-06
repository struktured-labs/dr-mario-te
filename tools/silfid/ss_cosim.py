#!/usr/bin/env python3
"""silfid lane: does the SILICON copro publish what the Verilator copro publishes on the IDENTICAL input?

The 10/05 couch "silicon-only" misses: silicon landed somewhere the Mesen replay of the same cart (driven by Verilator
co-sim timelines) does not. Emulation explains only part of it (the tie-break seed every replay left at 0). The rest
needs the silicon copro's own publish timeline, and a MiSTer save-state already carries everything required for ONE
exact comparison per snapshot -- no new cart, no new rbf:
  * the P2 board the search is running on ($0500-$057F: the falling capsule is not in the field until it locks, and in
    VS mode garbage drops only between pills, so while P2's capsule is still falling with its search ARMED this IS the
    board that was uploaded at GO), the capsule / preview colours ($0381/$0382, $039A/$039B), speedUps / speed
    ($038A/$038B) and the per-match tie-break seed SEED2 ($6168): the upload is rebuilt byte-for-byte the way handle(2)
    builds it (seed nibbles, DRREACHTX + DRTAPP nibbles);
  * the hooks since that GO (WDOGH2:WDOG2 = $6166:$6162, ~2 hooks per frame) and the copro's latest publish as the
    cart's live path last read it, BEFORE any DRLATEGUARD decision: the untorn snapshot $616C (orient4, raw) / $616D
    (column).
For every usable snapshot the shipped copro (RTL NES_MiSTer-dist 3b164c7 + fw 1488e158, Verilator vsim_pub2) runs the
same upload; its publish valid at the snapshot's time since GO must equal silicon's. A snapshot whose time lies within
TOL frames of a co-sim publish change is AMBIGUOUS (hook-to-frame conversion), never a mismatch.
  ss_cosim.py [--tol 1.0] [--hpf 2.0] [--json OUT] FILE.ss ...
Usable = mode $46 == 4, ARMED2 == 1, PEND2 == 0, PRE_ACT2 == 0 (a prestart uploads a PROJECTED board), nextAction == 0
(the capsule is falling), orient != $FF (a candidate has been published).
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "livecatch"))
import ss_decode as SD  # noqa: E402

VSIM = os.environ.get("VSIM", "/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/obj_pub2/vsim_pub2")
FWDIR = os.environ.get("FWDIR", "/home/struktured/projects/dr-mario-lateflip-wt/tmp/pubtrace/fw_1488e158")
FRAME = 29780.5 * 48
TAPP = int(os.environ.get("TAPP", "2"))
ARMED2, WDOG2, WDOGH2, PEND2, PRE_ACT2, SEED2 = 0x6161, 0x6162, 0x6166, 0x614F, 0x619A, 0x6168
LIVE_O, LIVE_C, TGT_C2, TGT_O2 = 0x616C, 0x616D, 0x6152, 0x6153


def upload_of(s):
    """Rebuild handle(2)'s upload: 128 board bytes ($00 -> $FF) + cA cB nA nB."""
    board = [0xFF if b == 0x00 else b for b in s.field(2)]
    seed = s.prg(SEED2)
    ca, cb, na, nb = (s.cpu(a) for a in (0x0381, 0x0382, 0x039A, 0x039B))
    spu, spd = s.cpu(0x038A), s.cpu(0x038B)
    cA = ((seed << 4) & 0xF0) | (ca & 0x0F)
    cB = (seed & 0xF0) | (cb & 0x0F)
    nA = (na & (0x03 if TAPP else 0x0F)) | ((spu & 0x0F) << 4) | (((TAPP & 3) << 2) if TAPP else 0)
    hi = ((((spu >> 4) & 0x03) | (((spd + 1) << 2) & 0xFF)) << 4) & 0xFF
    nB = (nb & (0x03 if TAPP else 0x0F)) | hi | ((((TAPP >> 2) & 3) << 2) if TAPP else 0)
    return "%d %d %d %d %s" % (cA, cB, nA, nB, " ".join("%02x" % v for v in board))


def cosim(line):
    out = subprocess.run(["nice", "-n", "19", VSIM, "64"], cwd=FWDIR, input=line + "\n", capture_output=True,
                         text=True).stdout.split()
    assert out and out[0] == "PUB", out[:5]
    n = int(out[1]); pubs, seen = [], False
    for k in range(n):
        clk, c, o = int(out[2 + 3 * k]), int(out[3 + 3 * k]), int(out[4 + 3 * k])
        if o == 0xFF:
            seen = True; continue
        if seen:
            pubs.append((clk / FRAME, c, o))
    i = 2 + 3 * n
    return pubs, (int(out[i + 1]) / FRAME, int(out[i + 2]), int(out[i + 3]))


def judge(pubs, done, t, col, o4, tol):
    """co-sim publish valid at t (frames since GO) vs silicon (col, o4)."""
    seq = list(pubs) + [(done[0], done[1], done[2])]
    cur = None; near = False
    for tt, c, o in seq:
        if abs(tt - t) <= tol:
            near = True
        if tt <= t:
            cur = (c, o)
    if cur == (col, o4):
        return "MATCH"
    ever = any((c, o) == (col, o4) for _, c, o in seq)
    if near:
        return "AMBIGUOUS"
    return "MISMATCH_IN_SEQ" if ever else "MISMATCH_NEW"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--tol", type=float, default=1.0)
    ap.add_argument("--hpf", type=float, default=2.0, help="driver hooks per frame (silicon measured ~1.9-2.0)")
    ap.add_argument("-j", type=int, default=int(os.environ.get("J", "4")))
    ap.add_argument("--json")
    a = ap.parse_args()
    rows, todo = [], []
    for f in a.files:
        try:
            s = SD.Snapshot(f)
        except Exception as e:  # noqa: BLE001 -- report and continue, never decode garbage
            rows.append(dict(file=os.path.basename(f), status="UNREADABLE", why=str(e)[:200])); continue
        st = dict(mode=s.cpu(0x46), armed=s.prg(ARMED2), pend=s.prg(PEND2), pre=s.prg(PRE_ACT2), na=s.cpu(0x0397),
                  o4=s.prg(LIVE_O), col=s.prg(LIVE_C), hooks=s.prg(WDOGH2) * 256 + s.prg(WDOG2), seed=s.prg(SEED2),
                  tgt=(s.prg(TGT_C2), s.prg(TGT_O2)), y=s.cpu(0x0386), x=s.cpu(0x0385))
        usable = st["mode"] == 4 and st["armed"] == 1 and st["pend"] == 0 and st["pre"] == 0 and st["na"] == 0 \
            and st["o4"] != 0xFF and st["col"] < 8
        row = dict(file=os.path.basename(f), invariant=s.invariant_ok, **st)
        if not usable:
            row["status"] = "UNUSABLE"
        else:
            row["upload"] = upload_of(s); todo.append(row)
        rows.append(row)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(a.j) as ex:
        res = list(ex.map(lambda r: cosim(r["upload"]), todo))
    for row, (pubs, done) in zip(todo, res):
        t = row["hooks"] / a.hpf
        row.update(status=judge(pubs, done, t, row["col"], row["o4"], a.tol), t_frames=round(t, 2),
                   cosim_pubs=[(round(tt, 2), c, o) for tt, c, o in pubs], cosim_done=(round(done[0], 2), done[1], done[2]))
        print(f"{row['file']}: {row['status']:16s} t={t:5.1f}f sil=(c{row['col']},o{row['o4']}) seed={row['seed']:02X} "
              f"cosim={row['cosim_pubs']} done={row['cosim_done']}", flush=True)
    tally = {}
    for r in rows:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print("TALLY", json.dumps(tally))
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
