#!/usr/bin/env python3
"""ORIENTATION-AT-LOCK harness for the P2 driver (couch forensics lead 2026-09-27: 180-degree colour flips cluster on
DRPROPH pills, 4/41 vs 2/817 on silicon).

Same closed loop as gate_tap_interface.py (the REAL emitted driver under py65; ROM getInputs semantics; the ROM-rule
world; an emulated copro on the P2 mailbox), but instead of checking the controller interface it scores WHERE and HOW
each capsule locks against the target the driver was actually given (the copro's last published answer, mapped to
game orient exactly as the driver maps it {0:3,1:1,2:0,3:2}):
  exact  : lock column == target column AND lock orient == target orient
  flip180: lock column == target column AND lock orient == target orient ^ 2  (right cells, halves reversed)
  other  : anything else (wrong column, 90-degree off, early lock ...)
split by whether PROPH was active on the pill (PROPH_DIR != 0 at any hook of the pill), and by DRTAPP (0 = DAS).
Each flip180 gets a per-frame trace (pad R / pressed / world rot / driver TGT_O2 / ROT_DONE2 / PEND2 / ARMED2 /
PROPH_DIR / tap cooldown) for the mechanism.
Usage: orient_harness.py --tap 2|0 [--frames N] [--seed S] [--throat F] [--flips F] [--overlay K=V ...]
"""
import argparse, collections, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_tap_interface as G

ROT_DONE2, PEND2, TGT_C2, TGT_O2, ARMED2, PROPH_DIR, DELAY2 = 0x616E, 0x614F, 0x6152, 0x6153, 0x6161, 0x61C6, 0x615F
TAP_CD, TAP_H = 0x61D2, 0x61D1
C2G = {0: 3, 1: 1, 2: 0, 3: 2}


class Copro(G.Copro):
    """Deterministic-per-GO answers; flips only with probability `flips`. Serves the tuck descriptor as 'no tuck'."""
    def __init__(self, wbase, rng, mem, flips):
        super().__init__(wbase, rng, mem); self.flips = flips

    def on_go(self, addr, value):
        super().on_go(addr, value)
        if self.rng.random() >= self.flips:
            self.t_flip = None
        return 0

    def read(self, addr):
        off = addr - self.w
        if off in (0x87, 0x88):
            return 0xFF if off == 0x87 else 0
        return super().read(addr)


class World(G.World):
    def __init__(self, rng, mem, throat, on_lock):
        self.throat = throat; self.on_lock = on_lock
        super().__init__(rng, mem)

    def new_board(self):
        super().new_board()
        if self.rng.random() < self.throat:                  # force the PROPH ledge regime: tall throat in c3/c4
            for c in (3, 4):
                h = self.rng.choice([13, 14, 15])
                for row in range(16):
                    self.board[row][c] = 0
                for row in range(16 - min(h, 15), 16):
                    self.board[row][c] = 0x60 | self.rng.randrange(3)
            for c in (3, 4):
                self.board[0][c] = 0

    def lock(self):
        self.on_lock(self.x, self.row, self.rot)
        super().lock()

    def step(self, frame, pressed, held):
        # a board reset is a new ROUND, modelled like the ROM: level init runs generateNextPill twice (counter += 2,
        # Y = $0F) with NO capsule live (nextAction = sendPill), then Mario's throw spawns the first capsule (counter
        # += 1, Y = $0F again). This is the state DRSPAWNEDGE must not double-fire in.
        if not self.active and self.spawn_in <= 1 and (not (self.empty(0, 3) and self.empty(0, 4))
                                                      or self.pills_on_board >= 30):
            self.new_board()
            self.pills += 2
            self.x, self.row, self.rot = 3, 0, 0
            self.spawn_in = self.rng.randint(12, 30)
            self.rounds = getattr(self, "rounds", 0) + 1
            return
        super().step(frame, pressed, held)


def run(tap, frames, seed, throat, flips, overlays, trace_n=6, trace_pred=None):
    tmpd = os.path.join(G.ROOT, "tmp", "tapgate"); os.makedirs(tmpd, exist_ok=True)
    extra = {"DRTAPP": str(tap)}; extra.update(overlays)
    tag = "_".join(f"{k}{v}" for k, v in sorted(overlays.items()))
    ir, snap = G.capture("couch", extra, os.path.join(tmpd, f"orient_p{tap}_{tag}_s{seed}_{os.getpid()}_ir.json"))  # per-process: parallel runs must not share the IR file
    assert snap.get("DRPROPH") == "1"
    wbase = 0x5000 if snap.get("DRPOCKET") == "1" else 0x5200
    rng = random.Random(seed)
    base = [0] * 0x10000
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    mem = G.ObservableMemory(subject=base)
    copro = Copro(wbase, rng, base, flips)
    mem.subscribe_to_write([wbase + 0x84], copro.on_go)
    mem.subscribe_to_read(range(wbase + 0x84, wbase + 0x89), copro.read)

    def on_delay2(addr, value):                             # the new-pill block's `LDA #15; STA DELAY2` = one edge firing
        if value == 15:
            pill["n_edges"] = pill.get("n_edges", 0) + 1
        return value
    mem.subscribe_to_write([DELAY2], on_delay2)
    mpu = G.MPU(memory=mem)
    entry = ir["units"]["main"]["base"] + ir["units"]["main"]["labels"]["main"]
    base[G.MAGIC] = 0xA5; base[G.MODE] = 4; base[G.Z04] = 1; base[G.MATCH] = 1
    base[0x0324] = 20; base[G.P2["vc"]] = 20; base[G.P2["lvl"]] = 11
    for i in range(128):
        base[0x0400 + i] = 0xFF; base[0x0780 + i] = rng.randrange(9)

    pill = {}; results = []; traces = []

    def on_lock(x, row, rot):
        tgt = (copro.col, copro.o4) if copro.o4 != 0xFF else (None, None)
        tcol = tgt[0]; trot = C2G.get(tgt[1]) if tgt[1] is not None else None
        if tcol is not None and trot is not None and trot % 2 == 0 and tcol > 6:
            tcol = 6
        if trot is None:
            cls = "noanswer"
        elif x == tcol and rot == trot:
            cls = "exact"
        elif x == tcol and rot == (trot ^ 2):
            cls = "flip180"
        else:
            cls = "other"
        rec = dict(pill=world_ref[0].pills, proph=pill.get("proph", False), cls=cls, x=x, row=row, rot=rot,
                   tcol=tcol, trot=trot, drv_tgt_o=base[TGT_O2], drv_tgt_c=base[TGT_C2], rot_done=base[ROT_DONE2],
                   pend=base[PEND2], armed=base[ARMED2], age=getattr(world_ref[0], "age", None),
                   spawn_edge=pill.get("edge", False), n_rot_press=pill.get("nrot", 0), n_lat_press=pill.get("nlat", 0),
                   ans_age=pill.get("ans_age"), chg_age=pill.get("chg_age"), nchg=pill.get("nchg", 0),
                   n_edges=pill.get("n_edges", 0))
        results.append(rec)
        want = trace_pred(rec) if trace_pred else cls == "flip180"
        if want and len(traces) < trace_n:
            traces.append(dict(rec=rec, trace=list(pill.get("trace", []))))

    world_ref = [None]
    world = World(rng, base, throat, on_lock); world_ref[0] = world
    world.publish()

    def hook():
        mpu.sp = 0xFD; r = 0x3000 - 1
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry; base[0x3000] = 0xEA
        k = 0
        while mpu.pc != 0x3000:
            mpu.step(); k += 1
            if k > 400000:
                raise RuntimeError(f"hook runaway pc=${mpu.pc:04X}")

    was_active = False
    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        outs = []
        for p in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0
            hook(); outs.append(base[0xF6])
            if base[PEND2]:
                pill["edge"] = True
        R = outs[0] & outs[1]
        held_used = base[0xF8]
        pressed = R & (R ^ held_used)
        base[0xF6] = pressed; base[0xF8] = R
        if world.active and not was_active:
            pass
        if world.active:
            if base[PROPH_DIR]:
                pill["proph"] = True
            if pressed & (G.A_ | G.B_):
                pill["nrot"] = pill.get("nrot", 0) + 1
            if pressed & (G.LEFT_ | G.RIGHT_):
                pill["nlat"] = pill.get("nlat", 0) + 1
            if "ans_age" not in pill and copro.o4 != 0xFF and not base[PEND2] and pill.get("edge"):
                pill["ans_age"] = world.age
            if copro.o4 != 0xFF and pill.get("edge") and not base[PEND2] and pill.get("last_ans") != (copro.col, copro.o4):
                pill["last_ans"] = (copro.col, copro.o4); pill["chg_age"] = world.age; pill["nchg"] = pill.get("nchg", 0) + 1
            pill.setdefault("trace", []).append(
                (f, world.age if hasattr(world, "age") else None, world.x, world.row, world.rot, hex(R), hex(pressed),
                 copro.col, copro.o4, base[TGT_C2], base[TGT_O2], base[ROT_DONE2], base[PEND2], base[ARMED2],
                 base[PROPH_DIR], base[TAP_CD]))
        prev_active = world.active
        world.step(f, pressed, R)
        world.publish()
        if prev_active and not world.active:
            pill = {}                                        # locked: next pill starts clean
        was_active = world.active

    by = collections.defaultdict(collections.Counter)
    for r in results:
        by["proph" if r["proph"] else "nonproph"][r["cls"]] += 1
    summ = {}
    for k, c in by.items():
        n = sum(c.values()); ans = n - c["noanswer"]
        summ[k] = dict(n=n, answered=ans, **{cl: c[cl] for cl in ("exact", "flip180", "other", "noanswer")},
                       flip180_rate=round(c["flip180"] / ans, 4) if ans else None,
                       flip180_given_rightcol=round(c["flip180"] / max(1, c["flip180"] + c["exact"]), 4))
    return dict(tap=tap, overlays=overlays, frames=frames, seed=seed, throat=throat, flips=flips,
                pills=len(results), summary=summ), traces, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tap", type=int, default=2); ap.add_argument("--frames", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--throat", type=float, default=0.5)
    ap.add_argument("--flips", type=float, default=0.0); ap.add_argument("--overlay", nargs="*", default=[])
    ap.add_argument("--traces", default=None); ap.add_argument("--rows", default=None)
    a = ap.parse_args()
    ov = dict(kv.split("=", 1) for kv in a.overlay)
    res, traces, rows = run(a.tap, a.frames, a.seed, a.throat, a.flips, ov)
    print(json.dumps(res))
    if a.traces:
        json.dump(traces, open(a.traces, "w"))
    if a.rows:
        with open(a.rows, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
