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
  PDW    (--pdw: + DRPUBLOG_PDW=1, the post-DONE watch) the copro model is given FALSE DONEs: on ~30% of searches $5284
         reads 1 for ONE frame mid-search, then 0 again until the real DONE. Every false DONE the cart consumed must
         produce a type-6 event in that search's slot (DONE read back as 0), and no search whose DONE was genuine may
         log one (non-vacuous both ways: false DONEs and genuine DONEs must each occur).
  test_publog.py [--frames N] [--seeds 5,11] [--extra 'K=V ...'] [--pdw]
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


class FalseDoneCopro(G.Copro):
    """G.Copro + FALSE DONEs: on ~30% of searches DONE reads 1 before the real DONE, either for ONE READ (a single-read
    glitch, caught by the immediate re-read) or for a whole frame (caught by the post-DONE watch)."""
    def on_go(self, addr, value):
        r = G.Copro.on_go(self, addr, value)
        self.t_false = None
        if self.t_done - self.frame >= 6 and self.rng.random() < 0.3:
            self.t_false = self.rng.randint(self.frame + 2, self.t_done - 3)
            self.single = self.rng.random() < 0.5; self.fired = False
        return r

    def read(self, addr):
        v = G.Copro.read(self, addr)
        if addr - self.w == 0x84 and self.state == "search" and self.t_false is not None and self.frame == self.t_false:
            if self.single:
                if self.fired:
                    return v
                self.fired = True
            return 1
        return v


def run(extra, frames, seed, check_log=True, pdw=False):
    ir, snap = G.capture(flagfile(extra), {}, "publog")
    base = G.fresh_mem(seed)
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    main = ir["units"]["main"]
    lab = {k: main["base"] + v for k, v in main["labels"].items()}
    mem = G.ObservableMemory(subject=base)
    copro = (FalseDoneCopro if pdw else G.Copro)(random.Random(seed * 7919 + 1))
    upbuf = [0] * 132
    false_done = {}                # go index -> hook that consumed a FALSE DONE (the search was still running)
    playhook = []                  # per hook index: was it a play hook
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
        if pdw and addr == 0x5284 and v == 1 and copro.state == "search" and gos and base[ARMED2]:
            st["false_read"] = "single" if copro.single else "frame"                            # a FALSE DONE read in an armed search (consumed iff
                                                               # the hook ends with the search torn down, below)
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
            play = base[G.MODE] == 4 and base[G.Z04] != 0       # pl_hook runs only on play hooks (dispatch)
            playhook.append(play)
            if gos and base[ARMED2] and copro.o4 != 0xFF and play:
                pubs[len(gos) - 1].append((st["hook"], (copro.col, copro.o4)))
            armed0 = base[ARMED2]; st["false_read"] = False
            hook()
            st["hook"] += 1
            if pdw and armed0 and not base[ARMED2] and st["false_read"] and len(gos) == ngo:
                false_done[len(gos) - 1] = (st["hook"] - 1, st["false_read"])   # consumed the false DONE (teardown)
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
        live = [(e[3], e[4]) for e in evs if e[0] & 0x3F == 1]
        done = [(e[3], e[4]) for e in evs if e[0] & 0x3F == 2]
        lock = [(e[3], e[4]) for e in evs if e[0] & 0x3F == 5]
        pdone = [(e[3], e[4], e[5]) for e in evs if e[0] & 0x3F == 6]
        rr0 = any(e[0] & 0x3F == 2 and e[0] & 0x40 for e in evs)          # DONE event flagged: re-read was 0
        if pdw and back > 0:                                   # (the newest search may not have reached its watch yet)
            if gi in false_done:
                # the watch's opportunity: play hooks after the consuming hook and before the next GO. The first few
                # carry the higher-priority DONE / target / lock events (one event per hook), so only a false DONE
                # followed by >= 6 play hooks is REQUIRED to be caught; shorter windows are counted, not judged.
                (h_c, kind), h_g = false_done[gi], gos[gi + 1][0]
                opp = sum(playhook[h_c + 1:h_g])
                caught = any(d[0] == 0 for d in pdone) or rr0
                if kind == "single":                           # the immediate re-read must flag it, window or not
                    act["pdw_single"] += 1
                    act["pdw_single_flagged" if rr0 else "pdw_missed"] += 1
                    if not rr0 and len(fails) < 6:
                        fails.append(dict(pdw_single_missed=gi, events=[list(e) for e in evs]))
                elif opp >= 6:
                    act["pdw_false_dones"] += 1
                    act["pdw_detected" if caught else "pdw_missed"] += 1
                    if not caught and len(fails) < 6:
                        fails.append(dict(pdw_missed=gi, window_play_hooks=opp, events=[list(e) for e in evs]))
                else:
                    act["pdw_short_window"] += 1; act["pdw_short_caught"] += caught
            elif done:
                act["pdw_genuine_dones"] += 1
                act["pdw_spurious"] += len(pdone) + int(rr0)
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
                    if len(fails) < 6:
                        fails.append(dict(long_pub_missing=v, go=gi, hooks=(h0, h1), go_hook=gos[gi][0],
                                          false_done=gi in false_done, events=[list(e) for e in evs]))
        for g2, v in dones:
            if g2 == gi:
                act["dones"] += 1
                if v not in done:
                    act["done_missing"] += 1
        for g2, v in locks:
            if g2 == gi:
                act["locks"] += 1
                if v not in lock and back > 0:
                    # pl_hook runs after handle(2) in the hook: a lock first observed in the hook that GOes the next
                    # search is logged as that NEXT slot's first event (hooks 0). Accepted, and counted.
                    s1 = RING + 0x100 * ((base[PL_SLOT] - back + 1) % NSLOT)
                    first = base[s1 + EV0:s1 + EV0 + EVSZ] if base[s1 + 11] else None
                    if first is not None and first[0] & 0x3F == 5 and first[1] == 0 and (first[3], first[4]) == v:
                        act["locks_in_next_slot"] += 1
                        continue
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
    ap.add_argument("--pdw", action="store_true", help="+ DRPUBLOG_PDW=1 with false-DONE injection (PDW check)")
    ap.add_argument("--extra", default="", help="extra K=V flags, e.g. 'DRP1HOLD=1 DRGPUMP=1' (PUBLOG capture #2); "
                    "the slice-guard checks then only require 0 violations and the DRSLICEGUARD2 mutant is skipped "
                    "(DRP1HOLD leaves almost no slice ticks to collide with -- the guard is proven on the base flags)")
    a = ap.parse_args()
    extra = a.extra.split() + (["DRPUBLOG_PDW=1"] if a.pdw else [])
    ok = True
    tot = collections.Counter(); fails = []
    for sd in (int(x) for x in a.seeds.split(",")):
        act, fl = run(["DRSLICEGUARD2=1", "DRPUBLOG=1"] + extra, a.frames, sd, pdw=a.pdw)
        tot.update(act); fails += fl
    checks = [
        ("RING", tot["ring_BAD"] == 0 and tot["ring_ok"] > 0 and tot["prestart_gos"] > 0,
         f"{tot['ring_ok']} GOs logged exactly ({tot['prestart_gos']} prestart), {tot['ring_BAD']} bad"),
        ("LIVE", tot["live_not_published"] == 0 and tot["long_pub_missing"] == 0 and tot["live_events"] > 0,
         f"{tot['live_events']} live events, {tot['live_not_published']} never published, "
         f"{tot['long_pub_missing']}/{tot['long_pubs']} long-lived publications missing"),
        ("DONE", tot["done_missing"] == 0 and tot["dones"] > 0, f"{tot['dones']} DONEs, {tot['done_missing']} missing"),
        ("LOCK", tot["lock_missing"] == 0 and tot["locks"] > 0, f"{tot['locks']} locks, {tot['lock_missing']} missing "
         f"({tot['locks_in_next_slot']} observed in the next search's GO hook, logged there)"),
        ("ZP", tot["zp_clobbered"] == 0, f"$CA/$CB changed across {tot['zp_clobbered']} hooks"),
        ("GUARD", tot["upload_and_slice_same_hook"] == 0 and (tot["slice_ticks"] > 0 or bool(extra)),
         f"{tot['slice_ticks']} slice ticks, {tot['upload_and_slice_same_hook']} hooks with upload + slice"),
    ]
    if a.pdw:
        checks.append(("PDW", tot["pdw_missed"] == 0 and tot["pdw_spurious"] == 0 and tot["pdw_false_dones"] > 0
                       and tot["pdw_single"] > 0 and tot["pdw_genuine_dones"] > 0,
                       f"{tot['pdw_single_flagged']}/{tot['pdw_single']} single-read false DONEs flagged by the "
                       f"immediate re-read; {tot['pdw_detected']}/{tot['pdw_false_dones']} frame-long false DONEs logged as type 6 "
                       f"(+{tot['pdw_short_caught']}/{tot['pdw_short_window']} with < 6 play hooks before the next GO), "
                       f"{tot['pdw_spurious']} type-6 events on {tot['pdw_genuine_dones']} genuine DONEs"))
    for name, good, msg in checks:
        ok &= good
        print(f"{name:6s} {'PASS' if good else 'FAIL'}  {msg}")
    if fails:
        print("  failures:", fails[:6])
    if extra:
        print(f"(extra flags {extra}: DRSLICEGUARD2 mutant skipped; world: {tot['gos']} GOs, garbage {tot['garbage']})")
        print("PUBLOG GATE: " + ("ALL PASS" if ok else "FAILED"))
        sys.exit(0 if ok else 1)
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
