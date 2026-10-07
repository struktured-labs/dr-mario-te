#!/usr/bin/env python3
"""DRPUBLOG gate (silicon-fidelity lane, 2026-10-06): the debug-log ring records exactly what the cart sent and saw.

The real emitted driver of the debug-log cart (tools/silfid/publog_flags.py cvcp2 + DRP1AIHI=1 DRSLICEGUARD2=1
DRPUBLOG=1) runs closed-loop under py65 in test_gravity_fidelity's ROM-rule P2 world (round starts, mid-round spawns,
garbage releases -> DRPRESTART pipelines, stale DONEs; the anytime copro model publishes, flips and DONEs). P1's sliced
native AI is kept busy by re-arming its search every 24 frames. Checked against independent truth captured by the
harness itself, never by reading the logger's own scratch:
  RING   every GO (normal and prestart) opens a slot whose board + cA cB nA nB equal the bytes WRITTEN to the $5200
         window for that GO (write callbacks), whose kind is 1 iff the GO came from the prestart commit, and which is
         marked complete ($A7); seq numbers are consecutive; slots never collide inside the 25-slot ring window.
  LIVE   every type-1 event is a (col, orient4) the copro model actually published during that search; every
         publication that stayed visible >= 3 hooks while the search was armed appears as an event.
  DONE   every consumed DONE is logged as a type-2 event with the copro's final (col, orient4).
  LOCK   every P2 lock is logged as a type-5 event with the world's lock pose (X, Y << 2 | rot).
  ZP     the borrowed zero-page pair $CA/$CB is identical before and after EVERY hook.
  GUARD  (DRSLICEGUARD2 premise of the census pp_spawn cut) no hook both performs a handle(2) spawn upload (pc reaches
         h2_cq) and ticks the P1 slice (pc reaches p1s_tick); slice ticks do happen (non-vacuous). MUTANT: the same
         image with DRSLICEGUARD2=0 must show such a hook (the check can see the defect it guards).
  test_publog.py [--frames N] [--seeds 5,11]
"""
import argparse, collections, json, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import test_gravity_fidelity as G  # noqa: E402

PL_SLOT, PL_SEQ = 0x6604, 0x6605
RING, NSLOT, EV0, EVSZ = 0x6700, 25, 0x90, 6
P1AI_Y, PRE_ACT2, ARMED2 = 0x617D, 0x619A, 0x6161


def flagfile(extra):
    snap = subprocess.run([sys.executable, os.path.join(ROOT, "tools/silfid/publog_flags.py"), "cvcp2",
                           "DRP1AIHI=1"] + extra, capture_output=True, text=True, check=True).stdout.split()
    d = os.path.join(ROOT, "tmp", "publog_gate"); os.makedirs(d, exist_ok=True)
    path = os.path.join("tmp", "publog_gate", "flags_" + "_".join(x.replace("=", "") for x in extra) + ".json")
    json.dump({"flag_snapshot": dict(kv.split("=", 1) for kv in snap)}, open(os.path.join(ROOT, path), "w"))
    return path


def run(extra, frames, seed, check_log=True):
    ir, snap = G.capture(flagfile(extra), {}, "publog")
    base = G.fresh_mem(seed)
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    main = ir["units"]["main"]
    lab = {k: main["base"] + v for k, v in main["labels"].items()}
    mem = G.ObservableMemory(subject=base)
    copro = G.Copro(random.Random(seed * 7919 + 1))
    upbuf = [0] * 132
    gos = []                       # (hook index, upload bytes, prestart?)
    pubs = collections.defaultdict(list)   # go index -> [(hook, (col, o4))] published while armed
    dones = []                     # (go index, (col, o4)) consumed
    st = {"hook": 0, "consumed": False}

    def on_up(addr, value):
        upbuf[addr - 0x5200] = value

    def on_go(addr, value):
        gos.append([st["hook"], list(upbuf), None])
        return copro.on_go(addr, value)

    def on_read(addr):
        v = copro.read(addr)
        if addr == 0x5284 and v == 1 and copro.state == "idle" and not st["consumed"] and gos:
            if not dones or dones[-1][0] != len(gos) - 1:
                dones.append((len(gos) - 1, (copro.col, copro.o4)))
        return v
    mem.subscribe_to_write(range(0x5200, 0x5284), on_up)
    mem.subscribe_to_write([0x5284], on_go)
    mem.subscribe_to_read(range(0x5284, 0x5289), on_read)
    mpu = G.MPU(memory=mem)
    entry = lab["main"]
    world = G.World(random.Random(seed), base)
    hit = set()
    watch = {lab[k]: k for k in ("h2_cq", "p1s_tick") if k in lab}

    def hook():
        mpu.sp = 0xFD
        r = 0x3000 - 1
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry; base[0x3000] = 0xEA
        hit.clear(); k = 0
        while mpu.pc != 0x3000:
            if mpu.pc in watch:
                hit.add(watch[mpu.pc])
            mpu.step(); k += 1
            if k > 600000:
                raise RuntimeError(f"hook runaway pc=${mpu.pc:04X}")

    act = collections.Counter(); fails = []
    locks = []                      # (go index at lock time, (x, y<<2|rot))
    last_na = base[G.NA]
    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        if f % 24 == 0:
            base[P1AI_Y] = 0                                   # re-arm P1's sliced search (non-vacuity of GUARD)
        outs = []
        for _ in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0
            zp = (base[0xCA], base[0xCB])
            pre0 = base[PRE_ACT2]; ngo = len(gos)
            if gos and base[ARMED2] and copro.o4 != 0xFF:
                pubs[len(gos) - 1].append((st["hook"], (copro.col, copro.o4)))
            hook()
            st["hook"] += 1
            if (base[0xCA], base[0xCB]) != zp:
                act["zp_clobbered"] += 1
            if "p1s_tick" in hit:
                act["slice_ticks"] += 1
            if "h2_cq" in hit and "p1s_tick" in hit:
                act["upload_and_slice_same_hook"] += 1
            if len(gos) > ngo:
                gos[-1][2] = bool(base[PRE_ACT2] and not pre0)
            outs.append(base[0xF6])
        R = outs[0] & outs[1]
        held_used = base[0xF8]
        pressed = R & (R ^ held_used)
        base[0xF6] = pressed; base[0xF8] = R
        na0 = base[G.NA]
        world.step(f, pressed, R)
        if last_na == 0 and base[G.NA] != 0 and base[G.NA] != 6 and f < frames - 2:
            # (a lock in the run's last frames has no later hook to log it in: not counted)
            locks.append((len(gos) - 1, (base[G.X2], ((base[G.Y2] << 2) | (base[G.ROT] & 3)) & 0xFF)))
        last_na = base[G.NA]
        if not check_log:
            continue
        # ---- RING: each GO is checked once, at the end of the frame it happened in
        cur_seq = base[PL_SEQ] | (base[PL_SEQ + 1] << 8)
        while act["gos_checked"] < len(gos):
            gi = act["gos_checked"]; act["gos_checked"] += 1
            back = len(gos) - 1 - gi
            slot = (base[PL_SLOT] - back) % NSLOT
            s0 = RING + 0x100 * slot
            seq = base[s0 + 1] | (base[s0 + 2] << 8)
            ok = base[s0] == 0xA7 and seq == (cur_seq - back) & 0xFFFF
            ok &= base[s0 + 16:s0 + 144] == gos[gi][1][:128] and base[s0 + 6:s0 + 10] == gos[gi][1][128:132]
            ok &= base[s0 + 5] == (1 if gos[gi][2] else 0)
            act["ring_ok" if ok else "ring_BAD"] += 1
            if not ok and len(fails) < 3:
                fails.append(dict(go=gi, slot=slot, magic=base[s0], seq=seq, want_seq=(cur_seq - back) & 0xFFFF,
                                  kind=base[s0 + 5], prestart=gos[gi][2],
                                  board_eq=base[s0 + 16:s0 + 144] == gos[gi][1][:128],
                                  cols=(list(base[s0 + 6:s0 + 10]), gos[gi][1][128:132])))
    # ---- events of the GOs still inside the ring window
    cur_seq = base[PL_SEQ] | (base[PL_SEQ + 1] << 8)
    for back in range(min(NSLOT, len(gos))):
        gi = len(gos) - 1 - back
        slot = (base[PL_SLOT] - back) % NSLOT
        s0 = RING + 0x100 * slot
        n = base[s0 + 11]
        evs = [base[s0 + EV0 + EVSZ * i:s0 + EV0 + EVSZ * (i + 1)] for i in range(min(n, 18))]
        live = [(e[3], e[4]) for e in evs if e[0] & 0x7F == 1]
        done = [(e[3], e[4]) for e in evs if e[0] & 0x7F == 2]
        lock = [(e[3], e[4]) for e in evs if e[0] & 0x7F == 5]
        published = {v for _, v in pubs.get(gi, [])}
        act["live_events"] += len(live)
        bad = [v for v in live if v not in published]
        act["live_not_published"] += len(bad)
        # long-lived publications must be logged
        seq = pubs.get(gi, [])
        runs = []
        for h, v in seq:
            if runs and runs[-1][0] == v and runs[-1][2] == h - 1:
                runs[-1][2] = h
            else:
                runs.append([v, h, h])
        for v, h0, h1 in runs:
            if h1 - h0 + 1 >= 3:
                act["long_pubs"] += 1
                if v not in live:
                    act["long_pub_missing"] += 1
        for g2, v in dones:
            if g2 == gi:
                act["dones"] += 1
                if v not in done:
                    act["done_missing"] += 1
        for g2, v in locks:
            if g2 == gi:
                act["locks"] += 1
                if v not in lock:
                    act["lock_missing"] += 1
                    if len(fails) < 6:
                        nxt = None
                        if back > 0:
                            s1 = RING + 0x100 * ((base[PL_SLOT] - back + 1) % NSLOT)
                            nxt = [list(base[s1 + EV0 + EVSZ * i:s1 + EV0 + EVSZ * (i + 1)]) for i in range(min(base[s1 + 11], 18))]
                        fails.append(dict(lock_missing=v, go=gi, back=back, events=[list(e) for e in evs], next_slot=nxt))
    act["gos"] = len(gos); act["prestart_gos"] = sum(1 for g in gos if g[2]); act["garbage"] = world.cnt.get("garbage", 0)
    return act, fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=4000)
    ap.add_argument("--seeds", default="5,11")
    a = ap.parse_args()
    ok = True
    tot = collections.Counter(); fails = []
    for sd in (int(x) for x in a.seeds.split(",")):
        act, fl = run(["DRSLICEGUARD2=1", "DRPUBLOG=1"], a.frames, sd)
        tot.update(act); fails += fl
    checks = [
        ("RING", tot["ring_BAD"] == 0 and tot["ring_ok"] > 0 and tot["prestart_gos"] > 0,
         f"{tot['ring_ok']} GOs logged exactly ({tot['prestart_gos']} prestart), {tot['ring_BAD']} bad"),
        ("LIVE", tot["live_not_published"] == 0 and tot["long_pub_missing"] == 0 and tot["live_events"] > 0,
         f"{tot['live_events']} live events, {tot['live_not_published']} never published, "
         f"{tot['long_pub_missing']}/{tot['long_pubs']} long-lived publications missing"),
        ("DONE", tot["done_missing"] == 0 and tot["dones"] > 0, f"{tot['dones']} DONEs, {tot['done_missing']} missing"),
        ("LOCK", tot["lock_missing"] == 0 and tot["locks"] > 0, f"{tot['locks']} locks, {tot['lock_missing']} missing"),
        ("ZP", tot["zp_clobbered"] == 0, f"$CA/$CB changed across {tot['zp_clobbered']} hooks"),
        ("GUARD", tot["upload_and_slice_same_hook"] == 0 and tot["slice_ticks"] > 0,
         f"{tot['slice_ticks']} slice ticks, {tot['upload_and_slice_same_hook']} hooks with upload + slice"),
    ]
    for name, good, msg in checks:
        ok &= good
        print(f"{name:6s} {'PASS' if good else 'FAIL'}  {msg}")
    if fails:
        print("  failures:", fails[:6])
    mt = collections.Counter()
    for sd in (int(x) for x in a.seeds.split(",")):
        act, _ = run(["DRSLICEGUARD2=0", "DRPUBLOG=1"], a.frames, sd, check_log=False)
        mt.update(act)
    killed = mt["upload_and_slice_same_hook"] > 0
    ok &= killed
    print(f"MUTANT DRSLICEGUARD2=0: {'KILLED' if killed else 'SURVIVED'} ({mt['upload_and_slice_same_hook']} hooks with "
          f"upload + slice, {mt['slice_ticks']} slice ticks)")
    print(f"(world: {tot['gos']} GOs, garbage {tot['garbage']})")
    print("PUBLOG GATE: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
