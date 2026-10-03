#!/usr/bin/env python3
"""py65 WHOLE-DECISION gates for DRTUCKREACH / DRTUCKLIVE / DRROOTORD (firmware LOGIC, golden-leaf engine emulator).

Part 1 -- reads py65_ab.py rows (every arm on the same boards) and checks:
  RO   DRROOTORD is decision-identical in every context it is added to: ro == off, ship == trtl (and trro == tr,
       rotl == tl when present) on the final (col, o4), the tuck descriptor AND the tuck candidate list at the
       extension's entry (with DRTUCKLIVE off the o_done restore must hand the enumerator today's CUR, byte-equal).
  TR   DRTUCKREACH vs off: identical wherever off's tuck did not commit, or R_FLT = 0, or off's final is in the mask;
       wherever the filter is live (R_FLT = 1) the tr final is inside the reach_fw mask; and no S_BEST store happens
       between the tuck-extension entry and the stub's DONE store (no bare live publish).
  REACH the R_FLT / ROK[32] the tuck extension reads == reach_fw (python spec) for the uploaded bytes.
  TL   DRTUCKLIVE: the enumerator's board -- reported (how often the stale CUR differs from LIVE, and how often the
       candidate list / final changes).
Part 2 (--mutants) -- targeted boards, each mutant must be KILLED:
  tr_nomask (DRTUCKREACH without the mask skip)  -> a final outside the mask on a filtered board
  tr_livepub (DRTUCKREACH keeping the bare publish) -> an S_BEST store inside the tuck extension
  ro_notie (no equal-val tie rule)               -> a final != off
  ro_fworder (pass C in today's order)           -> publish sequence == off's on EVERY board (real ro must differ)
  ro_norestore (no o_done CUR restore)           -> a tuck candidate list != off's
Part 3 (--ram) -- every RAM byte written by the ro / ship arms is written by the off arm too, or lies in the
  DRROOTORD block $0200-$0286.
Usage: gate_py65.py ROWS.jsonl [ROWS2.jsonl ...] [--mutants] [--ram] [--workers 3]
"""
import argparse
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def key(r, a):
    x = r[a]
    return tuple(x["final"]), tuple(x["tuck"])


def tucked(x):
    return x["tuck"][0] != 255


def in_mask(row, x):
    if not x["entry"] or x["entry"]["rflt"] == 0:
        return True
    return bool(row["mask"][x["final"][1] * 8 + x["final"][0]])


def bare_pub(x):
    """S_BEST stores after the tuck-extension entry other than the stub's final pair."""
    e = x["entry"]
    if not e:
        return 0
    return max(0, len(x["pubs"]) - e["npub"] - 2)


def part1(rows):
    out, ok = [], True
    arms = [a for a in ("off", "tr", "ro", "tl", "trro", "trtl", "rotl", "ship") if all(a in r for r in rows)]
    out.append(f"boards {len(rows)}, arms {arms}")
    # ---- RO identity
    for a, b in (("off", "ro"), ("tr", "trro"), ("tl", "rotl"), ("trtl", "ship")):
        if a in arms and b in arms:
            same = sum(key(r, a) == key(r, b) for r in rows)
            cand = sum((r[a]["entry"] or {}).get("cand") == (r[b]["entry"] or {}).get("cand") for r in rows)
            curq = sum((r[a]["entry"] or {}).get("cur") == (r[b]["entry"] or {}).get("cur") for r in rows)
            okk = same == len(rows) and cand == len(rows)
            ok &= okk
            out.append(f"RO  {b} vs {a}: final+tuck identical {same}/{len(rows)}; tuck candidate list identical "
                       f"{cand}/{len(rows)}; enumerator board ($0700) identical {curq}/{len(rows)}  "
                       f"{'PASS' if okk else 'FAIL'}")
            for r in rows:
                if key(r, a) != key(r, b):
                    out.append(f"    DIFF {r['id']}: {a} {key(r, a)} {b} {key(r, b)}")
    # ---- TR vs off
    if "tr" in arms:
        n_fire = n_out = n_same_req = n_same = 0
        moved = []
        for r in rows:
            o, t = r["off"], r["tr"]
            fired = tucked(o)
            n_fire += fired
            masked = fired and o["entry"]["rflt"] == 1 and not in_mask(r, o)
            n_out += masked
            if not masked:
                n_same_req += 1; n_same += key(r, "off") == key(r, "tr")
            else:
                moved.append(f"    MASKED TUCK {r['id']}: off {key(r, 'off')} -> tr {key(r, 'tr')} (in mask: {in_mask(r, t)})")
        tr_in = sum(in_mask(r, r["tr"]) for r in rows)
        bare = sum(bare_pub(r["tr"]) > 0 for r in rows)
        bare_off = sum(bare_pub(r["off"]) > 0 for r in rows)
        okk = n_same == n_same_req and tr_in == len(rows) and bare == 0
        ok &= okk
        out.append(f"TR  off: tuck commits {n_fire}/{len(rows)}, outside the mask (R_FLT=1) {n_out}")
        out.append(f"TR  tr == off where off's tuck did not fire / fired in-mask: {n_same}/{n_same_req}; tr final in the "
                   f"mask (or filter off) {tr_in}/{len(rows)}; boards with a bare live tuck publish: tr {bare}, off "
                   f"{bare_off}  {'PASS' if okk else 'FAIL'}")
        out += moved
    # ---- REACH state at the tuck entry == the python spec
    ent = [(r, r["off"]["entry"]) for r in rows if r["off"]["entry"]]
    rk = sum([e["rok"][i] for i in range(32)] == r["mask"] for r, e in ent)
    okk = rk == len(ent)
    ok &= okk
    out.append(f"REACH ROK[32] at the tuck entry == reach_fw(upload): {rk}/{len(ent)}; R_FLT=1 on "
               f"{sum(e['rflt'] == 1 for r, e in ent)} (0 = the all-masked Pass-0 fallback)  {'PASS' if okk else 'FAIL'}")
    # ---- TL
    if "tl" in arms:
        stale = sum(not r["off"]["entry"]["cur_eq_live"] for r in rows if r["off"]["entry"])
        cdiff = sum(r["off"]["entry"]["cand"] != r["tl"]["entry"]["cand"] for r in rows if r["off"]["entry"])
        fdiff = [r for r in rows if key(r, "off") != key(r, "tl")]
        tl_fire = sum(tucked(r["tl"]) for r in rows)
        out.append(f"TL  enumerator board != LIVE (stale CUR) on {stale}/{len(ent)}; candidate list changes {cdiff}; "
                   f"final/tuck changes {len(fdiff)}; tl tuck commits {tl_fire} (off {sum(tucked(r['off']) for r in rows)})")
        for r in fdiff:
            out.append(f"    TL {r['id']}: off {key(r, 'off')} in-mask {in_mask(r, r['off'])} -> tl {key(r, 'tl')} "
                       f"in-mask {in_mask(r, r['tl'])}")
    if "trtl" in arms:
        tin = sum(in_mask(r, r["trtl"]) for r in rows)
        out.append(f"TRTL final in the mask {tin}/{len(rows)}; tuck commits {sum(tucked(r['trtl']) for r in rows)}")
        ok &= tin == len(rows)
    return out, ok


MUT = {}


def mut_init():
    import fwlib as F
    D3, TV = F.D3, F.TV
    MUT["off"] = F.image()
    MUT["tr"] = F.image(1, 0)
    MUT["ro"] = F.image(0, 1)
    TV._TUCKREACH_NOMASK_MUT = True; MUT["tr_nomask"] = F.image(1, 0); TV._TUCKREACH_NOMASK_MUT = False
    TV._TUCKREACH_LIVEPUB_MUT = True; MUT["tr_livepub"] = F.image(1, 0); TV._TUCKREACH_LIVEPUB_MUT = False
    D3._ROOTORD_NOTIE_MUT = True; MUT["ro_notie"] = F.image(0, 1); D3._ROOTORD_NOTIE_MUT = False
    D3._ROOTORD_FWORDER_MUT = True; MUT["ro_fworder"] = F.image(0, 1); D3._ROOTORD_FWORDER_MUT = False
    D3._ROOTORD_NORESTORE_MUT = True; MUT["ro_norestore"] = F.image(0, 1); D3._ROOTORD_NORESTORE_MUT = False
    assert F.hex_md5(MUT["ro"]) != F.hex_md5(MUT["ro_notie"]) != F.hex_md5(MUT["ro_fworder"])


def mut_task(t):
    import fwlib as F
    bd, arms = t
    res = {"id": bd["id"], "mask": bd["mask"]}
    for a in arms:
        r = F.run(MUT[a], bd["nes"], *bd["go"])
        res[a] = dict(final=r["final"], tuck=r["tuck"], entry=r["entry"], npubs=len(r["pubs"]),
                      seq=[(c, v) for _, c, v in r["pubs"]], bare=bare_pub(r))
    return res


def run_forced(img, board, go, C=1000):
    """One whole decision with every root's val1 FORCED to the same value C at the deep comparison: reads of D_V1L/H
    return C while the search runs (in DRROOTORD images only during pass C, RO_MODE == 0, so the pre-pass d2 values --
    and therefore pass C's order -- stay genuine), and stop at the tuck-extension entry. All roots then tie: today's
    firmware keeps the FIRST root in today's order, which the tie rule must reproduce for any pass-C order."""
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    import fwlib as F
    D3, TV = F.D3, F.TV
    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    base = cpu.mem
    obs = ObservableMemory(subject=base)
    st = {"on": True}
    ro = bool(MUT.get("_ro_img") is img)

    def rd(addr):
        if st["on"] and (not ro or base[D3.RO_MODE] == 0):
            return (C & 0xFF) if addr == D3.D_V1L else (C >> 8)
        return base[addr]

    def on_bk(addr, v):
        base[addr] = v
        if v == 0 and st["on"]:
            st["on"] = False
            st["main"] = (base[D3.D_BC], base[D3.D_BO])       # the SEARCH's answer, before any tuck can replace it
    obs.subscribe_to_read([D3.D_V1L, D3.D_V1H], rd)
    obs.subscribe_to_write([TV.TK2_BKIND], on_bk)
    cpu.mpu.memory = obs; cpu.mem = obs
    cpu.mem[F.S_CA], cpu.mem[F.S_CB], cpu.mem[F.S_NA], cpu.mem[F.S_NB] = go
    cpu.mem[F.DONE] = 0
    m = cpu.mpu; m.pc = F.B.STUB; m.sp = 0xFF
    while base[F.DONE] != 1:
        m.step()
    return st.get("main")


def tie_task(t):
    """Tie-rule stress: off / ro / ro_notie with every root's val1 forced equal at the comparison (run_forced)."""
    res = {"id": t["id"]}
    for a in ("off", "ro", "ro_notie"):
        MUT["_ro_img"] = MUT[a] if a != "off" else None
        res[a] = run_forced(MUT[a], t["nes"], t["go"])
    return res


def part2(rows, workers):
    """Targeted boards from the A/B rows: tuck boards (off committed), double-pill boards, and a plain sample."""
    tuckb = [r for r in rows if tucked(r["off"])]
    trtk = [r for r in rows if tucked(r["tr"]) and r["tr"]["entry"]["rflt"] == 1]           # in-mask tuck commits
    dbl = [r for r in rows if (r["go"][0] & 3) == (r["go"][1] & 3)][:12]
    stale = [r for r in rows if r["off"]["entry"] and not r["off"]["entry"]["cur_eq_live"]
             and r["off"]["entry"]["cand"]][:12]
    plain = rows[:12]
    jobs = []
    for r in {x["id"]: x for x in tuckb + trtk[:8] + dbl + stale + plain}.values():
        bd = dict(id=r["id"], nes=r["nes"], go=r["go"], mask=r["mask"])
        jobs.append((bd, ["off", "tr", "ro", "tr_nomask", "tr_livepub", "ro_notie", "ro_fworder", "ro_norestore"]))
    with mp.get_context("fork").Pool(workers, initializer=mut_init) as pool:
        R = pool.map(mut_task, jobs, chunksize=1)
    out, ok = [f"mutant boards {len(R)} (tuck {len(tuckb)}, in-mask tr tuck {len(trtk)}, doubles {len(dbl)}, "
               f"stale-CUR {len(stale)})"], True
    inm = lambda x, r: (not x["entry"]) or x["entry"]["rflt"] == 0 or bool(r["mask"][x["final"][1] * 8 + x["final"][0]])
    k1 = sum(not inm(r["tr_nomask"], r) for r in R)
    k2 = sum(r["tr_livepub"]["bare"] > 0 for r in R)
    k2r = sum(r["tr"]["bare"] > 0 for r in R)
    k3 = sum((r["ro_notie"]["final"], r["ro_notie"]["tuck"]) != (r["off"]["final"], r["off"]["tuck"]) for r in R)
    k4m = sum(r["ro_fworder"]["seq"] != r["off"]["seq"] for r in R)
    k4r = sum(r["ro"]["seq"] != r["off"]["seq"] for r in R)
    k5 = sum((r["ro_norestore"]["entry"] or {}).get("cand") != (r["off"]["entry"] or {}).get("cand") for r in R)
    k5r = sum((r["ro"]["entry"] or {}).get("cand") != (r["off"]["entry"] or {}).get("cand") for r in R)
    tie_boards = [dict(id=r["id"], nes=r["nes"], go=r["go"]) for r in rows[::3][:12]]
    with mp.get_context("fork").Pool(workers, initializer=mut_init) as pool:
        TR = pool.map(tie_task, tie_boards, chunksize=1)
    t_same = sum(r["ro"] == r["off"] for r in TR)
    t_kill = sum(r["ro_notie"] != r["off"] for r in TR)
    out.append(f"  tie stress (every root's val1 forced equal at the comparison, {len(TR)} boards): ro == off "
               f"{t_same}/{len(TR)}; ro_notie != off {t_kill}")
    ok &= t_same == len(TR)
    k3 += t_kill
    for name, killed, detail in (
            ("tr_nomask", k1 > 0, f"finals outside the mask {k1}"),
            ("tr_livepub", k2 > 0 and k2r == 0, f"boards with a bare publish: mutant {k2}, real tr {k2r}"),
            ("ro_notie", k3 > 0, f"finals != off {k3}"),
            ("ro_fworder", k4m == 0 and k4r > 0, f"publish sequence != off: mutant {k4m}, real ro {k4r}"),
            ("ro_norestore", k5 > 0 and k5r == 0, f"tuck candidate list != off: mutant {k5}, real ro {k5r}")):
        out.append(f"  mutant {name:13s} {'KILLED' if killed else 'SURVIVED'}  ({detail})")
        ok &= killed
    return out, ok


def part3(rows, workers):
    import fwlib as F
    used = {}
    for a in ("off", "ro", "ship"):
        tr, ro, tl = {"off": (0, 0, 0), "ro": (0, 1, 0), "ship": (1, 1, 1)}[a]
        img = F.image(tr, ro, DRTUCKLIVE=tl)
        s = set()
        for r in rows[:4] + [x for x in rows if tucked(x["off"])][:2]:
            s |= F.run(img, r["nes"], *r["go"], ramscan=True)["ram"]
        used[a] = s
    blk = set(range(0x0200, 0x0287))
    bfs = set(range(0x0E00, 0x1000))   # tuck_bfs VISITED/OUT arrays + tier3 MONO_VIS: its own claim; how far the OUT
    out, ok = [], True                 # arrays fill depends on the candidate count, which DRTUCKLIVE changes
    for a in ("ro", "ship"):
        extra = sorted(used[a] - used["off"] - blk - bfs)
        out.append(f"RAM {a}: writes outside (off's set U $0200-$0286 U tuck_bfs's own $0E00-$0FFF): {len(extra)} "
                   f"{[hex(x) for x in extra[:8]]}; RO block bytes written {len(used[a] & blk)}; new bytes inside "
                   f"$0E00-$0FFF {len((used[a] - used['off']) & bfs)}")
        ok &= not extra
    out.append(f"RAM off arm never writes $0200-$02FF: {not any(0x0200 <= x < 0x0300 for x in used['off'])}")
    ok &= not any(0x0200 <= x < 0x0300 for x in used["off"])
    return out, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="+"); ap.add_argument("--mutants", action="store_true")
    ap.add_argument("--ram", action="store_true"); ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    rows = [json.loads(l) for f in args.rows for l in open(f)]
    o, ok = part1(rows)
    print("\n".join(o))
    if args.mutants:
        o2, ok2 = part2(rows, args.workers); print("\n".join(o2)); ok &= ok2
    if args.ram:
        o3, ok3 = part3(rows, args.workers); print("\n".join(o3)); ok &= ok3
    print("GATE_PY65", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
