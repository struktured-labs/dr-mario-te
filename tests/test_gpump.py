#!/usr/bin/env python3
"""DRP1HOLD + DRGPUMP gate (silfid lane 2026-10-07; PUBLOG capture #2's seat).

The REAL emitted driver (IR from tools/nmi126/capture_ir.py under the cvcp2 flag snapshot + overlays) runs under py65 in
tests/test_gravity_fidelity.py's ROM-rule P2 world (two hooks per frame, the copro mailbox answered, P1 garbage released
at P2's checkAttack). Checks, per arm:
  HOLD   after every hook in play: GRAV_P1 ($0312) == 0 and P1's pad ($F5) == 0 -- P1 never falls and never moves.
  PUMP   an exact REFERENCE MODEL of the pump (xorshift16 (7,9,8) on GP_L/GP_H, fire on states 1..T-1, size
         GP_SIZES[GP_N mod 32], pending store merged and capped at 4, delivered only into an EMPTY $0318 with colours
         GP_COLS[GP_C mod 64 ..+3]) is advanced every time the CPU executes `gp_pump`, from the RAM it reads there, and must predict
         EVERY driver store to $0318 / $0329-$032C (value and hook) and the telemetry GP_N / GP_C exactly.
         Every $0318 store must land on 0 (never overwrite a pending attack) with a size in 2..4, colours in 0..2.
         Round over (P2 virus count 0) -> no volley fires and nothing is delivered.
         `gp_pump` runs on BOTH hooks of every play frame (the rate formula assumes 2 per frame).
  RATE   fired volleys within 4 sigma of (T-1)/65535 per pump hook.
  DRAIN  (DRP1DRAIN arms) P2's outgoing attack $0398 is seeded non-zero before every hook and must read 0 after every
         play hook.
  NOPLAY (DRNAVESC_NOPLAY arms) the stuck-screen escape is primed to fire on the next hook: in a LIVE round (mode 4,
         P2 viruses != 0) the hook must NOT inject START; with P2's virus count 0 (a round-end wait) it MUST (positive
         control: the check can see an injection).
Arms: hold (DRP1HOLD alone: 0 pump stores), pump (T 27, the default), pump_t255 (fast, for statistics), c3 (PUBLOG
capture #3: the FAIR2PLUS P2 driver + hold-first + drain + escape guard + pump + PDW). Mutants M_* must be KILLED.
  test_gpump.py [--frames N] [--seed S] [--arm NAME]"""
import argparse, collections, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import test_gravity_fidelity as G
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

GP_L, GP_H, GP_S, GP_N, GP_C = 0x6630, 0x6631, 0x6632, 0x6633, 0x6635
ATK1, ATKC, VC, GRAV_P1 = 0x0318, 0x0329, 0x03A4, 0x0312
ARMS = {"hold": ({"DRPUBLOG": "1", "DRP1HOLD": "1"}, 0),
        "pump": ({"DRPUBLOG": "1", "DRP1HOLD": "1", "DRGPUMP": "1", "DRPUBLOG_PDW": "1"}, 27),   # = the capture cart
        "pump_t255": ({"DRPUBLOG": "1", "DRP1HOLD": "1", "DRGPUMP": "1", "DRGPUMP_T": "255"}, 255),
        # MUTANTS (must be KILLED): delivery into a pending slot; the hold without its gravity pin
        "M_overwrite": ({"DRPUBLOG": "1", "DRP1HOLD": "1", "DRGPUMP": "1", "DRGPUMP_T": "255", "DRGPUMP_MUT": "overwrite"}, 255),
        "M_nohold": ({"DRPUBLOG": "1", "DRP1HOLD": "1", "DRGPUMP": "1", "DRGPUMP_MUT": "nohold"}, 27)}
C3 = {"DRABORTSTALE": "1", "DRLGPRESTART": "1", "DRDISTROW": "2", "DRPUBLOG": "1", "DRPUBLOG_PDW": "1", "DRP1HOLD": "1",
      "DRGPUMP": "1", "DRP1DRAIN": "1", "DRNAVESC_NOPLAY": "1", "DRP1HOLDFIRST": "1"}
ARMS["c3"] = (C3, 27)
ARMS["M_nodrain"] = ({k: v for k, v in C3.items() if k != "DRP1DRAIN"}, 27)
ARMS["M_escplay"] = ({k: v for k, v in C3.items() if k != "DRNAVESC_NOPLAY"}, 27)
CHECKS = {"c3": {"drain", "noplay"}, "M_nodrain": {"drain"}, "M_escplay": {"noplay"}}
P2ATK, ESC_S0, ESC_CTL, INJ = 0x0398, 0x6180, 0x6183, 0x614B


def xs(lo, hi):
    """J. Metcalf's 16-bit xorshift (7,9,8), byte-exact with the emitted LSR/ROR/EOR sequence."""
    c = hi & 1
    a = ((c << 7) | (lo >> 1)) & 0xFF; c = lo & 1
    a ^= hi; hi = a
    a2 = ((c << 7) | (a >> 1)) & 0xFF
    a2 ^= lo; lo = a2
    a2 ^= hi; hi = a2
    return lo, hi


def _tables():
    """GP_SIZES / GP_COLS as written in patch_cartridge_copro.py (parsed, not imported: the patcher reads env at import)."""
    import ast, re
    src = open(os.path.join(os.path.dirname(HERE), "patch_cartridge_copro.py")).read()
    get = lambda n: ast.literal_eval(re.search(n + r" = (\([^)]*\))", src).group(1))
    return get("GP_SIZES"), get("GP_COLS")


class Ref:
    """Reference model of _emit_gpump, fed the RAM the CPU sees at gp_pump."""
    def __init__(self, T):
        self.T = T; self.fires = 0; self.cells = 0
        self.sizes, self.cols = _tables()
        assert len(self.sizes) == 32 and len(self.cols) == 64 and set(self.sizes) <= {2, 3, 4} and set(self.cols) <= {0, 1, 2}

    def run(self, m):
        """m: dict of the bytes at entry. Returns (expected stores [(addr, value)], new GP_L, GP_H, GP_S)."""
        st = []
        lo, hi, S = m["L"], m["H"], m["S"]
        if m["VC"] == 0:
            return st, lo, hi, S
        if lo == 0 and hi == 0:
            lo = 0xA5
        lo, hi = xs(lo, hi)
        if hi == 0 and lo < self.T:
            S = min(4, S + self.sizes[m["N"] & 0x1F]); self.fires += 1; m["N"] += 1
        if S:
            S = min(S, 4)
            if m["ATK"] == 0:
                for k in range(4):
                    st.append((ATKC + k, self.cols[((m["C"] & 0x3F) + k) % 64]))
                st.append((ATK1, S)); self.cells += S; S = 0
        return st, lo, hi, S


def run_arm(name, frames, seed):
    ov, T = ARMS[name]
    ir, snap = G.capture("experiments/silfid/cvcp2_flags.json", ov, "gpump_" + name)
    labels = ir["units"]["main"]["labels"]; mbase = ir["units"]["main"]["base"]
    gp_addr = mbase + labels["gp_pump"] if "gp_pump" in labels else None
    assert (gp_addr is not None) == (T > 0), f"gp_pump label presence {gp_addr} vs T {T}"
    base = G.fresh_mem(seed)
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    base[GP_L], base[GP_H] = 0xA5, 0x00                    # the cold-init state (do_init is not run by the harness)
    mem = ObservableMemory(subject=base)
    copro = G.Copro(random.Random(seed * 7919 + 1))
    mem.subscribe_to_read(range(0x5284, 0x5289), copro.read)
    mem.subscribe_to_write([0x5284], copro.on_go)
    hook_stores = []
    in_hook = [False]

    def on_w(addr, value):
        if in_hook[0]:
            hook_stores.append((addr, value, base[addr]))
    mem.subscribe_to_write([ATK1] + list(range(ATKC, ATKC + 4)), on_w)
    mpu = MPU(memory=mem)
    entry = mbase + labels["main"]
    world = G.World(random.Random(seed), base)
    ref = Ref(T)
    bad = []; cnt = collections.Counter()
    hold_bad = 0

    def hook():
        mpu.sp = 0xFD
        r = 0x3000 - 1
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry; base[0x3000] = 0xEA
        k = 0; pumps = 0; exp = []
        while mpu.pc != 0x3000:
            if mpu.pc == gp_addr:
                pumps += 1
                m = dict(L=base[GP_L], H=base[GP_H], S=base[GP_S], VC=base[VC], ATK=base[ATK1], N=base[GP_N], C=base[GP_C])
                st, lo, hi, S = ref.run(m)
                exp.append((st, lo, hi, S))
            mpu.step(); k += 1
            if k > 400000:
                raise RuntimeError(f"hook runaway pc=${mpu.pc:04X}")
        return pumps, exp

    vc_zero = range(frames // 2, frames // 2 + 400)       # a 'round over' stretch: P2's virus count reads 0
    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        base[VC] = 0 if f in vc_zero else 20
        play = base[G.MODE] == 4
        outs = []
        for hk in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0
            base[GRAV_P1] = 0x20                           # the ROM counts P1's gravity every frame: the pin must undo it
            base[P2ATK] = 7                                # P2's outgoing attack, never consumed by a held P1
            del hook_stores[:]
            in_hook[0] = True
            pumps, exp = hook()
            in_hook[0] = False
            outs.append(base[0xF6])
            if play and f not in vc_zero:
                cnt["play_hooks"] += 1
                cnt["pump_hooks"] += pumps
                if base[GRAV_P1] != 0 or base[0xF5] != 0:
                    hold_bad += 1
                if "drain" in CHECKS.get(name, ()) and base[P2ATK] != 0:
                    cnt["drain_violations"] += 1
            got = [(a, v) for a, v, old in hook_stores]
            want = [s for e in exp for s in e[0]]
            if got != want:
                bad.append(dict(frame=f, hook=hk, got=got, want=want))
            for a, v, old in hook_stores:
                if a == ATK1:
                    cnt["deliveries"] += 1
                    if old != 0 or not 2 <= v <= 4:
                        bad.append(dict(frame=f, overwrite_or_size=(old, v)))
                    if f in vc_zero:
                        cnt["delivered_while_round_over"] += 1
                elif v > 2:
                    bad.append(dict(frame=f, colour=v))
            if exp:
                _, lo, hi, S = exp[-1]
                if (base[GP_L], base[GP_H], base[GP_S]) != (lo, hi, S):
                    bad.append(dict(frame=f, hook=hk, state=(base[GP_L], base[GP_H], base[GP_S]), want=(lo, hi, S)))
        R = outs[0] & outs[1]                              # the ROM's two-pass read, as in the gravity gate
        pressed = R & (R ^ base[0xF8])
        base[0xF6] = pressed; base[0xF8] = R
        world.step(f, pressed, R)
    n_cart = base[GP_N] | (base[GP_N + 1] << 8); c_cart = base[GP_C] | (base[GP_C + 1] << 8)
    if "noplay" in CHECKS.get(name, ()):
        # prime the escape to fire on the next hook (counter at N-1, snapshot == the live tuple), in a live round and in a
        # round-end wait; ESC_N is the patcher's default 1200
        for vc, key in ((20, "esc_live"), (0, "esc_roundend")):
            base[G.MODE] = 4; base[VC] = vc
            base[ESC_S0], base[ESC_S0 + 1], base[ESC_S0 + 2] = base[0x46], base[0xF8], base[0x0386]
            base[ESC_CTL], base[ESC_CTL + 1] = 1199 & 0xFF, 1199 >> 8
            inj0 = base[INJ]; base[0xF5] = 0
            hook()
            cnt[key] = int(base[INJ] != inj0 or base[0xF5] == 0x10)
    res = dict(arm=name, T=T, frames=frames, seed=seed, mismatches=len(bad), first=bad[:3], hold_violations=hold_bad,
               fires_ref=ref.fires, fires_cart=n_cart, cells_ref=ref.cells, cells_cart=c_cart, **cnt)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--arm", action="append")
    a = ap.parse_args()
    ok = True
    for name in a.arm or list(ARMS):
        r = run_arm(name, a.frames, a.seed)
        T = r["T"]; ph = r.get("pump_hooks", 0); play = r.get("play_hooks", 0)
        why = []
        if r["mismatches"]:
            why.append(f"{r['mismatches']} reference mismatches e.g. {r['first']}")
        if r["hold_violations"]:
            why.append(f"P1 not held on {r['hold_violations']} play hooks")
        if T == 0:
            if r.get("deliveries", 0):
                why.append("hold-only arm delivered garbage")
        else:
            if ph != play:
                why.append(f"gp_pump ran on {ph} of {play} play hooks (the rate formula assumes every hook)")
            if (r["fires_ref"], r["cells_ref"]) != (r["fires_cart"], r["cells_cart"]):
                why.append(f"telemetry GP_N/GP_C {r['fires_cart']}/{r['cells_cart']} != ref {r['fires_ref']}/{r['cells_ref']}")
            p = (T - 1) / 65535.0; mu = p * ph; sd = math.sqrt(ph * p * (1 - p))
            if abs(r["fires_ref"] - mu) > 4 * sd + 1:
                why.append(f"rate: {r['fires_ref']} fires vs {mu:.1f} +- {sd:.1f}")
            if r.get("deliveries", 0) == 0:
                why.append("no volley delivered (vacuous)")
            if r.get("delivered_while_round_over", 0):
                why.append("delivered while P2's virus count was 0")
        if "drain" in CHECKS.get(name, ()) and r.get("drain_violations", 0):
            why.append(f"P2's attack $0398 not drained on {r['drain_violations']} play hooks")
        if "noplay" in CHECKS.get(name, ()):
            if r.get("esc_live", 0):
                why.append("the escape injected START in a LIVE round")
            if not r.get("esc_roundend", 0):
                why.append("positive control failed: no START injected in a round-end wait")
        good = not why
        if name.startswith("M_"):
            good = not good                                # a mutant must FAIL the gate
        ok &= good
        tag = ("KILLED" if good else "SURVIVED") if name.startswith("M_") else ("PASS" if good else "FAIL")
        print(f"{name:11s} T={T:3d} {tag}  play_hooks={play} pump_hooks={ph} fires={r['fires_ref']} "
              f"(cart GP_N {r['fires_cart']}) deliveries={r.get('deliveries', 0)} cells={r['cells_ref']} "
              f"(cart GP_C {r['cells_cart']}) hold_violations={r['hold_violations']}" + ("  <- " + "; ".join(why) if why else ""))
    print("GPUMP GATE: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
