"""VS decide: winner-trunk depth-3 + opponent INTERACTION terms.

Constant-per-pill opponent stats cannot change argmax by themselves.
Terms multiply a candidate-varying quantity by a latched opponent fact.

k=0 (all knobs) is move-identical to pressure_rig._choose_base(winner, wt=0, ws=0).

v1 (kr, kt) gen0 crowned k=0 — virus-deficit alone did not beat the trunk.
v2 adds send-shaped attack, ahead-safe spawn, and clock urgency.
"""
from __future__ import annotations
import numpy as np

# Trunk is the VS-strong solitaire eval (63.8% vs holes80). Not holes80.
TRUNK = "winner"
KNOBS = ("k_race", "k_tempo", "k_atk", "k_safe", "k_time", "k_clock", "k_hold")
# lockstep vs_sim / pressure_rig_time; T_LAT is per-pill constant (no argmax).
T_LAT, FPR = 0.6, 0.35


def zeros():
    return {k: 0.0 for k in KNOBS}


def _behind(own_v, opp_v):
    return max(0, int(own_v) - int(opp_v)) / 48.0


def _ahead(own_v, opp_v):
    return max(0, int(opp_v) - int(own_v)) / 48.0


def _dt(col, var, cc):
    return T_LAT + FPR * _fall_rows(col, var, cc)


def _maxh(col):
    return max(_col_h(col, c) for c in range(8))


def _fall_rows(col, var, cc):
    cols = [cc] if var in (2, 3) else [cc, min(cc + 1, 7)]
    hmax = 0
    for tc in cols:
        filled = [r for r in range(16) if col[r * 8 + tc] != 0]
        h = 16 - min(filled) if filled else 0
        if h > hmax:
            hmax = h
    return max(0, 16 - hmax)


def _col_h(col, tc):
    filled = [r for r in range(16) if col[r * 8 + tc] != 0]
    return (16 - min(filled)) if filled else 0


def _spawn_h(col):
    return max(_col_h(col, 3), _col_h(col, 4))


def _send_halves(cells):
    """Match vs_sim send_rule='cells': fire at cells>=6, min(4, cells//3)."""
    c = int(cells)
    return min(4, c // 3) if c >= 6 else 0


def _urgency(ctx):
    """I have the move, so own_t <= opp_t. Slack is how long until they land.
    urgency=1 when clocks are tied (hurry); 0 when they still have ~5s of fall.
    """
    slack = max(0.0, float(ctx.get("opp_t", 0.0)) - float(ctx.get("own_t", 0.0))) / 5.0
    return max(0.0, 1.0 - slack)


def choose(col, vir, ca, cb, na, nb, w, fl, ctx,
           k_race=0.0, k_tempo=0.0, k_atk=0.0, k_safe=0.0, k_time=0.0,
           k_clock=0.0, k_hold=0.0, wt=0, ws=0):
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded
    behind = _behind(ctx.get("own_vleft", 0), ctx.get("opp_vleft", 0))
    ahead = _ahead(ctx.get("own_vleft", 0), ctx.get("opp_vleft", 0))
    opp_threat = min(1.0, float(ctx.get("opp_spawn_h", 0)) / 16.0)
    urgency = _urgency(ctx)
    live = (k_race or k_tempo or k_atk or k_safe or k_time or k_clock or k_hold)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a, best_c1 = None, None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, 0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if live:
                if behind:
                    val += k_race * nv * behind
                    val += k_tempo * (-_fall_rows(col, var, cc)) * behind
                if k_atk and opp_threat:
                    val += k_atk * _send_halves(cells) * opp_threat
                if k_safe and ahead:
                    val += k_safe * (-_spawn_h(c1)) * ahead
                if k_time and urgency:
                    val += k_time * (-_fall_rows(col, var, cc)) * urgency
                if k_clock:
                    val -= k_clock * _dt(col, var, cc)
                if k_hold:
                    val -= k_hold * max(0, _maxh(col) - _maxh(c1))
            if best_val is None or val > best_val:
                best_val, best_a, best_c1 = val, var * 8 + cc, c1.copy()
    return best_a, best_c1


class VsPolicy:
    """play_vs protocol: object with .decide(...) and name()."""

    def __init__(self, k_race=0.0, k_tempo=0.0, k_atk=0.0, k_safe=0.0,
                 k_time=0.0, k_clock=0.0, k_hold=0.0, trunk=TRUNK, **extra):
        if extra:
            raise TypeError(f"unknown VsPolicy kwargs {sorted(extra)}")
        self.k_race = float(k_race)
        self.k_tempo = float(k_tempo)
        self.k_atk = float(k_atk)
        self.k_safe = float(k_safe)
        self.k_time = float(k_time)
        self.k_clock = float(k_clock)
        self.k_hold = float(k_hold)
        self.trunk = trunk
        import fast_rtl_x as FX
        self.w, self.fl = FX.variant(trunk)

    def knobs(self):
        return {k: getattr(self, k) for k in KNOBS}

    def name(self):
        k = self.knobs()
        return (f"{self.trunk}|kr{k['k_race']:g}|kt{k['k_tempo']:g}"
                f"|ka{k['k_atk']:g}|ks{k['k_safe']:g}|ki{k['k_time']:g}"
                f"|kc{k['k_clock']:g}|kh{k['k_hold']:g}")

    def decide(self, col, vir, ca, cb, na, nb, ctx):
        a, _ = choose(col, vir, ca, cb, na, nb, self.w, self.fl, ctx,
                      k_race=self.k_race, k_tempo=self.k_tempo,
                      k_atk=self.k_atk, k_safe=self.k_safe, k_time=self.k_time,
                      k_clock=self.k_clock, k_hold=self.k_hold, wt=0, ws=0)
        return a


def identity_selfcheck(n=40, seed0=40134, level=11):
    """k=0 must pick the same action as _choose_base(winner), even with live latches."""
    import pressure_rig as PR
    import vs_sim
    import fast_rtl_x as FX
    PR._init(level, 0, 0)
    w, fl = FX.variant(TRUNK)
    mismatches = 0
    pills = 0
    pol = VsPolicy()
    for i in range(n):
        seed = seed0 + i * 2
        env = vs_sim._mk_env(level, seed)
        from fb import FB
        import root_search as RS
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a0, _ = PR._choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                                int(env.nxt.a), int(env.nxt.b), w, fl, 0, 0)
        ctxs = [
            {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0,
             "opp_spawn_h": 0, "own_spawn_h": 0},
            {"own_vleft": 20, "opp_vleft": 5, "own_t": 12.0, "opp_t": 8.0,
             "opp_spawn_h": 16, "own_spawn_h": 10},
            {"own_vleft": 5, "opp_vleft": 20, "own_t": 8.0, "opp_t": 12.0,
             "opp_spawn_h": 14, "own_spawn_h": 4},
        ]
        for ctx in ctxs:
            a = pol.decide(col, vir, int(env.cur.a), int(env.cur.b),
                           int(env.nxt.a), int(env.nxt.b), ctx)
            pills += 1
            if a != a0:
                mismatches += 1
    return mismatches, pills


def scale_selfcheck(n_games=6, seed0=41134, level=11):
    """Count argmax moves vs k=0 on live-latch pills during real VS games."""
    import pressure_rig as PR
    import vs_sim
    PR._init(level, 0, 0)
    mutants = [
        ("ka200", dict(k_atk=200)),
        ("ka800", dict(k_atk=800)),
        ("ks200", dict(k_safe=200)),
        ("ks800", dict(k_safe=800)),
        ("ki80", dict(k_time=80)),
        ("ki200", dict(k_time=200)),
    ]
    base = VsPolicy()
    pols = {name: VsPolicy(**kw) for name, kw in mutants}

    class Probe:
        def __init__(self):
            self.stats = {name: {"moved": 0, "live": 0, "pills": 0} for name, _ in mutants}

        def name(self):
            return "probe"

        def decide(self, col, vir, ca, cb, na, nb, ctx):
            a0 = base.decide(col, vir, ca, cb, na, nb, ctx)
            behind = _behind(ctx.get("own_vleft", 0), ctx.get("opp_vleft", 0))
            ahead = _ahead(ctx.get("own_vleft", 0), ctx.get("opp_vleft", 0))
            threat = float(ctx.get("opp_spawn_h", 0)) > 0
            urg = _urgency(ctx) > 0
            live_of = {
                "ka200": threat, "ka800": threat,
                "ks200": ahead > 0, "ks800": ahead > 0,
                "ki80": urg, "ki200": urg,
            }
            for name, _kw in mutants:
                st = self.stats[name]
                st["pills"] += 1
                if live_of[name]:
                    st["live"] += 1
                    a = pols[name].decide(col, vir, ca, cb, na, nb, ctx)
                    if a != a0:
                        st["moved"] += 1
            return a0

    probe = Probe()
    for i in range(n_games):
        vs_sim.play_vs(seed0 + i * 2, level, probe, None, probe, None,
                       wt=0, ws=0, send_rule="cells")
    return probe.stats


def clock_scale_selfcheck(n_games=6, seed0=42134, level=11):
    """k_clock vs k=0: move rate overall and by board maxh. T_LAT cannot rerank;
    only FPR*fall_rows does, so empty-flat wells may not move."""
    import pressure_rig as PR
    import vs_sim
    PR._init(level, 0, 0)
    doses = (20.0, 40.0, 80.0, 160.0)
    base = VsPolicy()
    pols = {k: VsPolicy(k_clock=k) for k in doses}

    class Probe:
        def __init__(self):
            self.stats = {k: {"moved": 0, "pills": 0,
                              "empty": [0, 0], "mid": [0, 0], "tall": [0, 0]}
                          for k in doses}

        def name(self):
            return "clock-probe"

        def decide(self, col, vir, ca, cb, na, nb, ctx):
            a0 = base.decide(col, vir, ca, cb, na, nb, ctx)
            mh = _maxh(col)
            if mh <= 8:
                bucket = "empty"
            elif mh <= 12:
                bucket = "mid"
            else:
                bucket = "tall"
            for k, pol in pols.items():
                st = self.stats[k]
                st["pills"] += 1
                a = pol.decide(col, vir, ca, cb, na, nb, ctx)
                moved = int(a != a0)
                st["moved"] += moved
                st[bucket][0] += moved
                st[bucket][1] += 1
            return a0

    probe = Probe()
    for i in range(n_games):
        vs_sim.play_vs(seed0 + i * 2, level, probe, None, probe, None,
                       wt=0, ws=0, send_rule="cells")
    return probe.stats


if __name__ == "__main__":
    import import_pin
    import_pin.pin()
    import pressure_rig as PR
    PR._init(11, 0, 0)
    import sys
    m, p = identity_selfcheck()
    print(f"identity mismatches {m}/{p}", flush=True)
    if m:
        raise SystemExit("IDENTITY FAIL")
    print("IDENTITY_OK", flush=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "clock"
    if mode != "clock":
        raise SystemExit("usage: vs_choose.py [clock]")
    stats = clock_scale_selfcheck()
    any_dead = True
    ki80_class = []
    for k, st in stats.items():
        n = st["pills"] or 1
        rate = st["moved"] / n
        def br(name):
            mv, tot = st[name]
            return f"{mv}/{tot}" if tot else "0/0"
        print(f"clock kc{k:g}: moved {st['moved']}/{st['pills']} "
              f"({100*rate:.1f}%) empty {br('empty')} mid {br('mid')} "
              f"tall {br('tall')}", flush=True)
        if st["moved"] > 0:
            any_dead = False
        if rate >= 0.30:
            ki80_class.append(k)
    if any_dead:
        raise SystemExit("SCALE FAIL")
    if ki80_class:
        print(f"SCALE_WARN ki80-class doses (>=30%): {ki80_class}", flush=True)
    print("SCALE_OK", flush=True)
