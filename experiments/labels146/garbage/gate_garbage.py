"""gate_garbage.py — PREREG_GARBAGE §6 controls that run BEFORE the pilot
harvest (import-gate killed mutants, G-replay/M-stale on the bank, G-CRN,
G-pressure-live with a severed-injection arm).

M-mimic and M-shuffle need pilot labels and run in analyze_garbage.py; the
campaign is gated on ALL of them.

Exit 0 = every gate passed (each mutant FAILED as required).
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import garbcore as G
import labelcore as LC

OUT = os.path.join(HERE, "out")
VERDICTS = []


def check(name, ok, detail=""):
    VERDICTS.append((name, bool(ok), detail))
    print(f"[gate] {name}: {'PASS' if ok else 'FAIL'} {detail}", flush=True)
    return ok


def first_passing_state():
    for src in G.load_sources_A():
        try:
            st = G.read_state(src["path"])
            c, v, l = G.decode_planes(st["nes"])
            env = G.build_env(c, v, l, st["cur"], st["nxt"], 1234)
            return src, st, (c, v, l), env
        except G.ImportVoid:
            continue
    raise SystemExit("no stratum A state passes the import gates at all")


def mutant_kills(src, st):
    """§3 m1-m4 — each corruption MUST be rejected, with the right class.

    m1/m4 patch the RAW BLOB and go through read_state itself (the real gate
    path, not a reimplementation); m2/m3 corrupt the decoded planes/bytes fed
    to the real decode/build path.
    """
    ok = True
    blob = bytearray(open(src["path"], "rb").read())
    base = st["base"]
    tmp = os.path.join(OUT, ".mutant.ss")

    def read_patched(off, val):
        b = bytearray(blob)
        b[base + off] = val
        with open(tmp, "wb") as fh:
            fh.write(bytes(b))
        return G.read_state(tmp)

    def expect_void(name, cls, fn):
        nonlocal ok
        try:
            fn()
            check(name, False, "mutant SURVIVED — gate is vacuous")
            ok = False
        except G.ImportVoid as ex:
            ok &= check(name, ex.cls == cls, f"class={ex.cls} want={cls}")

    # m1 counter: blank one virus tile in the blob's board region
    def m1():
        i = next(i for i, b in enumerate(st["nes"]) if (b >> 4) == 0xD)
        read_patched(G.P2_BOARD + i, 0xFF)
    expect_void("m1_counter", "counter", m1)

    # m2 settle: lift the topmost occupied tile of some column one row up
    def m2():
        c, v, l = G.decode_planes(st["nes"])
        for cc in range(8):
            occ = np.nonzero(c[:, cc])[0]
            # need an UNLINKED cell (a lifted linked half would be a link void)
            if len(occ) and occ[0] >= 1 and l[occ[0], cc] is None \
                    and not v[occ[0], cc]:
                r = occ[0]
                c[r - 1, cc], c[r, cc] = c[r, cc], 0
                break
        else:
            raise AssertionError("no liftable tile")
        G.build_env(c, v, l, st["cur"], st["nxt"], 1234)
    expect_void("m2_settle", "settle", m2)

    # m3 links: a $6x with no $7x partner
    def m3():
        nes = list(st["nes"])
        i = next(i for i, b in enumerate(nes) if b == 0xFF)
        nes[i] = 0x60          # left half, partner cell stays empty
        G.decode_planes(nes)
    expect_void("m3_links", "links", m3)

    # m4 mode: blob's mode byte forced to 7, through read_state itself
    expect_void("m4_mode", "mode", lambda: read_patched(G.MODE, 7))
    # m5 pills: cur byte forced out of range (0..2), through read_state
    expect_void("m5_pills", "pills", lambda: read_patched(G.P2_CUR_A, 9))
    if os.path.exists(tmp):
        os.remove(tmp)
    return ok


def g_replay_mstale():
    """G-replay on 2 banked topout seeds + M-stale liveness on the first."""
    C, bmodel = LC.init_rig()
    games = LC.bank_games()
    tops = [g for g in games if g["res"] == "topout" and g["n_plies"] >= 60]
    ok = True
    done = []
    for g in tops[:2]:
        seed = g["seed"]
        rows, game = LC.load_bank_game(seed)
        gen = LC.replay_game(seed, C, bmodel, rows)
        try:
            while True:
                next(gen)
        except StopIteration as stop:
            res = stop.value
        ok &= check(f"G-replay_{seed}", res == game["res"],
                    f"res={res} want={game['res']}")
        done.append(seed)
    seed = done[0]
    rows, _ = LC.load_bank_game(seed)
    try:
        gen = LC.replay_game(seed, C, bmodel, rows, mutate_skip_ply=5)
        while True:
            next(gen)
        ok &= check("M-stale", False, "skipped action NOT caught")
    except LC.ReplayMismatch:
        ok &= check("M-stale", True, "gate aborted as required")
    except StopIteration:
        ok &= check("M-stale", False, "replay ran to completion")
    return ok, done


def g_crn(env, skey):
    """Labeling twice => byte-equal rows (determinism + CRN)."""
    C, bmodel = LC.init_rig()
    a = G.label_import_state(copy.deepcopy(env), C, bmodel, skey)
    b = G.label_import_state(copy.deepcopy(env), C, bmodel, skey)
    return check("G-CRN", json.dumps(a) == json.dumps(b),
                 f"cands={len(a)}")


def g_pressure_live():
    """Injection fires in forks AND severing it moves survival somewhere."""
    import bursty_model as BM
    C, bmodel = LC.init_rig()
    srcs, used, inj_counts, means = G.load_sources_A(), [], [], []
    real_inject = BM.inject_bursty_garbage
    for src in srcs:
        if len(used) == 3:
            break
        try:
            st = G.read_state(src["path"])
            c, v, l = G.decode_planes(st["nes"])
        except G.ImportVoid:
            continue
        skey = G.source_key("A", src["seed"], src["pre_idx"])
        env = G.build_env(c, v, l, st["cur"], st["nxt"], skey & 0xFFFF)
        n = {"inj": 0}

        def counting(board, model, seed, pills, clear_size):
            n["inj"] += 1
            return real_inject(board, model, seed, pills, clear_size)

        BM.inject_bursty_garbage = counting
        try:
            ents_inj = G.label_import_state(copy.deepcopy(env), C, bmodel, skey)
        finally:
            BM.inject_bursty_garbage = real_inject

        BM.inject_bursty_garbage = lambda *a, **k: None   # severed arm
        try:
            ents_sev = G.label_import_state(copy.deepcopy(env), C, bmodel, skey)
        finally:
            BM.inject_bursty_garbage = real_inject
        m_inj = float(np.mean([sum(e["surv"]) for e in ents_inj]))
        m_sev = float(np.mean([sum(e["surv"]) for e in ents_sev]))
        used.append(G.state_id(src))
        inj_counts.append(n["inj"])
        means.append((m_inj, m_sev))
        print(f"[gate]   {G.state_id(src)}: injections={n['inj']} "
              f"mean_surv inj={m_inj:.2f} sev={m_sev:.2f}", flush=True)
    ok = check("G-pressure-live_fired", sum(inj_counts) > 0,
               f"injections={inj_counts}")
    moved = any(abs(a - b) > 1e-9 for a, b in means)
    sane = all(b >= a - 1e-9 for a, b in means)
    ok &= check("G-pressure-live_binding", moved,
                f"means={[(round(a,2), round(b,2)) for a, b in means]}")
    ok &= check("G-pressure-live_direction", sane,
                "severed >= injected everywhere" if sane else
                "severing DECREASED survival somewhere — instrument suspect")
    return ok


def main():
    os.makedirs(OUT, exist_ok=True)
    src, st, planes, env = first_passing_state()
    print(f"[gate] reference state: {G.state_id(src)}", flush=True)
    ok = True
    ok &= mutant_kills(src, st)
    skey = G.source_key("A", src["seed"], src["pre_idx"])
    ok &= g_crn(env, skey)
    r_ok, seeds = g_replay_mstale()
    ok &= r_ok
    ok &= g_pressure_live()
    with open(os.path.join(OUT, "gate_garbage.json"), "w") as fh:
        json.dump({"verdicts": [(n, o, d) for n, o, d in VERDICTS],
                   "replay_seeds": seeds, "ref_state": G.state_id(src)},
                  fh, indent=1)
    print("GATE_GARBAGE", "PASS" if ok else "FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
