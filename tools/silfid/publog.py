#!/usr/bin/env python3
"""DRPUBLOG ring decoder (silicon-fidelity lane, 2026-10-06).

Reads the per-pill log ring the DRPUBLOG cart keeps in PRG-RAM ($6600 header, 25 x 256 B slots at $6700-$7FFF; layout in
patch_cartridge_copro.py's DRPUBLOG flag block) out of MiSTer save-states (1,327,112 B; CPU RAM at 0x102B08, cart WRAM at
+0x800) or raw dumps (2 KB CPU RAM + 8 KB PRG-RAM, the silfid_dump_probe format), and merges several snapshots by pill
sequence number.

  publog.py FILE... [--json OUT]       -> one record per logged pill (newest copy of each seq wins)
"""
import json, os, sys

SS_SIZE, RAM_HINT, WRAM_DELTA = 1327112, 0x102B08, 0x800
NAV_MAGIC = 0x6149
HDR, RING, NSLOT, EV0, EVSZ, EVMAX = 0x6600, 0x6700, 25, 0x90, 6, 18
EVTYPE = {1: "live", 2: "done", 3: "tgt", 5: "lock", 6: "pdone"}   # 6: DRPUBLOG_PDW post-DONE watch (a=$5284, b=col, c=o4)


def load_prg(path):
    """-> (cpu_ram 2 KB, prg_ram 8 KB indexed from $6000) or raise ValueError."""
    b = open(path, "rb").read()
    if len(b) == 0x800 + 0x2000:                               # silfid_dump_probe raw dump
        return b[:0x800], b[0x800:]
    if len(b) != SS_SIZE:
        raise ValueError(f"{path}: {len(b)} bytes is neither a MiSTer NES save-state nor a raw dump")
    for ram in (RAM_HINT,):
        w = ram + WRAM_DELTA
        prg = b[w:w + 0x2000]
        if prg[NAV_MAGIC - 0x6000] == 0xA5:
            return b[ram:ram + 0x800], prg
    raise ValueError(f"{path}: driver PRG-RAM not found at the hinted offset (NAV_MAGIC != $A5)")


def decode(path):
    cpu, prg = load_prg(path)
    g = lambda a: prg[a - 0x6000]
    hdr = dict(magic=bytes(prg[HDR - 0x6000:HDR - 0x6000 + 4]).hex(), slot=g(0x6604),
               seq=g(0x6605) | (g(0x6606) << 8), hooks=g(0x6607) | (g(0x6608) << 8), dropped=g(0x6617),
               open=g(0x660E))
    pills = []
    for k in range(NSLOT):
        s = RING - 0x6000 + 0x100 * k
        sl = prg[s:s + 0x100]
        if sl[0] != 0xA7:
            continue
        seq = sl[1] | (sl[2] << 8)
        back = (hdr["seq"] - seq) & 0xFFFF
        if back >= NSLOT or (hdr["slot"] - k) % NSLOT != back:
            continue                       # not written by this ring's current run (stale / power-on garbage)
        n = sl[11]
        evs = []
        for i in range(min(n, EVMAX)):
            e = sl[EV0 + EVSZ * i:EV0 + EVSZ * (i + 1)]
            t = e[0] & 0x3F                # $80: hooks >= 256; $40: DONE whose immediate re-read was 0 (DRPUBLOG_PDW)
            ev = dict(type=EVTYPE.get(t, str(t)), hooks=e[1] + (256 if e[0] & 0x80 else 0), frames=e[2],
                      a=e[3], b=e[4], c=e[5])
            if e[0] & 0x40:
                ev["reread0"] = True
            evs.append(ev)
        pills.append(dict(slot=k, seq=sl[1] | (sl[2] << 8), hookctr=sl[3] | (sl[4] << 8), kind=sl[5],
                          upload4=list(sl[6:10]), frame0=sl[10], nev=n, viruses_bcd=sl[12], y=sl[13], x=sl[14],
                          na=sl[15], board=bytes(sl[16:144]).hex(), events=evs, src=os.path.basename(path)))
    pills.sort(key=lambda p: p["seq"])
    return hdr, pills


def upload_line(p):
    """The exact upload as vsim_pub2 takes it: 'cA cB nA nB <128 hex>'."""
    b = bytes.fromhex(p["board"])
    return "%d %d %d %d %s" % (*p["upload4"], " ".join("%02x" % v for v in b))


def merge(paths):
    """Newest copy of each seq (by file order, then event count); a pill is FINAL once a later seq exists in the
    same snapshot (its search has been superseded by the next GO, so no more events can arrive)."""
    best = {}
    for path in paths:
        try:
            hdr, pills = decode(path)
        except ValueError as e:
            print(f"skip {e}", file=sys.stderr); continue
        top = hdr["seq"]
        for p in pills:
            p["final"] = p["seq"] != top                    # superseded by a later GO: no more events can arrive
            old = best.get(p["seq"])
            if old is None or (p["final"], p["nev"]) >= (old["final"], old["nev"]):
                best[p["seq"]] = p
    return [best[k] for k in sorted(best)]


if __name__ == "__main__":
    args = sys.argv[1:]
    out = None
    if "--json" in args:
        i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
    pills = merge(args)
    for p in pills:
        ev = " ".join(f"{e['type']}@{e['hooks']}:{e['a']},{e['b']}" for e in p["events"])
        print(f"seq {p['seq']:5d} kind {p['kind']} final {int(p['final'])} up4 {p['upload4']} n{p['nev']:2d} | {ev}")
    print(f"{len(pills)} pills ({sum(p['final'] for p in pills)} final)")
    if out:
        json.dump(pills, open(out, "w"), indent=1)
